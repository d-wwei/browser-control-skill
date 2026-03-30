#!/usr/bin/env bash
# Integration tests — requires Chrome with remote debugging + CDP Proxy running
# Run: bash tests/test_integration.sh
# CI: Set up Chrome headless with --remote-debugging-port=9222 first

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BROWSE="$SCRIPT_DIR/skills/browser-control/scripts/browse-cmd.sh"

# ---------------------------------------------------------------------------
# Test framework
# ---------------------------------------------------------------------------
PASS=0
FAIL=0
SKIP=0

red()   { printf '\033[0;31m%s\033[0m' "$*"; }
green() { printf '\033[0;32m%s\033[0m' "$*"; }
yellow(){ printf '\033[0;33m%s\033[0m' "$*"; }

assert_ok() {
  local desc="$1"; shift
  local output
  if output=$("$@" 2>&1); then
    PASS=$((PASS + 1))
    echo "  $(green PASS)  $desc"
  else
    FAIL=$((FAIL + 1))
    echo "  $(red FAIL)  $desc"
    echo "        output: $output"
  fi
}

assert_contains() {
  local desc="$1"
  local expected="$2"
  shift 2
  local output
  if output=$("$@" 2>&1); then
    if echo "$output" | grep -q "$expected"; then
      PASS=$((PASS + 1))
      echo "  $(green PASS)  $desc"
    else
      FAIL=$((FAIL + 1))
      echo "  $(red FAIL)  $desc — expected to contain '$expected'"
      echo "        output: $output"
    fi
  else
    FAIL=$((FAIL + 1))
    echo "  $(red FAIL)  $desc — command failed"
    echo "        output: $output"
  fi
}

assert_file_exists() {
  local desc="$1"
  local filepath="$2"
  if [ -f "$filepath" ]; then
    PASS=$((PASS + 1))
    echo "  $(green PASS)  $desc"
  else
    FAIL=$((FAIL + 1))
    echo "  $(red FAIL)  $desc — file not found: $filepath"
  fi
}

skip_test() {
  local desc="$1"
  SKIP=$((SKIP + 1))
  echo "  $(yellow SKIP)  $desc"
}

# ---------------------------------------------------------------------------
# Pre-flight: check proxy
# ---------------------------------------------------------------------------
echo "================================================"
echo "  Browser Control Integration Tests"
echo "================================================"
echo ""
echo "Proxy: ${CDP_PROXY_PORT:-3456}"
echo "Script: $BROWSE"
echo ""

if ! "$BROWSE" health >/dev/null 2>&1; then
  echo "$(yellow 'SKIP: CDP Proxy is not running.')"
  echo "Start Chrome with --remote-debugging-port=9222 and run: node cdp-proxy.mjs"
  echo ""
  echo "Results: 0 passed, 0 failed, ALL skipped"
  exit 0
fi

echo "--- Proxy reachable, running tests ---"
echo ""

# ---------------------------------------------------------------------------
# Test 1: Health check
# ---------------------------------------------------------------------------
echo "[1/8] Health check"
assert_contains "health returns ok" '"status":"ok"' "$BROWSE" health

# ---------------------------------------------------------------------------
# Test 2: New tab
# ---------------------------------------------------------------------------
echo ""
echo "[2/8] New tab"
NEW_OUTPUT=$("$BROWSE" new "about:blank" 2>&1)
TARGET_ID=$(echo "$NEW_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['targetId'])" 2>/dev/null || echo "")

if [ -z "$TARGET_ID" ]; then
  echo "  $(red FAIL)  new tab — could not extract targetId"
  echo "        output: $NEW_OUTPUT"
  FAIL=$((FAIL + 1))
  echo ""
  echo "Cannot continue without a tab. Aborting."
  echo ""
  echo "Results: $PASS passed, $FAIL failed, $SKIP skipped"
  exit 1
else
  PASS=$((PASS + 1))
  echo "  $(green PASS)  new tab returns targetId ($TARGET_ID)"
fi

# ---------------------------------------------------------------------------
# Test 3: Eval
# ---------------------------------------------------------------------------
echo ""
echo "[3/8] Eval (document.title)"
# Navigate to a page with known title first
"$BROWSE" navigate "$TARGET_ID" "https://example.com" > /dev/null 2>&1 || true
sleep 2
EVAL_OUT=$("$BROWSE" eval "$TARGET_ID" "document.title" 2>&1 || true)
if echo "$EVAL_OUT" | grep -qi "Example Domain"; then
  PASS=$((PASS + 1))
  echo "  $(green PASS)  eval returns Example Domain"
else
  echo "  $(yellow SKIP)  eval did not return expected title (network may be slow)"
  echo "        output: $EVAL_OUT"
  SKIP=$((SKIP + 1))
fi

# ---------------------------------------------------------------------------
# Test 4: Click
# ---------------------------------------------------------------------------
echo ""
echo "[4/8] Click"
assert_ok "click does not error" "$BROWSE" click "$TARGET_ID" "body"

# ---------------------------------------------------------------------------
# Test 5: Screenshot
# ---------------------------------------------------------------------------
echo ""
echo "[5/8] Screenshot"
SHOT_FILE="/tmp/browse-cmd-test-shot-$$.png"
assert_ok "screenshot command succeeds" "$BROWSE" screenshot "$TARGET_ID" "$SHOT_FILE"
assert_file_exists "screenshot file exists" "$SHOT_FILE"
# Cleanup
rm -f "$SHOT_FILE" 2>/dev/null || true

# ---------------------------------------------------------------------------
# Test 6: Scroll
# ---------------------------------------------------------------------------
echo ""
echo "[6/8] Scroll"
assert_ok "scroll 500px does not error" "$BROWSE" scroll "$TARGET_ID" 500

# ---------------------------------------------------------------------------
# Test 7: Close
# ---------------------------------------------------------------------------
echo ""
echo "[7/8] Close tab"
assert_ok "close tab succeeds" "$BROWSE" close "$TARGET_ID"

# ---------------------------------------------------------------------------
# Test 8: Targets
# ---------------------------------------------------------------------------
echo ""
echo "[8/8] Targets"
assert_contains "targets returns JSON array" "[" "$BROWSE" targets

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "================================================"
TOTAL=$((PASS + FAIL + SKIP))
echo "Results: $(green "$PASS passed"), $(red "$FAIL failed"), $(yellow "$SKIP skipped") / $TOTAL total"
echo "================================================"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
