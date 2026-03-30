# Remix Provenance

## Sources

### Source A: browser-control-skill
- **Author**: d-wwei
- **Version**: 1.0 (10 commits, latest: 3e2d651)
- **URL**: https://github.com/d-wwei/browser-control-skill
- **License**: MIT (implied)
- **Analyzed**: 2026-03-29
- **Files**: 10 (SKILL.md 1619 lines, cdp-helper.py 537 lines, 4 adapter files)

### Source B: web-access
- **Author**: 一泽Eze
- **Version**: 2.4.1
- **URL**: https://github.com/eze-is/web-access
- **License**: MIT
- **Analyzed**: 2026-03-29
- **Files**: 8 (SKILL.md 243 lines, cdp-proxy.mjs 572 lines, 2 shell scripts)
- **Stars**: 2,082 (as of analysis date)

## Strategy

**Balanced fusion** — dual-source merge into new unified architecture.

## Provenance Map

| Output Component | Primary Source | Secondary Source | Notes |
|-----------------|---------------|-----------------|-------|
| Browsing Philosophy | B (web-access) | — | "Browse like a human" 4-phase model |
| EOPA Reasoning Cycle | A (browser-control-skill) | — | Evaluate-Observe-Plan-Act with auto-snapshot rules |
| Multi-Channel Dispatch | B (web-access) | — | WebSearch → WebFetch → Jina → curl → CDP |
| macOS AppleScript Commands | A (browser-control-skill) | — | Full command reference including JXA |
| CDP Proxy (cdp-proxy.mjs) | B (web-access) | — | HTTP-to-CDP bridge, copied verbatim |
| CDP Helper (cdp-helper.py) | A (browser-control-skill) | — | Python CDP client, copied verbatim |
| check-deps.sh | B (web-access) | — | Environment validator, copied verbatim |
| match-site.sh | B (web-access) | — | Site experience matcher, copied verbatim |
| DOM-to-Markdown Converter | A (browser-control-skill) | — | Full JS converter with table/code/list support |
| Interactive Element Indexer | A (browser-control-skill) | — | JS scanner with element caching |
| Three-Layer Safety System | A (browser-control-skill) | — | Domain blacklist + element check + operation confirmation |
| Sub-Agent Parallel Dispatch | B (web-access) | — | Tab-level isolation, goal-oriented prompts |
| Site Experience Memory | B (web-access) | — | Per-domain knowledge accumulation |
| Information Verification | B (web-access) | — | Primary source hierarchy |
| Console & Network Interception | A (browser-control-skill) | — | JS interceptor injection |
| Virtual Scroll Crawler | A (browser-control-skill) | — | SPA/virtualized list crawler |
| Annotated Screenshots | A (browser-control-skill) | — | Element index badge overlay |
| Wait for Element | A (browser-control-skill) | — | MutationObserver-based smart wait |
| CDP Write Operations | A (browser-control-skill) | B (web-access) | A's keyboard/upload/select + B's clickAt/setFiles |
| Login Handling | B (web-access) | — | "Did I get the content?" approach |
| Platform Detection | A (browser-control-skill) | B (web-access) | A's detection + B's Linux support |
| Recovery Strategy | A (browser-control-skill) | B (web-access) | Combined |
| Best Practices | A + B (merged) | — | Unified from both sources |

## Decisions

1. **Architecture**: Adopted B's single-truth-source approach over A's 7-file duplication.
   - Rationale: A had identical content copied across 7 files — maintenance nightmare.

2. **CDP layer**: Kept BOTH B's HTTP proxy (easy curl calls) AND A's Python helper (rich keyboard/upload).
   - Rationale: Complementary — proxy handles most operations, helper handles CDP-specific inputs.

3. **Safety**: Adopted A's three-layer system wholesale — B had no safety mechanism.
   - Rationale: Safety is non-negotiable for a skill that controls authenticated sessions.

4. **Philosophy**: Led with B's "browse like a human" then embedded A's EOPA as the tactical loop.
   - Rationale: B's philosophy is strategic; A's EOPA is operational. They compose naturally.

5. **Multi-channel**: Adopted B's tool selection table — A had no concept of non-browser tools.
   - Rationale: Most tasks don't need the browser. Lighter tools first.

6. **Linux**: Added Linux as a first-class platform via CDP Proxy.
   - Rationale: B already supported it; A had a gap.

## Risk Register

| Risk | Severity | Mitigation |
|------|----------|------------|
| SKILL.md is large (~800 lines) — may exceed context windows of some agents | Medium | Adapter files provide condensed versions; agents load only what they need |
| Two CDP mechanisms (proxy + helper) could confuse agents | Low | Clear guidance: proxy for most operations, helper for keyboard/upload/hover |
| Site experience files are runtime-generated, not shipped | Low | Expected — starts empty, grows with use |
| cdp-helper.py has CSS selector injection risk (from Source A) | Low | Documented in A's original analysis; context is user's own browser |
