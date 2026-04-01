---
name: web-search
description: "Search the public web and fetch page content as clean Markdown. Powered by omni-search-skill (optional companion). Provides search, fetch, resolve, and crawl operations."
argument-hint: "<query or url>"
---

# Web Search (Companion Sub-Skill)

Search the public web, fetch page content, and crawl documentation sites. This is a companion to Browser Control — use this for public content, use Browser Control (CDP / AppleScript) for authenticated pages.

## Availability Check

Before using any web-search command, check if omni-search-skill is installed:

```bash
OMNI_SEARCH_DIR="${OMNI_SEARCH_DIR:-$(find ~ -maxdepth 4 -type d -name 'omni-search-skill' 2>/dev/null | head -1)}"
if [ -z "$OMNI_SEARCH_DIR" ] || [ ! -f "$OMNI_SEARCH_DIR/scripts/omni_search.py" ]; then
  echo "omni-search-skill not found"
else
  echo "omni-search-skill found at: $OMNI_SEARCH_DIR"
fi
```

If not found, inform the user:

> Web search capability requires omni-search-skill. Install it with:
> ```bash
> git clone https://github.com/d-wwei/omni-search-skill.git
> cd omni-search-skill && python3 -m pip install -r requirements.txt
> ```

Then continue with whatever other tools are available (WebSearch, WebFetch, Jina, curl — see Browser Control's multi-channel tool selection).

## Commands

All commands use the same entry point. Replace `<OMNI_SEARCH_DIR>` with the actual path.

### Search — find information on the web

```bash
python3 <OMNI_SEARCH_DIR>/scripts/omni_search.py search "<query>"
```

### Fetch — extract a URL as clean Markdown

```bash
python3 <OMNI_SEARCH_DIR>/scripts/omni_search.py fetch "<url>"
```

### Resolve — search then auto-fetch top results

```bash
python3 <OMNI_SEARCH_DIR>/scripts/omni_search.py resolve "<query>"
```

### Crawl — index a documentation site

```bash
python3 <OMNI_SEARCH_DIR>/scripts/omni_search.py crawl "<url>"
```

## When to Use This vs Browser Control vs Built-in Tools

| Scenario | Tool |
|---|---|
| Quick search snippets | **WebSearch** (built-in, lightest) |
| Deep multi-engine search | **web-search** `search` |
| Read a public URL | **web-search** `fetch` or **WebFetch** (built-in) |
| Search + auto-fetch top results | **web-search** `resolve` |
| Crawl public documentation | **web-search** `crawl` |
| Read a URL that requires login (SSO, MFA, corporate) | **Browser Control** (CDP / AppleScript) |
| Find a URL via search, then access an authenticated result | **web-search** `search` → **Browser Control** navigate + read |
| Interact with a page (click, fill, navigate, upload) | **Browser Control** (CDP / AppleScript) |

## Combined Workflow Example

When a task requires both searching and authenticated access:

1. Use `web-search search "<query>"` to find relevant URLs
2. Identify which results require authentication
3. For public results → use `web-search fetch "<url>"` to read directly
4. For authenticated results → use `/browse bg` to navigate and read via CDP

## Notes

- omni-search-skill is maintained independently — update it with `cd <OMNI_SEARCH_DIR> && git pull`
- Works without API keys (free providers), but performs better with optional keys (see omni-search-skill README)
- If omni-search-skill is not installed, the agent should use the built-in multi-channel tools (WebSearch → WebFetch → Jina → curl → CDP)
