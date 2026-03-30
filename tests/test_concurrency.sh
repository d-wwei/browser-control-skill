#!/usr/bin/env bash
# =============================================================================
# Concurrency Pressure Test for Browser Control Skill
# =============================================================================
#
# Measures how many concurrent Chrome tabs the CDP Proxy can handle before
# performance degrades. Opens increasing numbers of tabs in parallel, runs
# eval (document.title) on each, and reports timing + memory metrics.
#
# Prerequisites:
#   1. Chrome running with --remote-debugging-port=9222
#   2. CDP Proxy running (node cdp-proxy.mjs) on port 3456 (or CDP_PROXY_PORT)
#
# Usage:
#   bash tests/test_concurrency.sh            # default rounds: 5,10,15,20,30
#   bash tests/test_concurrency.sh --max 15   # cap at 15 tabs max
#   bash tests/test_concurrency.sh --max 50   # push further
#
# Output: per-round timing breakdown + summary table with status ratings.
# =============================================================================

set -uo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BROWSE="$SCRIPT_DIR/skills/browser-control/scripts/browse-cmd.sh"
PROXY="http://localhost:${CDP_PROXY_PORT:-3456}"

MAX_TABS=30

# Parse --max flag
while [[ $# -gt 0 ]]; do
  case "$1" in
    --max)
      shift
      if [[ $# -eq 0 ]] || ! [[ "$1" =~ ^[0-9]+$ ]]; then
        echo "ERROR: --max requires a numeric argument" >&2
        exit 1
      fi
      MAX_TABS="$1"
      shift
      ;;
    -h|--help)
      head -24 "$0" | tail -20
      exit 0
      ;;
    *)
      echo "ERROR: Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

# Build round list: 5, 10, 15, 20, 30 — capped at MAX_TABS
BASE_ROUNDS=(5 10 15 20 30)
ROUNDS=()
for r in "${BASE_ROUNDS[@]}"; do
  if [[ "$r" -le "$MAX_TABS" ]]; then
    ROUNDS+=("$r")
  fi
done
# Ensure MAX_TABS itself is in the list if not already
LAST_ROUND="${ROUNDS[${#ROUNDS[@]}-1]:-0}"
if [[ "${#ROUNDS[@]}" -eq 0 ]] || [[ "$LAST_ROUND" -ne "$MAX_TABS" ]]; then
  ROUNDS+=("$MAX_TABS")
fi

# Lightweight URLs to cycle through (small pages, fast to load)
URLS=(
  "https://example.com"
  "https://httpbin.org/html"
  "https://jsonplaceholder.typicode.com"
)

# Temp directory for per-tab results
TMPDIR_TEST=$(mktemp -d /tmp/concurrency-test-XXXXXX)
trap 'rm -rf "$TMPDIR_TEST"' EXIT

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
red()    { printf '\033[0;31m%s\033[0m' "$*"; }
green()  { printf '\033[0;32m%s\033[0m' "$*"; }
yellow() { printf '\033[0;33m%s\033[0m' "$*"; }
cyan()   { printf '\033[0;36m%s\033[0m' "$*"; }

# Portable sub-second timestamp (seconds with 3 decimal places)
now_s() {
  python3 -c "import time; print(f'{time.time():.3f}')"
}

# Elapsed time between two timestamps
elapsed() {
  python3 -c "print(f'{$2 - $1:.3f}')"
}

# Get Chrome memory usage in MB
chrome_memory_mb() {
  ps aux 2>/dev/null | grep -i '[c]hrome' | awk '{sum += $6} END {if(NR>0) printf "%.0f", sum/1024; else print "0"}'
}

# Extract targetId from browse-cmd new output (JSON)
extract_target_id() {
  python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('targetId', ''))
except:
    print('')
"
}

# ---------------------------------------------------------------------------
# Pre-flight check
# ---------------------------------------------------------------------------
echo ""
echo "$(cyan '=== Concurrency Pressure Test ===')"
echo ""
echo "Proxy:   $PROXY"
echo "Script:  $BROWSE"
echo "Max:     $MAX_TABS tabs"
echo "Rounds:  ${ROUNDS[*]}"
echo ""

