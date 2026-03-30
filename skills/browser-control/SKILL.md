---
name: browser-control
description: "Full browser control skill for AI agents. Multi-channel web access (search, fetch, Jina, CDP) with real Chrome session inheritance. Read, click, fill, upload, screenshot — including pages behind authentication. Three-layer safety system. Sub-agent parallel dispatch. Site experience memory. Auto-detects macOS, Windows, and Linux."
argument-hint: "<url or action>"
license: MIT
version: "3.0.0"
metadata:
  remixed-from:
    - {name: "browser-control-skill", author: "d-wwei", version: "1.0", url: "https://github.com/d-wwei/browser-control-skill"}
    - {name: "web-access", author: "一泽Eze", version: "2.4.1", url: "https://github.com/eze-is/web-access"}
---

# Browser Control

Control the user's real Chrome browser with full login session inheritance. Multi-channel web access — from lightweight search to full CDP browser automation — with three-layer safety, sub-agent parallel dispatch, and site experience memory.

## When to Use

- Access any web page — public or behind corporate authentication (SSO, MFA, security gateways)
- Search, fetch, and extract information from the web
- Automate browser interactions: clicking, form filling, navigation, file upload
- Read content from dynamic pages (SPA, lazy-load, infinite scroll, virtual DOM)
- Write operations: compose messages, submit forms, upload files on web apps
- Rich interactions: React/Vue apps, rich text editors, file pickers, dropdowns
- Parallel research: dispatch sub-agents to investigate multiple targets simultaneously

---

## Browsing Philosophy

**Browse like a human — goal-driven, adaptive, evidence-based.**

Do not over-plan steps upfront. Enter with a clear goal, observe the page, decide the next action based on what you see, handle obstacles as they arise, and dig deeper when content is insufficient. Every decision traces back to: "Am I getting closer to what the user needs?"

### The Four Phases

**1. Understand** — Clarify what the user wants. Define success: what information, what action, what result? This anchors all subsequent decisions.

**2. Enter** — Choose the most direct entry point for the task. Consider platform characteristics and success criteria. If login is needed or static methods are known to fail (e.g., Xiaohongshu, WeChat), go straight to CDP.

**3. Verify** — Every result is evidence, not just pass/fail. Compare against the success criteria from phase 1. Is the path progressing? Is the quality, relevance, and completeness pointing toward the goal? If direction is wrong, pivot immediately — don't retry the same approach hoping for different results. Search misses don't always mean "wrong query" — they might mean "target doesn't exist." API errors, missing DOM elements, unchanged results after retry: these all signal "reassess direction."

**4. Complete** — Check against the defined success criteria. Stop when done. Don't over-operate for the sake of "completeness."

### Step-by-Step Reasoning (EOPA)

Before each browser action, follow this mental model:

**E — EVALUATE**: What happened after my last action? Did it succeed?
- If I navigated: did the URL change? Is the page loaded?
- If I clicked: did anything change on the page?
- If I typed: is the text visible in the field?

**O — OBSERVE**: What does the current page state tell me?
- Read page content or check the current URL
- What interactive elements are available?
- Am I on the right page for the user's goal?

**Auto-snapshot rules** — decide whether to re-read:
- Last action was **read-only** (get text, get URL, list elements) → page state unchanged, **skip re-read**
- Last action was **click / navigate / submit / scroll-that-loads** → page state likely changed, **must re-read**
- You already have the **exact selector or element index** → **operate directly**, no need to list all elements first
- **Never** execute the same read command twice consecutively

**P — PLAN**: What is the single next action needed?
- Do I need to scroll to reveal more content?
- Do I need to wait for something to load?
- Which specific element should I interact with?

**A — ACT**: Execute exactly ONE browser action, then return to E.

---

## Multi-Channel Web Access

Choose the lightest tool that gets the job done. Escalate only when lighter tools fail.

| Scenario | Tool | Notes |
|----------|------|-------|
| Search snippets, discover sources | **WebSearch** | Discovery only — not proof of truth |
| Known URL, extract specific info | **WebFetch** | Small model processes content per your prompt |
| Known URL, need raw HTML (meta, JSON-LD) | **curl** | Direct, fast |
| Known URL, convert to Markdown (save tokens) | **Jina** (`r.jina.ai/example.com`) | 20 RPM limit; best for articles/docs |
| Dynamic content, anti-scraping sites | **CDP Browser** | Full browser rendering |
| Login required, interactive operations | **CDP Browser** | Inherits real session |

