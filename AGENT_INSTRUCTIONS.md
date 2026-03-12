# Chrome Control — Agent Instructions

Control the user's local Chrome browser using their real login session. This enables access to any page the user can access, including pages behind corporate authentication (SSO, MFA, security gateways).

Other browser automation tools (Playwright, Puppeteer, headless browsers) typically fail on corporate login systems due to automation fingerprint detection and cookie isolation. This approach bypasses those issues by operating on the user's actual Chrome instance.

## Platform Detection

Before executing any browser command, detect the platform:

```bash
uname -s
```

- Output `Darwin` → macOS → use **AppleScript approach**
- Output contains `MINGW`, `CYGWIN`, `MSYS` → Windows → use **CDP approach**

## Mandatory Preflight Rule

Before any read, click, navigation, fill, or JavaScript execution:

1. Detect the platform.
2. Run the platform-specific prerequisite check.
3. If the check fails, stop and tell the user exactly how to enable the missing prerequisite.
4. Only continue after the user confirms the setup is complete, or after the verification command succeeds.

---

## macOS: AppleScript Approach

### Prerequisite

The user must enable one Chrome setting (one-time only):

- English: Chrome menu → View → Developer → Allow JavaScript from Apple Events
- 中文: Chrome 菜单 → 查看 → 开发者 → 允许 Apple 事件中的 JavaScript

### macOS Preflight Check

Verify Chrome automation first:

```bash
osascript -e 'tell application "Google Chrome" to get name'
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.title"'
```

If the JavaScript command fails, do not continue. Tell the user to:

- Open Chrome
- Enable `View -> Developer -> Allow JavaScript from Apple Events`
- Approve any macOS automation permission prompt
- Retry the check

### Commands

**Get current tab URL:**
```bash
osascript -e 'tell application "Google Chrome" to return URL of active tab of front window'
```

**Get page title:**
```bash
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.title"'
```

**Get page text content:**
```bash
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.body.innerText"'
```

For long pages, paginate with substring:
```bash
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.body.innerText.substring(0, 15000)"'
```

For lazy-loaded or infinite-scroll pages, scroll the real page first, wait, then read again:
```bash
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "window.scrollBy(0, window.innerHeight); \"done\";"'
```

**Get page HTML:**
```bash
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.documentElement.outerHTML.substring(0, 10000)"'
```

**Navigate to URL:**
```bash
osascript -e 'tell application "Google Chrome" to set URL of active tab of front window to "https://example.com"'
```

**Click element by CSS selector:**
```bash
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.querySelector(\"#submit-btn\").click()"'
```

**Click element by text content:**
```bash
osascript -e '
tell application "Google Chrome"
    execute active tab of front window javascript "
        var items = document.querySelectorAll(\"li, a, button, span, div\");
        for (var i = 0; i < items.length; i++) {
            if (items[i].textContent.trim() === \"Target Text\" && items[i].children.length === 0) {
                items[i].click();
                break;
            }
        }
        \"done\";
    "
end tell'
```

**Click element by index:**
```bash
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.querySelectorAll(\"li\")[2].click(); \"done\";"'
```

**Fill a form field:**
```bash
osascript -e '
tell application "Google Chrome"
    execute active tab of front window javascript "
        var input = document.querySelector(\"input[name=search]\");
        input.value = \"search text\";
        input.dispatchEvent(new Event(\"input\", {bubbles: true}));
        \"done\";
    "
end tell'
```

**Execute arbitrary JavaScript:**
```bash
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "YOUR_JS_CODE_HERE"'
```

**List all open tabs:**
```bash
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

**Switch to specific tab:**
```bash
osascript -e 'tell application "Google Chrome" to set active tab index of front window to 3'
```

### macOS Troubleshooting

- **`missing value` returned**: JavaScript returned `undefined`/`null`. Make the JS expression explicitly return a string.
- **Escaped quotes**: Use `\"` for double quotes inside AppleScript JavaScript strings.
- **Multiple windows**: Commands target `front window` by default. Use `window 2`, `window 3` for others.
- **No screenshot support**: AppleScript cannot capture browser screenshots.

---

## Windows: Chrome CDP Approach

### Prerequisites

One-time setup:
```powershell
npm install -g agent-browser
agent-browser install
```

### Windows Preflight Check

Verify the tooling and CDP endpoint first:

