---
domain: zhihu.com
aliases: [知乎, Zhihu]
updated: 2026-03-29
confidence: low
source: community-knowledge
---

> **Note:** This is a starter pattern based on general knowledge. Verify and update after actual operation.

## Platform Characteristics

- Chinese Q&A platform (similar to Quora)
- Moderate anti-scraping measures — shows login prompts and may limit anonymous access
- Content is a mix of server-rendered and client-loaded
- Long answers are truncated by default; require a click to expand
- Rich text content with images, code blocks, and LaTeX formulas

## Effective Patterns

- **Questions**: `zhihu.com/question/{questionId}`
- **Specific answers**: `zhihu.com/question/{questionId}/answer/{answerId}`
- **Articles (专栏)**: `zhuanlan.zhihu.com/p/{articleId}`
- **User profiles**: `zhihu.com/people/{userId}`
- **Search**: `zhihu.com/search?type=content&q={query}`
- **Answer content**: main content is in `div.RichContent` or `div.RichContent-inner`
- **Expand truncated answers**: click the "展开阅读全文" (Read full text) button before extracting content
- For articles (zhuanlan), content is typically fully rendered and easier to extract

## Known Traps

- **Login prompts**: anonymous browsing triggers login modals after several page views; can sometimes be dismissed
- **Truncated answers**: long answers show only a preview; must click "展开阅读全文" to get full content
- **Lazy-loaded images**: images in answers use lazy loading; scroll into view or wait for load
- **Different subdomains**: `zhihu.com` (Q&A), `zhuanlan.zhihu.com` (articles/columns), `www.zhihu.com` — content structure differs
- **Anti-scraping headers**: requests without proper User-Agent or cookies may get blocked or return limited content
- **Video answers**: some answers are video-only and cannot be extracted as text
- **Salt/Hot list**: trending content at `zhihu.com/hot` uses a different layout from regular Q&A pages