**Jina usage**: Prefix URL without `http(s)://` — e.g., `curl -s https://r.jina.ai/example.com`. Great for articles, blogs, documentation. May extract wrong sections on dashboards or product pages.

**Escalation principle**: When multiple search attempts show no quality improvement, escalate to primary sources (official sites, original pages) via CDP.

**Information integrity**: Search engines are discovery tools, not proof. Primary sources (official sites, original documents, source code) outweigh secondary reports. Multiple media citing the same error creates circular confirmation — always trace to origin.

### Programmatic vs GUI Interaction

Inside the browser, two approaches:

- **Programmatic** (construct URL, eval DOM): Fast and precise when it works, but sites may detect non-human behavior and trigger anti-scraping.
- **GUI interaction** (click buttons, fill inputs, scroll): Designed for humans — sites never restrict normal UI operations. Reliable fallback.

When programmatic access fails, GUI interaction is the dependable fallback. Site-generated links (DOM hrefs) carry full context; manually constructed URLs may miss implicit parameters.

---

## Platform Detection

Before executing any command, detect the platform:

```bash
uname -s
```

- **Darwin** → macOS → AppleScript (basic) + CDP Proxy (advanced)
- **Linux** → CDP Proxy
- **MINGW* / CYGWIN* / MSYS* / Windows_NT** → CDP Proxy (+ optional agent-browser)

---

## Preflight Check

### macOS AppleScript Preflight

```bash
# Check Chrome is running and JS access is enabled
osascript -e 'tell application "Google Chrome" to get name'
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.title"'
```

If the second command fails: Chrome → View → Developer → Allow JavaScript from Apple Events (中文: 查看 → 开发者 → 允许 Apple 事件中的 JavaScript).

### CDP Preflight (All Platforms)

```bash
bash "${SKILL_DIR}/scripts/check-deps.sh"
```

The script checks Node.js 22+, Chrome debug port, and starts the CDP Proxy if needed.

**Chrome remote debugging setup**: Open `chrome://inspect/#remote-debugging` in Chrome, check "Allow remote debugging for this browser instance", restart Chrome if needed.

---

## Mode Routing

This skill operates in two modes. The `/browse` command handles routing automatically, but the logic is documented here for all agents.

### Two Modes

**Foreground (`here`)** — macOS AppleScript, operates on user's visible page
- Targets `front window` → `active tab` — the page the user is looking at
- User sees every action in real time
- Zero dependencies beyond Chrome
- Single-page, supervised operations

**Background (`bg`)** — CDP Proxy, operates in background tabs
- Creates its own tabs, never touches user's tabs
- User continues browsing normally, zero disruption
- Supports sub-agent parallel dispatch
- Required for advanced write operations (keyboard, upload, hover, isTrusted)

### Routing Decision

```
Platform is macOS?
├─ NO → background (CDP only option)
└─ YES
    ├─ User references current page? ("这个页面", "current tab", etc.)
    │   → foreground
    ├─ Multiple targets or parallel work? ("同时", "simultaneously", etc.)
    │   → background
    ├─ Implies don't-disturb? ("后台", "background", etc.)
    │   → background
    ├─ Needs keyboard/upload/isTrusted/hover?
    │   → background
    └─ DEFAULT → foreground (simpler, zero-dep)
```

### Escalation Within Foreground Mode

If a foreground (AppleScript) operation fails:
1. Try React-compatible event dispatch (still AppleScript)
2. Still fails → auto-start CDP Proxy, switch to CDP for that operation
3. Simple reads can stay on AppleScript even after one operation escalated

### Operation-Level Reference

| Task | Foreground | Background |
|------|-----------|------------|
| Read page text/HTML | AppleScript JS eval | CDP `/eval` |
| Click links, basic form fill | AppleScript JS click | CDP `/click` |
| Navigate | AppleScript new tab | CDP `/new` |
| Upload files | — (escalate to CDP) | CDP `/setFiles` or helper |
| Rich text editors | — (escalate to CDP) | CDP helper `type` |
| Sites checking `isTrusted` | — (escalate to CDP) | CDP `/clickAt` |
| Keyboard shortcuts | — (escalate to CDP) | CDP helper `key` |
| Hover-triggered menus | — (escalate to CDP) | CDP helper `hover` |
| Parallel multi-target | Not possible | Sub-agent dispatch |

