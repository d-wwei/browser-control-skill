# Chrome Control — Browser Automation for AI Coding Agents

[中文说明](./README_CN.md)

Give your AI coding agent direct access to your Chrome browser — including pages behind corporate SSO, MFA, and security gateways.

No extensions. No servers. No API keys. Just your real Chrome, controlled through native OS mechanisms.

Works with **Claude Code**, **Codex**, **Cursor**, **Gemini CLI**, **Windsurf**, and any agent that can execute shell commands.

## Why This Exists

Every AI coding agent can fetch public web pages. None of them can access the pages you actually need — behind corporate login, VPN, or MFA.

This skill solves that by operating on **your real Chrome instance**, inheriting your full login session. If you can see it in Chrome, the agent can read and interact with it.

## How It's Different

There are many browser automation tools for AI agents. Here's how this one is positioned:

| | Chrome Control | Chrome DevTools MCP | agent-browser / Playwright | WebFetch / Firecrawl | Browserbase |
|---|---|---|---|---|---|
| **What it is** | A documentation skill — agents learn browser control through instructions | Official Chrome MCP server; talks to Chrome via CDP | Headless browser automation library | HTTP-based content extraction | Cloud-hosted browser sessions |
| **Browser** | User's own Chrome | User's Chrome (requires debug flag) | Launches separate Chromium | No browser | Remote Chromium |
| **Login session** | Fully inherited | Inherited (if Chrome is running) | Fresh session each time | None | Fresh session |
| **Corporate auth** | Works — it's your browser | Works (same Chrome) | Usually blocked | Blocked | Blocked |
| **Setup** | macOS: 1 checkbox; Windows: npm install | npm install + Chrome restart with flag | npm + Chromium (~500MB) | API key | API key + account |
| **Agent support** | Claude Code, Codex, Cursor, Gemini CLI, Windsurf | Claude Code (MCP only) | Framework-dependent | Most agents | Framework-dependent |
| **Architecture** | Zero-dependency docs | MCP server process | Library / MCP server | API service | Cloud API |

### When to use what

- **Authenticated / internal pages** → **Chrome Control**. The only option that inherits your real login state with near-zero setup.
- **Deep browser inspection** (network, performance, debugging) → **Chrome DevTools MCP**. More powerful, but requires Chrome restart with `--remote-debugging-port` and only works via MCP protocol.
- **Automated testing of public sites** → **agent-browser / Playwright**. Better for headless batch operations, screenshots, PDF generation.
- **Quick scraping of public content** → **WebFetch / Firecrawl**. Lightest — one HTTP call, no browser needed.
- **Parallel browser sessions at scale** → **Browserbase**. Cloud-hosted, isolated, but no login session inheritance.

## Design Principles

This skill is intentionally minimal:

1. **Pure documentation, zero infrastructure** — The entire skill is a set of instructions that teach agents how to use `osascript` (macOS) or `agent-browser` (Windows). No extension, no server process, no runtime dependency.

2. **Real session first** — Designed around inheriting the user's existing Chrome login, not creating fresh automated sessions.

3. **Structured reasoning** — Agents follow an EVALUATE → OBSERVE → PLAN → ACT cycle before each action, reducing blind clicks and wasted tool calls.

4. **Safety boundaries** — Built-in blacklists for banking, payment, and auth sites. Password fields and payment buttons are never touched. Pre-action URL verification is mandatory.

5. **Tab preservation** — Agents always open new tabs; the user's existing tabs are never navigated away.

6. **Multi-agent packaging** — One skill, adapted for 5+ agent formats. Same behavior whether you use Claude Code, Codex, Cursor, Gemini CLI, or Windsurf.

## How It Works

| Platform | Mechanism | Dependencies |
|---|---|---|
| **macOS** | AppleScript communicates directly with Chrome | None (native macOS) |
| **Windows** | Chrome DevTools Protocol via agent-browser | Node.js + agent-browser |

Both approaches operate on the user's real Chrome instance. The skill auto-detects the platform (`uname -s`) and uses the appropriate method.

## Setup

### macOS

One-time Chrome setting:

> Chrome menu bar → **View** → **Developer** → **Allow JavaScript from Apple Events**

That's it. No other setup needed.

### Windows

1. Install [Node.js](https://nodejs.org/)
2. Install agent-browser:
   ```powershell
   npm install -g agent-browser
   agent-browser install
   ```
3. Start Chrome with debug port: `chrome.exe --remote-debugging-port=9222`

## Agent Installation

### Claude Code

```bash
claude install-skill /path/to/browser-control-skill
```

### Codex (OpenAI)

Copy `adapters/codex/AGENTS.md` into your project root.

### Cursor

Copy `adapters/cursor/.cursorrules` into your project root, or append to your existing `.cursorrules`.

### Gemini CLI

Copy `adapters/gemini/GEMINI.md` into your project root.

### Windsurf

Copy `adapters/windsurf/.windsurfrules` into your project root, or append to your existing `.windsurfrules`.

### Other Agents

Copy `AGENT_INSTRUCTIONS.md` into your project, or paste its contents into the agent's system prompt.

## Usage

Once installed, talk to the agent naturally. Use phrases like "in my Chrome" to signal browser control:

- **Read authenticated pages**: "Read the content of my current Chrome tab"
- **Navigate**: "Open https://internal.company.com/dashboard in my Chrome"
- **Click**: "Click the Settings tab"
- **Extract data**: "Extract all links on this page"
- **Fill forms**: "Fill in the search box with quarterly report"

The agent automatically:
1. Detects the platform
2. Runs preflight checks
3. Guides you through setup if anything is missing
4. Opens new tabs for navigation (never touches your existing tabs)
5. Follows the EVALUATE → OBSERVE → PLAN → ACT cycle for each action

### Quick Start

1. Open the target page in Chrome and log in normally
2. Tell the agent what you want to do
3. The agent controls Chrome and returns results

## Roadmap

This skill is Phase 1 of a larger browser tools evolution:

```
Phase 1 (current)          Phase 1.5                Phase 2                  Phase 3+
Pure documentation skill → Chrome DevTools MCP   → WebMCP integration    → Site experience
AppleScript + CDP           integration               (when Chrome Stable      caching &
Zero dependencies           Deep browser inspection   supports it, est.       memory
                                                      2026 H2+)
```

The design ensures each phase builds on the previous one rather than replacing it. Even when WebMCP arrives, the current AppleScript/CDP approach remains as a reliable fallback.

## Security

These rules are enforced — the agent will refuse operations that violate them:

- **Sensitive site blacklist**: Banking, payment, auth, and cloud console sites are read-only (no clicks, fills, or JS execution)
- **Password fields**: Never filled or clicked
- **Payment buttons**: Never clicked (pay, purchase, checkout, subscribe, etc.)
- **Pre-action URL check**: Before interacting with any page, the agent verifies the URL against the blacklist

## Requirements

### macOS
- Google Chrome
- "Allow JavaScript from Apple Events" enabled

### Windows
- Google Chrome + Node.js
- agent-browser (`npm install -g agent-browser`)
- Chrome started with `--remote-debugging-port=9222`

## Limitations

- Cannot log in on behalf of the user — you must be authenticated first
- macOS: Chrome must be open (AppleScript cannot control a hidden browser)
- Windows: Chrome must be restarted with debugging flag each session
- Very large pages need paginated reading
- One action at a time — complex workflows may require multiple turns

## License

MIT
