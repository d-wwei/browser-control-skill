#!/usr/bin/env python3
"""cdp-helper.py — Lightweight Chrome DevTools Protocol client.

Zero external dependencies — Python 3.6+ stdlib only.
Connects to Chrome's debugging port via WebSocket to send CDP commands
that cannot be achieved through JavaScript alone (trusted input events,
file uploads, etc.).

Usage:
  python3 cdp-helper.py [options] <command> [args...]

Commands:
  raw <method> [params_json]     Send raw CDP method
  click <x> <y>                  Trusted mouse click at coordinates
  hover <x> <y>                  Move mouse to coordinates (trigger hover menus)
  type <text>                    Type text via insertText (works in rich editors)
  key <key> [modifiers]          Press key (Enter, Tab, Escape, Backspace, etc.)
  upload <selector> <file>...    Upload file(s) to a file input element
  select <selector> <value>      Set <select> element value
  evaluate <js_expression>       Execute JavaScript and return result
  screenshot [filepath]          Capture page screenshot (default: /tmp/cdp-screenshot.png)
  wait <selector> [timeout_ms]   Wait for element to appear (default: 5000ms)
  info                           Show connected browser info

Options:
  --port PORT      Chrome debugging port (default: 9222)
  --target INDEX   Tab index to target (default: 0, or 'active' for active tab)
"""

import socket
import struct
import hashlib
import base64
import os
import json
import sys
import time
import urllib.request


# =============================================================================
# Minimal WebSocket Client (stdlib only)
# =============================================================================

class WebSocket:
    """Minimal WebSocket client using Python stdlib only."""

    def __init__(self, url):
        parsed = url.replace("ws://", "").split("/", 1)
        host_port = parsed[0]
        path = "/" + (parsed[1] if len(parsed) > 1 else "")
        if ":" in host_port:
            host, port = host_port.rsplit(":", 1)
            port = int(port)
        else:
            host, port = host_port, 80
        self.sock = socket.create_connection((host, port), timeout=30)
        self._handshake(host, port, path)

    def _handshake(self, host, port, path):
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"\r\n"
        )
        self.sock.sendall(req.encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            chunk = self.sock.recv(1)
            if not chunk:
                raise ConnectionError("WebSocket handshake failed: connection closed")
            resp += chunk
        if b"101" not in resp.split(b"\r\n")[0]:
            raise ConnectionError(f"WebSocket handshake rejected: {resp.decode()}")

    def send(self, text):
        payload = text.encode("utf-8")
        frame = bytearray([0x81])  # FIN + text opcode
        mask_key = os.urandom(4)
        plen = len(payload)
        if plen < 126:
            frame.append(0x80 | plen)
        elif plen < 65536:
            frame.append(0x80 | 126)
            frame.extend(struct.pack(">H", plen))
        else:
            frame.append(0x80 | 127)
            frame.extend(struct.pack(">Q", plen))
        frame.extend(mask_key)
        frame.extend(bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload)))
        self.sock.sendall(frame)

    def recv(self):
        def _read_exact(n):
            buf = b""
            while len(buf) < n:
                chunk = self.sock.recv(n - len(buf))
                if not chunk:
                    raise ConnectionError("WebSocket connection closed")
                buf += chunk
            return buf

        while True:
            header = _read_exact(2)
            fin = header[0] & 0x80
            opcode = header[0] & 0x0F
            masked = header[1] & 0x80
            length = header[1] & 0x7F

            if length == 126:
                length = struct.unpack(">H", _read_exact(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", _read_exact(8))[0]

            mask = _read_exact(4) if masked else None
            data = _read_exact(length)
            if mask:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))

            if opcode == 0x08:  # Close
                raise ConnectionError("WebSocket closed by server")
            if opcode == 0x09:  # Ping → send Pong
                pong = bytearray([0x8A, 0x80 | len(data)])
                pong_mask = os.urandom(4)
                pong.extend(pong_mask)
                pong.extend(bytes(b ^ pong_mask[i % 4] for i, b in enumerate(data)))
                self.sock.sendall(pong)
                continue
            if opcode == 0x0A:  # Pong → ignore
                continue
            if opcode in (0x01, 0x02):  # Text or Binary
                return data.decode("utf-8")

    def close(self):
        try:
            self.sock.sendall(b"\x88\x80" + os.urandom(4))  # Close frame
        except Exception:
            pass
        self.sock.close()


# =============================================================================
# CDP Connection
# =============================================================================

