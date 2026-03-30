# macOS AppleScript Mode — Full Command Reference

Zero-dependency browser control using macOS native AppleScript. No npm, no Python, no setup beyond one Chrome checkbox.

## Observation

```bash
# Get current URL
osascript -e 'tell application "Google Chrome" to return URL of active tab of front window'

# Get page title
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.title"'

# Get page text (with length limit)
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.body.innerText.substring(0, 15000)"'

# Get page HTML (first 10KB)
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.documentElement.outerHTML.substring(0, 10000)"'

# List all open tabs
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

## Navigation

> **Never navigate in the user's current tab.** Always open a new tab or use a dedicated task window.

```bash
# Open URL in new tab
osascript -e 'tell application "Google Chrome" to tell front window to make new tab with properties {URL:"https://example.com"}'

# Dedicated task window (recommended for multi-step workflows)
osascript -l JavaScript -e '
function run() {
    var chrome = Application("Google Chrome");
    var wins = chrome.windows();
    var taskWin = null;
    for (var i = 0; i < wins.length; i++) {
        var tabs = wins[i].tabs();
        for (var j = 0; j < tabs.length; j++) {
            if (tabs[j].url().indexOf("__agentTask") !== -1) { taskWin = wins[i]; break; }
        }
        if (taskWin) break;
    }
    if (!taskWin) { taskWin = chrome.Window().make(); }
    taskWin.activeTab.url = "https://example.com";
    return "task window " + taskWin.id() + ", tabs: " + taskWin.tabs.length;
}'

# Switch to a specific tab
osascript -e 'tell application "Google Chrome" to set active tab index of front window to 3'
```

## Interaction

```bash
# Click by CSS selector
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.querySelector(\"#submit-btn\").click()"'

# Click by text content
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "
    var items = document.querySelectorAll(\"li, a, button, span, div\");
    for (var i = 0; i < items.length; i++) {
        if (items[i].textContent.trim() === \"Target Text\" && items[i].children.length === 0) {
            items[i].click(); break;
        }
    }
    \"done\";
"'

# Fill a form field (with event dispatch for React/Vue)
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "
    var input = document.querySelector(\"input[name=search]\");
    input.value = \"search text\";
    input.dispatchEvent(new Event(\"input\", {bubbles: true}));
    \"done\";
"'

# Execute arbitrary JavaScript
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "YOUR_JS_CODE_HERE"'

# Scroll (for lazy-loaded content)
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "window.scrollBy(0, window.innerHeight); \"done\";"'
```

## Advanced: Read Page as Structured Markdown

DOM-to-Markdown converter preserving headings, lists, tables, links, code blocks, images. Far better than `innerText` when structure matters.

**Full reference**: `modules/dom-extraction.md` — load when you need DOM-to-Markdown conversion or SPA crawling.

## Advanced: List Interactive Elements & Click by Index

Scan, index, and cache all interactive elements. Click or fill by numeric index. Includes annotated screenshots.

**Full reference**: `modules/interactive-elements.md` — load when you need element indexing, click-by-index, or annotated screenshots.

## Advanced: Virtual Scrolling & SPA Crawler

Scroll-and-accumulate crawler for apps that destroy DOM nodes when scrolled out of view (X/Twitter, React Virtualized).

**Full reference**: `modules/dom-extraction.md` — includes the virtual scroll crawler alongside the DOM-to-Markdown converter.

## Advanced: Console & Network Interception

Inject interceptors to capture console logs and XHR/fetch network requests for debugging.

**Full reference**: `modules/console-network.md` — load when you need console log or network request interception.

## Advanced: Screenshots & Annotated Screenshots

Plain and annotated (element-index badges) screenshot capture. Depends on the interactive element indexer.

**Full reference**: `modules/interactive-elements.md` — includes screenshot capture with element annotations.

## macOS Tips

- **`missing value`**: JS returned `undefined`. Ensure expression returns a string.
- **Escaped quotes**: Use `\"` inside AppleScript JS strings. For complex JS, use heredoc.
- **Multiple windows**: `front window` by default. Use `window 2` for others.
- **`-1719` error**: Chrome may have hidden windows. Use JXA to find visible window.
