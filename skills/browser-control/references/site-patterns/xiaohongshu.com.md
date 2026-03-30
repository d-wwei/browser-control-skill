---
domain: xiaohongshu.com
aliases: [小红书, RED, RedNote]
updated: 2026-03-29
confidence: low
source: community-knowledge
---

> **Note:** This is a starter pattern based on general knowledge. Verify and update after actual operation.

## Platform Characteristics

- Chinese social commerce platform focused on lifestyle content (beauty, fashion, travel, food)
- Content is primarily image/video "notes" (笔记) with text descriptions
- Aggressive anti-scraping measures — blocks most static HTTP methods (requests, curl, etc.)
- Content is lazy-loaded; note cards appear as you scroll
- Mobile-first design; web version has limited functionality compared to app
- Requires CDP (Chrome DevTools Protocol) for reliable automated access

## Effective Patterns

- **Use site search** (`/search/result?keyword=xxx`) rather than constructing URLs directly
- **Feed browsing**: `/explore` is the discovery/feed page
- **Note pages**: `/explore/{noteId}` or `/discovery/item/{noteId}`
- **User profiles**: `/user/profile/{userId}`
- CDP scroll-and-capture approach works for collecting visible note cards
- Wait for lazy-loaded images to render before capturing content
- Use network idle detection to confirm content has fully loaded

## Known Traps

- **Direct URL construction often fails** — note IDs are not always predictable; use search to find content
- **Rate limiting**: rapid requests trigger CAPTCHA or IP blocks
- **Login walls**: some content requires login to view; anonymous access is limited
- **Dynamic rendering**: content is rendered client-side; server responses contain minimal HTML
- **Image URLs are CDN-hosted** with signed tokens that expire — don't cache image URLs long-term
- **Anti-bot detection**: headless browser fingerprinting is actively checked; stealth plugins may be needed
