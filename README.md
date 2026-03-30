# Browser Control Skill (Remixed)

Full browser control skill for AI coding agents. Multi-channel web access with real Chrome session inheritance.

> Remixed from [browser-control-skill](https://github.com/d-wwei/browser-control-skill) (d-wwei) and [web-access](https://github.com/eze-is/web-access) (一泽Eze).

## What It Does

Gives any AI coding agent the ability to control the user's real Chrome browser — including pages behind corporate authentication (SSO, MFA, security gateways). Multi-channel tool selection from lightweight search to full CDP automation.

## Key Capabilities

| Capability | Source |
|-----------|--------|
| Multi-channel dispatch (WebSearch → WebFetch → Jina → curl → CDP) | web-access |
| Real Chrome session inheritance (zero credential management) | Both |
| Three-layer safety system (domain blacklist + element check + operation confirmation) | browser-control-skill |
| DOM-to-Markdown converter (preserves tables, code blocks, lists) | browser-control-skill |
| CDP Proxy (HTTP-to-CDP bridge, simple curl calls) | web-access |
| CDP Helper (Python, zero-dependency, keyboard/upload/select/hover) | browser-control-skill |
| Sub-agent parallel dispatch (tab-level isolation) | web-access |
| Site experience memory (per-domain knowledge accumulation) | web-access |
| EOPA reasoning cycle (Evaluate-Observe-Plan-Act) | browser-control-skill |
| "Browse like a human" philosophy | web-access |
| Virtual scrolling & SPA crawler | browser-control-skill |
| Console & network interception | browser-control-skill |
| Annotated screenshots | browser-control-skill |
| Information verification framework | web-access |
| macOS + Linux + Windows support | Combined |

## Architecture

```
skills/browser-control/
  SKILL.md                          # Core: unified skill definition
  scripts/
    cdp-proxy.mjs                   # HTTP-to-CDP bridge proxy (Node.js 22+)
    cdp-helper.py                   # Python CDP client (zero-dep, keyboard/upload/hover)
    check-deps.sh                   # Environment validator + proxy auto-launcher
    match-site.sh                   # Site experience matcher
  references/
    cdp-api.md                      # CDP API documentation
    site-patterns/                  # Per-domain operational experience (runtime-generated)
adapters/
  codex/AGENTS.md                   # OpenAI Codex adapter
  gemini/GEMINI.md                  # Google Gemini CLI adapter
  cursor/.cursorrules               # Cursor IDE adapter
  windsurf/.windsurfrules           # Windsurf IDE adapter
```

## Quick Start

### Claude Code
```bash
# Clone and install
git clone <this-repo> ~/.claude/skills/browser-control
# The skill auto-loads when referenced
```

### Other Agents
Copy the appropriate adapter file to your project root.

## Platform Support

| Platform | Basic Mode | CDP Mode |
|----------|-----------|----------|
| macOS | AppleScript (zero-dep) | CDP Proxy + CDP Helper |
| Linux | CDP Proxy | CDP Proxy + CDP Helper |
| Windows | CDP Proxy | CDP Proxy + CDP Helper + optional agent-browser |

## Setup

1. **Chrome**: Open `chrome://inspect/#remote-debugging`, enable "Allow remote debugging"
2. **macOS extra**: Chrome → View → Developer → Allow JavaScript from Apple Events
3. **Node.js 22+**: Required for CDP Proxy
4. **Python 3.6+**: Required for CDP Helper (optional, only for advanced write operations)

## Comparison

| Feature | This Skill | Chrome DevTools MCP | Playwright | WebFetch |
|---------|:---------:|:------------------:|:----------:|:--------:|
| Real login session | Yes | No | No | No |
| Multi-channel dispatch | Yes | No | No | N/A |
| Zero-dep basic mode (macOS) | Yes | No | No | N/A |
| Three-layer safety | Yes | Partial | No | N/A |
| Sub-agent parallel dispatch | Yes | No | Manual | No |
| Site experience memory | Yes | No | No | No |
| Rich text editor support | Yes | Yes | Yes | No |
| Multi-agent adapters | 5 agents | Claude only | Framework | Claude only |

## License

MIT
