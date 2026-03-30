---
name: browse
description: "Browser control with mode routing. /browse = auto-detect, /browse here = foreground (operate on the page user is looking at), /browse bg = background (CDP, no user disruption). Supports parallel sub-agent dispatch in bg mode."
argument-hint: "[here|bg] <url or instruction>"
---

# /browse — Browser Control Router

## Usage

```
/browse <instruction>          → auto-detect foreground vs background
/browse here <instruction>     → foreground mode (AppleScript, user's current page)
/browse bg <instruction>       → background mode (CDP Proxy, no user disruption)
```

## Mode Resolution

Parse the first argument. If it is `here` or `bg`, use that mode explicitly. Otherwise, auto-detect.

### Explicit Modes

**`/browse here`** — Foreground Mode
- Use macOS AppleScript to operate on the user's **current visible page**
- Target: `front window` → `active tab`
- User can see every action in real time
- Requires: macOS + Chrome + "Allow JavaScript from Apple Events"
- Best for: "帮我在这个页面上..." / "当前页面" / user is watching and supervising

**`/browse bg`** — Background Mode
- Use CDP Proxy to operate in **background tabs**
- Agent creates its own tabs, user's tabs are untouched
- User continues browsing normally, zero disruption
- Supports sub-agent parallel dispatch (multiple tabs simultaneously)
- Requires: Node.js 22+ + Chrome remote debugging enabled
- Best for: "帮我去查..." / "同时调研..." / bulk research / parallel tasks

### Auto-Detection (`/browse` without mode)

When no explicit mode is given, infer from context:

```
IS the platform macOS?
├─ NO → bg (CDP is the only option)
└─ YES
    ├─ Does the instruction reference the user's current page?
    │   ("这个页面", "当前页面", "this page", "current tab",
    │    "我正在看的", "the page I'm on", "帮我在这里...")
    │   └─ YES → here (user wants agent on THEIR visible page)
    │
    ├─ Does the instruction involve multiple targets or parallel work?
    │   ("同时", "并行", "这几个", "分别查", "simultaneously",
    │    "in parallel", "these N sites/pages")
    │   └─ YES → bg (AppleScript can't parallelize)
    │
    ├─ Does the instruction imply background / don't-disturb?
    │   ("后台", "别打扰我", "background", "while I work")
    │   └─ YES → bg
    │
    ├─ Does the instruction require advanced write operations?
    │   (keyboard input, file upload, isTrusted events, hover menus)
    │   └─ YES → bg (needs CDP capabilities)
    │
    └─ DEFAULT → here (on macOS, prefer the simpler zero-dep path)
```

**On macOS, the default is `here`** because:
- Zero setup cost (AppleScript is built-in)
- Most natural UX for single-page operations
- User gets immediate visual feedback
- If AppleScript hits a limitation (value doesn't stick, isTrusted check, file upload), **auto-escalate to CDP** within the session — no need to restart with `/browse bg`

## Escalation Within Foreground Mode

When operating in `here` mode, if a basic AppleScript operation fails:

1. `el.value = "..."` doesn't stick (React/Vue) → try React-compatible event dispatch (still AppleScript)
2. Still fails → auto-escalate: start CDP Proxy, switch to CDP helper for that operation
3. Report to user: "AppleScript 基础模式无法完成此操作，已切换到 CDP 增强模式。"

The escalation is **per-operation, not per-session**. Simple reads can stay on AppleScript even after one operation escalated to CDP.

## Execution

After mode resolution, load the full browser-control skill and execute:

1. Run platform detection and preflight for the resolved mode
2. Follow the browser-control SKILL.md instructions using the resolved mode's commands
3. Apply all safety rules (three-layer security) regardless of mode
4. In `bg` mode: if task has multiple independent targets, consider sub-agent parallel dispatch

### Foreground Mode Quick Reference

```bash
# Read current page
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.body.innerText.substring(0, 15000)"'

# Click element
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.querySelector(\"SELECTOR\").click()"'

# Fill field
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "var el=document.querySelector(\"SELECTOR\"); el.value=\"VALUE\"; el.dispatchEvent(new Event(\"input\",{bubbles:true})); \"done\";"'

# Navigate (new tab, never in user's current tab)
osascript -e 'tell application "Google Chrome" to tell front window to make new tab with properties {URL:"URL"}'
```

### Background Mode Quick Reference

```bash
# Start proxy (if not running)
bash "${SKILL_DIR}/../browser-control/scripts/check-deps.sh"

# Create background tab
curl -s "http://localhost:3456/new?url=URL"

# Execute JS in background tab
curl -s -X POST "http://localhost:3456/eval?target=ID" -d 'JS_CODE'

# Click in background tab
curl -s -X POST "http://localhost:3456/click?target=ID" -d 'SELECTOR'

# Close background tab when done
curl -s "http://localhost:3456/close?target=ID"
```

### CDP Helper (Advanced Write Operations, Both Modes)

```bash
python3 "${SKILL_DIR}/../browser-control/scripts/cdp-helper.py" type "text"
python3 "${SKILL_DIR}/../browser-control/scripts/cdp-helper.py" key Enter
python3 "${SKILL_DIR}/../browser-control/scripts/cdp-helper.py" upload "input[type=file]" /path/to/file
python3 "${SKILL_DIR}/../browser-control/scripts/cdp-helper.py" click <x> <y>
```

## Full Reference

For complete documentation (DOM-to-Markdown, element indexer, virtual scroll, console/network interception, screenshots, sub-agent dispatch, site experience memory, safety system), see:

`skills/browser-control/SKILL.md`
