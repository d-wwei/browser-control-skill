# CDP Advanced Write Operations Module

> Part of browser-control skill. Load when needed, not by default.

For operations beyond simple click/fill -- keyboard input, file upload, rich text editing, dropdowns, hover menus.

## Keyboard Input

```bash
# Via CDP helper (macOS/Windows with Python)
python3 "${SKILL_DIR}/scripts/cdp-helper.py" key Enter
python3 "${SKILL_DIR}/scripts/cdp-helper.py" key Tab
python3 "${SKILL_DIR}/scripts/cdp-helper.py" key a "ctrl"       # Ctrl+A
python3 "${SKILL_DIR}/scripts/cdp-helper.py" key Enter "shift"  # Shift+Enter

# Type text (works with ALL rich text editors)
python3 "${SKILL_DIR}/scripts/cdp-helper.py" type "Hello, typed text."

# Common patterns:
python3 "${SKILL_DIR}/scripts/cdp-helper.py" type "search query"
python3 "${SKILL_DIR}/scripts/cdp-helper.py" key Enter

# Clear and retype
python3 "${SKILL_DIR}/scripts/cdp-helper.py" key a "ctrl"
python3 "${SKILL_DIR}/scripts/cdp-helper.py" key Backspace
python3 "${SKILL_DIR}/scripts/cdp-helper.py" type "new value"
```

## File Upload

```bash
# Via CDP Proxy
curl -s -X POST "http://localhost:3456/setFiles?target=ID" -d '{"selector":"input[type=file]","files":["/path/to/file.png"]}'

# Via CDP helper (alternative)
python3 "${SKILL_DIR}/scripts/cdp-helper.py" upload "input[type=file]" /path/to/file.png

# Find hidden file inputs
curl -s -X POST "http://localhost:3456/eval?target=ID" -d 'JSON.stringify(Array.from(document.querySelectorAll("input[type=file]")).map((el,i)=>({index:i,name:el.name,accept:el.accept,multiple:el.multiple,hidden:!el.offsetParent})))'
```

## React/Rich Text Editor Fill

**Pattern A: CDP type (recommended -- works with ALL editors)**
```bash
# Focus -> select all -> type new value
curl -s -X POST "http://localhost:3456/eval?target=ID" -d 'document.querySelector("#my-input").focus()'
python3 "${SKILL_DIR}/scripts/cdp-helper.py" key a "ctrl"
python3 "${SKILL_DIR}/scripts/cdp-helper.py" type "New value"
```

**Pattern B: React-compatible events (no CDP required)**
```bash
curl -s -X POST "http://localhost:3456/eval?target=ID" -d '
(function(sel, val) {
  var el = document.querySelector(sel);
  if (!el) return "not found";
  var setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), "value") ||
               Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
  if (setter && setter.set) setter.set.call(el, val); else el.value = val;
  el.dispatchEvent(new Event("input", {bubbles: true}));
  el.dispatchEvent(new Event("change", {bubbles: true}));
  return "filled: " + el.value;
})("#my-input", "my value")'
```

**Pattern C: contenteditable (Notion, Slack, Gmail compose)**
```bash
curl -s -X POST "http://localhost:3456/eval?target=ID" -d '
(function(sel, text) {
  var el = document.querySelector(sel);
  if (!el) return "not found";
  el.focus(); el.innerHTML = "";
  document.execCommand("insertText", false, text);
  return "inserted";
})("[contenteditable=true]", "Your text here")'
```

## Select / Dropdown

```bash
# Standard <select>
python3 "${SKILL_DIR}/scripts/cdp-helper.py" select "#country" "US"

# Custom dropdown (div-based, React Select, MUI)
# Step 1: Click trigger
curl -s -X POST "http://localhost:3456/clickAt?target=ID" -d '.dropdown-trigger'
# Step 2: Wait for options
python3 "${SKILL_DIR}/scripts/cdp-helper.py" wait "[role=listbox]" 3000
# Step 3: Click option by text
curl -s -X POST "http://localhost:3456/eval?target=ID" -d '
(function(text){
  var opts = document.querySelectorAll("[role=option], li.option, .dropdown-item");
  for (var i=0;i<opts.length;i++) if(opts[i].textContent.trim()===text){opts[i].click();return "selected"}
  return "not found"
})("Target Value")'
```

## Hover Trigger

```bash
python3 "${SKILL_DIR}/scripts/cdp-helper.py" hover <x> <y>
python3 "${SKILL_DIR}/scripts/cdp-helper.py" wait ".hover-menu" 2000
python3 "${SKILL_DIR}/scripts/cdp-helper.py" click <menu_x> <menu_y>
```

## iframe Penetration

```bash
# List iframes
curl -s -X POST "http://localhost:3456/eval?target=ID" -d 'JSON.stringify(Array.from(document.querySelectorAll("iframe")).map((f,i)=>({index:i,src:f.src,id:f.id,name:f.name})))'

# Same-origin iframe: access directly
curl -s -X POST "http://localhost:3456/eval?target=ID" -d 'document.querySelector("iframe#myFrame").contentDocument.querySelector("button.submit").click()'

# Cross-origin iframe: use CDP frame targeting
python3 "${SKILL_DIR}/scripts/cdp-helper.py" raw "Page.getFrameTree" '{}'
```
