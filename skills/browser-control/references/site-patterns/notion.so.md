---
domain: notion.so
aliases: [Notion]
updated: 2026-03-29
confidence: low
source: community-knowledge
---

> **Note:** This is a starter pattern based on general knowledge. Verify and update after actual operation.

## Platform Characteristics

- All-in-one workspace for notes, docs, databases, and wikis
- Heavily SPA (Single Page Application) — content is loaded dynamically via JavaScript
- Rich text uses `contenteditable` block-based editing (each paragraph/heading/list item is a block)
- Public pages are accessible without login; workspace/private pages require authentication
- Real-time collaborative editing with WebSocket connections

## Effective Patterns

- **Public pages**: `notion.so/{pageId}` or custom domain — accessible without login
- **For reading public pages**: Jina or Firecrawl may work; CDP also reliable
- **Text input**: use CDP `type` command for entering text into contenteditable blocks; standard `value` setting does not work
- **Block structure**: each content block is a separate DOM element; select by `data-block-id` attributes
- **Database views**: tables, boards, galleries are rendered as interactive views with filterable content
- **Wait for render**: must wait for dynamic content to fully load; Notion pages have a loading spinner phase

## Known Traps

- **SPA navigation**: page transitions don't reload the page; URL changes are handled client-side
- **Contenteditable complexity**: DOM structure for rich text is deeply nested; avoid trying to manipulate it directly
- **Login for workspaces**: private pages redirect to login; Notion supports Google SSO, Apple SSO, email/password
- **Block IDs are UUIDs**: page and block IDs are long UUIDs, sometimes with dashes removed in URLs
- **Embeds and integrations**: pages can contain embedded content (databases, synced blocks) that load separately
- **Clipboard-based input**: for complex content, Notion sometimes responds better to clipboard paste events than keystroke-by-keystroke typing
- **Export alternatives**: Notion API (api.notion.com) provides structured block-level access and may be preferable to browser automation for data extraction
