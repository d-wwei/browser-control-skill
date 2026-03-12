# Chrome Control

You have the ability to control the user's local Chrome browser to access authenticated web pages.

## Setup

Read `AGENT_INSTRUCTIONS.md` in the project root for full command reference.

## Quick Reference

### Platform detection
```bash
uname -s
# Darwin → macOS (use AppleScript)
# MINGW/CYGWIN/MSYS → Windows (use CDP)
```

Before any browser action, run the platform-specific preflight check. If it fails, stop and guide the user through setup before continuing.

### macOS — requires user to enable: Chrome → View → Developer → Allow JavaScript from Apple Events

Preflight:

```bash
osascript -e 'tell application "Google Chrome" to get name'
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.title"'
```

```bash
# Read page text
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.body.innerText.substring(0, 15000)"'

# Scroll one viewport down for lazy-loaded pages
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "window.scrollBy(0, window.innerHeight); \"done\";"'

# Get URL
osascript -e 'tell application "Google Chrome" to return URL of active tab of front window'

# Navigate
osascript -e 'tell application "Google Chrome" to set URL of active tab of front window to "URL_HERE"'

# Click by text
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "
    var items = document.querySelectorAll(\"li, a, button, span, div\");
    for (var i = 0; i < items.length; i++) {
        if (items[i].textContent.trim() === \"TARGET\" && items[i].children.length === 0) { items[i].click(); break; }
    }
    \"done\";"'

# Execute JS
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "JS_CODE_HERE"'
```

### Windows — requires: `npm install -g agent-browser && agent-browser install`

User must start Chrome with: `chrome.exe --remote-debugging-port=9222`

Preflight:

```powershell
where agent-browser
Invoke-RestMethod -Uri "http://127.0.0.1:9222/json/version"
```

```bash
agent-browser --cdp 9222 get text           # Read page
agent-browser --cdp 9222 eval "window.scrollBy(0, window.innerHeight); 'done'"   # Scroll one viewport down
agent-browser --cdp 9222 get url            # Get URL
agent-browser --cdp 9222 open "URL"         # Navigate
agent-browser --cdp 9222 snapshot -i        # List interactive elements
agent-browser --cdp 9222 click @e3          # Click element
agent-browser --cdp 9222 fill @e1 "text"    # Fill form
agent-browser --cdp 9222 screenshot out.png # Screenshot
```

## Rules

- Always detect platform first with `uname -s`.
- Always run the platform preflight check before reading, clicking, navigation, filling, or executing JavaScript.
- If preflight fails, stop and tell the user how to satisfy the missing prerequisite.
- Ask the user to log in before attempting to read authenticated pages.
- For lazy-loaded or infinite-scroll pages, scroll the real page first and read again after waiting 1-2 seconds.
- Prefer scrolling the live browser page over alternate fetch methods when trying to read more of the current page.
- Wait 2-3 seconds after clicking navigation elements or scrolling before reading content (SPA pages / lazy-loaded pages).
- For long pages, paginate with `.substring(0, 15000)` on macOS only after the content has been loaded into the page.
- Never run untrusted JavaScript in the user's browser session.
