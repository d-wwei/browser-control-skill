# Site Experience Memory Module

> Part of browser-control skill. Load when needed, not by default.

Per-domain knowledge accumulated during operations. Stored in `references/site-patterns/`.

**Before operating on a known site**: Check if experience exists and load it.

```bash
ls "${SKILL_DIR}/references/site-patterns/" 2>/dev/null
# Or use the matcher:
bash "${SKILL_DIR}/scripts/match-site.sh" "user input text"
```

**After successfully operating on a site**: If you discovered new patterns worth recording (URL structure, platform characteristics, effective strategies, known traps), write them to the experience file. Only write verified facts, never unconfirmed guesses.

**File format:**
```markdown
---
domain: example.com
aliases: [示例, Example]
updated: 2026-03-29
---
## Platform Characteristics
Architecture, anti-scraping behavior, login requirements, content loading patterns

## Effective Patterns
Verified URL patterns, operational strategies, selectors

## Known Traps
What fails and why
```

Experience entries are date-stamped. Treat them as "likely valid hints" not "guaranteed facts." If following experience fails, fall back to general approach and update the experience file.
