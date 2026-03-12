---
name: chrome-control
description: "Control the user's Chrome browser via their real login session. Read page content, click elements, fill forms, execute JavaScript, and navigate — including pages behind corporate authentication. Auto-detects macOS or Windows."
argument-hint: "<url or action>"
---

# Chrome Control

Control the user's local Chrome browser using their real login session to access any page — including pages behind corporate authentication (SSO, MFA, security gateways).

## When to Use

- Access internal/authenticated web pages (e.g., company portals, OA systems, dashboards)
- Read content from pages that require login
- Automate repetitive browser interactions (clicking, form filling, navigation)
- Extract text, HTML, or structured data from web pages the user is already logged into

## Platform Detection

Before executing any command, detect the platform and use the corresponding approach:

```bash
uname -s
```

- **Darwin** → macOS → use AppleScript approach
- **MINGW* / CYGWIN* / MSYS* / Windows_NT** → Windows → use CDP approach
- You can also check: `[[ "$OSTYPE" == "darwin"* ]]` for macOS, or `[[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]` for Windows

## Required Preflight Check

Before reading, clicking, navigating, filling, or executing JavaScript, always verify that the platform-specific prerequisites are satisfied.

- If the prerequisite check is not done yet, do it first.
- If the prerequisite check fails, stop browser automation.
- Explain what is missing and guide the user through setup.
- Only continue after the user confirms setup is complete, or after a verification command succeeds.

---

# macOS Approach (AppleScript)

Uses macOS native AppleScript to communicate directly with the user's running Chrome. Zero dependencies.

## macOS Prerequisites

The user must enable one Chrome setting (one-time):

> **Chrome menu bar → View → Developer → Allow JavaScript from Apple Events**

Localized menu paths:
- English: View → Developer → Allow JavaScript from Apple Events
- 中文: 查看 → 开发者 → 允许 Apple 事件中的 JavaScript

## macOS Preflight

Run these checks before browser automation:

```bash
osascript -e 'tell application "Google Chrome" to get name'
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.title"'
```

Interpretation:

- If the first command fails, Chrome may not be running, or automation access to Chrome is blocked.
- If the second command fails, assume `Allow JavaScript from Apple Events` is not enabled yet, or macOS automation permissions are blocking access.
- In either case, stop and guide the user to fix the prerequisite before continuing.

## macOS Commands

### Get Current Tab URL

```bash
osascript -e '
tell application "Google Chrome"
    return URL of active tab of front window
end tell'
```

### Get Page Title

```bash
osascript -e '
tell application "Google Chrome"
    execute active tab of front window javascript "document.title"
end tell'
```

### Get Page Text Content

```bash
osascript -e '
tell application "Google Chrome"
    execute active tab of front window javascript "document.body.innerText"
end tell'
```

For long pages, use substring to avoid output limits:

```bash
osascript -e '
tell application "Google Chrome"
    execute active tab of front window javascript "document.body.innerText.substring(0, 15000)"
end tell'
```

### Get Page HTML

```bash
osascript -e '
tell application "Google Chrome"
    execute active tab of front window javascript "document.documentElement.outerHTML.substring(0, 10000)"
end tell'
```

### Navigate to a URL

```bash
osascript -e '
tell application "Google Chrome"
    set URL of active tab of front window to "https://example.com"
end tell'
```

### Click an Element

By CSS selector:

```bash
osascript -e '
tell application "Google Chrome"
    execute active tab of front window javascript "document.querySelector(\"#submit-btn\").click()"
end tell'
```

By text content:

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

By index:

```bash
osascript -e '
tell application "Google Chrome"
    execute active tab of front window javascript "document.querySelectorAll(\"li\")[2].click(); \"done\";"
end tell'
```

### Fill a Form Field

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

### Execute Arbitrary JavaScript

```bash
osascript -e '
tell application "Google Chrome"
    execute active tab of front window javascript "YOUR_JS_CODE_HERE"
end tell'
```

### List All Open Tabs

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

### Switch to a Specific Tab

```bash
osascript -e '
tell application "Google Chrome"
    set active tab index of front window to 3
end tell'
```

## macOS Tips

- **`missing value` returned**: The JavaScript returned `undefined` or `null`. Ensure the JS expression explicitly returns a string.
- **Escaped quotes**: Inside AppleScript's JavaScript strings, use `\"` for double quotes. For complex JS, use heredoc: `osascript <<'EOF' ... EOF`.
- **Multiple windows**: Commands target `front window` by default. Use `window 2`, `window 3` for other windows.

---

# Windows Approach (Chrome CDP)

Uses Chrome's built-in remote debugging protocol (CDP). Requires a helper script to manage Chrome lifecycle.

## Windows Prerequisites

### One-time setup

Install agent-browser (requires Node.js):

```powershell
npm install -g agent-browser
agent-browser install
```

Chrome must also be running with remote debugging enabled for the current session.

## Windows Preflight

Run these checks before browser automation:

```powershell
where agent-browser
Invoke-RestMethod -Uri "http://127.0.0.1:9222/json/version"
```

Interpretation:

- If `agent-browser` is not found, Node.js or `agent-browser` is not installed correctly.
- If the CDP endpoint check fails, Chrome is not running with `--remote-debugging-port=9222`.
- In either case, stop and guide the user to fix the prerequisite before continuing.

