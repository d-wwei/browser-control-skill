---
domain: google.com
aliases: [Google Search, Google, 谷歌]
updated: 2026-03-29
confidence: low
source: community-knowledge
---

> **Note:** This is a starter pattern based on general knowledge. Verify and update after actual operation.

## Platform Characteristics

- World's dominant search engine
- Search results are well-structured in the DOM
- Server-side rendered with progressive enhancement
- For most use cases, the WebSearch tool is sufficient — no need for CDP browser automation
- CAPTCHA challenges triggered by automated access patterns

## Effective Patterns

- **Prefer WebSearch tool**: built-in web search is usually faster and more reliable than browser automation
- **Search URL**: `google.com/search?q={query}` with various parameters (`&num=`, `&start=`, `&tbs=` for time filters)
- **If CDP needed**: search results are in `div.g` containers; each result has a link, title, and snippet
- **Featured snippets**: appear in `div.xpdopen` or similar containers above regular results
- **Knowledge panels**: appear on the right side in `div.kp-wholepage`
- **Image search**: `google.com/search?tbm=isch&q={query}`
- **News search**: `google.com/search?tbm=nws&q={query}`

## Known Traps

- **CAPTCHA/reCAPTCHA**: automated access frequently triggers CAPTCHA challenges; very difficult to bypass
- **Personalization**: search results vary by location, history, and account; results may not match expectations
- **Dynamic result types**: Google mixes organic results with ads, knowledge panels, featured snippets, "People also ask", videos, maps — each has different DOM structure
- **Consent screens**: EU/certain regions show cookie consent dialogs that block the page
- **Rate limiting**: rapid sequential searches from the same IP trigger temporary blocks
- **URL redirects**: result links go through `google.com/url?...` redirects; extract the actual URL from the `href` or `data-href` attribute
- **Layout changes**: Google frequently A/B tests result page layouts; selectors may break
