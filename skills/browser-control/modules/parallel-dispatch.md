# Parallel Research: Sub-Agent Dispatch Module

> Part of browser-control skill. Load when needed, not by default.

When a task has multiple **independent** targets (e.g., research N companies, check N pages), dispatch sub-agents for parallel execution instead of serial processing.

**Benefits:**
- **Speed**: Total time ~ single sub-task duration
- **Context protection**: Raw content stays in sub-agent context; main agent receives only summaries

**How it works**: Each sub-agent creates its own tabs via `/new`, operates independently, closes tabs with `/close` when done. All sub-agents share one Chrome instance and one Proxy -- different `targetId` per tab, no race conditions.

**Sub-agent prompt writing**: Goal-oriented, not step-oriented.
- Write: "Investigate X and summarize findings" (the sub-agent decides how)
- Avoid: "Search for X, then open the first result" (anchors sub-agent to specific method)
- Avoid method-implying verbs: "search", "crawl", "scrape" -> use "investigate", "gather", "find out"

**When to parallelize:**

| Parallelize | Don't parallelize |
|-------------|-------------------|
| Independent targets, no dependency | Next target needs previous result |
| Each sub-task is substantial (multi-page, multi-step) | Simple single-page query |
| Needs CDP or long-running operations | A few WebSearch/Jina calls suffice |