### Create helper script

Save the following as `chrome-debug.ps1` in a convenient location (e.g., `~\scripts\chrome-debug.ps1`):

```powershell
# chrome-debug.ps1 — Start Chrome with remote debugging enabled
param(
    [int]$Port = 9222,
    [string]$Url = "about:blank"
)

$chromePaths = @(
    "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)

$chromePath = $chromePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $chromePath) {
    Write-Error "Chrome not found. Please install Google Chrome."
    exit 1
}

# Kill existing Chrome processes
Write-Host "Closing existing Chrome instances..."
Get-Process "chrome" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

# Verify Chrome is fully closed
$remaining = Get-Process "chrome" -ErrorAction SilentlyContinue
if ($remaining) {
    Write-Host "Waiting for Chrome to fully close..."
    Start-Sleep -Seconds 3
    Get-Process "chrome" -ErrorAction SilentlyContinue | Stop-Process -Force
}

# Start Chrome with debugging port
Write-Host "Starting Chrome with debugging on port $Port..."
Start-Process $chromePath -ArgumentList "--remote-debugging-port=$Port", "--no-first-run", "--no-default-browser-check", $Url

# Wait and verify
Start-Sleep -Seconds 5
try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/json/version" -TimeoutSec 5
    Write-Host "Chrome debugging active."
    Write-Host "Browser: $($response.Browser)"
    Write-Host "Ready for: agent-browser --cdp $Port"
} catch {
    Write-Error "Failed to connect to Chrome debugging port. Try running this script again."
    exit 1
}
```

## Windows Usage

### Step 1: Start Chrome in debug mode

```powershell
# Run the helper script (closes existing Chrome, restarts with debugging)
powershell -ExecutionPolicy Bypass -File ~\scripts\chrome-debug.ps1
```

Or manually:

```powershell
# Close Chrome completely
taskkill /F /IM chrome.exe 2>$null
timeout /t 3

# Start with debugging port
start chrome --remote-debugging-port=9222 --no-first-run
```

### Step 2: Log in normally

The user logs into the target page in the Chrome window that just opened.

### Step 3: Use agent-browser to interact

```bash
# Get page accessibility snapshot (best for AI to understand page structure)
agent-browser --cdp 9222 snapshot

# Get page text content
agent-browser --cdp 9222 get text

# Get current URL
agent-browser --cdp 9222 get url

# Get page title
agent-browser --cdp 9222 get title

# Navigate to a URL
agent-browser --cdp 9222 open "https://example.com"

# Click an element by reference (from snapshot)
agent-browser --cdp 9222 click @e3

# Click by CSS selector
agent-browser --cdp 9222 click "#submit-btn"

# Fill a form field
agent-browser --cdp 9222 fill @e1 "search text"

# Take a screenshot
agent-browser --cdp 9222 screenshot /tmp/page.png

# Take a full-page screenshot
agent-browser --cdp 9222 screenshot --full /tmp/full-page.png

# Save as PDF
agent-browser --cdp 9222 pdf /tmp/page.pdf

# Execute JavaScript
agent-browser --cdp 9222 eval "document.title"

# List open tabs
agent-browser --cdp 9222 tab list

# Switch tab
agent-browser --cdp 9222 tab 2
```

## Windows Tips

- **Chrome must be fully closed** before starting with `--remote-debugging-port`. If any Chrome process remains, the port will not bind.
- **Port conflict**: If 9222 is taken, use a different port (e.g., 9333) in both the startup command and `--cdp` flag.
- **First use**: After installing agent-browser, run `agent-browser install` once to download Chromium (used only as fallback; CDP connects to your real Chrome).
- **Snapshot for navigation**: Use `agent-browser --cdp 9222 snapshot -i` to get interactive elements only. Each element has a `@ref` (e.g., `@e2`) you can use in click/fill commands.

---

# Common Workflow: Access an Authenticated Page

This workflow applies to both platforms:

1. **Detect platform** with `uname -s`
2. **Run the platform-specific preflight check**
3. **If preflight fails, stop and guide the user through setup**
4. **Ask the user** to open the target URL in their Chrome and log in normally
5. **Confirm the page is loaded**:
   - macOS: `osascript -e 'tell application "Google Chrome" to return URL of active tab of front window'`
   - Windows: `agent-browser --cdp 9222 get url`
6. **Extract content**:
   - macOS: `osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.body.innerText.substring(0, 15000)"'`
   - Windows: `agent-browser --cdp 9222 get text`
7. **Interact with the page** (click, navigate, fill) using platform-specific commands above
8. **Wait after navigation** — SPA pages may need `sleep 2` before reading updated content

# Common Limitations

- **Requires user login**: This skill cannot log in on behalf of the user. The user must be authenticated in Chrome first.
- **Long content**: Paginate reads with `.substring(start, end)` (macOS) or `--max-output` (Windows).
- **SPA pages**: Wait 2-3 seconds after clicking navigation elements before reading content.
- **Security**: Commands execute JavaScript in the user's authenticated session. Never run untrusted scripts.
- **macOS-specific**: No screenshot support via AppleScript. Chrome must be in foreground.
- **Windows-specific**: Chrome must be restarted with debugging flag. Requires agent-browser + Node.js.
