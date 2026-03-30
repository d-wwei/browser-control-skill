English | [中文](README.md)

# Humans and AI Can Finally Share a Browser

You're in the foreground, it's in the background. Ask it for help, and it takes over your page — clicking buttons, filling forms, uploading files, typing in rich text editors. Tell it to research on its own, and it quietly opens tabs in parallel. Shared login sessions, safety boundaries, works across 5 AI platforms.

---

## Let's Be Clear: This Is Not a "Web Reader"

Most AI web access tools can only **read** pages — scrape text, extract content, return summaries.

Browser Control Skill can **control** your browser:

- Click buttons, links, and menu items — including dynamic elements rendered by React/Vue frameworks
- Fill forms — compatible with native inputs and React controlled components, values won't get swallowed by the framework
- Type in Notion, Slack, and Gmail's rich text editors — via CDP's `Input.insertText`, even contenteditable areas work
- Keyboard shortcuts — Enter to submit, Tab between fields, Ctrl+A to select all
- Upload files — bypasses the OS file dialog, directly sets files on `<input type="file">`
- Operate dropdowns and hover menus — both standard `<select>` and custom div-based dropdowns
- Screenshots with element annotations — numbers every interactive element, crystal clear at a glance
- Intercept console logs and network requests — see what's happening behind the scenes when debugging web apps

**This is full browser control, not read-only content extraction.**

---

## The Problem: Humans and AI Can't Share a Browser

You're already logged into your company intranet, enterprise dashboards, and various SaaS platforms in Chrome. You want AI to help out —

But every existing solution breaks down somewhere:

**Playwright / Puppeteer** — Opens a brand new browser. Your login sessions? Gone. You'd have to log in again or wrestle with cookie exports. It's not even using your Chrome.

**Chrome DevTools MCP** — Can connect to your Chrome, but you and AI can't operate simultaneously. The moment the agent acts, your page jumps. No safety guardrails either — it can click your banking page just as easily.

**AppleScript-only solutions** — Can only target the "front window." You're reading docs, AI needs to fill a form — it hijacks your page. Serial execution only: researching 5 sites takes 5x the time.

**WebFetch / curl** — Can't access authenticated pages at all.

The common thread: **no existing solution lets humans and AI coexist peacefully in the same browser.**

---

## The Solution: Foreground Collaboration, Background Parallelism, One Shared Chrome

Browser Control Skill doesn't give AI a separate browser — it teaches AI to **share your Chrome with you**.

### Two Modes, Automatic Switching

```
/browse here help me fill out this form        ← you watch it work on your current page
/browse bg research these 5 companies           ← it works quietly in background tabs
/browse look up this company's info             ← auto-detects foreground vs background
```

| Mode | How It Works | Your Experience |
|------|-------------|----------------|
| **Foreground** (here) | AppleScript, targets your `front window` | You watch AI operate your page, every step visible |
| **Background** (bg) | CDP protocol, addresses tabs by `targetId` | AI opens its own tabs, your pages don't move |

Foreground operates through the UI layer; background operates through the protocol layer. That's why background mode **never touches your tabs** — it doesn't interact through the interface at all, but communicates directly with target tabs via Chrome's debugging protocol.

### Use Cases

**Scenario 1: You're on a page and need AI to help operate it**

You've opened an internal approval system and want AI to fill in a form.

```
/browse here change the applicant to John, set department to Engineering, then upload attachment.pdf from my desktop
```

AI operates right on the page you're looking at — fills text fields, selects dropdowns, uploads files. You watch every step and confirm before submitting.

**Scenario 2: You're working, AI researches in the background**

You're writing code and need AI to check 5 competitors' latest updates.

```
/browse bg research these 5 companies' websites and summarize their recent product updates
```

AI opens 5 tabs in the background, dispatches 5 sub-agents to research in parallel. Your Chrome interface is completely unaffected. When done, it delivers a summary.

**Scenario 3: Operating enterprise dashboards**

You're logged into Salesforce / Jira / Notion. AI inherits your session — not just reading data, but operating:

```
/browse here add a new row in this spreadsheet with these fields
/browse bg extract all ticket titles and statuses from this Jira sprint
/browse here write meeting notes in this Notion page
```

Read, click, fill, upload — all within your authenticated session. No API tokens needed.

---

## Safety: Shared Browser, Clear Rules

AI is operating your real browser with your real login sessions. Safety boundaries must be rock solid:

**Layer 1: Domain Blocklist** — Banking (Chase, Wells Fargo), payments (PayPal, Stripe), auth pages (accounts.google.com, Okta), cloud consoles (AWS, GCP, Azure) → automatically read-only, agent won't click or fill anything.

**Layer 2: Element-Level Protection** — Password fields are never filled. Payment buttons are never clicked. Bilingual detection: "pay," "checkout," "purchase," as well as Chinese equivalents.

**Layer 3: Action Confirmation** — Before submitting forms, sending messages, or deleting anything — agent asks you first.

Shared browser ≠ unlimited access. AI has hands, but you set the rules.

---

## Beyond Browser Control: 5-Level Channel Routing

Not every web task needs a browser. The skill automatically picks the lightest tool:

```
WebSearch → WebFetch → Jina → curl → CDP Browser
  snippets    extraction  Markdown   raw HTML   full control
```

