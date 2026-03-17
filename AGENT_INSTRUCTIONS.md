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

## Step-by-Step Reasoning

Before each browser action, follow this mental model:

### 1. EVALUATE
What happened after my last action? Did it succeed?
- If I navigated: did the URL change? Is the page loaded?
- If I clicked: did anything change on the page?
- If I typed: is the text visible in the field?

### 2. OBSERVE
What does the current page state tell me?
- Read page content or check the current URL
- What interactive elements are available?
- Am I on the right page for the user's goal?

**Auto-snapshot rules** — decide whether to re-read:
- Last action was **read-only** (get text, get URL, list elements) → page state unchanged, **skip re-read**
- Last action was **click / navigate / submit / scroll-that-loads** → page state likely changed, **must re-read**
- You already have the **exact selector or element index** for your next target → **operate directly**, no need to list all elements first
- **Never** execute the same read command twice consecutively

### 3. PLAN
What is the single next action needed?
- Do I need to scroll to reveal more content?
- Do I need to wait for something to load?
- Which specific element should I interact with?

### 4. ACT
Execute exactly ONE browser action, then return to step 1.
- Use the most reliable targeting method available
- Be specific about which tab or window

## Element Targeting Priority

### macOS (AppleScript)
Preferred order: element index (inject indexing script first, then operate by index) → text content match → CSS selector → coordinates (last resort only — use `document.elementFromPoint(x,y).click()`)

> To use element indexing: inject a JS snippet via `osascript` that scans all `a[href], button, input, select, textarea, [role="button"], [onclick], [contenteditable], [tabindex]` elements, filters out hidden/zero-size ones, assigns sequential indexes from 0, and caches references in `window.__interactiveElements`. Then operate by index (e.g. `window.__interactiveElements[3].click()`). This is the most reliable method, analogous to Windows @ref.
>
> **Minimal inline example** — list interactive elements:
> ```
> osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "
>     var els=document.querySelectorAll(\"a[href],button,input,select,textarea,[role=button],[onclick],[tabindex]\");
>     var r=[],c=[];
>     for(var i=0;i<els.length;i++){var e=els[i];var b=e.getBoundingClientRect();
>       if(b.width<=0||b.height<=0||e.hidden)continue;
>       var s=window.getComputedStyle(e);if(s.display===\"none\"||s.visibility===\"hidden\")continue;
>       var idx=c.length;c.push(e);
>       r.push(\"[\"+idx+\"] <\"+e.tagName.toLowerCase()+\"> \"+(e.getAttribute(\"aria-label\")||(e.textContent||\"\").trim().substring(0,60)));
>     }window.__interactiveElements=c;r.join(\"\\n\");
> "'
> ```
> Then click: `window.__interactiveElements[3].click()`; fill: `var el=window.__interactiveElements[5]; el.value='text'; el.dispatchEvent(new Event('input',{bubbles:true}));`

### Windows (agent-browser)
Preferred order: @ref from `snapshot -i` (e.g. `@e3`) → CSS selector → JS via eval

Always prefer structured references over manually constructed CSS selectors.

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

**Observation:**

Get current tab URL:
```bash
osascript -e 'tell application "Google Chrome" to return URL of active tab of front window'
```

Get page title:
```bash
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.title"'
```

Get page text content:
```bash
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.body.innerText"'
```

> For scenarios requiring preserved structure (tables, lists, code blocks), inject a DOM→Markdown converter JS via `osascript` instead of using plain `innerText`. The converter should prioritize `<main>`/`<article>` content, skip `script`/`style`/`nav`/`footer`, and convert headings to `#`, lists to `- `/`1. `, tables to `| col |` format, links to `[text](url)`, and code blocks to fenced markdown.

For long pages, paginate with substring:
```bash
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.body.innerText.substring(0, 15000)"'
```

For lazy-loaded or infinite-scroll pages, scroll the real page first, wait, then read again:
```bash
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "window.scrollBy(0, window.innerHeight); \"done\";"'
```

Get page HTML:
```bash
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.documentElement.outerHTML.substring(0, 10000)"'
```

List all open tabs:
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

