# Browser Control — Universal Agent Instructions

Control the user's real Chrome browser with full login session inheritance. Multi-channel web access with three-layer safety.

## Mode Routing (Claude Code: `/browse` command)

```
/browse <instruction>       → auto-detect foreground vs background
/browse here <instruction>  → foreground (AppleScript, user's current page)
/browse bg <instruction>    → background (CDP Proxy, no user disruption)
```

**Foreground** = operate on what user is looking at. **Background** = agent creates own tabs, user unaffected.
On macOS, default is foreground. On Linux/Windows, always background. If foreground fails (isTrusted, upload, keyboard), auto-escalate to CDP.

## Multi-Channel Tool Selection

| Scenario | Tool |
|----------|------|
| Search snippets, discover sources | **WebSearch** |
| Known URL, extract info | **WebFetch** |
| Known URL, raw HTML | **curl** |
| Convert page to Markdown (save tokens) | **Jina** (`r.jina.ai/example.com`) |
| Dynamic content, anti-scraping, login-required | **CDP Browser** |

Escalate from lightest to heaviest. CDP is the fallback when lighter tools fail.

## Platform Detection

```bash
uname -s  # Darwin = macOS, Linux = Linux, MINGW*/CYGWIN* = Windows
```

## Preflight

**macOS**: `osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.title"'`
**All platforms CDP**: `bash "${SKILL_DIR}/scripts/check-deps.sh"`

## Core Commands

### macOS AppleScript

```bash
# Read page text
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.body.innerText.substring(0, 15000)"'

# Navigate (always new tab)
osascript -e 'tell application "Google Chrome" to tell front window to make new tab with properties {URL:"https://example.com"}'

# Click by selector
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.querySelector(\"#btn\").click()"'

# Fill form field
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "var el=document.querySelector(\"input[name=q]\"); el.value=\"text\"; el.dispatchEvent(new Event(\"input\",{bubbles:true})); \"done\";"'
```

### CDP Proxy (All Platforms)

```bash
curl -s "http://localhost:3456/new?url=https://example.com"  # New tab
curl -s -X POST "http://localhost:3456/eval?target=ID" -d 'document.title'  # Eval JS
curl -s -X POST "http://localhost:3456/click?target=ID" -d 'button.submit'  # Click
curl -s "http://localhost:3456/scroll?target=ID&direction=bottom"  # Scroll
curl -s "http://localhost:3456/screenshot?target=ID&file=/tmp/shot.png"  # Screenshot
curl -s "http://localhost:3456/close?target=ID"  # Close tab
```

### CDP Helper (Advanced Write Operations)

```bash
python3 "${SKILL_DIR}/scripts/cdp-helper.py" type "text"       # Type into focused element
python3 "${SKILL_DIR}/scripts/cdp-helper.py" key Enter          # Press key
python3 "${SKILL_DIR}/scripts/cdp-helper.py" upload "input[type=file]" /path/to/file
python3 "${SKILL_DIR}/scripts/cdp-helper.py" select "#dropdown" "value"
python3 "${SKILL_DIR}/scripts/cdp-helper.py" click <x> <y>     # Trusted mouse click
python3 "${SKILL_DIR}/scripts/cdp-helper.py" hover <x> <y>     # Hover trigger
```

## Safety Rules (Mandatory)

**Domain blacklist** (read-only on these): banking (chase, wellsfargo, etc.), payments (paypal, stripe, etc.), auth (accounts.google.com, okta, etc.), cloud consoles (AWS, GCP, Azure), chrome:// pages.

**Element protection**: Never fill password fields. Never click payment buttons (pay, purchase, buy, checkout, 付款, 支付, 购买).

**Operation confirmation**: Confirm with user before submit/send/post/delete on unfamiliar pages.

## Omni Search Integration (Optional)

Browser Control can be paired with [omni-search-skill](https://github.com/d-wwei/omni-search-skill) for enhanced public web search and content fetching. This is a separate, optional companion — Browser Control works fully without it.

### Check availability

```bash
OMNI_SEARCH_DIR="${OMNI_SEARCH_DIR:-$(find ~ -maxdepth 4 -type d -name 'omni-search-skill' 2>/dev/null | head -1)}"
[ -n "$OMNI_SEARCH_DIR" ] && [ -f "$OMNI_SEARCH_DIR/scripts/omni_search.py" ] && echo "available" || echo "not installed"
```

If not installed, suggest once: `git clone https://github.com/d-wwei/omni-search-skill.git && cd omni-search-skill && python3 -m pip install -r requirements.txt`

### When to use omni-search vs multi-channel tools vs CDP

| Task | Tool |
|---|---|
| Quick search snippets | **WebSearch** (built-in) |
| Deep multi-engine search | `python3 <OMNI_SEARCH_DIR>/scripts/omni_search.py search "<query>"` |
| Fetch public URL as Markdown | `python3 <OMNI_SEARCH_DIR>/scripts/omni_search.py fetch "<url>"` |
| Search + auto-fetch top results | `python3 <OMNI_SEARCH_DIR>/scripts/omni_search.py resolve "<query>"` |
| Crawl documentation site | `python3 <OMNI_SEARCH_DIR>/scripts/omni_search.py crawl "<url>"` |
| Login-required / dynamic page | **CDP Browser** (this document) |
| Search → then access authenticated result | omni-search `search` → CDP navigate + read |

### Fallback

If omni-search-skill is not installed, use the built-in multi-channel tools (WebSearch → WebFetch → Jina → curl → CDP). Do not block the user's workflow.

## Behavior Rules

1. **Never navigate in user's existing tabs** — always open new tabs
2. **One action at a time** — execute, observe result, then decide next
3. **Smart wait** — use MutationObserver wait, not blind sleep
4. **Don't re-read after read-only actions** — only re-read after state changes
5. **Safety check before interacting with unfamiliar pages**
6. **Close your own tabs when done** — keep user's environment clean
7. **Escalate progressively** — AppleScript → CDP Proxy → CDP Helper

## Full Reference

For complete documentation including DOM-to-Markdown converter, interactive element indexer, virtual scroll crawler, console/network interception, annotated screenshots, sub-agent dispatch, and site experience memory, see `skills/browser-control/SKILL.md`.