Simple searches use WebSearch. Public page extraction uses WebFetch. Token-saving conversions use Jina. The browser only starts when login sessions, interactions, or heavy lifting are needed.

---

## Parallel Research: 5 Targets at Once

In background mode, the skill can dispatch multiple sub-agents, each with its own tab:

```
Main Agent: "Research these 5 competitors"
  ├─ Sub-Agent 1 → Competitor A (own tab)
  ├─ Sub-Agent 2 → Competitor B (own tab)
  ├─ Sub-Agent 3 → Competitor C (own tab)
  ├─ Sub-Agent 4 → Competitor D (own tab)
  └─ Sub-Agent 5 → Competitor E (own tab)
  → Each researches independently, closes its tab, reports back
```

All sub-agents share your one Chrome and one proxy process, operating different tabs via unique `targetId`s. Your pages are completely unaffected.

---

## Site Experience Memory

The skill remembers platform characteristics, effective strategies, and known pitfalls for sites it has operated on. Comes with 8 pre-loaded site profiles: Xiaohongshu, WeChat Official Accounts, Twitter, LinkedIn, GitHub, Notion, Google, Zhihu.

---

## Comparison

|  | Browser Control Skill | Chrome DevTools MCP | Playwright | WebFetch |
|--|:----:|:----:|:----:|:----:|
| Full browser control (click/fill/upload/keyboard) | ✅ | ✅ | ✅ | ❌ Read-only |
| Uses your logged-in Chrome | ✅ | ❌ | ❌ | ❌ |
| Human + AI can use simultaneously | ✅ Foreground/background | ❌ Interferes | ❌ Separate browser | — |
| Background parallel ops | ✅ Multi-tab | ❌ | Manual | ❌ |
| Three-layer safety | ✅ | Partial | ❌ | — |
| 5-level channel routing | ✅ | ❌ | ❌ | Fetch only |
| Site experience memory | ✅ | ❌ | ❌ | ❌ |
| Supported AI platforms | 5 | Claude only | Framework | Claude only |
| macOS zero-dependency | ✅ | ❌ | ❌ | — |

---

## Supports 5 AI Platforms

| Platform | Adapter File |
|----------|-------------|
| Claude Code | `skills/browse/SKILL.md` (`/browse` command ready) |
| OpenAI Codex | `adapters/codex/AGENTS.md` |
| Google Gemini CLI | `adapters/gemini/GEMINI.md` |
| Cursor | `adapters/cursor/.cursorrules` |
| Windsurf | `adapters/windsurf/.windsurfrules` |

Supports macOS, Linux, and Windows. macOS has an additional zero-dependency AppleScript foreground mode.

---

## Get Started in 3 Minutes

### Claude Code

```bash
# 1. Clone to skills directory
git clone https://github.com/d-wwei/browser-control-skill.git ~/.claude/skills/browser-control

# 2. Create symlink for /browse command
ln -sf ~/.claude/skills/browser-control/skills/browse ~/.claude/skills/browse

# 3. Chrome setup (one-time)
#    Open chrome://inspect/#remote-debugging
#    Check "Allow remote debugging for this browser instance"
#    macOS also: Chrome → View → Developer → Allow JavaScript from Apple Events
```

Done. Try it:

```
/browse here read the title of the current page
/browse bg open example.com and tell me what's on it
```

### Other Platforms

Copy the adapter file from `adapters/` to your project root.

---

## Architecture

```
skills/
  browse/SKILL.md                     # /browse command entry (foreground/background routing)
  browser-control/
    SKILL.md                          # Core skill definition (384 lines + 10 on-demand modules)
    modules/                          # Loaded on demand (agent reads what it needs)
    scripts/
      cdp-proxy.mjs                   # HTTP-to-CDP bridge proxy (background mode core)
      cdp-helper.py                   # CDP write operations (keyboard/upload/hover)
      browse-cmd.sh                   # Unified CLI entry point
      check-deps.sh                   # Environment check + proxy auto-start
      match-site.sh                   # Site experience matcher
    references/
      site-patterns/                  # 8 pre-loaded + runtime-accumulated site profiles
adapters/                             # 5 platform adapter files
tests/                                # 200 automated tests
.github/workflows/test.yml           # GitHub Actions CI
```

---

## Dependencies

| Component | Requirement | Purpose |
|-----------|------------|---------|
| Chrome | Any modern version | Your daily browser |
| Node.js 22+ | Required for background mode | CDP Proxy |
| Python 3.6+ | Required for advanced write ops | CDP Helper |
| macOS | Required for foreground mode | AppleScript zero-dependency |

Background mode needs Node.js. Foreground mode on macOS has zero additional dependencies — just Chrome.

---

## Auto-Update

Built-in [update-kit](https://github.com/d-wwei/update-kit) for automatic version checking. The skill silently checks on each load (<5ms, from cache) and shows a one-liner when a new version is available:

```
Browser Control Skill update available: 3.1.0 — run: cd ~/.claude/skills/browser-control && npx update-kit apply
```

- Default `manual` policy — notifies only, never auto-upgrades
- Upgrade: `cd ~/.claude/skills/browser-control && npx update-kit apply`
- Rollback: `npx update-kit rollback`

---

## License

MIT

---

**Humans and AI sharing one Chrome — foreground collaboration, background parallelism.** GitHub: [github.com/d-wwei/browser-control-skill](https://github.com/d-wwei/browser-control-skill)