if ! curl -sf --max-time 3 "$PROXY/health" >/dev/null 2>&1; then
  echo "$(yellow 'SKIP: CDP Proxy is not running.')"
  echo "Start Chrome with --remote-debugging-port=9222 and run: node cdp-proxy.mjs"
  echo ""
  exit 0
fi

echo "$(green 'Proxy reachable.') Starting pressure test..."
echo ""

# ---------------------------------------------------------------------------
# Storage for summary table
# ---------------------------------------------------------------------------
declare -a SUMMARY_TABS=()
declare -a SUMMARY_OPEN=()
declare -a SUMMARY_EVAL=()
declare -a SUMMARY_MEM=()
declare -a SUMMARY_STATUS=()

# ---------------------------------------------------------------------------
# Run test rounds
# ---------------------------------------------------------------------------
ROUND_NUM=0
for TAB_COUNT in "${ROUNDS[@]}"; do
  ROUND_NUM=$((ROUND_NUM + 1))

  echo "$(cyan "Round $ROUND_NUM: $TAB_COUNT tabs")"

  # --- Phase 1: Open tabs concurrently ---
  TARGET_IDS=()
  OPEN_FAILURES=0

  T_OPEN_START=$(now_s)

  # Launch all tab-open requests in parallel, collect PIDs
  for i in $(seq 1 "$TAB_COUNT"); do
    url_idx=$(( (i - 1) % ${#URLS[@]} ))
    url="${URLS[$url_idx]}"
    result_file="$TMPDIR_TEST/open_${ROUND_NUM}_${i}.json"
    (
      output=$("$BROWSE" new "$url" 2>&1) || true
      echo "$output" > "$result_file"
    ) &
  done

  # Wait for all background open jobs
  wait

  T_OPEN_END=$(now_s)
  OPEN_TIME=$(elapsed "$T_OPEN_START" "$T_OPEN_END")

  # Collect target IDs
  for i in $(seq 1 "$TAB_COUNT"); do
    result_file="$TMPDIR_TEST/open_${ROUND_NUM}_${i}.json"
    if [[ -f "$result_file" ]]; then
      tid=$(cat "$result_file" | extract_target_id)
      if [[ -n "$tid" ]]; then
        TARGET_IDS+=("$tid")
      else
        OPEN_FAILURES=$((OPEN_FAILURES + 1))
      fi
    else
      OPEN_FAILURES=$((OPEN_FAILURES + 1))
    fi
  done

  OPENED=${#TARGET_IDS[@]}

  # Brief pause for pages to finish loading
  sleep 1

  # --- Phase 2: Eval document.title on each tab, measure response time ---
  EVAL_TIMES=()
  EVAL_FAILURES=0

  for i in "${!TARGET_IDS[@]}"; do
    tid="${TARGET_IDS[$i]}"
    eval_time_file="$TMPDIR_TEST/eval_${ROUND_NUM}_${i}.time"
    eval_result_file="$TMPDIR_TEST/eval_${ROUND_NUM}_${i}.result"
    (
      t_start=$(now_s)
      result=$("$BROWSE" eval "$tid" "document.title" 2>&1) || result="EVAL_ERROR"
      t_end=$(now_s)
      elapsed_val=$(elapsed "$t_start" "$t_end")
      echo "$elapsed_val" > "$eval_time_file"
      echo "$result" > "$eval_result_file"
    ) &
  done

  wait

  # Collect eval timings
  TOTAL_EVAL_TIME="0"
  EVAL_COUNT=0
  for i in "${!TARGET_IDS[@]}"; do
    eval_time_file="$TMPDIR_TEST/eval_${ROUND_NUM}_${i}.time"
    eval_result_file="$TMPDIR_TEST/eval_${ROUND_NUM}_${i}.result"
    if [[ -f "$eval_time_file" ]]; then
      et=$(cat "$eval_time_file")
      result=$(cat "$eval_result_file" 2>/dev/null || echo "")
      if [[ "$result" == "EVAL_ERROR" ]]; then
        EVAL_FAILURES=$((EVAL_FAILURES + 1))
      else
        EVAL_TIMES+=("$et")
        EVAL_COUNT=$((EVAL_COUNT + 1))
        TOTAL_EVAL_TIME=$(python3 -c "print(f'{$TOTAL_EVAL_TIME + $et:.3f}')")
      fi
    else
      EVAL_FAILURES=$((EVAL_FAILURES + 1))
    fi
  done

  # Compute average eval time
  if [[ "$EVAL_COUNT" -gt 0 ]]; then
    AVG_EVAL=$(python3 -c "print(f'{$TOTAL_EVAL_TIME / $EVAL_COUNT:.3f}')")
  else
    AVG_EVAL="0.000"
  fi

  # --- Phase 3: Chrome memory ---
  MEMORY=$(chrome_memory_mb)

  # --- Phase 4: Determine status ---
  STATUS="OK"
  AVG_EVAL_CMP=$(python3 -c "
v = $AVG_EVAL
if v > 3.0 or $OPEN_FAILURES > 0 or $EVAL_FAILURES > ($TAB_COUNT // 2):
    print('DEGRADED')
elif v > 1.0 or $EVAL_FAILURES > 0:
    print('SLOW')
else:
    print('OK')
")
  STATUS="$AVG_EVAL_CMP"

  # --- Phase 5: Close all tabs ---
  for tid in "${TARGET_IDS[@]}"; do
    "$BROWSE" close "$tid" >/dev/null 2>&1 &
  done
  wait

  # Brief pause between rounds to let Chrome stabilize
  sleep 1

  # --- Print round results ---
  STATUS_COLOR="$STATUS"
  case "$STATUS" in
    OK)       STATUS_COLOR="$(green OK)" ;;
    SLOW)     STATUS_COLOR="$(yellow SLOW)" ;;
    DEGRADED) STATUS_COLOR="$(red DEGRADED)" ;;
  esac

  echo "  Open time:     ${OPEN_TIME}s (${OPENED}/${TAB_COUNT} opened)"
  echo "  Avg eval time: ${AVG_EVAL}s (${EVAL_COUNT} succeeded, ${EVAL_FAILURES} failed)"
  echo "  Chrome memory: ${MEMORY} MB"
  echo "  Status:        ${STATUS_COLOR}"
  if [[ "$OPEN_FAILURES" -gt 0 ]]; then
    echo "  $(yellow "Warning: $OPEN_FAILURES tab(s) failed to open")"
  fi
  echo ""

  # Store for summary
  SUMMARY_TABS+=("$TAB_COUNT")
  SUMMARY_OPEN+=("$OPEN_TIME")
  SUMMARY_EVAL+=("$AVG_EVAL")
  SUMMARY_MEM+=("$MEMORY")
  SUMMARY_STATUS+=("$STATUS")

  # Clean up round temp files
  rm -f "$TMPDIR_TEST"/open_${ROUND_NUM}_*.json
  rm -f "$TMPDIR_TEST"/eval_${ROUND_NUM}_*.time
  rm -f "$TMPDIR_TEST"/eval_${ROUND_NUM}_*.result

done

# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------
echo "$(cyan '=== Summary ===')"
echo ""
printf "| %5s | %8s | %12s | %11s | %-8s |\n" "Tabs" "Open (s)" "Eval avg (s)" "Memory (MB)" "Status"
printf "|-------|----------|--------------|-------------|----------|\n"

for i in "${!SUMMARY_TABS[@]}"; do
  status="${SUMMARY_STATUS[$i]}"
  case "$status" in
    OK)       status_disp="$(green OK)      " ;;
    SLOW)     status_disp="$(yellow SLOW)    " ;;
    DEGRADED) status_disp="$(red DEGRADED)" ;;
    *)        status_disp="$status   " ;;
  esac
  printf "| %5s | %8s | %12s | %11s | %s |\n" \
    "${SUMMARY_TABS[$i]}" \
    "${SUMMARY_OPEN[$i]}" \
    "${SUMMARY_EVAL[$i]}" \
    "${SUMMARY_MEM[$i]}" \
    "$status_disp"
done

echo ""

# ---------------------------------------------------------------------------
# Exit code: fail if any round is DEGRADED
# ---------------------------------------------------------------------------
HAS_DEGRADED=0
for s in "${SUMMARY_STATUS[@]}"; do
  if [[ "$s" == "DEGRADED" ]]; then
    HAS_DEGRADED=1
    break
  fi
done

if [[ "$HAS_DEGRADED" -eq 1 ]]; then
  echo "$(red 'Result: DEGRADED — performance dropped under load.')"
  exit 1
else
  echo "$(green 'Result: All rounds within acceptable limits.')"
  exit 0
fi
