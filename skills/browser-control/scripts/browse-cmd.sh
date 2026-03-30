#!/usr/bin/env bash
# browse-cmd.sh — Unified browser control CLI
# Routes to CDP Proxy (curl) or CDP Helper (Python) automatically

set -euo pipefail

PROXY="http://localhost:${CDP_PROXY_PORT:-3456}"
HELPER_DIR="$(cd "$(dirname "$0")" && pwd)"
HELPER="python3 $HELPER_DIR/cdp-helper.py"

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
usage() {
  cat << 'EOF'
Usage: browse-cmd.sh <command> [args...]

Tab Management:
  new <url>                  Open new background tab, return targetId
  close <targetId>           Close a tab
  targets                    List all open tabs
  info <targetId>            Get tab info

Navigation:
  navigate <targetId> <url>  Navigate tab to URL
  back <targetId>            Go back

Read:
  eval <targetId> <js>       Execute JS in tab
  screenshot <targetId> <file>  Capture page screenshot

Interaction:
  click <targetId> <selector>     JS click (simple, fast)
  clickat <targetId> <selector>   CDP trusted mouse click (bypasses isTrusted)
  type <text>                     Type text into focused element (CDP)
  key <key> [modifier]            Press key (CDP)
  upload <targetId> <selector> <file...>  Upload file(s)
  select <selector> <value>       Set dropdown value (CDP)
  hover <x> <y>                   Hover at coordinates (CDP)
  scroll <targetId> <y|direction>  Scroll page

  wait <selector> [timeout_ms]    Wait for element (CDP)

Meta:
  health                     Check proxy health
  help                       Show this help
EOF
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
die() { echo "ERROR: $*" >&2; exit 1; }

# Check if proxy is reachable (silent, returns 0/1)
proxy_ok() {
  curl -sf --max-time 2 "$PROXY/health" >/dev/null 2>&1
}

# Require proxy to be running, or exit with helpful message
require_proxy() {
  if ! proxy_ok; then
    die "CDP Proxy is not running at $PROXY. Start it with: node cdp-proxy.mjs"
  fi
}

# Require at least N positional args (after command)
require_args() {
  local need="$1"; shift
  local cmd="$1"; shift
  if [ "$#" -lt "$need" ]; then
    die "Usage: browse-cmd.sh $cmd requires at least $need argument(s). Run 'browse-cmd.sh help'."
  fi
}

# URL-encode a string (portable, no jq needed)
urlencode() {
  python3 -c "import urllib.parse, sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "$1"
}

# ---------------------------------------------------------------------------
# Proxy-routed commands (curl)
# ---------------------------------------------------------------------------
cmd_health() {
  if proxy_ok; then
    curl -sf "$PROXY/health" 2>/dev/null
  else
    echo '{"status":"unreachable","proxy":"'"$PROXY"'"}'
    return 1
  fi
}

cmd_targets() {
  require_proxy
  curl -sf "$PROXY/targets"
}

cmd_new() {
  require_proxy
  local url="${1:-about:blank}"
  local enc_url; enc_url="$(urlencode "$url")"
  curl -sf "$PROXY/new?url=$enc_url"
}

cmd_close() {
  require_proxy
  local target="$1"
  curl -sf "$PROXY/close?target=$target"
}

cmd_info() {
  require_proxy
  local target="$1"
  curl -sf "$PROXY/info?target=$target"
}

cmd_navigate() {
  require_proxy
  local target="$1"
  local url="$2"
  local enc_url; enc_url="$(urlencode "$url")"
  curl -sf "$PROXY/navigate?target=$target&url=$enc_url"
}

cmd_back() {
  require_proxy
  local target="$1"
  curl -sf "$PROXY/back?target=$target"
}

cmd_eval() {
  require_proxy
  local target="$1"
  shift
  local js="$*"
  curl -sf -X POST "$PROXY/eval?target=$target" -d "$js"
}

cmd_click() {
  require_proxy
  local target="$1"
  local selector="$2"
  curl -sf -X POST "$PROXY/click?target=$target" -d "$selector"
}

cmd_clickat() {
  require_proxy
  local target="$1"
  local selector="$2"
  curl -sf -X POST "$PROXY/clickAt?target=$target" -d "$selector"
}

cmd_screenshot() {
  require_proxy
  local target="$1"
  local file="$2"
  local enc_file; enc_file="$(urlencode "$file")"
  curl -sf "$PROXY/screenshot?target=$target&file=$enc_file"
}

cmd_scroll() {
  require_proxy
  local target="$1"
  local arg="${2:-500}"
  # If arg is a number, treat as pixel offset; otherwise treat as direction keyword
  if [[ "$arg" =~ ^-?[0-9]+$ ]]; then
    curl -sf "$PROXY/scroll?target=$target&y=$arg"
  else
    curl -sf "$PROXY/scroll?target=$target&direction=$arg"
  fi
}

# ---------------------------------------------------------------------------
# Helper-routed commands (python3 cdp-helper.py)
# ---------------------------------------------------------------------------
cmd_type() {
  local text="$*"
  $HELPER type "$text"
}

cmd_key() {
  local key="$1"
  local mod="${2:-}"
  if [ -n "$mod" ]; then
    $HELPER key "$key" "$mod"
  else
    $HELPER key "$key"
  fi
}

cmd_select() {
  local selector="$1"
  local value="$2"
  $HELPER select "$selector" "$value"
}

cmd_hover() {
  local x="$1"
  local y="$2"
  $HELPER hover "$x" "$y"
}

cmd_wait() {
  local selector="$1"
  local timeout="${2:-5000}"
  $HELPER wait "$selector" "$timeout"
}

cmd_upload() {
  local target="$1"
  local selector="$2"
  shift 2
  local files=("$@")

  # Try proxy /setFiles first
  local json_files
  json_files=$(python3 -c "import json,sys; print(json.dumps(sys.argv[1:]))" "${files[@]}")
  local body="{\"selector\":$(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$selector"),\"files\":$json_files}"

  local result
  result=$(curl -sf -X POST "$PROXY/setFiles?target=$target" \
    -H "Content-Type: application/json" \
    -d "$body" 2>/dev/null) && {
    echo "$result"
    return 0
  }

  # Fallback to helper
  $HELPER upload "$selector" "${files[@]}"
}

