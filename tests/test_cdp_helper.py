"""Tests for cdp-helper.py — the lightweight CDP client.

Covers:
  - WebSocket frame encoding (send) and decoding (recv) for various payload sizes
  - CDP message serialization with incrementing IDs
  - CLI argument parsing for all commands
  - Key mapping table completeness and modifier flag calculation
  - Coordinate parsing for click/hover commands
  - CSS selector injection surface in upload/select/wait commands
  - High-level command functions (click, hover, type, key, upload, select, evaluate, screenshot, wait, raw)

Run:
  python3 -m pytest tests/test_cdp_helper.py -v
"""

import importlib
import json
import os
import struct
import sys
import types
from io import BytesIO
from unittest.mock import MagicMock, patch, call

import pytest

# ---------------------------------------------------------------------------
# Import the module under test from its file path
# ---------------------------------------------------------------------------
SCRIPT_PATH = os.path.join(
    os.path.dirname(__file__), os.pardir,
    "skills", "browser-control", "scripts", "cdp-helper.py",
)

def _import_cdp_helper():
    """Import cdp-helper.py as a module despite the hyphen in its name."""
    spec = importlib.util.spec_from_file_location("cdp_helper", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

cdp_helper = _import_cdp_helper()


# ============================================================================
# 1. WebSocket Frame Encoding (WebSocket.send)
# ============================================================================

class TestWsFrameEncoding:
    """Test that WebSocket.send() produces correctly formatted frames."""

    def _make_ws(self):
        """Create a WebSocket instance with a mocked socket (skip handshake)."""
        ws = object.__new__(cdp_helper.WebSocket)
        ws.sock = MagicMock()
        return ws

    # -- small payload (< 126 bytes) -----------------------------------------

    def test_small_payload(self):
        ws = self._make_ws()
        ws.send("hi")
        frame = ws.sock.sendall.call_args[0][0]
        # First byte: FIN + text opcode = 0x81
        assert frame[0] == 0x81
        # Second byte: mask bit set + length
        plen = len("hi".encode())
        assert frame[1] & 0x80  # mask bit set
        assert frame[1] & 0x7F == plen
        # 4-byte mask key follows
        mask_key = frame[2:6]
        assert len(mask_key) == 4
        # Masked payload
        masked_payload = frame[6:]
        decoded = bytes(b ^ mask_key[i % 4] for i, b in enumerate(masked_payload))
        assert decoded == b"hi"

    # -- 126-byte boundary payload -------------------------------------------

    def test_medium_payload_boundary_125(self):
        """125 bytes should still use the single-byte length."""
        ws = self._make_ws()
        text = "a" * 125
        ws.send(text)
        frame = ws.sock.sendall.call_args[0][0]
        assert frame[1] & 0x7F == 125

    def test_medium_payload_126(self):
        """126 bytes should trigger the 2-byte extended length."""
        ws = self._make_ws()
        text = "a" * 126
        ws.send(text)
        frame = ws.sock.sendall.call_args[0][0]
        assert frame[1] & 0x7F == 126
        ext_len = struct.unpack(">H", bytes(frame[2:4]))[0]
        assert ext_len == 126

    def test_medium_payload_200(self):
        ws = self._make_ws()
        text = "b" * 200
        ws.send(text)
        frame = ws.sock.sendall.call_args[0][0]
        assert frame[1] & 0x7F == 126
        ext_len = struct.unpack(">H", bytes(frame[2:4]))[0]
        assert ext_len == 200

    # -- 65536-byte boundary payload -----------------------------------------

    def test_large_payload_65535(self):
        """65535 bytes should still use 2-byte extended length."""
        ws = self._make_ws()
        text = "c" * 65535
        ws.send(text)
        frame = ws.sock.sendall.call_args[0][0]
        assert frame[1] & 0x7F == 126
        ext_len = struct.unpack(">H", bytes(frame[2:4]))[0]
        assert ext_len == 65535

    def test_large_payload_65536(self):
        """65536 bytes should trigger 8-byte extended length."""
        ws = self._make_ws()
        text = "d" * 65536
        ws.send(text)
        frame = ws.sock.sendall.call_args[0][0]
        assert frame[1] & 0x7F == 127
        ext_len = struct.unpack(">Q", bytes(frame[2:10]))[0]
        assert ext_len == 65536

    # -- masking is always applied -------------------------------------------

    def test_mask_key_is_random(self):
        """Two consecutive sends should produce different mask keys."""
        ws = self._make_ws()
        ws.send("test")
        frame1 = bytes(ws.sock.sendall.call_args[0][0])
        ws.send("test")
        frame2 = bytes(ws.sock.sendall.call_args[0][0])
        mask1 = frame1[2:6]
        mask2 = frame2[2:6]
        # Extremely unlikely to be the same
        assert mask1 != mask2

    def test_payload_is_correctly_masked(self):
        """Verify round-trip: unmask the masked payload to get the original."""
        ws = self._make_ws()
        original = "Hello, CDP!"
        ws.send(original)
        frame = ws.sock.sendall.call_args[0][0]
        mask_key = frame[2:6]
        masked = frame[6:]
        decoded = bytes(b ^ mask_key[i % 4] for i, b in enumerate(masked))
        assert decoded == original.encode("utf-8")

    # -- unicode payload -----------------------------------------------------

    def test_unicode_payload(self):
        ws = self._make_ws()
        text = "cafe\u0301"  # e + combining accent
        ws.send(text)
        frame = ws.sock.sendall.call_args[0][0]
        payload_bytes = text.encode("utf-8")
        mask_key = frame[2:6]
        masked = frame[6:]
        decoded = bytes(b ^ mask_key[i % 4] for i, b in enumerate(masked))
        assert decoded == payload_bytes


# ============================================================================
# 2. WebSocket Frame Decoding (WebSocket.recv)
# ============================================================================

class TestWsFrameDecoding:
    """Test WebSocket.recv() parsing of incoming frames."""

    def _make_ws_with_data(self, raw_bytes):
        """Create a WebSocket whose socket yields *raw_bytes* on recv()."""
        ws = object.__new__(cdp_helper.WebSocket)
        buf = BytesIO(raw_bytes)

        def fake_recv(n):
            data = buf.read(n)
            if not data:
                raise ConnectionError("WebSocket connection closed")
            return data

        ws.sock = MagicMock()
        ws.sock.recv = fake_recv
        return ws

    def _build_unmasked_text_frame(self, text):
        """Build a server-sent unmasked text frame (servers do not mask)."""
        payload = text.encode("utf-8")
        frame = bytearray()
        frame.append(0x81)  # FIN + text
        plen = len(payload)
        if plen < 126:
            frame.append(plen)  # no mask bit for server frames
        elif plen < 65536:
            frame.append(126)
            frame.extend(struct.pack(">H", plen))
        else:
            frame.append(127)
            frame.extend(struct.pack(">Q", plen))
        frame.extend(payload)
        return bytes(frame)

    def test_recv_small_text_frame(self):
        raw = self._build_unmasked_text_frame('{"id":1,"result":{}}')
        ws = self._make_ws_with_data(raw)
        msg = ws.recv()
        assert json.loads(msg) == {"id": 1, "result": {}}

    def test_recv_medium_text_frame(self):
        text = "x" * 200
        raw = self._build_unmasked_text_frame(text)
        ws = self._make_ws_with_data(raw)
        assert ws.recv() == text

    def test_recv_large_text_frame(self):
        text = "y" * 70000
        raw = self._build_unmasked_text_frame(text)
        ws = self._make_ws_with_data(raw)
        assert ws.recv() == text

    def test_recv_close_frame_raises(self):
        # Close frame: opcode 0x08, no payload
        raw = bytes([0x88, 0x00])
        ws = self._make_ws_with_data(raw)
        with pytest.raises(ConnectionError, match="closed by server"):
            ws.recv()

    def test_recv_ping_sends_pong_then_reads_next(self):
        """Ping frames should be answered with Pong, then recv continues."""
        ping_payload = b"ping-data"
        ping_frame = bytearray([0x89, len(ping_payload)])
        ping_frame.extend(ping_payload)
        text_frame = self._build_unmasked_text_frame("after-ping")

        raw = bytes(ping_frame) + text_frame
        ws = self._make_ws_with_data(raw)
        ws.sock.sendall = MagicMock()  # capture pong

        result = ws.recv()
        assert result == "after-ping"
        # Verify pong was sent
        ws.sock.sendall.assert_called_once()
        pong_frame = ws.sock.sendall.call_args[0][0]
        assert pong_frame[0] == 0x8A  # Pong opcode with FIN

    def test_recv_pong_frame_is_ignored(self):
        """Pong frames should be silently skipped."""
        pong_frame = bytes([0x8A, 0x00])  # Pong, no payload
        text_frame = self._build_unmasked_text_frame("after-pong")
        raw = pong_frame + text_frame
        ws = self._make_ws_with_data(raw)
        result = ws.recv()
        assert result == "after-pong"

    def test_recv_binary_frame(self):
        """Binary frames (opcode 0x02) should also be returned as decoded text."""
        payload = b'{"binary":true}'
        frame = bytearray([0x82, len(payload)])  # FIN + binary
        frame.extend(payload)
        ws = self._make_ws_with_data(bytes(frame))
        result = ws.recv()
        assert json.loads(result) == {"binary": True}


# ============================================================================
# 3. CDP Message Serialization (CDPConnection.send)
# ============================================================================

class TestCDPMessageSerialization:
    """Test that CDPConnection.send() formats JSON correctly."""

    def _make_cdp(self, responses=None):
        """Create a CDPConnection without connecting, with mock WS responses."""
        cdp = object.__new__(cdp_helper.CDPConnection)
        cdp.msg_id = 0
        cdp.ws = MagicMock()
        cdp.port = 9222
        # Queue up responses for ws.recv()
        if responses is None:
            responses = []
        response_iter = iter(responses)
        cdp.ws.recv = lambda: next(response_iter)
        return cdp

    def test_incrementing_ids(self):
        cdp = self._make_cdp([
            json.dumps({"id": 1, "result": {"a": 1}}),
            json.dumps({"id": 2, "result": {"b": 2}}),
            json.dumps({"id": 3, "result": {"c": 3}}),
        ])
        cdp.send("Method.one")
        cdp.send("Method.two")
        cdp.send("Method.three")

        calls = cdp.ws.send.call_args_list
        assert len(calls) == 3
        for i, c in enumerate(calls, 1):
            msg = json.loads(c[0][0])
            assert msg["id"] == i

    def test_method_is_set(self):
        cdp = self._make_cdp([json.dumps({"id": 1, "result": {}})])
        cdp.send("Page.navigate", {"url": "https://example.com"})
        sent = json.loads(cdp.ws.send.call_args[0][0])
        assert sent["method"] == "Page.navigate"
        assert sent["params"] == {"url": "https://example.com"}

    def test_no_params_key_when_none(self):
        cdp = self._make_cdp([json.dumps({"id": 1, "result": {}})])
        cdp.send("Target.getTargets")
        sent = json.loads(cdp.ws.send.call_args[0][0])
        assert "params" not in sent

    def test_error_response_returned(self):
        cdp = self._make_cdp([json.dumps({"id": 1, "error": {"code": -32600, "message": "bad"}})])
        result = cdp.send("Bad.method")
        assert "error" in result
        assert result["error"]["code"] == -32600

    def test_skips_events_until_matching_id(self):
        """Events (messages without matching id) should be skipped."""
        cdp = self._make_cdp([
            json.dumps({"method": "Network.requestWillBeSent", "params": {}}),
            json.dumps({"method": "Page.loadEventFired", "params": {}}),
            json.dumps({"id": 1, "result": {"done": True}}),
        ])
        result = cdp.send("Page.enable")
        assert result == {"done": True}


# ============================================================================
# 4. CLI Argument Parsing
# ============================================================================

class TestCLIArgParsing:
    """Test main() argument parsing and dispatch for each command."""

    def _run_main(self, argv_list):
        """Run main() with mocked sys.argv and CDPConnection."""
        with patch.object(sys, "argv", ["cdp-helper.py"] + argv_list):
            with patch.object(cdp_helper, "CDPConnection") as MockCDP:
                mock_cdp = MagicMock()
                MockCDP.return_value = mock_cdp
                # Default send return
                mock_cdp.send.return_value = {}
                with patch("builtins.print") as mock_print:
                    cdp_helper.main()
                return mock_cdp, mock_print, MockCDP

    def test_port_option(self):
        """--port should be passed to CDPConnection."""
        with patch.object(sys, "argv", ["cdp-helper.py", "--port", "9333", "click", "10", "20"]):
            with patch.object(cdp_helper, "CDPConnection") as MockCDP:
                mock_cdp = MagicMock()
                MockCDP.return_value = mock_cdp
                mock_cdp.send.return_value = {}
                with patch("builtins.print"):
                    cdp_helper.main()
                MockCDP.assert_called_once_with(9333, 0)

    def test_target_option_numeric(self):
        with patch.object(sys, "argv", ["cdp-helper.py", "--target", "2", "click", "0", "0"]):
            with patch.object(cdp_helper, "CDPConnection") as MockCDP:
                mock_cdp = MagicMock()
                MockCDP.return_value = mock_cdp
                mock_cdp.send.return_value = {}
                with patch("builtins.print"):
                    cdp_helper.main()
                MockCDP.assert_called_once_with(9222, 2)

    def test_target_option_active(self):
        with patch.object(sys, "argv", ["cdp-helper.py", "--target", "active", "click", "0", "0"]):
            with patch.object(cdp_helper, "CDPConnection") as MockCDP:
                mock_cdp = MagicMock()
                MockCDP.return_value = mock_cdp
                mock_cdp.send.return_value = {}
                with patch("builtins.print"):
                    cdp_helper.main()
                MockCDP.assert_called_once_with(9222, "active")

    def test_click_command(self):
        mock_cdp, mock_print, _ = self._run_main(["click", "100", "200"])
        # click dispatches 3 mouse events
        assert mock_cdp.send.call_count == 3
        methods = [c[0][0] for c in mock_cdp.send.call_args_list]
        assert all(m == "Input.dispatchMouseEvent" for m in methods)

    def test_hover_command(self):
        mock_cdp, _, _ = self._run_main(["hover", "50", "75"])
        mock_cdp.send.assert_called_once_with("Input.dispatchMouseEvent", {
            "type": "mouseMoved", "x": 50.0, "y": 75.0,
        })

    def test_type_command_joins_args(self):
        mock_cdp, _, _ = self._run_main(["type", "hello", "world"])
        mock_cdp.send.assert_called_once_with("Input.insertText", {"text": "hello world"})

    def test_key_command(self):
        mock_cdp, _, _ = self._run_main(["key", "Enter"])
        assert mock_cdp.send.call_count == 2  # keyDown + keyUp

    def test_key_command_with_modifiers(self):
        mock_cdp, _, _ = self._run_main(["key", "a", "ctrl,shift"])
        assert mock_cdp.send.call_count == 2
        # Check that modifiers are passed
        first_call_params = mock_cdp.send.call_args_list[0][0][1]
        assert first_call_params["modifiers"] == (2 | 8)  # ctrl=2, shift=8

    def test_upload_command(self):
        """Upload dispatches to cmd_upload; verify the first CDP call is Runtime.evaluate with the selector."""
        mock_cdp, _, _ = self._run_main(["upload", "#file-input", "/tmp/a.txt", "/tmp/b.txt"])
        # The first call should be Runtime.evaluate to resolve the selector.
        # Subsequent calls depend on the return value, which the mock returns as {}.
        # cmd_upload detects missing objectId and returns early, so we just verify
        # that the first call used the right method and selector.
        first_call = mock_cdp.send.call_args_list[0]
        assert first_call[0][0] == "Runtime.evaluate"
        assert "#file-input" in first_call[0][1]["expression"]

    def test_select_command(self):
        mock_cdp, _, _ = self._run_main(["select", "#dropdown", "option-2"])
        mock_cdp.send.assert_called_once()
        call_args = mock_cdp.send.call_args
        assert call_args[0][0] == "Runtime.evaluate"

    def test_evaluate_command_joins_args(self):
        mock_cdp, _, _ = self._run_main(["evaluate", "1", "+", "2"])
        mock_cdp.send.assert_called_once()
        call_args = mock_cdp.send.call_args
        assert call_args[0][0] == "Runtime.evaluate"
        assert "1 + 2" in call_args[0][1]["expression"]

    def test_screenshot_default_path(self):
        mock_cdp, _, _ = self._run_main(["screenshot"])
        mock_cdp.send.assert_called_once_with("Page.captureScreenshot", {"format": "png"})

    def test_screenshot_custom_path(self):
        mock_cdp, _, _ = self._run_main(["screenshot", "/tmp/custom.png"])
        mock_cdp.send.assert_called_once_with("Page.captureScreenshot", {"format": "png"})

    def test_screenshot_alias_ss(self):
        mock_cdp, _, _ = self._run_main(["ss"])
        mock_cdp.send.assert_called_once_with("Page.captureScreenshot", {"format": "png"})

    def test_wait_command_default_timeout(self):
        mock_cdp, _, _ = self._run_main(["wait", ".my-element"])
        # Wait calls Runtime.evaluate in a loop; at least one call
        assert mock_cdp.send.call_count >= 1
        call_args = mock_cdp.send.call_args_list[0]
        assert call_args[0][0] == "Runtime.evaluate"

    def test_raw_command(self):
        mock_cdp, _, _ = self._run_main(["raw", "Page.navigate", '{"url":"https://example.com"}'])
        mock_cdp.send.assert_called_once_with("Page.navigate", {"url": "https://example.com"})

    def test_info_command_no_cdp_connection(self):
        """info command should NOT create a CDPConnection."""
        with patch.object(sys, "argv", ["cdp-helper.py", "info"]):
            with patch.object(cdp_helper, "CDPConnection") as MockCDP:
                with patch.object(cdp_helper, "cmd_info", return_value={"browser": "test"}):
                    with patch("builtins.print"):
                        cdp_helper.main()
                MockCDP.assert_not_called()

    def test_no_command_shows_help_and_exits(self):
        with patch.object(sys, "argv", ["cdp-helper.py"]):
            with pytest.raises(SystemExit) as exc_info:
                with patch("builtins.print"):
                    cdp_helper.main()
            assert exc_info.value.code == 1

    def test_help_flag_exits_zero(self):
        with patch.object(sys, "argv", ["cdp-helper.py", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                with patch("builtins.print"):
                    cdp_helper.main()
            assert exc_info.value.code == 0

    def test_unknown_option_calls_die(self):
        with patch.object(sys, "argv", ["cdp-helper.py", "--bogus", "click", "0", "0"]):
            with pytest.raises(SystemExit):
                cdp_helper.main()

    def test_unknown_command_calls_die(self):
        with patch.object(sys, "argv", ["cdp-helper.py", "nosuchcmd"]):
            with patch.object(cdp_helper, "CDPConnection") as MockCDP:
                mock_cdp = MagicMock()
                MockCDP.return_value = mock_cdp
                with pytest.raises(SystemExit):
                    cdp_helper.main()

    def test_click_missing_args_calls_die(self):
        with patch.object(sys, "argv", ["cdp-helper.py", "click", "10"]):
            with patch.object(cdp_helper, "CDPConnection") as MockCDP:
                mock_cdp = MagicMock()
                MockCDP.return_value = mock_cdp
                with pytest.raises(SystemExit):
                    cdp_helper.main()


# ============================================================================
# 5. Key Mapping & Modifier Handling
# ============================================================================

class TestKeyMapping:
    """Test the _KEY_MAP dictionary and modifier flag calculation."""

    def test_key_map_has_common_keys(self):
        km = cdp_helper._KEY_MAP
        expected_keys = [
            "enter", "return", "tab", "escape", "esc",
            "backspace", "delete", "space",
            "arrowup", "arrowdown", "arrowleft", "arrowright",
            "home", "end", "pageup", "pagedown",
        ]
        for k in expected_keys:
            assert k in km, f"Missing key: {k}"

    def test_key_map_enter_values(self):
        key, text, code = cdp_helper._KEY_MAP["enter"]
        assert key == "Enter"
        assert text == "\r"
        assert code == 13

    def test_key_map_tab_values(self):
        key, text, code = cdp_helper._KEY_MAP["tab"]
        assert key == "Tab"
        assert text == "\t"
        assert code == 9

    def test_key_map_escape_values(self):
        key, text, code = cdp_helper._KEY_MAP["escape"]
        assert key == "Escape"
        assert code == 27

    def test_key_map_backspace_values(self):
        key, text, code = cdp_helper._KEY_MAP["backspace"]
        assert key == "Backspace"
        assert code == 8

    def test_key_map_arrow_keys(self):
        arrows = {
            "arrowup": ("ArrowUp", 38),
            "arrowdown": ("ArrowDown", 40),
            "arrowleft": ("ArrowLeft", 37),
            "arrowright": ("ArrowRight", 39),
        }
        for alias, (expected_key, expected_code) in arrows.items():
            key, text, code = cdp_helper._KEY_MAP[alias]
            assert key == expected_key
            assert code == expected_code

    def test_key_map_return_is_alias_for_enter(self):
        assert cdp_helper._KEY_MAP["enter"] == cdp_helper._KEY_MAP["return"]

    def test_key_map_esc_is_alias_for_escape(self):
        assert cdp_helper._KEY_MAP["esc"] == cdp_helper._KEY_MAP["escape"]

    def test_modifier_flags_alt(self):
        cdp = self._make_cdp()
        cdp_helper.cmd_key(cdp, "a", "alt")
        params = json.loads(cdp.ws.send.call_args_list[0][0][0])["params"]
        assert params["modifiers"] == 1

    def test_modifier_flags_ctrl(self):
        cdp = self._make_cdp()
        cdp_helper.cmd_key(cdp, "a", "ctrl")
        params = json.loads(cdp.ws.send.call_args_list[0][0][0])["params"]
        assert params["modifiers"] == 2

    def test_modifier_flags_control_alias(self):
        cdp = self._make_cdp()
        cdp_helper.cmd_key(cdp, "a", "control")
        params = json.loads(cdp.ws.send.call_args_list[0][0][0])["params"]
        assert params["modifiers"] == 2

    def test_modifier_flags_meta(self):
        cdp = self._make_cdp()
        cdp_helper.cmd_key(cdp, "a", "meta")
        params = json.loads(cdp.ws.send.call_args_list[0][0][0])["params"]
        assert params["modifiers"] == 4

    def test_modifier_flags_cmd_alias(self):
        cdp = self._make_cdp()
        cdp_helper.cmd_key(cdp, "a", "cmd")
        params = json.loads(cdp.ws.send.call_args_list[0][0][0])["params"]
        assert params["modifiers"] == 4

    def test_modifier_flags_shift(self):
        cdp = self._make_cdp()
        cdp_helper.cmd_key(cdp, "a", "shift")
        params = json.loads(cdp.ws.send.call_args_list[0][0][0])["params"]
        assert params["modifiers"] == 8

    def test_modifier_flags_combined(self):
        cdp = self._make_cdp()
        cdp_helper.cmd_key(cdp, "a", "ctrl,shift,alt")
        params = json.loads(cdp.ws.send.call_args_list[0][0][0])["params"]
        # alt=1 + ctrl=2 + shift=8 = 11
        assert params["modifiers"] == 11

    def test_single_char_key_generates_code(self):
        """A single character key should produce code like 'KeyA'."""
        cdp = self._make_cdp()
        cdp_helper.cmd_key(cdp, "a", "")
        params = json.loads(cdp.ws.send.call_args_list[0][0][0])["params"]
        assert params["key"] == "a"
        assert params["code"] == "KeyA"
        assert params["windowsVirtualKeyCode"] == ord("a")
        assert params["text"] == "a"

    def test_unknown_key_name(self):
        """Unknown multi-char key names should still work with code=0."""
        cdp = self._make_cdp()
        cdp_helper.cmd_key(cdp, "F13", "")
        params = json.loads(cdp.ws.send.call_args_list[0][0][0])["params"]
        assert params["key"] == "F13"
        assert params["windowsVirtualKeyCode"] == 0
        assert "text" not in params  # empty text is not added

    def _make_cdp(self):
        """Create a mock CDPConnection for cmd_key testing."""
        cdp = object.__new__(cdp_helper.CDPConnection)
        cdp.msg_id = 0
        cdp.ws = MagicMock()
        cdp.ws.recv = MagicMock(side_effect=[
            json.dumps({"id": 1, "result": {}}),
            json.dumps({"id": 2, "result": {}}),
        ])
        return cdp


# ============================================================================
# 6. Coordinate Parsing (click, hover)
# ============================================================================

class TestCoordinateParsing:
    """Test that click/hover properly parse and convert coordinate arguments."""

    def _make_cdp(self):
        cdp = object.__new__(cdp_helper.CDPConnection)
        cdp.msg_id = 0
        cdp.ws = MagicMock()
        call_count = [0]

        def fake_recv():
            call_count[0] += 1
            return json.dumps({"id": call_count[0], "result": {}})

        cdp.ws.recv = fake_recv
        return cdp

    def test_click_integer_coords(self):
        cdp = self._make_cdp()
        result = cdp_helper.cmd_click(cdp, "100", "200")
        assert result["x"] == 100.0
        assert result["y"] == 200.0

    def test_click_float_coords(self):
        cdp = self._make_cdp()
        result = cdp_helper.cmd_click(cdp, "100.5", "200.7")
        assert result["x"] == 100.5
        assert result["y"] == 200.7

    def test_hover_integer_coords(self):
        cdp = self._make_cdp()
        result = cdp_helper.cmd_hover(cdp, "50", "75")
        assert result["x"] == 50.0
        assert result["y"] == 75.0

    def test_hover_float_coords(self):
        cdp = self._make_cdp()
        result = cdp_helper.cmd_hover(cdp, "0.5", "0.5")
        assert result["x"] == 0.5
        assert result["y"] == 0.5

    def test_click_zero_coords(self):
        cdp = self._make_cdp()
        result = cdp_helper.cmd_click(cdp, "0", "0")
        assert result["x"] == 0.0
        assert result["y"] == 0.0

    def test_click_negative_coords(self):
        """Negative coords should not raise (Chrome may reject them but we pass through)."""
        cdp = self._make_cdp()
        result = cdp_helper.cmd_click(cdp, "-10", "-20")
        assert result["x"] == -10.0
        assert result["y"] == -20.0

    def test_click_dispatches_three_events(self):
        cdp = self._make_cdp()
        cdp_helper.cmd_click(cdp, "100", "200")
        assert cdp.ws.send.call_count == 3
        sent_msgs = [json.loads(c[0][0]) for c in cdp.ws.send.call_args_list]
        types = [m["params"]["type"] for m in sent_msgs]
        assert types == ["mouseMoved", "mousePressed", "mouseReleased"]

    def test_click_button_is_left(self):
        cdp = self._make_cdp()
        cdp_helper.cmd_click(cdp, "10", "20")
        sent_msgs = [json.loads(c[0][0]) for c in cdp.ws.send.call_args_list]
        # mousePressed and mouseReleased should have button=left
        for msg in sent_msgs[1:]:
            assert msg["params"]["button"] == "left"
            assert msg["params"]["clickCount"] == 1


# ============================================================================
# 7. High-Level Command Functions
# ============================================================================

class TestHighLevelCommands:
    """Test the high-level cmd_* functions."""

    def _make_cdp(self, responses=None):
        cdp = object.__new__(cdp_helper.CDPConnection)
        cdp.msg_id = 0
        cdp.ws = MagicMock()
        if responses is None:
            call_count = [0]
            def fake_recv():
                call_count[0] += 1
                return json.dumps({"id": call_count[0], "result": {}})
            cdp.ws.recv = fake_recv
        else:
            response_iter = iter(responses)
            cdp.ws.recv = lambda: next(response_iter)
        return cdp

    # -- cmd_type -----------------------------------------------------------

    def test_cmd_type_sends_insert_text(self):
        cdp = self._make_cdp()
        result = cdp_helper.cmd_type(cdp, "hello")
        sent = json.loads(cdp.ws.send.call_args[0][0])
        assert sent["method"] == "Input.insertText"
        assert sent["params"]["text"] == "hello"
        assert result["status"] == "typed"
        assert result["length"] == 5

    def test_cmd_type_empty_string(self):
        cdp = self._make_cdp()
        result = cdp_helper.cmd_type(cdp, "")
        assert result["length"] == 0

    # -- cmd_evaluate -------------------------------------------------------

    def test_cmd_evaluate_returns_value(self):
        cdp = self._make_cdp([
            json.dumps({"id": 1, "result": {"result": {"type": "number", "value": 42}}})
        ])
        result = cdp_helper.cmd_evaluate(cdp, "21 + 21")
        assert result["result"] == 42

    def test_cmd_evaluate_undefined_returns_none(self):
        cdp = self._make_cdp([
            json.dumps({"id": 1, "result": {"result": {"type": "undefined"}}})
        ])
        result = cdp_helper.cmd_evaluate(cdp, "void 0")
        assert result["result"] is None

    def test_cmd_evaluate_exception(self):
        cdp = self._make_cdp([
            json.dumps({
                "id": 1,
                "result": {
                    "result": {"type": "object"},
                    "exceptionDetails": {
                        "text": "ReferenceError",
                        "exception": {"description": "x is not defined"},
                    },
                },
            })
        ])
        result = cdp_helper.cmd_evaluate(cdp, "x")
        assert "error" in result
        assert "ReferenceError" in result["error"]

    # -- cmd_screenshot -----------------------------------------------------

    def test_cmd_screenshot_saves_file(self, tmp_path):
        import base64 as b64
        img_data = b64.b64encode(b"fake-png-data").decode()
        cdp = self._make_cdp([
            json.dumps({"id": 1, "result": {"data": img_data}})
        ])
        filepath = str(tmp_path / "test.png")
        result = cdp_helper.cmd_screenshot(cdp, filepath)
        assert result["status"] == "saved"
        assert result["path"] == filepath
        with open(filepath, "rb") as f:
            assert f.read() == b"fake-png-data"

    def test_cmd_screenshot_no_data(self):
        cdp = self._make_cdp([
            json.dumps({"id": 1, "result": {}})
        ])
        result = cdp_helper.cmd_screenshot(cdp, "/tmp/no-data.png")
        assert "error" in result

    def test_cmd_screenshot_default_path(self):
        import base64 as b64
        img_data = b64.b64encode(b"fake").decode()
        cdp = self._make_cdp([
            json.dumps({"id": 1, "result": {"data": img_data}})
        ])
        with patch("builtins.open", MagicMock()):
            with patch("os.path.getsize", return_value=4):
                result = cdp_helper.cmd_screenshot(cdp)
        assert result["path"] == "/tmp/cdp-screenshot.png"

    # -- cmd_raw ------------------------------------------------------------

    def test_cmd_raw_sends_method_and_params(self):
        cdp = self._make_cdp()
        result = cdp_helper.cmd_raw(cdp, "Page.reload", '{"ignoreCache": true}')
        sent = json.loads(cdp.ws.send.call_args[0][0])
        assert sent["method"] == "Page.reload"
        assert sent["params"] == {"ignoreCache": True}

    def test_cmd_raw_invalid_json(self):
        cdp = self._make_cdp()
        result = cdp_helper.cmd_raw(cdp, "Page.reload", "not-json{")
        assert "error" in result
        assert "Invalid JSON" in result["error"]

    def test_cmd_raw_default_empty_params(self):
        """cmd_raw with no params_json defaults to '{}', which is an empty dict.
        CDPConnection.send treats empty dict as falsy, so 'params' key is omitted."""
        cdp = self._make_cdp()
        cdp_helper.cmd_raw(cdp, "Page.enable")
        sent = json.loads(cdp.ws.send.call_args[0][0])
        # Empty dict {} is falsy in Python, so CDPConnection.send omits the params key
        assert "params" not in sent

    # -- cmd_upload ---------------------------------------------------------

    def test_cmd_upload_element_not_found(self):
        cdp = self._make_cdp([
            json.dumps({"id": 1, "result": {"result": {"type": "object", "subtype": "null"}}})
        ])
        result = cdp_helper.cmd_upload(cdp, "#missing", ["/tmp/f.txt"])
        assert "error" in result
        assert "not found" in result["error"]

    def test_cmd_upload_success(self):
        cdp = self._make_cdp([
            # Runtime.evaluate returns objectId
            json.dumps({"id": 1, "result": {"result": {"objectId": "obj-123"}}}),
            # DOM.describeNode returns backendNodeId
            json.dumps({"id": 2, "result": {"node": {"backendNodeId": 456}}}),
            # DOM.setFileInputFiles succeeds
            json.dumps({"id": 3, "result": {}}),
            # Runtime.evaluate (change event)
            json.dumps({"id": 4, "result": {}}),
        ])
        result = cdp_helper.cmd_upload(cdp, "#file-input", ["/tmp/a.txt"])
        assert result["status"] == "uploaded"
        assert result["files"] == ["/tmp/a.txt"]

    # -- cmd_select ---------------------------------------------------------

    def test_cmd_select_success(self):
        cdp = self._make_cdp([
            json.dumps({
                "id": 1,
                "result": {
                    "result": {
                        "type": "string",
                        "value": json.dumps({"status": "selected", "value": "opt1", "text": "Option 1"}),
                    }
                }
            })
        ])
        result = cdp_helper.cmd_select(cdp, "#dropdown", "opt1")
        assert result["status"] == "selected"
        assert result["value"] == "opt1"

    def test_cmd_select_element_not_found(self):
        cdp = self._make_cdp([
            json.dumps({
                "id": 1,
                "result": {
                    "result": {
                        "type": "string",
                        "value": json.dumps({"error": "Element not found: #missing"}),
                    }
                }
            })
        ])
        result = cdp_helper.cmd_select(cdp, "#missing", "v")
        assert "error" in result

    def test_cmd_select_non_json_result(self):
        cdp = self._make_cdp([
            json.dumps({
                "id": 1,
                "result": {
                    "result": {
                        "type": "string",
                        "value": "not-json",
                    }
                }
            })
        ])
        result = cdp_helper.cmd_select(cdp, "#sel", "v")
        assert result["status"] == "selected"
        assert result["raw"] == "not-json"

    # -- cmd_wait -----------------------------------------------------------

    def test_cmd_wait_found_immediately(self):
        cdp = self._make_cdp([
            json.dumps({
                "id": 1,
                "result": {"result": {"type": "string", "value": "visible"}}
            })
        ])
        result = cdp_helper.cmd_wait(cdp, ".target", 5000)
        assert result["found"] is True
        assert result["elapsed_ms"] >= 0

    def test_cmd_wait_timeout(self):
        """Element never appears; should return found=False after timeout."""
        responses = [
            json.dumps({
                "id": i,
                "result": {"result": {"type": "string", "value": "not_found"}}
            })
            for i in range(1, 100)
        ]
        cdp = self._make_cdp(responses)
        result = cdp_helper.cmd_wait(cdp, ".never", 200)  # 200ms timeout
        assert result["found"] is False
        assert result["last_status"] == "not_found"

    def test_cmd_wait_hidden_then_visible(self):
        """Element is hidden first, then becomes visible."""
        cdp = self._make_cdp([
            json.dumps({"id": 1, "result": {"result": {"type": "string", "value": "hidden"}}}),
            json.dumps({"id": 2, "result": {"result": {"type": "string", "value": "hidden"}}}),
            json.dumps({"id": 3, "result": {"result": {"type": "string", "value": "visible"}}}),
        ])
        result = cdp_helper.cmd_wait(cdp, ".appearing", 10000)
        assert result["found"] is True

    # -- cmd_key (key dispatch) ---------------------------------------------

    def test_cmd_key_enter(self):
        cdp = self._make_cdp()
        result = cdp_helper.cmd_key(cdp, "Enter")
        assert result["status"] == "key_pressed"
        assert result["key"] == "Enter"

    def test_cmd_key_dispatches_keydown_and_keyup(self):
        cdp = self._make_cdp()
        cdp_helper.cmd_key(cdp, "Tab")
        sent = [json.loads(c[0][0]) for c in cdp.ws.send.call_args_list]
        assert sent[0]["params"]["type"] == "keyDown"
        assert sent[1]["params"]["type"] == "keyUp"


# ============================================================================
# 8. CSS Selector Usage in Commands
# ============================================================================

class TestCSSSelectors:
    """Test how CSS selectors are passed to CDP commands.

    The script currently injects selectors directly into JS template strings.
    These tests document the current behavior and highlight the injection surface.
    """

    def _make_cdp(self, responses=None):
        cdp = object.__new__(cdp_helper.CDPConnection)
        cdp.msg_id = 0
        cdp.ws = MagicMock()
        if responses is None:
            call_count = [0]
            def fake_recv():
                call_count[0] += 1
                return json.dumps({"id": call_count[0], "result": {}})
            cdp.ws.recv = fake_recv
        else:
            response_iter = iter(responses)
            cdp.ws.recv = lambda: next(response_iter)
        return cdp

    def test_normal_selector_in_upload(self):
        cdp = self._make_cdp()
        cdp_helper.cmd_upload(cdp, "#file-input", ["/tmp/f.txt"])
        sent = json.loads(cdp.ws.send.call_args_list[0][0][0])
        assert '#file-input' in sent["params"]["expression"]

    def test_selector_with_attribute_in_upload(self):
        cdp = self._make_cdp()
        cdp_helper.cmd_upload(cdp, 'input[type="file"]', ["/tmp/f.txt"])
        sent = json.loads(cdp.ws.send.call_args_list[0][0][0])
        assert 'input[type=' in sent["params"]["expression"]

    def test_normal_selector_in_wait(self):
        cdp = self._make_cdp([
            json.dumps({"id": 1, "result": {"result": {"type": "string", "value": "visible"}}})
        ])
        cdp_helper.cmd_wait(cdp, ".my-class", 5000)
        sent = json.loads(cdp.ws.send.call_args_list[0][0][0])
        assert '.my-class' in sent["params"]["expression"]

    def test_selector_with_child_combinator_in_select(self):
        cdp = self._make_cdp()
        cdp_helper.cmd_select(cdp, "form > select.country", "CA")
        sent = json.loads(cdp.ws.send.call_args_list[0][0][0])
        assert 'form > select.country' in sent["params"]["expression"]


# ============================================================================
# 9. WebSocket Handshake
# ============================================================================

class TestWebSocketHandshake:
    """Test the WebSocket handshake path."""

    def test_handshake_sends_upgrade_request(self):
        mock_sock = MagicMock()
        # Simulate 101 Switching Protocols response
        response = b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n\r\n"
        mock_sock.recv = MagicMock(side_effect=list(response[i:i+1] for i in range(len(response))))

        with patch("socket.create_connection", return_value=mock_sock):
            ws = cdp_helper.WebSocket("ws://localhost:9222/devtools/page/ABC")

        # Verify sendall was called with the handshake
        sent_data = mock_sock.sendall.call_args[0][0].decode()
        assert "GET /devtools/page/ABC HTTP/1.1" in sent_data
        assert "Upgrade: websocket" in sent_data
        assert "Sec-WebSocket-Key:" in sent_data
        assert "Sec-WebSocket-Version: 13" in sent_data

    def test_handshake_failure_raises(self):
        mock_sock = MagicMock()
        response = b"HTTP/1.1 400 Bad Request\r\n\r\n"
        mock_sock.recv = MagicMock(side_effect=list(response[i:i+1] for i in range(len(response))))

        with patch("socket.create_connection", return_value=mock_sock):
            with pytest.raises(ConnectionError, match="handshake rejected"):
                cdp_helper.WebSocket("ws://localhost:9222/devtools/page/XYZ")

    def test_handshake_connection_closed_raises(self):
        mock_sock = MagicMock()
        mock_sock.recv = MagicMock(return_value=b"")

        with patch("socket.create_connection", return_value=mock_sock):
            with pytest.raises(ConnectionError, match="handshake failed"):
                cdp_helper.WebSocket("ws://localhost:9222/devtools/page/XYZ")

    def test_url_parsing_default_port(self):
        """ws://hostname/path should default to port 80."""
        mock_sock = MagicMock()
        response = b"HTTP/1.1 101 Switching Protocols\r\n\r\n"
        mock_sock.recv = MagicMock(side_effect=list(response[i:i+1] for i in range(len(response))))

        with patch("socket.create_connection", return_value=mock_sock) as mock_connect:
            cdp_helper.WebSocket("ws://myhost/some/path")
        mock_connect.assert_called_once_with(("myhost", 80), timeout=30)


# ============================================================================
# 10. WebSocket.close()
# ============================================================================

class TestWebSocketClose:
    """Test WebSocket close frame."""

    def test_close_sends_close_frame(self):
        ws = object.__new__(cdp_helper.WebSocket)
        ws.sock = MagicMock()
        ws.close()
        # Should send a close frame starting with 0x88 0x80
        sent = ws.sock.sendall.call_args[0][0]
        assert sent[0] == 0x88
        assert sent[1] == 0x80
        assert len(sent) == 6  # 2 header + 4 mask key
        ws.sock.close.assert_called_once()

    def test_close_handles_socket_error(self):
        ws = object.__new__(cdp_helper.WebSocket)
        ws.sock = MagicMock()
        ws.sock.sendall.side_effect = OSError("broken pipe")
        # Should not raise
        ws.close()
        ws.sock.close.assert_called_once()


# ============================================================================
# 11. die() helper
# ============================================================================

class TestDieHelper:
    """Test the die() function."""

    def test_die_prints_json_to_stderr_and_exits(self):
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.stderr") as mock_stderr:
                cdp_helper.die("something went wrong")
        assert exc_info.value.code == 1

    def test_die_output_is_valid_json(self, capsys):
        with pytest.raises(SystemExit):
            cdp_helper.die("test error message")
        captured = capsys.readouterr()
        parsed = json.loads(captured.err)
        assert parsed["error"] == "test error message"


# ============================================================================
# 12. CDPConnection._connect()
# ============================================================================

class TestCDPConnectionConnect:
    """Test CDPConnection initialization and tab selection."""

    def test_connect_with_active_target(self):
        tabs_data = [
            {"type": "page", "title": "Tab 1", "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/A"},
            {"type": "page", "title": "Tab 2", "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/B"},
        ]
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = json.dumps(tabs_data).encode()
            with patch.object(cdp_helper, "WebSocket") as MockWS:
                cdp = cdp_helper.CDPConnection(9222, "active")
                # "active" resolves to index 0
                MockWS.assert_called_once_with("ws://localhost:9222/devtools/page/A")

    def test_connect_with_tab_index(self):
        tabs_data = [
            {"type": "page", "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/A"},
            {"type": "page", "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/B"},
        ]
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = json.dumps(tabs_data).encode()
            with patch.object(cdp_helper, "WebSocket") as MockWS:
                cdp = cdp_helper.CDPConnection(9222, 1)
                MockWS.assert_called_once_with("ws://localhost:9222/devtools/page/B")

    def test_connect_clamps_index_to_last_tab(self):
        tabs_data = [
            {"type": "page", "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/A"},
        ]
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = json.dumps(tabs_data).encode()
            with patch.object(cdp_helper, "WebSocket") as MockWS:
                cdp = cdp_helper.CDPConnection(9222, 99)
                MockWS.assert_called_once_with("ws://localhost:9222/devtools/page/A")

    def test_connect_filters_non_page_types(self):
        tabs_data = [
            {"type": "background_page", "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/BG"},
            {"type": "page", "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/A"},
        ]
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = json.dumps(tabs_data).encode()
            with patch.object(cdp_helper, "WebSocket") as MockWS:
                cdp = cdp_helper.CDPConnection(9222, 0)
                MockWS.assert_called_once_with("ws://localhost:9222/devtools/page/A")

    def test_connect_no_pages_dies(self):
        tabs_data = [{"type": "background_page"}]
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.read.return_value = json.dumps(tabs_data).encode()
            with pytest.raises(SystemExit):
                cdp_helper.CDPConnection(9222, 0)

    def test_connect_http_error_dies(self):
        with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
            with pytest.raises(SystemExit):
                cdp_helper.CDPConnection(9222, 0)


# ============================================================================
# 13. cmd_info
# ============================================================================

class TestCmdInfo:
    """Test the info command (no WebSocket needed)."""

    def test_cmd_info_success(self):
        version_data = {"Browser": "Chrome/120", "Protocol-Version": "1.3"}
        tabs_data = [
            {"type": "page", "title": "Google", "url": "https://google.com"},
            {"type": "page", "title": "GitHub", "url": "https://github.com"},
            {"type": "background_page", "title": "Extension"},
        ]

        def fake_urlopen(url, timeout=5):
            resp = MagicMock()
            if "version" in url:
                resp.read.return_value = json.dumps(version_data).encode()
            else:
                resp.read.return_value = json.dumps(tabs_data).encode()
            return resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = cdp_helper.cmd_info(9222)

        assert result["browser"] == "Chrome/120"
        assert result["protocol"] == "1.3"
        assert len(result["tabs"]) == 2  # only pages
        assert result["tabs"][0]["title"] == "Google"
        assert result["tabs"][1]["index"] == 1

    def test_cmd_info_connection_error(self):
        with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
            result = cdp_helper.cmd_info(9222)
        assert "error" in result
