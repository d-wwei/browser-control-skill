# Chrome Control — Browser Automation for AI Coding Agents

[中文说明](./README_CN.md)

Control your local Chrome browser directly from AI coding agents. Access any page you can access — including pages behind corporate authentication (SSO, MFA, security gateways).

Supports **macOS** and **Windows**. Auto-detects platform and uses the appropriate approach.

Works with **Claude Code**, **Codex**, **Cursor**, **Gemini CLI**, **Windsurf**, and any agent that can execute shell commands.

## What Makes This Different

This skill is not trying to be the most powerful browser automation stack. It is optimized for one specific job: letting a coding agent use the user's real Chrome session to work on authenticated pages with the lowest possible setup cost.

- **Real Chrome session first**: it is designed around inheriting the user's existing login state, instead of creating a fresh automated browser session.
- **Built for authenticated/internal pages**: SSO, MFA, and corporate gateways are the primary target, not an edge case.
- **Pragmatic cross-platform design**: macOS uses native AppleScript with nearly zero setup; Windows uses CDP where that is the practical choice.
- **Skill-first packaging**: this repository is structured to drop directly into Claude Code, Codex, Cursor, Gemini CLI, and similar agents, instead of asking users to assemble an automation stack first.
- **Explicit preflight checks**: agents are expected to verify prerequisites before acting, and to stop and guide the user if the environment is not ready.

## Why This Skill?

AI coding agents have several ways to access web content, but none of them can handle authenticated pages behind corporate login systems:

| | Chrome Control (this skill) | agent-browser (Vercel) | WebFetch / Firecrawl |
|---|---|---|---|
| **Browser** | User's own Chrome | Playwright Chromium | No browser (HTTP only) |
| **Login session** | Fully inherited — if you're logged in, Claude can access it | Fresh session, must re-login | None |
| **Corporate auth (SSO/MFA)** | Works — it's your real browser | Usually blocked (automation fingerprint + cookie isolation) | Blocked |
| **Install dependencies** | None on macOS; Node.js on Windows | npm + Chromium (~500MB) | API key |
| **Screenshots** | macOS: no / Windows: yes | Yes | No |
| **Headless mode** | No (Chrome must be open) | Yes | Inherently headless |
| **Cross-platform** | macOS + Windows | macOS / Windows / Linux | All platforms |

### When to use what

- **Authenticated / internal pages** → **Chrome Control**. This is the only reliable option. Other tools cannot pass corporate login systems.
- **Automating public websites** (no login needed) → **agent-browser** is more capable, with screenshot, PDF, and headless batch support.
- **Quick scraping of public pages** → **WebFetch** is the lightest — one call, no setup.

## How It Works

| Platform | Mechanism | Dependencies |
|---|---|---|
| **macOS** | AppleScript communicates directly with Chrome | None (native macOS) |
| **Windows** | Chrome DevTools Protocol (CDP) via agent-browser | Node.js + agent-browser |

Both approaches operate on the user's real Chrome instance, inheriting the full login session.

## Setup

### macOS

One-time Chrome setting:

> Chrome menu bar → **View** → **Developer** → **Allow JavaScript from Apple Events**

That's it. No other setup needed.

Before the agent performs any browser action, it should verify the prerequisite with:

```bash
osascript -e 'tell application "Google Chrome" to get name'
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.title"'
```

If the JavaScript check fails, the agent should stop and guide the user to:

- Open Chrome
- Enable `View -> Developer -> Allow JavaScript from Apple Events`
- Approve any macOS automation permission prompt
- Retry the check

### Windows

1. Install [Node.js](https://nodejs.org/)
2. Install agent-browser:
   ```powershell
   npm install -g agent-browser
   agent-browser install
   ```
3. See SKILL.md for the optional `chrome-debug.ps1` helper script

Before the agent performs any browser action, it should verify the prerequisite with:

```powershell
where agent-browser
Invoke-RestMethod -Uri "http://127.0.0.1:9222/json/version"
```

If either check fails, the agent should stop and guide the user to:

- Install Node.js
- Run `npm install -g agent-browser`
- Run `agent-browser install`
- Fully close Chrome
- Restart Chrome with `--remote-debugging-port=9222`
- Retry the check

## Agent Installation

### Claude Code

```bash
claude install-skill /path/to/browser-control-skill
```
Or copy `skills/chrome-control/` into your project's skill directory.

### Codex (OpenAI)

Copy `adapters/codex/AGENTS.md` into your project root, or append its contents to your existing `AGENTS.md`.

### Cursor

Copy `adapters/cursor/.cursorrules` into your project root, or append its contents to your existing `.cursorrules`.

### Gemini CLI

Copy `adapters/gemini/GEMINI.md` into your project root.

### Windsurf

Copy `adapters/windsurf/.windsurfrules` into your project root, or append its contents to your existing `.windsurfrules`.

### Other agents

Copy `AGENT_INSTRUCTIONS.md` into your project, or paste its contents into the agent's system prompt / custom instructions.

## Usage

The agent should always:

1. Detect the platform.
2. Run the platform-specific preflight check.
3. Stop and guide the user through setup if the check fails.
4. Only continue with browser automation after the prerequisite is confirmed.
5. If the page is lazy-loaded or infinite-scroll, scroll the real browser page first to load more content before trying other reading strategies.

Once installed, the agent can:

- **Read any page you're logged into**: "Read the content of my current Chrome tab"
- **Navigate and click**: "Click the Settings tab" or "Go to https://..."
- **Extract data**: "Extract all the links on this page"
- **Fill forms**: "Fill in the search box with..."

## Example

```
You: Read the content of my current Chrome page
Agent: [extracts page text via AppleScript (macOS) or CDP (Windows)]

You: Click on the "Reports" tab
Agent: [finds and clicks the element]

You: Navigate to https://internal.company.com/dashboard
Agent: [navigates the active tab to the URL]
```

## Requirements

### macOS
- Google Chrome
- "Allow JavaScript from Apple Events" enabled
- AppleScript preflight check passes

### Windows
- Google Chrome
- Node.js
- agent-browser (`npm install -g agent-browser`)
- Chrome started with `--remote-debugging-port=9222`
- Windows preflight check passes

## Limitations

- Cannot log in on behalf of the user — the user must be authenticated first
- macOS: no screenshot support via AppleScript; Chrome must be in foreground
- Windows: Chrome must be restarted with debugging flag each session
- Very large pages need paginated reading

## License

MIT