---

## Element Targeting Priority

### macOS (AppleScript)
1. **Element index** — inject `List Interactive Elements`, then use `window.__interactiveElements[index]` (most reliable)
2. **Text content match** — most readable for buttons/links
3. **CSS selector** — for form inputs, specific elements
4. **Coordinates** — last resort, fragile across screen sizes

### CDP (All Platforms)
1. **CSS selector** via `/click` — simple JS click, fast
2. **CDP mouse event** via `/clickAt` — trusted, bypasses anti-automation
3. **JS eval** — for complex targeting logic
4. **Coordinates** via CDP `Input.dispatchMouseEvent` — when all else fails

---

## macOS AppleScript Quick Reference

Zero-dependency browser control via macOS native AppleScript. **Full reference**: `modules/applescript-commands.md`

```bash
# Get current URL
osascript -e 'tell application "Google Chrome" to return URL of active tab of front window'
# Get page text
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.body.innerText.substring(0, 15000)"'
# Open URL in new tab
osascript -e 'tell application "Google Chrome" to tell front window to make new tab with properties {URL:"https://example.com"}'
# Click by CSS selector
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.querySelector(\"#submit-btn\").click()"'
# Execute arbitrary JavaScript
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "YOUR_JS_CODE_HERE"'
```

For JXA tab targeting and MutationObserver-based element waiting, see `modules/advanced-applescript.md`.

---

## CDP Proxy Quick Reference

HTTP-to-CDP bridge proxy for the user's daily Chrome. **Full reference**: `modules/cdp-proxy-api.md`

```bash
# Create new background tab
curl -s "http://localhost:3456/new?url=https://example.com"
# Execute JS
curl -s -X POST "http://localhost:3456/eval?target=ID" -d 'document.title'
# JS click
curl -s -X POST "http://localhost:3456/click?target=ID" -d 'button.submit'
# Close tab
curl -s "http://localhost:3456/close?target=ID"
# Screenshot
curl -s "http://localhost:3456/screenshot?target=ID&file=/tmp/shot.png"
```

Setup: `bash "${SKILL_DIR}/scripts/check-deps.sh"` — proxy listens on `localhost:3456`.

---

## Security Boundaries (Summary)

Three-layer safety system. **Full reference with injectable scripts**: `modules/safety-system.md`

**Layer 1 — Domain Blacklist** (read-only, no interactions):
- Banking: chase, wellsfargo, bankofamerica, citi, capitalone, usbank, pnc, tdbank, hsbc, any `.bank`
- Payments: paypal, venmo, stripe, squareup, wise, revolut, robinhood, coinbase, binance
- Identity/Auth: `accounts.google.com`, `login.microsoftonline.com`, `login.live.com`, `icloud.com/account`, `*.okta.com`, `*.auth0.com`, `*.onelogin.com`
- Cloud: `console.aws.amazon.com`, `console.cloud.google.com`, `portal.azure.com`
- Chrome: `chrome://`, `chrome-extension://`, `about:`

**Layer 2 — Element Protection**: Never interact with password fields (`input[type=password]`, `*[name*=password]`, `*[autocomplete=*-password]`). Never click payment buttons (pay, purchase, buy, checkout, place order, subscribe, 付款, 支付, 购买, 下单).

**Layer 3 — Operation Confirmation**: Confirm with user before: form submissions, submit/send/post/publish/create/delete/remove actions, file uploads to external services, actions on unvisited pages.

**General**: No untrusted JS in authenticated sessions. `chrome://` shadow DOM is inaccessible. Cross-origin iframes cannot be accessed. Confirm before extracting sensitive financial/medical data.

---

## Parallel Research: Sub-Agent Dispatch

Dispatch sub-agents for parallel execution when a task has multiple independent targets.

**Full reference**: `modules/parallel-dispatch.md` — load when you have multiple independent targets to research in parallel.

---

## Site Experience Memory

Per-domain knowledge for known sites — load patterns, check experience, record new findings.

**Full reference**: `modules/site-experience.md` — load when operating on a site with known patterns.

---

## Login Handling

The user's daily Chrome naturally carries login sessions. Most commonly used sites are already logged in.

**Core question**: Did I get the target content?

