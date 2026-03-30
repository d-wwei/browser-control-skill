---
domain: mp.weixin.qq.com
aliases: [微信公众号, WeChat Official Account, WeChat MP]
updated: 2026-03-29
confidence: low
source: community-knowledge
---

> **Note:** This is a starter pattern based on general knowledge. Verify and update after actual operation.

## Platform Characteristics

- WeChat's official account article publishing platform
- Individual published articles have stable, publicly accessible URLs
- Article listing/search pages have anti-scraping protections
- Admin panel (mp.weixin.qq.com backend) requires WeChat login via QR code scan
- Articles are standalone HTML pages — no SPA framework required

## Effective Patterns

- **Individual articles**: `mp.weixin.qq.com/s/{articleId}` — publicly accessible, no login needed
- **Article content**: main body is in `#js_content` div — rich text with inline styles
- **Images**: hosted on `mmbiz.qpic.cn` CDN; some have referrer checks
- For extracting article text, standard DOM parsing or Jina/Firecrawl works well on individual articles
- Article metadata (author, publish date, account name) is in the page header area
- Use `#js_name` for account name, `#publish_time` for publish date

## Known Traps

- **Listing pages are protected** — you cannot easily scrape an account's article list without login
- **Article URLs with `__biz` parameter**: some older URL formats use encoded parameters that are session-specific
- **Image hotlink protection**: images may not load if referrer header is wrong; set referrer to `mp.weixin.qq.com`
- **Temporary links**: some shared article links (via `temp_url`) expire after a period
- **No public search API**: finding articles requires using Sogou WeChat search (`weixin.sogou.com`) or similar external indexes
- **Rich text formatting**: articles use heavy inline CSS; extracting clean text requires stripping styles