**Navigation:**

Navigate to URL:
```bash
osascript -e 'tell application "Google Chrome" to set URL of active tab of front window to "https://example.com"'
```

Switch to specific tab in the front window:
```bash
osascript -e 'tell application "Google Chrome" to set active tab index of front window to 3'
```

> The tab list spans all Chrome windows, but the switch command only changes the active tab in the **front window**. For cross-window targeting, use JXA (`osascript -l JavaScript`) to iterate over all windows and tabs by URL.

**Interaction:**

Click element by CSS selector:
```bash
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.querySelector(\"#submit-btn\").click()"'
```

Click element by text content:
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

Click element by index:
```bash
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.querySelectorAll(\"li\")[2].click(); \"done\";"'
```

Fill a form field:
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

**Advanced:**

Execute arbitrary JavaScript:
```bash
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "YOUR_JS_CODE_HERE"'
```

### macOS Troubleshooting

- **`missing value` returned**: JavaScript returned `undefined`/`null`. Make the JS expression explicitly return a string.
- **Escaped quotes**: Use `\"` for double quotes inside AppleScript JavaScript strings.
- **Multiple windows**: Commands target `front window` by default. Use `window 2`, `window 3` for others.
- **Screenshots**: AppleScript has no screenshot API, but `screencapture -l <windowID>` captures the Chrome window. Get the window ID: `osascript -e 'tell application "Google Chrome" to id of front window'`.

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
Get-Command agent-browser
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

**Observation:**

```bash
agent-browser --cdp 9222 get text          # Get page text
agent-browser --cdp 9222 get url           # Get current URL
agent-browser --cdp 9222 get title         # Get page title
agent-browser --cdp 9222 snapshot          # Accessibility tree (best for understanding page structure)
agent-browser --cdp 9222 snapshot -i       # Interactive elements only (with @ref labels)
```

> For scenarios requiring preserved structure (tables, lists, code blocks), inject a DOM→Markdown converter JS via `agent-browser --cdp 9222 eval "..."` instead of using `get text`. The converter should prioritize `<main>`/`<article>` content, skip `script`/`style`/`nav`/`footer`, and convert headings, lists, tables, links, and code blocks to Markdown format.

**Navigation:**

```bash
agent-browser --cdp 9222 open "https://example.com"   # Navigate to URL
agent-browser --cdp 9222 tab list                      # List open tabs
agent-browser --cdp 9222 tab 2                         # Switch to tab 2
```

**Interaction:**

```bash
agent-browser --cdp 9222 click @e3         # Click by ref from snapshot
agent-browser --cdp 9222 click "#submit"   # Click by CSS selector
agent-browser --cdp 9222 fill @e1 "text"   # Fill form field
```

**Capture:**

```bash
agent-browser --cdp 9222 screenshot /tmp/page.png        # Screenshot
agent-browser --cdp 9222 screenshot --full /tmp/full.png  # Full-page screenshot
agent-browser --cdp 9222 pdf /tmp/page.pdf                # Save as PDF
```

**Advanced:**

