---
domain: linkedin.com
aliases: [LinkedIn, 领英]
updated: 2026-03-29
confidence: low
source: community-knowledge
---

> **Note:** This is a starter pattern based on general knowledge. Verify and update after actual operation.

## Platform Characteristics

- Professional networking platform
- Aggressive login wall — most content requires authentication to view
- Once logged in, DOM is relatively standard and elements are accessible
- Server-side rendering with client-side hydration
- Anti-scraping measures include rate limiting and account restrictions for automated behavior

## Effective Patterns

- **Profile pages**: `linkedin.com/in/{username}` — requires login to view full content
- **Job listings**: `linkedin.com/jobs/view/{jobId}` — some basic info visible without login
- **Company pages**: `linkedin.com/company/{companySlug}`
- **Job search**: `linkedin.com/jobs/search/?keywords={query}`
- After authentication via CDP, standard DOM selectors work for content extraction
- Profile sections have well-structured markup with identifiable section containers
- Job postings have structured data (title, company, location, description)

## Known Traps

- **Login wall is strict** — almost all useful content is gated behind authentication
- **Account restrictions**: automated access patterns can trigger account limitations or bans
- **Authwall redirect**: unauthenticated requests redirect to `/authwall` page
- **Dynamic content**: feed and recommendations are loaded dynamically via AJAX
- **Profile variations**: profiles have different layouts depending on relationship (1st/2nd/3rd connection) and profile completeness
- **Rate limiting**: too many profile views in a short period triggers warnings
- **CSRF tokens**: form submissions require valid CSRF tokens from the session
