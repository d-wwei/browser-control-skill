# CDP Proxy Mode — Full API Reference

HTTP-to-CDP bridge proxy that connects to the user's daily Chrome. All operations via simple `curl` calls. Works on macOS, Linux, and Windows.

## Setup

```bash
# Run preflight + auto-start proxy
bash "${SKILL_DIR}/scripts/check-deps.sh"
```

The proxy listens on `localhost:3456`. Singleton: if already running, new instances detect it and exit.

## CDP Proxy API

```bash
# List user's open tabs
curl -s http://localhost:3456/targets

# Create new background tab (auto-waits for load)
curl -s "http://localhost:3456/new?url=https://example.com"

# Page info
curl -s "http://localhost:3456/info?target=ID"

# Execute arbitrary JS (the most powerful primitive)
curl -s -X POST "http://localhost:3456/eval?target=ID" -d 'document.title'

# JS click (simple, fast)
curl -s -X POST "http://localhost:3456/click?target=ID" -d 'button.submit'

# Real mouse click (CDP Input.dispatchMouseEvent — trusted, bypasses anti-automation)
curl -s -X POST "http://localhost:3456/clickAt?target=ID" -d 'button.upload'

# File upload (bypasses OS file dialog)
curl -s -X POST "http://localhost:3456/setFiles?target=ID" -d '{"selector":"input[type=file]","files":["/path/to/file.png"]}'

# Scroll (triggers lazy-load, 800ms wait)
curl -s "http://localhost:3456/scroll?target=ID&y=3000"
curl -s "http://localhost:3456/scroll?target=ID&direction=bottom"

# Screenshot (captures current render including video frames)
curl -s "http://localhost:3456/screenshot?target=ID&file=/tmp/shot.png"

# Navigate / back
curl -s "http://localhost:3456/navigate?target=ID&url=URL"
curl -s "http://localhost:3456/back?target=ID"

# Close tab
curl -s "http://localhost:3456/close?target=ID"

# Health check
curl -s http://localhost:3456/health
```

## CDP Advanced Write Operations

Keyboard input, file upload, rich text editor fill, select/dropdown, hover trigger, iframe penetration.

**Full reference**: `modules/cdp-write-ops.md` — load when you need keyboard input, file upload, rich text fill, dropdown, hover, or iframe operations.

## CDP Technical Notes

- **Tab isolation**: Each tab has its own `targetId`. Sub-agents create and manage their own tabs.
- **Page load waiting**: Proxy polls `document.readyState === 'complete'` with 15s timeout.
- **Lazy-load**: `/scroll` to bottom triggers lazy-load with 800ms wait.
- **DOM beyond viewport**: Carousels, collapsed sections, hidden tabs — content exists in DOM but isn't visible. Think in data structures (containers, attributes, node relationships) to access hidden content.
- **Shadow DOM / iframe boundaries**: `/eval` with recursive traversal can penetrate all layers.
- **Media extraction**: Use `/eval` to get image URLs from DOM directly — more precise than full-page screenshot.
- **Video analysis**: Control `<video>` elements via `/eval` (seek, play, pause), then `/screenshot` to capture specific frames.