```bash
agent-browser --cdp 9222 eval "document.title"   # Execute JavaScript
agent-browser --cdp 9222 eval "window.scrollBy(0, window.innerHeight); 'done'"   # Scroll down one viewport
agent-browser --cdp 9222 eval "window.scrollTo(0, document.body.scrollHeight); 'done'"   # Scroll to bottom
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
9. **Wait after navigation or scroll**: SPA pages and lazy-loaded pages need time before content updates. Prefer smart wait (watch for target element to appear); fall back to `sleep 2` only when no specific wait condition is available.

## Best Practices

1. **Smart wait after navigation**: Prefer injecting a MutationObserver-based wait script that watches for a specific target element (by CSS selector + condition: `visible`/`hidden`/`attached`/`loaded`) with a timeout, rather than a blind `sleep 2`. Example approach: inject JS that calls `new MutationObserver(...)` on `document.documentElement`, checks `document.querySelector(sel)` on each mutation, and resolves with `{found: true/false, elapsed: ms}`. Only fall back to `sleep 2` when you cannot determine a specific element or condition to wait for.
2. **Scroll before clicking**: If the target might be off-screen, scroll down first.
3. **Confirm actions**: After each action, verify the result before proceeding.
4. **One action at a time**: Don't chain multiple actions without observing between them.
5. **Use snapshot on Windows**: Run `agent-browser --cdp 9222 snapshot -i` before interacting to get reliable @ref labels.
6. **Paginate long content**: Use `.substring(start, end)` on macOS. Never read an entire very long page at once.
7. **Prefer scrolling**: For lazy-loaded content, scroll the real page rather than switching strategies.
8. **Avoid redundant reads**: If your last action was a pure read (did not change page state), do not re-read the same content. Only re-read after click, navigation, form submission, or scroll that loads new content. If you already know the exact selector or element index, operate directly without listing all elements first. Never execute the same read command twice in a row.

## Recovery Strategy

If a browser action fails:
1. Read the page or take a screenshot (Windows) to see current state
2. Re-read elements — the page may have changed
3. Try alternative targeting (different selector, text match, etc.)
4. Check for blocking overlays (modals, cookie banners)
5. Do NOT retry the same failed action more than twice — change approach

## Security (Mandatory Rules)

The following are **enforced rules**, not suggestions. Violations must be refused.

### Sensitive Site Blacklist (read-only access)

On the following domains, **only read operations are allowed** (get text, get URL, get title, read page as markdown). All click, fill, and execute operations are **forbidden**.

- **Banking**: chase, wellsfargo, bankofamerica, citi, capitalone, usbank, pnc, tdbank, hsbc, and any `.bank` domain
- **Payments**: paypal, venmo, stripe, squareup, wise, revolut, robinhood, coinbase, binance
- **Identity/Auth**: `accounts.google.com`, `login.microsoftonline.com`, `login.live.com`, `icloud.com/account`, `*.okta.com`, `*.auth0.com`, `*.onelogin.com`
- **Cloud Consoles**: `console.aws.amazon.com`, `console.cloud.google.com`, `portal.azure.com`
- **Chrome Internal**: `chrome://`, `chrome-extension://`, `about:`

### Password Field Protection

Before executing any fill or click action, check the target element. **Refuse** the operation if the target matches any of:

- `input[type="password"]`
- `input[name]` containing "password" or "passwd"
- `input[autocomplete="current-password"]` or `input[autocomplete="new-password"]`

### Payment Button Protection

**Never click** buttons whose text matches any of these patterns:

- English: pay, purchase, buy, checkout, place order, submit order, confirm payment, subscribe, upgrade, donate
- 中文: 付款, 支付, 购买, 下单, 确认订单, 立即购买

### Pre-action Safety Check

Before any interaction (click/fill/execute) on an unfamiliar page, verify the current URL against the blacklist above. You can inject a JS check via `osascript` (macOS) or `agent-browser --cdp 9222 eval` (Windows) that tests `location.href` against the sensitive domain patterns listed above and returns `{safe: true/false, reason: '...'}`. If the URL matches any blacklisted pattern, switch to read-only mode.

### General Rules

- Never execute untrusted or user-provided JavaScript — commands run in the user's authenticated session
- Cross-origin iframes are not accessible
- Do not attempt to access chrome:// pages or browser extension pages — blocked by Chrome security
- Confirm with the user before extracting sensitive financial or medical data

## Limitations

- Cannot log in on behalf of the user — user must authenticate in Chrome first.
- Long content on lazy-loaded pages should be loaded by scrolling the real page first. Use `.substring(start, end)` on macOS or `eval "document.body.innerText.substring(0, 15000)"` on Windows to paginate output after the content is present in the page.
- SPA pages require a wait after navigation before reading updated content.
- macOS: AppleScript itself has no screenshot API, but you can capture the Chrome window using `screencapture -l <windowID> /tmp/screenshot.png` (get the window ID with `osascript -e 'tell application "Google Chrome" to id of front window'`). Chrome must be in foreground.
- Windows: Chrome must be restarted with `--remote-debugging-port` flag; requires Node.js.
- Security: commands execute JavaScript in the user's authenticated session. Never run untrusted scripts.
