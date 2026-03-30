---
domain: github.com
aliases: [GitHub, GH]
updated: 2026-03-29
confidence: low
source: community-knowledge
---

> **Note:** This is a starter pattern based on general knowledge. Verify and update after actual operation.

## Platform Characteristics

- Code hosting and collaboration platform
- Public repositories and content are freely accessible without login
- No significant anti-scraping for public content
- Server-rendered pages with progressive enhancement
- Extensive REST and GraphQL APIs available

## Effective Patterns

- **Prefer CLI/API over browser**: `gh` CLI tool handles most tasks (issues, PRs, repos, releases) more reliably
- **Repository pages**: `github.com/{owner}/{repo}`
- **File browsing**: `github.com/{owner}/{repo}/blob/{branch}/{path}`
- **Raw file content**: `raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}` — direct file download
- **Issues**: `github.com/{owner}/{repo}/issues/{number}`
- **Pull requests**: `github.com/{owner}/{repo}/pull/{number}`
- **Search**: `github.com/search?q={query}&type={repositories|code|issues}`
- API access via `gh api` command is generally superior to browser automation
- Use browser only for: authenticated UI actions, visual review, features without API equivalents

## Known Traps

- **Rate limiting on API**: unauthenticated requests limited to 60/hour; authenticated to 5000/hour
- **Raw content URL format differs**: `raw.githubusercontent.com` vs `github.com` — don't mix them up
- **Large files**: files over 1MB may not render in browser; use raw URL or API
- **Code search limitations**: code search has specific syntax and scope requirements
- **Private repos**: require authentication; `gh` CLI handles this automatically if configured
- **Markdown rendering**: GitHub-flavored Markdown has extensions (task lists, mermaid diagrams) not in standard Markdown