class CDPConnection:
    """Chrome DevTools Protocol connection."""

    def __init__(self, port=9222, target_idx=0):
        self.port = port
        self.msg_id = 0
        self.ws = None
        self._connect(target_idx)

    def _connect(self, target_idx):
        url = f"http://localhost:{self.port}/json"
        try:
            data = json.loads(urllib.request.urlopen(url, timeout=5).read())
        except Exception as e:
            die(f"Cannot connect to Chrome on port {self.port}. "
                f"Is Chrome running with --remote-debugging-port={self.port}?\n"
                f"Error: {e}")
        pages = [t for t in data if t.get("type") == "page"]
        if not pages:
            die("No browser tabs found. Open at least one tab in Chrome.")
        if isinstance(target_idx, str) and target_idx == "active":
            target_idx = 0  # First page is typically the active one
        idx = min(int(target_idx), len(pages) - 1)
        ws_url = pages[idx]["webSocketDebuggerUrl"]
        self.ws = WebSocket(ws_url)

    def send(self, method, params=None):
        self.msg_id += 1
        cmd = {"id": self.msg_id, "method": method}
        if params:
            cmd["params"] = params
        self.ws.send(json.dumps(cmd))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.msg_id:
                if "error" in msg:
                    return {"error": msg["error"]}
                return msg.get("result", {})

    def close(self):
        if self.ws:
            self.ws.close()


# =============================================================================
# Helpers
# =============================================================================

def escape_css_selector(selector):
    """Escape a CSS selector for safe embedding in a JavaScript double-quoted string."""
    return selector.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')


def escape_js_string(value):
    """Escape an arbitrary value for safe embedding in a JavaScript double-quoted string."""
    return value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')


# =============================================================================
# High-Level Commands
# =============================================================================

def cmd_click(cdp, x, y):
    """Trusted mouse click: mouseMoved → mousePressed → mouseReleased."""
    x, y = float(x), float(y)
    cdp.send("Input.dispatchMouseEvent", {
        "type": "mouseMoved", "x": x, "y": y
    })
    cdp.send("Input.dispatchMouseEvent", {
        "type": "mousePressed", "x": x, "y": y,
        "button": "left", "clickCount": 1
    })
    result = cdp.send("Input.dispatchMouseEvent", {
        "type": "mouseReleased", "x": x, "y": y,
        "button": "left", "clickCount": 1
    })
    return {"status": "clicked", "x": x, "y": y, **result}


def cmd_hover(cdp, x, y):
    """Move mouse to coordinates (triggers hover menus/tooltips)."""
    x, y = float(x), float(y)
    result = cdp.send("Input.dispatchMouseEvent", {
        "type": "mouseMoved", "x": x, "y": y
    })
    return {"status": "hovered", "x": x, "y": y, **result}


def cmd_type(cdp, text):
    """Type text using CDP Input.insertText (works in contenteditable, rich editors)."""
    result = cdp.send("Input.insertText", {"text": text})
    return {"status": "typed", "length": len(text), **result}


# Key name mapping: user-friendly name → CDP key descriptor
_KEY_MAP = {
    "enter": ("Enter", "\r", 13),
    "return": ("Enter", "\r", 13),
    "tab": ("Tab", "\t", 9),
    "escape": ("Escape", "\x1b", 27),
    "esc": ("Escape", "\x1b", 27),
    "backspace": ("Backspace", "\x08", 8),
    "delete": ("Delete", "", 46),
    "space": (" ", " ", 32),
    "arrowup": ("ArrowUp", "", 38),
    "arrowdown": ("ArrowDown", "", 40),
    "arrowleft": ("ArrowLeft", "", 37),
    "arrowright": ("ArrowRight", "", 39),
    "home": ("Home", "", 36),
    "end": ("End", "", 35),
    "pageup": ("PageUp", "", 33),
    "pagedown": ("PageDown", "", 34),
}


def cmd_key(cdp, key_name, modifiers_str=""):
    """Press a key with optional modifiers (e.g., 'Enter', 'Tab', 'a ctrl')."""
    key_lower = key_name.lower()
    mod_flags = 0
    modifiers = [m.lower() for m in modifiers_str.split(",") if m.strip()] if modifiers_str else []
    if "alt" in modifiers:
        mod_flags |= 1
    if "ctrl" in modifiers or "control" in modifiers:
        mod_flags |= 2
    if "meta" in modifiers or "cmd" in modifiers:
        mod_flags |= 4
    if "shift" in modifiers:
        mod_flags |= 8

    if key_lower in _KEY_MAP:
        key, text, code = _KEY_MAP[key_lower]
    elif len(key_name) == 1:
        key = key_name
        text = key_name
        code = ord(key_name)
    else:
        key = key_name
        text = ""
        code = 0

    base = {
        "key": key,
        "code": f"Key{key.upper()}" if len(key) == 1 and key.isalpha() else key,
        "windowsVirtualKeyCode": code,
        "nativeVirtualKeyCode": code,
        "modifiers": mod_flags,
    }
    if text:
        base["text"] = text
        base["unmodifiedText"] = text

    cdp.send("Input.dispatchKeyEvent", {"type": "keyDown", **base})
    result = cdp.send("Input.dispatchKeyEvent", {"type": "keyUp", **base})
    return {"status": "key_pressed", "key": key, **result}


