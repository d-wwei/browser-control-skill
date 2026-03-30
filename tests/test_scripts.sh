#!/usr/bin/env bash
# Tests for browser-control shell scripts
# Run: bash tests/test_scripts.sh
# No Chrome or Node.js runtime required — external deps are mocked.

set -euo pipefail

PASS=0
FAIL=0
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MATCH_SCRIPT="$SCRIPT_DIR/skills/browser-control/scripts/match-site.sh"
CHECK_SCRIPT="$SCRIPT_DIR/skills/browser-control/scripts/check-deps.sh"

# --- Test helpers ---

assert_eq() {
  local label="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    echo "  PASS: $label"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $label"
    echo "    expected: $(printf '%q' "$expected")"
    echo "    actual:   $(printf '%q' "$actual")"
    FAIL=$((FAIL + 1))
  fi
}

assert_contains() {
  local label="$1" needle="$2" haystack="$3"
  if echo "$haystack" | grep -qF "$needle"; then
    echo "  PASS: $label"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $label"
    echo "    expected to contain: $needle"
    echo "    actual output: $haystack"
    FAIL=$((FAIL + 1))
  fi
}

assert_empty() {
  local label="$1" actual="$2"
  if [ -z "$actual" ]; then
    echo "  PASS: $label"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $label"
    echo "    expected empty, got: $actual"
    FAIL=$((FAIL + 1))
  fi
}

assert_not_empty() {
  local label="$1" actual="$2"
  if [ -n "$actual" ]; then
    echo "  PASS: $label"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $label"
    echo "    expected non-empty output"
    FAIL=$((FAIL + 1))
  fi
}

assert_exit_code() {
  local label="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    echo "  PASS: $label"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $label"
    echo "    expected exit code: $expected"
    echo "    actual exit code:   $actual"
    FAIL=$((FAIL + 1))
  fi
}

# --- Setup temp environment for match-site.sh ---

TMPDIR_ROOT=$(mktemp -d)
# Replicate the directory structure match-site.sh expects:
#   scripts/match-site.sh looks for ../references/site-patterns relative to itself
# So we create: $TMPDIR_ROOT/scripts/match-site.sh (symlink) and $TMPDIR_ROOT/references/site-patterns/
mkdir -p "$TMPDIR_ROOT/scripts"
mkdir -p "$TMPDIR_ROOT/references/site-patterns"

# Create a wrapper script that sources match-site.sh logic but from our temp structure
# Instead of symlink (which would resolve DIR to original location), copy and work in-place
cp "$MATCH_SCRIPT" "$TMPDIR_ROOT/scripts/match-site.sh"
chmod +x "$TMPDIR_ROOT/scripts/match-site.sh"

MATCH="$TMPDIR_ROOT/scripts/match-site.sh"

# Create test site pattern files
cat > "$TMPDIR_ROOT/references/site-patterns/example.com.md" << 'SITEEOF'
---
domain: example.com
aliases: [示例网站, Example Site]
updated: 2026-03-29
---
## Platform Characteristics
This is the example.com experience guide.

### Key Notes
- Example is a reserved domain.
SITEEOF

cat > "$TMPDIR_ROOT/references/site-patterns/github.com.md" << 'SITEEOF'
---
domain: github.com
aliases: [GitHub, GH]
updated: 2026-03-29
---
## Platform Characteristics
GitHub is a code hosting platform.

### Key Notes
- Supports Git repositories.
SITEEOF

cat > "$TMPDIR_ROOT/references/site-patterns/google.com.md" << 'SITEEOF'
---
domain: google.com
aliases: [谷歌, Google Search]
updated: 2026-03-29
---
## Platform Characteristics
Google is a search engine.
SITEEOF

# ============================================================
echo "=== match-site.sh tests ==="
# ============================================================

# Test 1: Exact domain match
echo ""
echo "[Test 1] Exact domain match"
OUTPUT=$(bash "$MATCH" "I want to visit example.com")
assert_contains "finds example.com by domain" "站点经验: example.com" "$OUTPUT"
assert_contains "includes body content" "This is the example.com experience guide." "$OUTPUT"

# Test 2: Alias match (case-insensitive)
echo ""
echo "[Test 2] Alias match (case-insensitive)"
OUTPUT=$(bash "$MATCH" "打开示例网站")
assert_contains "matches Chinese alias" "站点经验: example.com" "$OUTPUT"

OUTPUT=$(bash "$MATCH" "open example site please")
assert_contains "matches English alias case-insensitively" "站点经验: example.com" "$OUTPUT"

OUTPUT=$(bash "$MATCH" "go to EXAMPLE SITE")
assert_contains "matches alias in uppercase" "站点经验: example.com" "$OUTPUT"

# Test 3: No match returns empty
echo ""
echo "[Test 3] No match returns empty"
OUTPUT=$(bash "$MATCH" "I want to visit nonexistent.org")
assert_empty "no match produces empty output" "$OUTPUT"

# Test 4: Empty input returns empty
echo ""
echo "[Test 4] Empty input returns empty"
OUTPUT=$(bash "$MATCH" "")
assert_empty "empty string produces empty output" "$OUTPUT"

# Also test with no argument at all
OUTPUT=$(bash "$MATCH" 2>/dev/null || true)
assert_empty "no argument produces empty output" "$OUTPUT"

# Test 5: Multiple matches
echo ""
echo "[Test 5] Multiple matches in single input"
OUTPUT=$(bash "$MATCH" "compare github.com and google.com features")
assert_contains "matches github.com" "站点经验: github.com" "$OUTPUT"
assert_contains "matches google.com" "站点经验: google.com" "$OUTPUT"

