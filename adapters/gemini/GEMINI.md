# Chrome Control

You can control the user's local Chrome browser to access authenticated web pages (corporate SSO, MFA, internal portals). This works by operating on the user's real Chrome instance with their existing login session.

## Platform Detection

```bash
uname -s
```
- `Darwin` → macOS → AppleScript approach
- `MINGW*` / `CYGWIN*` / `MSYS*` → Windows → CDP approach

## macOS (AppleScript)

**Prerequisite**: User enables Chrome → View → Developer → Allow JavaScript from Apple Events

| Action | Command |
|---|---|
| Get URL | `osascript -e 'tell application "Google Chrome" to return URL of active tab of front window'` |
| Get title | `osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.title"'` |
| Get text | `osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.body.innerText.substring(0, 15000)"'` |
| Get HTML | `osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.documentElement.outerHTML.substring(0, 10000)"'` |
| Navigate | `osascript -e 'tell application "Google Chrome" to set URL of active tab of front window to "URL"'` |
| Click (CSS) | `osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.querySelector(\"SEL\").click()"'` |
| Run JS | `osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "CODE"'` |

**Click by text content:**
```bash
osascript -e '
tell application "Google Chrome"
    execute active tab of front window javascript "
        var items = document.querySelectorAll(\"li, a, button, span, div\");
        for (var i = 0; i < items.length; i++) {
            if (items[i].textContent.trim() === \"TARGET\" && items[i].children.length === 0) { items[i].click(); break; }
        }
        \"done\";"
end tell'
```

**Fill form field:**
```bash
osascript -e '
tell application "Google Chrome"
    execute active tab of front window javascript "
        var input = document.querySelector(\"SELECTOR\");
        input.value = \"VALUE\";
        input.dispatchEvent(new Event(\"input\", {bubbles: true}));
        \"done\";"
end tell'
```

**List all tabs:**
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

## Windows (Chrome CDP)

**Prerequisites**: `npm install -g agent-browser && agent-browser install`

**Start Chrome** (must close Chrome fully first):
```powershell
taskkill /F /IM chrome.exe 2>$null
timeout /t 3
start chrome --remote-debugging-port=9222 --no-first-run
```

| Action | Command |
|---|---|
| Get text | `agent-browser --cdp 9222 get text` |
| Get URL | `agent-browser --cdp 9222 get url` |
| Get title | `agent-browser --cdp 9222 get title` |
| Snapshot | `agent-browser --cdp 9222 snapshot -i` |
| Navigate | `agent-browser --cdp 9222 open "URL"` |
| Click ref | `agent-browser --cdp 9222 click @e3` |
| Click CSS | `agent-browser --cdp 9222 click "#sel"` |
| Fill form | `agent-browser --cdp 9222 fill @e1 "text"` |
| Screenshot | `agent-browser --cdp 9222 screenshot out.png` |
| Run JS | `agent-browser --cdp 9222 eval "CODE"` |
| List tabs | `agent-browser --cdp 9222 tab list` |

## Rules

1. Always detect platform first with `uname -s`.
2. Ask user to log in before reading authenticated pages.
3. Wait 2-3 seconds after navigation clicks before reading content.
4. Paginate long content: `.substring(0, 15000)` on macOS, `--max-output` on Windows.
5. `missing value` from AppleScript means JS returned undefined — return a string explicitly.
6. Never execute untrusted JavaScript in the user's authenticated session.
