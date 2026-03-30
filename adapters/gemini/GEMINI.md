# Browser Control Skill — Gemini Adapter

> This skill provides browser control capabilities. Load the full reference from skills/browser-control/SKILL.md when needed.

Control the user's real Chrome browser with full login session inheritance. Multi-channel web access with three-layer safety.

## Mode Routing

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

**Element protection**: Never fill password fields. Never click payment buttons (pay, purchase, buy, checkout).

**Operation confirmation**: Confirm with user before submit/send/post/delete on unfamiliar pages.

## Behavior Rules

1. **Never navigate in user's existing tabs** — always open new tabs
2. **One action at a time** — execute, observe result, then decide next
3. **Smart wait** — use MutationObserver wait, not blind sleep
4. **Don't re-read after read-only actions** — only re-read after state changes
5. **Safety check before interacting with unfamiliar pages**
6. **Close your own tabs when done** — keep user's environment clean
7. **Escalate progressively** — AppleScript -> CDP Proxy -> CDP Helper

---

For full reference including DOM-to-Markdown, element indexer, screenshots, sub-agent dispatch, site experience: see skills/browser-control/SKILL.md