```powershell
where agent-browser
Invoke-RestMethod -Uri "http://127.0.0.1:9222/json/version"
```

If either command fails, do not continue. Tell the user to:

- Install Node.js
- Run `npm install -g agent-browser`
- Run `agent-browser install`
- Fully close Chrome
- Restart Chrome with `--remote-debugging-port=9222`
- Retry the check

### Starting Chrome with debugging

Chrome must be fully closed before starting with the debugging flag. Use this PowerShell sequence:

```powershell
# Kill all Chrome processes
taskkill /F /IM chrome.exe 2>$null
timeout /t 3

# Start Chrome with debugging port
start chrome --remote-debugging-port=9222 --no-first-run

# Verify (after a few seconds)
Invoke-RestMethod -Uri "http://127.0.0.1:9222/json/version"
```

The user then logs into the target page in the Chrome window that opens.

### Commands

```bash
# Page content
agent-browser --cdp 9222 get text          # Get page text
agent-browser --cdp 9222 get url           # Get current URL
agent-browser --cdp 9222 get title         # Get page title
agent-browser --cdp 9222 snapshot          # Accessibility tree (best for understanding page structure)
agent-browser --cdp 9222 snapshot -i       # Interactive elements only (with @ref labels)

# Navigation
agent-browser --cdp 9222 open "https://example.com"   # Navigate to URL

# Interaction
agent-browser --cdp 9222 click @e3         # Click by ref from snapshot
agent-browser --cdp 9222 click "#submit"   # Click by CSS selector
agent-browser --cdp 9222 fill @e1 "text"   # Fill form field

# Capture
agent-browser --cdp 9222 screenshot /tmp/page.png        # Screenshot
agent-browser --cdp 9222 screenshot --full /tmp/full.png  # Full-page screenshot
agent-browser --cdp 9222 pdf /tmp/page.pdf                # Save as PDF

# JavaScript
agent-browser --cdp 9222 eval "document.title"   # Execute JavaScript
agent-browser --cdp 9222 eval "window.scrollBy(0, window.innerHeight); 'done'"   # Scroll down one viewport
agent-browser --cdp 9222 eval "window.scrollTo(0, document.body.scrollHeight); 'done'"   # Scroll to bottom

# Tabs
agent-browser --cdp 9222 tab list          # List open tabs
agent-browser --cdp 9222 tab 2             # Switch to tab 2
```

### Windows Troubleshooting

- **Port not binding**: Chrome was not fully closed. Kill all `chrome.exe` processes and retry.
- **Port conflict**: Use a different port (e.g., 9333) in both startup and `--cdp` flag.
- **Snapshot refs**: Use `snapshot -i` to see interactive elements with `@e1`, `@e2` labels for click/fill commands.

---

## Common Workflow

1. **Detect platform**.
2. **Run the platform preflight check**.
3. **If preflight fails, stop and guide the user through setup**.
4. **Ask the user** to open the target URL in Chrome and log in normally.
5. **Confirm the page is loaded**:
   - macOS: `osascript -e 'tell application "Google Chrome" to return URL of active tab of front window'`
   - Windows: `agent-browser --cdp 9222 get url`
6. **If the page is long, lazy-loaded, or infinite-scroll, scroll the real page first**:
   - Scroll one viewport at a time.
   - Wait 1-2 seconds after each scroll.
   - Read again after new content appears.
   - Prefer scrolling over alternate fetch methods when the goal is to read more of the current page.
7. **Extract content**:
   - macOS: `osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.body.innerText.substring(0, 15000)"'`
   - Windows: `agent-browser --cdp 9222 get text`
8. **Interact** (click, navigate, fill) using platform-specific commands.
9. **Wait after navigation or scroll**: SPA pages and lazy-loaded pages need 1-3 seconds before content updates. Use `sleep 2` between scrolling/navigation and reading.

## Limitations

- Cannot log in on behalf of the user — user must authenticate in Chrome first.
- Long content on lazy-loaded pages should be loaded by scrolling the real page first. Use `.substring(start, end)` on macOS or `--max-output` on Windows only to paginate output after the content is present in the page.
- SPA pages require a wait after navigation before reading updated content.
- macOS: no screenshots; Chrome must be in foreground.
- Windows: Chrome must be restarted with `--remote-debugging-port` flag; requires Node.js.
- Security: commands execute JavaScript in the user's authenticated session. Never run untrusted scripts.
