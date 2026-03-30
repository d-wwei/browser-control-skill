---
domain: twitter.com
aliases: [X, x.com, Twitter]
updated: 2026-03-29
confidence: low
source: community-knowledge
---

> **Note:** This is a starter pattern based on general knowledge. Verify and update after actual operation.

## Platform Characteristics

- Microblogging platform (rebranded to X, but twitter.com still works and redirects)
- Virtual DOM architecture — aggressively destroys and recreates DOM nodes on scroll
- Content is loaded via internal GraphQL API, not server-rendered HTML
- Login wall: shows a login/signup modal after viewing a few pages or tweets without authentication
- Rate limits on both UI and API access

## Effective Patterns

- **Individual tweets**: `twitter.com/{username}/status/{tweetId}` or `x.com/{username}/status/{tweetId}`
- **For known tweet URLs**: use Jina or similar extraction tools — often more reliable than CDP
- **Profile pages**: `twitter.com/{username}`
- **Search**: `twitter.com/search?q={query}`
- If using CDP: must implement scroll-and-capture pattern since nodes are destroyed outside viewport
- Capture tweet content immediately when visible before scrolling past
- Use network request interception to capture GraphQL API responses for structured data

## Known Traps

- **Login wall**: after ~3-5 page views, a modal blocks content; login or use alternative extraction
- **Virtual DOM scrolling**: standard "scroll to bottom and read all" approach fails — nodes are recycled
- **Rate limiting**: aggressive rate limits on both authenticated and unauthenticated access
- **Redirect**: twitter.com now redirects to x.com; handle both domains
- **Dynamic loading**: timeline content is infinite-scroll with GraphQL-fetched batches
- **Media**: images/videos are behind `pbs.twimg.com` CDN with various size parameters
- **Nitter alternatives**: third-party frontends (nitter instances) sometimes provide easier access but availability is unreliable