# ---------------------------------------------------------------------------
# Main dispatch
# ---------------------------------------------------------------------------
if [ $# -eq 0 ]; then
  usage
  exit 1
fi

CMD="$(echo "$1" | tr '[:upper:]' '[:lower:]')"  # lowercase, portable
shift

case "$CMD" in
  # Meta
  health)
    cmd_health
    ;;
  help|--help|-h)
    usage
    ;;

  # Tab management (proxy)
  new)
    require_args 1 "new <url>" "$@"
    cmd_new "$1"
    ;;
  close)
    require_args 1 "close <targetId>" "$@"
    cmd_close "$1"
    ;;
  targets)
    cmd_targets
    ;;
  info)
    require_args 1 "info <targetId>" "$@"
    cmd_info "$1"
    ;;

  # Navigation (proxy)
  navigate)
    require_args 2 "navigate <targetId> <url>" "$@"
    cmd_navigate "$1" "$2"
    ;;
  back)
    require_args 1 "back <targetId>" "$@"
    cmd_back "$1"
    ;;

  # Read (proxy)
  eval)
    require_args 2 "eval <targetId> <js>" "$@"
    target="$1"; shift
    cmd_eval "$target" "$@"
    ;;
  screenshot)
    require_args 2 "screenshot <targetId> <file>" "$@"
    cmd_screenshot "$1" "$2"
    ;;

  # Interaction — proxy-routed
  click)
    require_args 2 "click <targetId> <selector>" "$@"
    cmd_click "$1" "$2"
    ;;
  clickat)
    require_args 2 "clickat <targetId> <selector>" "$@"
    cmd_clickat "$1" "$2"
    ;;
  scroll)
    require_args 1 "scroll <targetId> [y|direction]" "$@"
    target="$1"
    arg="${2:-500}"
    cmd_scroll "$target" "$arg"
    ;;

  # Interaction — helper-routed
  type)
    require_args 1 "type <text>" "$@"
    cmd_type "$@"
    ;;
  key)
    require_args 1 "key <key> [modifier]" "$@"
    cmd_key "$1" "${2:-}"
    ;;
  select)
    require_args 2 "select <selector> <value>" "$@"
    cmd_select "$1" "$2"
    ;;
  hover)
    require_args 2 "hover <x> <y>" "$@"
    cmd_hover "$1" "$2"
    ;;
  wait)
    require_args 1 "wait <selector> [timeout_ms]" "$@"
    cmd_wait "$1" "${2:-5000}"
    ;;

  # Upload — proxy first, fallback to helper
  upload)
    require_args 3 "upload <targetId> <selector> <file...>" "$@"
    cmd_upload "$@"
    ;;

  *)
    die "Unknown command: $CMD. Run 'browse-cmd.sh help' for usage."
    ;;
esac