def cmd_upload(cdp, selector, files):
    """Upload files to a file input element identified by CSS selector."""
    safe_sel = escape_css_selector(selector)
    # Resolve the DOM node
    eval_result = cdp.send("Runtime.evaluate", {
        "expression": f'document.querySelector("{safe_sel}")',
        "returnByValue": False,
    })
    obj_id = eval_result.get("result", {}).get("objectId")
    if not obj_id:
        return {"error": f"Element not found: {selector}"}

    # Get DOM nodeId from the remote object
    node_info = cdp.send("DOM.describeNode", {"objectId": obj_id})
    node_id = node_info.get("node", {}).get("backendNodeId")
    if not node_id:
        return {"error": "Could not resolve DOM node for element"}

    # Set files on the input
    result = cdp.send("DOM.setFileInputFiles", {
        "files": files,
        "backendNodeId": node_id,
    })

    # Dispatch change event via JS to notify frameworks
    cdp.send("Runtime.evaluate", {
        "expression": f'''
            (function() {{
                var el = document.querySelector("{safe_sel}");
                if (el) {{
                    el.dispatchEvent(new Event("change", {{bubbles: true}}));
                    el.dispatchEvent(new Event("input", {{bubbles: true}}));
                }}
                return "events dispatched";
            }})()
        ''',
    })

    return {"status": "uploaded", "files": files, "selector": selector, **result}


def cmd_select(cdp, selector, value):
    """Set a <select> element's value and fire change events."""
    safe_sel = escape_css_selector(selector)
    safe_val = escape_js_string(value)
    result = cdp.send("Runtime.evaluate", {
        "expression": f'''
            (function() {{
                var el = document.querySelector("{safe_sel}");
                if (!el) return JSON.stringify({{error: "Element not found: {safe_sel}"}});
                if (el.tagName.toLowerCase() !== "select")
                    return JSON.stringify({{error: "Element is not a <select>: " + el.tagName}});
                el.value = "{safe_val}";
                el.dispatchEvent(new Event("change", {{bubbles: true}}));
                el.dispatchEvent(new Event("input", {{bubbles: true}}));
                var opt = el.options[el.selectedIndex];
                return JSON.stringify({{status: "selected", value: el.value, text: opt ? opt.text : ""}});
            }})()
        ''',
        "returnByValue": True,
    })
    inner = result.get("result", {}).get("value", "{}")
    try:
        return json.loads(inner)
    except json.JSONDecodeError:
        return {"status": "selected", "raw": inner}


def cmd_evaluate(cdp, expression):
    """Execute JavaScript and return the result."""
    result = cdp.send("Runtime.evaluate", {
        "expression": expression,
        "returnByValue": True,
        "awaitPromise": True,
    })
    val = result.get("result", {})
    if val.get("type") == "undefined":
        return {"result": None}
    ex = result.get("exceptionDetails")
    if ex:
        return {"error": ex.get("text", "JS exception"),
                "detail": ex.get("exception", {}).get("description", "")}
    return {"result": val.get("value", val.get("description", str(val)))}


def cmd_screenshot(cdp, filepath=None):
    """Capture page screenshot as PNG."""
    filepath = filepath or "/tmp/cdp-screenshot.png"
    result = cdp.send("Page.captureScreenshot", {"format": "png"})
    data = result.get("data", "")
    if data:
        import base64 as b64
        with open(filepath, "wb") as f:
            f.write(b64.b64decode(data))
        return {"status": "saved", "path": filepath, "size": os.path.getsize(filepath)}
    return {"error": "No screenshot data returned"}


