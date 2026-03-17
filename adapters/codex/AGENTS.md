# Chrome Control

You have the ability to control the user's local Chrome browser to access authenticated web pages.

## Setup

This file contains all commands needed for browser control. Advanced techniques (JXA cross-window targeting, virtual scrolling crawlers) are available in `skills/chrome-control/SKILL.md` at the project root.

## Quick Reference

### Platform detection
```bash
uname -s
# Darwin → macOS (use AppleScript)
# MINGW/CYGWIN/MSYS → Windows (use CDP)
```

Before any browser action, run the platform-specific preflight check. If it fails, stop and guide the user through setup before continuing.

### Reasoning (before each action)

1. EVALUATE — did my last action succeed?
2. OBSERVE — read current page state
3. PLAN — what single action advances the goal?
4. ACT — execute one action, then re-evaluate

### Element Targeting

**macOS**: element index (inject indexing script, then `window.__interactiveElements[i]` — most reliable) → text match → CSS selector
**Windows**: @ref from `snapshot -i` (preferred) → CSS selector → eval JS

### macOS — requires user to enable: Chrome → View → Developer → Allow JavaScript from Apple Events

Preflight:

```bash
osascript -e 'tell application "Google Chrome" to get name'
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.title"'
```

```bash
# Get current URL
osascript -e 'tell application "Google Chrome" to return URL of active tab of front window'

# Get page text (paginate for long pages)
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.body.innerText.substring(0, 15000)"'

# Get page title
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.title"'

# Get page HTML (truncated)
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.documentElement.outerHTML.substring(0, 10000)"'

# Navigate
osascript -e 'tell application "Google Chrome" to set URL of active tab of front window to "URL_HERE"'

# Click by CSS selector
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.querySelector(\"SELECTOR\").click()"'

# Click by visible text
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "
    var items = document.querySelectorAll(\"li, a, button, span, div\");
    for (var i = 0; i < items.length; i++) {
        if (items[i].textContent.trim() === \"TARGET_TEXT\" && items[i].children.length === 0) { items[i].click(); break; }
    }
    \"done\";"'

# Fill form field
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "
    var input = document.querySelector(\"SELECTOR\");
    input.value = \"VALUE\";
    input.dispatchEvent(new Event(\"input\", {bubbles: true}));
    \"done\";"'

# Scroll down one viewport
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "window.scrollBy(0, window.innerHeight); \"done\";"'

# Execute JS
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "JS_CODE_HERE"'

# List all tabs
osascript <<'EOF'
tell application "Google Chrome"
    set allTabs to {}
    set i to 1
    repeat with w in windows
        set j to 1
        repeat with t in tabs of w
            set end of allTabs to ("w" & i & "-t" & j & ": " & URL of t)
            set j to j + 1
        end repeat
        set i to i + 1
    end repeat
    set AppleScript's text item delimiters to linefeed
    return allTabs as text
end tell
EOF
```

> The tab list spans all Chrome windows, but `set active tab index of front window` only switches tabs in the front window. For cross-window targeting, use JXA (`osascript -l JavaScript`).

### Windows — requires: `npm install -g agent-browser && agent-browser install`

User must start Chrome with: `chrome.exe --remote-debugging-port=9222`

Preflight:

```powershell
Get-Command agent-browser
Invoke-RestMethod -Uri "http://127.0.0.1:9222/json/version"
```

```bash
agent-browser --cdp 9222 get text           # Page text
agent-browser --cdp 9222 get url            # Current URL
agent-browser --cdp 9222 get title          # Page title
agent-browser --cdp 9222 open "URL"         # Navigate
agent-browser --cdp 9222 snapshot -i        # Interactive elements with @refs
agent-browser --cdp 9222 click @e3          # Click by ref
agent-browser --cdp 9222 click "#selector"  # Click by CSS
agent-browser --cdp 9222 fill @e1 "text"    # Fill form
agent-browser --cdp 9222 screenshot out.png # Screenshot
agent-browser --cdp 9222 eval "JS_CODE"     # Execute JS
agent-browser --cdp 9222 tab list           # List tabs
```

## Security (Mandatory)

These rules are **enforced** — refuse any operation that violates them.

**Sensitive site blacklist** — only read operations allowed (no click/fill/execute):
- Banking: chase, wellsfargo, bankofamerica, citi, capitalone, usbank, pnc, tdbank, hsbc, any `.bank` domain
- Payments: paypal, venmo, stripe, squareup, wise, revolut, robinhood, coinbase, binance
- Auth: `accounts.google.com`, `login.microsoftonline.com`, `login.live.com`, `icloud.com/account`, `*.okta.com`, `*.auth0.com`, `*.onelogin.com`
- Cloud consoles: `console.aws.amazon.com`, `console.cloud.google.com`, `portal.azure.com`
- Chrome internal: `chrome://`, `chrome-extension://`, `about:`

**Password fields** — never fill or click: `input[type="password"]`, inputs with name containing "password"/"passwd", or `autocomplete="current-password"`/`"new-password"`.

**Payment buttons** — never click buttons matching: pay, purchase, buy, checkout, place order, submit order, confirm payment, subscribe, upgrade, donate, 付款, 支付, 购买, 下单, 确认订单, 立即购买.

**Pre-action safety check** — before interacting with an unfamiliar page, verify the current URL against the blacklist above. Inject a JS check via `osascript` (macOS) or `agent-browser --cdp 9222 eval` (Windows) that tests `new URL(location.href).hostname` against the sensitive domain patterns and returns `{safe: true/false}`. If unsafe, switch to read-only mode.

## Rules

- Always detect platform with `uname -s` before running browser commands.
- Always run the platform preflight check before any browser action.
- If preflight fails, stop and tell the user how to fix the prerequisite.
- Ask the user to log in before attempting to read authenticated pages.
- **Smart wait after navigation**: prefer waiting for a specific target element to appear (e.g. inject a MutationObserver-based check), only fall back to `sleep 2` when you cannot determine a wait condition.
- **Scroll before clicking** if the target element might be off-screen.
- For lazy-loaded or infinite-scroll pages, scroll the real page first, wait for new content, then read again.
- Prefer scrolling the live browser page over alternate fetch methods.
- **One action at a time** — observe the result before proceeding to the next action.
- On Windows, use `snapshot -i` to get @ref labels before interacting with elements.
- For long pages, paginate with `.substring(0, 15000)` on macOS.
- If an action fails, re-read the page, try alternative targeting, and do NOT retry the same failed action more than twice.
- `missing value` from AppleScript means JS returned undefined — return a string explicitly.