# Test 6: Alias match for second site
echo ""
echo "[Test 6] Alias-based match for other sites"
OUTPUT=$(bash "$MATCH" "search on 谷歌")
assert_contains "matches Google via Chinese alias" "站点经验: google.com" "$OUTPUT"

OUTPUT=$(bash "$MATCH" "push code to GH")
assert_contains "matches GitHub via GH alias" "站点经验: github.com" "$OUTPUT"

# Test 7: Frontmatter is stripped from output
echo ""
echo "[Test 7] Frontmatter is stripped from output"
OUTPUT=$(bash "$MATCH" "visit example.com")
# The output should NOT contain the YAML frontmatter fields
if echo "$OUTPUT" | grep -q "^domain:"; then
  echo "  FAIL: frontmatter domain line leaked into output"
  FAIL=$((FAIL + 1))
else
  echo "  PASS: frontmatter domain line not in output"
  PASS=$((PASS + 1))
fi

if echo "$OUTPUT" | grep -q "^aliases:"; then
  echo "  FAIL: frontmatter aliases line leaked into output"
  FAIL=$((FAIL + 1))
else
  echo "  PASS: frontmatter aliases line not in output"
  PASS=$((PASS + 1))
fi

# Test 8: Missing site-patterns directory — should exit silently
echo ""
echo "[Test 8] Missing site-patterns directory exits silently"
EMPTY_TMPDIR=$(mktemp -d)
mkdir -p "$EMPTY_TMPDIR/scripts"
cp "$MATCH_SCRIPT" "$EMPTY_TMPDIR/scripts/match-site.sh"
# No references/site-patterns directory created
OUTPUT=$(bash "$EMPTY_TMPDIR/scripts/match-site.sh" "example.com" 2>/dev/null)
EXIT_CODE=$?
assert_eq "exits with code 0 when dir missing" "0" "$EXIT_CODE"
assert_empty "no output when dir missing" "$OUTPUT"
rm -rf "$EMPTY_TMPDIR"


# ============================================================
echo ""
echo "=== check-deps.sh tests ==="
# ============================================================

# Test 1: Script exits with error when node is not found
echo ""
echo "[Test 1] Missing node produces error exit"
# Use PATH manipulation to hide node
OUTPUT=$(PATH="/usr/bin:/bin" bash "$CHECK_SCRIPT" 2>&1 || true)
EXIT_CODE=$(PATH="/usr/bin:/bin" bash "$CHECK_SCRIPT" 2>&1; echo $?)
# Extract just the exit code (last line)
EXIT_CODE=$(echo "$EXIT_CODE" | tail -1)
# Re-run cleanly to get separate exit code
set +e
PATH="/usr/bin:/bin" bash "$CHECK_SCRIPT" > /dev/null 2>&1
ACTUAL_EXIT=$?
set -e
assert_eq "exit code is 1 when node missing" "1" "$ACTUAL_EXIT"

# Test 2: Error message mentions node
echo ""
echo "[Test 2] Error message format when node is missing"
OUTPUT=$(PATH="/usr/bin:/bin" bash "$CHECK_SCRIPT" 2>&1 || true)
assert_contains "message says node is missing" "node: missing" "$OUTPUT"
assert_contains "message includes install hint" "Node.js" "$OUTPUT"

# Test 3: Output format — when node IS available, first line should start with "node:"
echo ""
echo "[Test 3] Output format when node is available"
if command -v node &>/dev/null; then
  # Node is available in this environment; test the output prefix
  # We still expect the script to fail later (no Chrome), but the first line should be about node
  OUTPUT=$(bash "$CHECK_SCRIPT" 2>&1 || true)
  FIRST_LINE=$(echo "$OUTPUT" | head -1)
  if echo "$FIRST_LINE" | grep -q "^node:"; then
    echo "  PASS: first output line starts with 'node:'"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: first output line does not start with 'node:'"
    echo "    got: $FIRST_LINE"
    FAIL=$((FAIL + 1))
  fi

  # Check that it reports ok or warn
  if echo "$FIRST_LINE" | grep -qE "^node: (ok|warn)"; then
    echo "  PASS: node status is 'ok' or 'warn'"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: unexpected node status"
    echo "    got: $FIRST_LINE"
    FAIL=$((FAIL + 1))
  fi
else
  echo "  SKIP: node not available in test environment (2 tests skipped)"
fi

# Test 4: Script exits non-zero when Chrome is not connected (node available, no Chrome)
echo ""
echo "[Test 4] Exits non-zero when Chrome debug port unreachable"
if command -v node &>/dev/null; then
  set +e
  bash "$CHECK_SCRIPT" > /dev/null 2>&1
  ACTUAL_EXIT=$?
  set -e
  # Without Chrome running, script should fail (exit 1)
  if [ "$ACTUAL_EXIT" -ne 0 ]; then
    echo "  PASS: non-zero exit when Chrome not connected"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: expected non-zero exit, got 0"
    FAIL=$((FAIL + 1))
  fi
else
  echo "  SKIP: node not available (1 test skipped)"
fi


# ============================================================
# Cleanup
# ============================================================
rm -rf "$TMPDIR_ROOT"

# ============================================================
# Results
# ============================================================
echo ""
echo "========================================"
echo "Results: $PASS passed, $FAIL failed"
echo "========================================"
[ $FAIL -eq 0 ] || exit 1