def cmd_wait(cdp, selector, timeout_ms=5000):
    """Wait for element to appear in DOM (polls via evaluate)."""
    safe_sel = escape_css_selector(selector)
    timeout_ms = int(timeout_ms)
    start = time.time()
    deadline = start + timeout_ms / 1000.0
    while time.time() < deadline:
        result = cdp.send("Runtime.evaluate", {
            "expression": f'''
                (function() {{
                    var el = document.querySelector("{safe_sel}");
                    if (!el) return "not_found";
                    var r = el.getBoundingClientRect();
                    if (r.width === 0 && r.height === 0) return "hidden";
                    var s = window.getComputedStyle(el);
                    if (s.display === "none" || s.visibility === "hidden") return "hidden";
                    return "visible";
                }})()
            ''',
            "returnByValue": True,
        })
        status = result.get("result", {}).get("value", "not_found")
        if status == "visible":
            elapsed = int((time.time() - start) * 1000)
            return {"found": True, "elapsed_ms": elapsed}
        time.sleep(0.25)
    elapsed = int((time.time() - start) * 1000)
    return {"found": False, "elapsed_ms": elapsed, "last_status": status}


def cmd_info(port):
    """Show browser info and open tabs."""
    try:
        ver = json.loads(urllib.request.urlopen(
            f"http://localhost:{port}/json/version", timeout=5).read())
        tabs = json.loads(urllib.request.urlopen(
            f"http://localhost:{port}/json", timeout=5).read())
        pages = [t for t in tabs if t.get("type") == "page"]
        return {
            "browser": ver.get("Browser", "unknown"),
            "protocol": ver.get("Protocol-Version", "unknown"),
            "tabs": [{"index": i, "title": p.get("title", ""), "url": p.get("url", "")}
                     for i, p in enumerate(pages)]
        }
    except Exception as e:
        return {"error": str(e)}


def cmd_raw(cdp, method, params_json="{}"):
    """Send a raw CDP command."""
    try:
        params = json.loads(params_json)
    except json.JSONDecodeError:
        return {"error": f"Invalid JSON params: {params_json}"}
    return cdp.send(method, params)


# =============================================================================
# CLI
# =============================================================================

def die(msg):
    print(json.dumps({"error": msg}), file=sys.stderr)
    sys.exit(1)


def main():
    args = sys.argv[1:]
    port = 9222
    target = 0

    # Parse options
    while args and args[0].startswith("--"):
        opt = args.pop(0)
        if opt == "--port" and args:
            port = int(args.pop(0))
        elif opt == "--target" and args:
            target = args.pop(0)
            if target != "active":
                target = int(target)
        elif opt in ("--help", "-h"):
            print(__doc__)
            sys.exit(0)
        else:
            die(f"Unknown option: {opt}")

    if not args:
        print(__doc__)
        sys.exit(1)

    command = args[0].lower()

    # Info doesn't need WebSocket
    if command == "info":
        print(json.dumps(cmd_info(port), indent=2))
        return

    # Commands that need CDP connection
    cdp = CDPConnection(port, target)
    try:
        if command == "raw":
            method = args[1] if len(args) > 1 else die("Usage: raw <method> [params_json]")
            params_json = args[2] if len(args) > 2 else "{}"
            result = cmd_raw(cdp, method, params_json)
        elif command == "click":
            if len(args) < 3:
                die("Usage: click <x> <y>")
            result = cmd_click(cdp, args[1], args[2])
        elif command == "hover":
            if len(args) < 3:
                die("Usage: hover <x> <y>")
            result = cmd_hover(cdp, args[1], args[2])
        elif command == "type":
            if len(args) < 2:
                die("Usage: type <text>")
            result = cmd_type(cdp, " ".join(args[1:]))
        elif command == "key":
            if len(args) < 2:
                die("Usage: key <key> [modifiers]")
            mods = args[2] if len(args) > 2 else ""
            result = cmd_key(cdp, args[1], mods)
        elif command == "upload":
            if len(args) < 3:
                die("Usage: upload <selector> <file1> [file2...]")
            result = cmd_upload(cdp, args[1], args[2:])
        elif command == "select":
            if len(args) < 3:
                die("Usage: select <selector> <value>")
            result = cmd_select(cdp, args[1], args[2])
        elif command == "evaluate":
            if len(args) < 2:
                die("Usage: evaluate <js_expression>")
            result = cmd_evaluate(cdp, " ".join(args[1:]))
        elif command in ("screenshot", "ss"):
            filepath = args[1] if len(args) > 1 else None
            result = cmd_screenshot(cdp, filepath)
        elif command == "wait":
            if len(args) < 2:
                die("Usage: wait <selector> [timeout_ms]")
            timeout = args[2] if len(args) > 2 else "5000"
            result = cmd_wait(cdp, args[1], timeout)
        else:
            die(f"Unknown command: {command}. Run with --help for usage.")
            return
        print(json.dumps(result, indent=2, ensure_ascii=False))
    finally:
        cdp.close()


if __name__ == "__main__":
    main()