Open the page and try to get content first. Only if content is inaccessible and login would solve it:
> "This page requires login to access [specific content]. Please log into [site name] in your Chrome, then tell me to continue."

After login, no restart needed — just refresh the page.

---

## Information Verification

| Information Type | Primary Source |
|-----------------|---------------|
| Policy/regulation | Issuing authority's official site |
| Corporate announcement | Company's official news page |
| Academic claim | Original paper / institutional site |
| Tool capability/usage | Official docs, source code |

When official source is unavailable, authoritative media (original reporting, not syndicated) serves as secondary evidence — but inform the user: "Official source not found. The following is from [media name] reporting; transcription error possible."

---

## Best Practices

1. **Smart wait**: Prefer `Wait for Element` over blind `sleep`. Fall back to `sleep 2` only when no specific condition is available.
2. **Scroll before interacting**: Off-screen elements may fail to click.
3. **Confirm actions succeeded**: After navigate → check URL. After click → check content. After fill → verify value.
4. **One action at a time**: Execute one action, observe, then decide next.
5. **Paginate long content**: Use `.substring(start, end)` to read in chunks.
6. **Prefer scrolling for lazy-load**: Scroll the real page first rather than switching strategies.
7. **Avoid redundant reads**: Don't re-read after read-only actions. If you know the selector, operate directly.
8. **Safety check on unfamiliar pages**: Inject the safety check before interacting.
9. **Verify each field after filling**: Read back values. React/Vue may silently reject `el.value`.
10. **Escalate progressively**: AppleScript → CDP Proxy → CDP helper. Only escalate when simpler mode fails.
11. **Screenshot before irreversible actions**: Capture state before Submit/Send/Delete.
12. **Coordinates expire**: After scroll/reflow/dropdown, re-query positions before CDP click.
13. **Tab hygiene**: Never navigate in user's tabs. Create and close your own.
14. **Proxy stays running**: Don't stop the proxy — restarting requires Chrome re-authorization.

## Recovery Strategy

If a browser action fails:

1. **Observe**: Read content or screenshot to understand current state
2. **Re-index**: Page may have changed — refresh element references
3. **Alternative targeting**: CSS selector failed → try text match. Text match failed → try different selector
4. **Check for overlays**: Dialogs, cookie banners, modals may be blocking — dismiss them first
5. **Don't retry blindly**: Never repeat the same failed action >2 times. Change approach.

---

## Limitations

- **Requires user login**: Cannot log in on behalf of the user
- **Long content**: Scroll first for lazy-load, then paginate output with `.substring()`
- **SPA navigation**: Wait for content after clicking navigation elements
- **Security**: JS executes in the user's authenticated session — never run untrusted scripts
- **macOS AppleScript**: No screenshot API (use `screencapture -l`). Chrome must be in foreground.
- **CDP**: Requires Chrome with remote debugging enabled. Coordinates are viewport-relative.
- **File upload**: Only `<input type="file">`. Drag-and-drop zones without file input need `DataTransfer` API fallback.
- **Cross-origin iframes**: Many enterprise apps use strict CSP that blocks automation.
- **Anti-scraping**: Some sites detect automation. Escalate from programmatic to GUI interaction.

---

## Module Index

| Module | When to Load |
|--------|-------------|
| `modules/applescript-commands.md` | Need full AppleScript command reference (observation, navigation, interaction) |
| `modules/advanced-applescript.md` | Need JXA robust tab targeting or MutationObserver element waiting |
| `modules/cdp-proxy-api.md` | Need full CDP Proxy API reference (all endpoints, setup, technical notes) |
| `modules/safety-system.md` | Need injectable safety check scripts (AppleScript + CDP versions) |
| `modules/dom-extraction.md` | Need structured Markdown extraction or virtual scroll |
| `modules/interactive-elements.md` | Need element indexing, click-by-index, or annotated screenshots |
| `modules/cdp-write-ops.md` | Need keyboard input, file upload, rich text fill, dropdown, hover, iframe |
| `modules/console-network.md` | Need console log or network request interception |
| `modules/parallel-dispatch.md` | Multiple independent targets to research in parallel |
| `modules/site-experience.md` | Operating on a site with known patterns |

---

## References

| File | When to Load |
|------|-------------|
| `references/cdp-api.md` | Need CDP API detail, JS extraction patterns, error handling |
| `references/site-patterns/{domain}.md` | Before operating on a known site |
