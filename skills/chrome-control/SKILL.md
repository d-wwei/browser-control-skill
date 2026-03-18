---
name: chrome-control
description: "Control the user's Chrome browser via their real login session. Read page content, click elements, fill forms, execute JavaScript, and navigate — including pages behind corporate authentication. Auto-detects macOS or Windows."
argument-hint: "<url or action>"
---

# Chrome Control

Control the user's local Chrome browser using their real login session to access any page — including pages behind corporate authentication (SSO, MFA, security gateways).

## When to Use

- Access internal/authenticated web pages (e.g., company portals, OA systems, dashboards)
- Read content from pages that require login
- Automate repetitive browser interactions (clicking, form filling, navigation)
- Extract text, HTML, or structured data from web pages the user is already logged into

## Platform Detection

Before executing any command, detect the platform and use the corresponding approach:

```bash
uname -s
```

- **Darwin** → macOS → use AppleScript approach
- **MINGW* / CYGWIN* / MSYS* / Windows_NT** → Windows → use CDP approach
- You can also check: `[[ "$OSTYPE" == "darwin"* ]]` for macOS, or `[[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]` for Windows

## Required Preflight Check

Before reading, clicking, navigating, filling, or executing JavaScript, always verify that the platform-specific prerequisites are satisfied.

- If the prerequisite check is not done yet, do it first.
- If the prerequisite check fails, stop browser automation.
- Explain what is missing and guide the user through setup.
- Only continue after the user confirms setup is complete, or after a verification command succeeds.

## Step-by-Step Reasoning

Before each browser action, follow this mental model:

### 1. EVALUATE
What happened after my last action? Did it succeed?
- If I navigated: did the URL change? Is the page loaded?
- If I clicked: did anything change on the page?
- If I typed: is the text visible in the field?

### 2. OBSERVE
What does the current page state tell me?
- Read page content or check the current URL
- What interactive elements are available?
- Am I on the right page for the user's goal?

**Auto-snapshot rules** — decide whether to re-read:
- Last action was **read-only** (get text, get URL, list elements) → page state unchanged, **skip re-read**
- Last action was **click / navigate / submit / scroll-that-loads** → page state likely changed, **must re-read**
- You already have the **exact selector or element index** for your next target → **operate directly**, no need to list all elements first
- **Never** execute the same read command twice consecutively

### 3. PLAN
What is the single next action needed?
- Do I need to scroll to reveal more content?
- Do I need to wait for something to load?
- Which specific element should I interact with?

### 4. ACT
Execute exactly ONE browser action, then return to step 1.
- Use the most reliable targeting method available
- Be specific about which tab or window

## Element Targeting Priority

Use the most reliable method available for the current platform:

### macOS (AppleScript)
1. **Element index** (inject `List Interactive Elements` first to get indexed list, then use `window.__interactiveElements[index]` — most reliable, analogous to Windows @ref)
2. **Text content match** (most readable, preferred for buttons/links)
3. **CSS selector** (for form inputs, specific elements)
4. **Coordinates** (last resort only — use `document.elementFromPoint(x,y).click()`; fragile across screen sizes)

### Windows (agent-browser)
1. **@ref from snapshot** (e.g., `@e3` — most reliable, preferred)
   - Run `agent-browser --cdp 9222 snapshot -i` first to get refs
2. **CSS selector** (e.g., `"#submit-btn"`)
3. **JavaScript via eval** (for complex targeting)

Always prefer structured references (@ref on Windows, element index on macOS) over manually constructed CSS selectors — selectors are fragile and break when page structure changes.

---

# macOS Approach (AppleScript)

Uses macOS native AppleScript to communicate directly with the user's running Chrome. Zero dependencies.

## macOS Prerequisites

The user must enable one Chrome setting (one-time):

> **Chrome menu bar → View → Developer → Allow JavaScript from Apple Events**

Localized menu paths:
- English: View → Developer → Allow JavaScript from Apple Events
- 中文: 查看 → 开发者 → 允许 Apple 事件中的 JavaScript

## macOS Preflight

Run these checks before browser automation:

```bash
osascript -e 'tell application "Google Chrome" to get name'
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.title"'
```

Interpretation:

- If the first command fails, Chrome may not be running, or automation access to Chrome is blocked.
- If the second command fails, assume `Allow JavaScript from Apple Events` is not enabled yet, or macOS automation permissions are blocking access.
- In either case, stop and guide the user to fix the prerequisite before continuing.

## macOS Commands

### Observation

#### Get Current Tab URL

```bash
osascript -e '
tell application "Google Chrome"
    return URL of active tab of front window
end tell'
```

#### Get Page Title

```bash
osascript -e '
tell application "Google Chrome"
    execute active tab of front window javascript "document.title"
end tell'
```

#### Get Page Text Content

```bash
osascript -e '
tell application "Google Chrome"
    execute active tab of front window javascript "document.body.innerText"
end tell'
```

> For scenarios requiring preserved structure (tables, lists, code blocks), prefer the `Read Page as Structured Markdown` method in the Advanced section below.

For long pages, use substring to avoid output limits:

```bash
osascript -e '
tell application "Google Chrome"
    execute active tab of front window javascript "document.body.innerText.substring(0, 15000)"
end tell'
```

For lazy-loaded or infinite-scroll pages, scroll the real page first, wait for content to load, then read again:

```bash
osascript -e '
tell application "Google Chrome"
    execute active tab of front window javascript "window.scrollBy(0, window.innerHeight); \"done\";"
end tell'
```

#### Get Page HTML

```bash
osascript -e '
tell application "Google Chrome"
    execute active tab of front window javascript "document.documentElement.outerHTML.substring(0, 10000)"
end tell'
```

#### List All Open Tabs

```bash
osascript <<'EOF'
tell application "Google Chrome"
    set allTabs to {}
    set i to 1
    repeat with w in windows
        set j to 1
        repeat with t in tabs of w
            set end of allTabs to ("w" & i & "-t" & j & ": " & URL of t)
            set j to j + 1
        end repeat
        set i to i + 1
    end repeat
    set AppleScript's text item delimiters to linefeed
    return allTabs as text
end tell
EOF
```

### Navigation

> **Never navigate in the user's current tab.** Always open a new tab or use a dedicated task window. The user's existing tabs must be preserved.

#### Navigate to a URL (new tab)

```bash
osascript -e 'tell application "Google Chrome" to tell front window to make new tab with properties {URL:"https://example.com"}'
```

#### Navigate in a Dedicated Task Window (recommended for multi-step workflows)

```bash
osascript -l JavaScript -e '
function run() {
    var chrome = Application("Google Chrome");
    var wins = chrome.windows();
    var taskWin = null;
    for (var i = 0; i < wins.length; i++) {
        var tabs = wins[i].tabs();
        for (var j = 0; j < tabs.length; j++) {
            if (tabs[j].url().indexOf("__agentTask") !== -1) { taskWin = wins[i]; break; }
        }
        if (taskWin) break;
    }
    if (!taskWin) { taskWin = chrome.Window().make(); }
    taskWin.activeTab.url = "https://example.com";
    return "task window " + taskWin.id() + ", tabs: " + taskWin.tabs.length;
}
'
```

> When starting a multi-step workflow, create a dedicated Chrome window for all task-related navigation. Subsequent navigations within the same task should add new tabs to this window or reuse tabs the agent already opened.

#### Switch to a Specific Tab in the Front Window

```bash
osascript -e '
tell application "Google Chrome"
    set active tab index of front window to 3
end tell'
```

> **Note**: The tab list (`List All Open Tabs`) spans all Chrome windows, but the simple switch command above only changes the active tab in the **front window**. For cross-window targeting, use the JXA advanced example below to locate and interact with a tab in any window.

### Interaction

#### Click an Element

By CSS selector:

```bash
osascript -e '
tell application "Google Chrome"
    execute active tab of front window javascript "document.querySelector(\"#submit-btn\").click()"
end tell'
```

By text content:

```bash
osascript -e '
tell application "Google Chrome"
    execute active tab of front window javascript "
        var items = document.querySelectorAll(\"li, a, button, span, div\");
        for (var i = 0; i < items.length; i++) {
            if (items[i].textContent.trim() === \"Target Text\" && items[i].children.length === 0) {
                items[i].click();
                break;
            }
        }
        \"done\";
    "
end tell'
```

By index:

```bash
osascript -e '
tell application "Google Chrome"
    execute active tab of front window javascript "document.querySelectorAll(\"li\")[2].click(); \"done\";"
end tell'
```

#### Fill a Form Field

```bash
osascript -e '
tell application "Google Chrome"
    execute active tab of front window javascript "
        var input = document.querySelector(\"input[name=search]\");
        input.value = \"search text\";
        input.dispatchEvent(new Event(\"input\", {bubbles: true}));
        \"done\";
    "
end tell'
```

### Advanced

#### Execute Arbitrary JavaScript

```bash
osascript -e '
tell application "Google Chrome"
    execute active tab of front window javascript "YOUR_JS_CODE_HERE"
end tell'
```

#### Read Page as Structured Markdown

Convert the current page DOM into clean Markdown that preserves headings, lists, tables, links, code blocks, and images. Far more useful than `document.body.innerText` when structure matters.

**Multi-line (readable) version — inject via heredoc:**

```bash
osascript <<'APPLESCRIPT'
tell application "Google Chrome"
    execute active tab of front window javascript "
(function(maxLen){
  var R=['script','style','noscript','svg','canvas','template','iframe','object','embed'];
  var S=['nav','footer','header','aside'];
  var out=[],cc=0,tr=false;
  function add(l){if(tr)return;if(cc+l.length+1>maxLen){var r=maxLen-cc;if(r>20)out.push(l.slice(0,r-12)+'…[truncated]');tr=true;return}out.push(l);cc+=l.length+1}
  function vis(e){if(!(e instanceof HTMLElement))return true;if(e.hidden||e.getAttribute('aria-hidden')==='true')return false;var s=e.style;return s.display!=='none'&&s.visibility!=='hidden'}
  function res(h){try{return new URL(h,document.baseURI).href}catch(e){return h}}
  function inl(el){var r='';for(var i=0;i<el.childNodes.length;i++){var c=el.childNodes[i];if(c.nodeType===3){r+=c.textContent.replace(/\\s+/g,' ')}else if(c.nodeType===1){var t=c.tagName.toLowerCase(),tx=inl(c);if(t==='strong'||t==='b')r+='**'+tx.trim()+'**';else if(t==='em'||t==='i')r+='*'+tx.trim()+'*';else if(t==='code')r+='`'+tx.trim()+'`';else if(t==='a'){var hr=c.getAttribute('href')||'';if(hr&&!hr.startsWith('#')&&!hr.startsWith('javascript:'))r+='['+tx.trim()+']('+res(hr)+')';else r+=tx}else if(t==='img'){var sr=c.getAttribute('src')||'',al=c.getAttribute('alt')||'';if(sr)r+='!['+al+']('+res(sr)+')'}else if(t==='br')r+='\\n';else r+=tx}}return r}
  function li(el,ord,ind){var idx=1;for(var i=0;i<el.children.length;i++){if(tr)return;var ch=el.children[i];if(ch.tagName.toLowerCase()==='li'){var pf='  '.repeat(ind)+(ord?idx+'. ':'- ');var pts=[];for(var j=0;j<ch.childNodes.length;j++){var n=ch.childNodes[j];if(n.nodeType===3){var t=n.textContent.replace(/\\s+/g,' ').trim();if(t)pts.push(t)}else if(n.nodeType===1){var nt=n.tagName.toLowerCase();if(nt!=='ul'&&nt!=='ol'){var t=(n.textContent||'').replace(/\\s+/g,' ').trim();if(t)pts.push(t)}}}if(pts.length)add(pf+pts.join(' '));var nl=ch.querySelector(':scope>ul,:scope>ol');if(nl)li(nl,nl.tagName.toLowerCase()==='ol',ind+1);idx++}}}
  function tbl(el){var rows=[];var th=el.querySelector('thead');if(th){th.querySelectorAll('tr').forEach(function(tr){var c=[];tr.querySelectorAll('th,td').forEach(function(d){c.push((d.textContent||'').replace(/\\s+/g,' ').trim())});if(c.length)rows.push(c)})}var bd=th?el.querySelector('tbody')||el:el;bd.querySelectorAll('tr').forEach(function(tr){if(th&&tr.closest('thead'))return;var c=[];tr.querySelectorAll('th,td').forEach(function(d){c.push((d.textContent||'').replace(/\\s+/g,' ').trim())});if(c.length)rows.push(c)});if(!rows.length)return;var mc=Math.max.apply(null,rows.map(function(r){return r.length}));rows.forEach(function(r){while(r.length<mc)r.push('')});for(var i=0;i<rows.length;i++){add('| '+rows[i].join(' | ')+' |');if(i===0)add('| '+rows[i].map(function(){return'---'}).join(' | ')+' |');if(tr)return}}
  function walk(node,d,sel){if(tr)return;if(node.nodeType===3){var t=node.textContent.replace(/\\s+/g,' ').trim();if(t)add(t);return}if(node.nodeType!==1)return;var el=node,tag=el.tagName.toLowerCase();if(R.indexOf(tag)!==-1)return;if(!vis(el))return;if(!sel&&S.indexOf(tag)!==-1&&d<3)return;var m=tag.match(/^h([1-6])$/);if(m){var tx=(el.textContent||'').replace(/\\s+/g,' ').trim();if(tx){add('');add('#'.repeat(parseInt(m[1]))+' '+tx);add('')}return}if(tag==='p'){var tx=inl(el).trim();if(tx){add('');add(tx)}return}if(tag==='a'){var hr=el.getAttribute('href')||'',tx=(el.textContent||'').replace(/\\s+/g,' ').trim();if(tx&&hr&&!hr.startsWith('#')&&!hr.startsWith('javascript:'))add('['+tx+']('+res(hr)+')');else if(tx)add(tx);return}if(tag==='img'){var sr=el.getAttribute('src')||'',al=el.getAttribute('alt')||'';if(sr)add('!['+al+']('+res(sr)+')');return}if(tag==='hr'){add('');add('---');add('');return}if(tag==='br'){add('');return}if(tag==='ul'||tag==='ol'){add('');li(el,tag==='ol',0);add('');return}if(tag==='table'){add('');tbl(el);add('');return}if(tag==='pre'){var ce=el.querySelector('code'),lang=ce&&ce.className?ce.className.match(/language-(\\w+)/):null;add('');add('```'+(lang?lang[1]:''));(el.textContent||'').trimEnd().split('\\n').forEach(function(l){add(l)});add('```');add('');return}if(tag==='blockquote'){var tx=(el.textContent||'').replace(/\\s+/g,' ').trim();if(tx){add('');tx.split('\\n').forEach(function(l){add('> '+l.trim())});add('')}return}for(var i=0;i<el.childNodes.length;i++){walk(el.childNodes[i],d+1,sel);if(tr)return}}
  var root=document.querySelector('main')||document.querySelector('article')||document.querySelector('[role=main]')||document.body;
  if(!root)return '[Empty page]';
  walk(root,0,false);
  return out.join('\\n').replace(/\\n{3,}/g,'\\n\\n').trim();
})(15000)
    "
end tell
APPLESCRIPT
```

**Compressed single-line version** (for direct osascript -e injection):

```bash
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "(function(maxLen){var R=[\"script\",\"style\",\"noscript\",\"svg\",\"canvas\",\"template\",\"iframe\",\"object\",\"embed\"];var S=[\"nav\",\"footer\",\"header\",\"aside\"];var out=[],cc=0,tr=false;function add(l){if(tr)return;if(cc+l.length+1>maxLen){var r=maxLen-cc;if(r>20)out.push(l.slice(0,r-12)+\"…[truncated]\");tr=true;return}out.push(l);cc+=l.length+1}function vis(e){if(!(e instanceof HTMLElement))return true;if(e.hidden||e.getAttribute(\"aria-hidden\")===\"true\")return false;var s=e.style;return s.display!==\"none\"&&s.visibility!==\"hidden\"}function res(h){try{return new URL(h,document.baseURI).href}catch(e){return h}}function inl(el){var r=\"\";for(var i=0;i<el.childNodes.length;i++){var c=el.childNodes[i];if(c.nodeType===3){r+=c.textContent.replace(/\\s+/g,\" \")}else if(c.nodeType===1){var t=c.tagName.toLowerCase(),tx=inl(c);if(t===\"strong\"||t===\"b\")r+=\"**\"+tx.trim()+\"**\";else if(t===\"em\"||t===\"i\")r+=\"*\"+tx.trim()+\"*\";else if(t===\"code\")r+=\"`\"+tx.trim()+\"`\";else if(t===\"a\"){var hr=c.getAttribute(\"href\")||\"\";if(hr&&!hr.startsWith(\"#\")&&!hr.startsWith(\"javascript:\"))r+=\"[\"+tx.trim()+\"](\"+res(hr)+\")\";else r+=tx}else if(t===\"img\"){var sr=c.getAttribute(\"src\")||\"\",al=c.getAttribute(\"alt\")||\"\";if(sr)r+=\"![\"+al+\"](\"+res(sr)+\")\"}else if(t===\"br\")r+=\"\\n\";else r+=tx}}return r}function walk(node,d){if(tr)return;if(node.nodeType===3){var t=node.textContent.replace(/\\s+/g,\" \").trim();if(t)add(t);return}if(node.nodeType!==1)return;var el=node,tag=el.tagName.toLowerCase();if(R.indexOf(tag)!==-1)return;if(!vis(el))return;if(S.indexOf(tag)!==-1&&d<3)return;var m=tag.match(/^h([1-6])$/);if(m){var tx=(el.textContent||\"\").replace(/\\s+/g,\" \").trim();if(tx){add(\"\");add(\"#\".repeat(parseInt(m[1]))+\" \"+tx);add(\"\")}return}if(tag===\"p\"){var tx=inl(el).trim();if(tx){add(\"\");add(tx)}return}if(tag===\"a\"){var hr=el.getAttribute(\"href\")||\"\",tx=(el.textContent||\"\").replace(/\\s+/g,\" \").trim();if(tx&&hr&&!hr.startsWith(\"#\")&&!hr.startsWith(\"javascript:\"))add(\"[\"+tx+\"](\"+res(hr)+\")\");else if(tx)add(tx);return}if(tag===\"img\"){var sr=el.getAttribute(\"src\")||\"\",al=el.getAttribute(\"alt\")||\"\";if(sr)add(\"![\"+al+\"](\"+res(sr)+\")\");return}if(tag===\"table\"){add(\"\");var rows=[];var th=el.querySelector(\"thead\");if(th){th.querySelectorAll(\"tr\").forEach(function(r){var c=[];r.querySelectorAll(\"th,td\").forEach(function(d){c.push((d.textContent||\"\").replace(/\\s+/g,\" \").trim())});if(c.length)rows.push(c)})}var bd=th?el.querySelector(\"tbody\")||el:el;bd.querySelectorAll(\"tr\").forEach(function(r){if(th&&r.closest(\"thead\"))return;var c=[];r.querySelectorAll(\"th,td\").forEach(function(d){c.push((d.textContent||\"\").replace(/\\s+/g,\" \").trim())});if(c.length)rows.push(c)});if(rows.length){var mc=Math.max.apply(null,rows.map(function(r){return r.length}));rows.forEach(function(r){while(r.length<mc)r.push(\"\")});for(var i=0;i<rows.length;i++){add(\"| \"+rows[i].join(\" | \")+\" |\");if(i===0)add(\"| \"+rows[i].map(function(){return\"---\"}).join(\" | \")+\" |\")}}add(\"\");return}if(tag===\"pre\"){var ce=el.querySelector(\"code\"),lang=ce&&ce.className?ce.className.match(/language-(\\\\w+)/):null;add(\"\");add(\"```\"+(lang?lang[1]:\"\"));(el.textContent||\"\").trimEnd().split(\"\\n\").forEach(function(l){add(l)});add(\"```\");add(\"\");return}if(tag===\"blockquote\"){var tx=(el.textContent||\"\").replace(/\\s+/g,\" \").trim();if(tx){add(\"\");add(\"> \"+tx);add(\"\")}return}if(tag===\"ul\"||tag===\"ol\"){add(\"\");var ord=tag===\"ol\";var idx=1;for(var i=0;i<el.children.length;i++){var ch=el.children[i];if(ch.tagName.toLowerCase()===\"li\"){add((ord?idx+\". \":\"- \")+(ch.textContent||\"\").replace(/\\s+/g,\" \").trim());idx++}}add(\"\");return}for(var i=0;i<el.childNodes.length;i++){walk(el.childNodes[i],d+1)}}var root=document.querySelector(\"main\")||document.querySelector(\"article\")||document.querySelector(\"[role=main]\")||document.body;if(!root)return \"[Empty page]\";walk(root,0);return out.join(\"\\n\").replace(/\\n{3,}/g,\"\\n\\n\").trim()})(15000)"'
```

**Custom maxLength**: Replace the `15000` parameter at the end to control output length.

#### List Interactive Elements

Scan all interactive elements on the page, filter hidden ones, assign each a numeric index, and cache element references in `window.__interactiveElements` for subsequent operations.

**Multi-line (readable) version:**

```bash
osascript <<'APPLESCRIPT'
tell application "Google Chrome"
    execute active tab of front window javascript "
(function(){
  var SEL='a[href],button,input,select,textarea,[role=button],[onclick],[contenteditable=true],[tabindex]';
  var els=document.querySelectorAll(SEL);
  var result=[], cache=[];
  for(var i=0;i<els.length;i++){
    var el=els[i];
    if(el.tagName.toLowerCase()==='script'||el.tagName.toLowerCase()==='style')continue;
    if(el.closest('script,style'))continue;
    if(el.getAttribute('aria-hidden')==='true')continue;
    var rect=el.getBoundingClientRect();
    if(rect.width<=0||rect.height<=0)continue;
    var cs=window.getComputedStyle(el);
    if(cs.display==='none'||cs.visibility==='hidden'||cs.opacity==='0')continue;
    if(el.hidden)continue;
    var idx=cache.length;
    cache.push(el);
    var tag=el.tagName.toLowerCase();
    var parts='['+idx+'] <'+tag+'>';
    if(el.type)parts+=' type=\"'+el.type+'\"';
    if(el.name)parts+=' name=\"'+el.name+'\"';
    if(el.placeholder)parts+=' placeholder=\"'+el.placeholder+'\"';
    if(el.href)parts+=' href=\"'+el.href+'\"';
    var label=el.getAttribute('aria-label')||(el.textContent||'').replace(/\\s+/g,' ').trim();
    if(label)parts+=' \"'+label.substring(0,80)+'\"';
    result.push(parts);
  }
  window.__interactiveElements=cache;
  return result.join('\\n');
})()
    "
end tell
APPLESCRIPT
```

**Compressed single-line version:**

```bash
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "(function(){var SEL=\"a[href],button,input,select,textarea,[role=button],[onclick],[contenteditable=true],[tabindex]\";var els=document.querySelectorAll(SEL);var result=[],cache=[];for(var i=0;i<els.length;i++){var el=els[i];if(el.tagName.toLowerCase()===\"script\"||el.tagName.toLowerCase()===\"style\")continue;if(el.closest(\"script,style\"))continue;if(el.getAttribute(\"aria-hidden\")===\"true\")continue;var rect=el.getBoundingClientRect();if(rect.width<=0||rect.height<=0)continue;var cs=window.getComputedStyle(el);if(cs.display===\"none\"||cs.visibility===\"hidden\"||cs.opacity===\"0\")continue;if(el.hidden)continue;var idx=cache.length;cache.push(el);var tag=el.tagName.toLowerCase();var parts=\"[\"+idx+\"] <\"+tag+\">\";if(el.type)parts+=\" type=\\\"\"+el.type+\"\\\"\";if(el.name)parts+=\" name=\\\"\"+el.name+\"\\\"\";if(el.placeholder)parts+=\" placeholder=\\\"\"+el.placeholder+\"\\\"\";if(el.href)parts+=\" href=\\\"\"+el.href+\"\\\"\";var label=el.getAttribute(\"aria-label\")||(el.textContent||\"\").replace(/\\s+/g,\" \").trim();if(label)parts+=\" \\\"\"+label.substring(0,80)+\"\\\"\";result.push(parts)}window.__interactiveElements=cache;return result.join(\"\\n\")})()"'
```

#### Click/Fill by Element Index

After running `List Interactive Elements`, use the cached `window.__interactiveElements` array:

```bash
# Click element at index 3
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "window.__interactiveElements[3].click(); \"done\";"'

# Fill input at index 5
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "var el=window.__interactiveElements[5]; el.value=\"search text\"; el.dispatchEvent(new Event(\"input\",{bubbles:true})); \"done\";"'

# Read value of element at index 2
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "var el=window.__interactiveElements[2]; el.value||el.textContent"'
```

> **Important**: Element indices become stale after page navigation or DOM changes. Re-run `List Interactive Elements` to refresh.

#### Safety Check (Pre-action)

Inject this function to verify the current page is safe for interaction before executing click/fill operations.

**Multi-line version:**

```bash
osascript <<'APPLESCRIPT'
tell application "Google Chrome"
    execute active tab of front window javascript "
(function(){
  var href=location.href;
  if(/^chrome:|^chrome-extension:|^about:/.test(href))return JSON.stringify({safe:false,reason:'Chrome internal page'});
  var u;try{u=new URL(href)}catch(e){return JSON.stringify({safe:false,reason:'Invalid URL'})}
  var h=u.hostname.toLowerCase();
  function endsWith(host,suffix){return host===suffix||host.slice(-(suffix.length+1))==='.'+ suffix}
  if(h.endsWith('.bank'))return JSON.stringify({safe:false,reason:'Banking domain (.bank)'});
  var bankDomains=['chase.com','wellsfargo.com','bankofamerica.com','citi.com','citibank.com','capitalone.com','usbank.com','pnc.com','tdbank.com','hsbc.com'];
  for(var i=0;i<bankDomains.length;i++){if(endsWith(h,bankDomains[i]))return JSON.stringify({safe:false,reason:'Banking: '+bankDomains[i]})}
  var payDomains=['paypal.com','venmo.com','stripe.com','squareup.com','wise.com','revolut.com','robinhood.com','coinbase.com','binance.com'];
  for(var i=0;i<payDomains.length;i++){if(endsWith(h,payDomains[i]))return JSON.stringify({safe:false,reason:'Payment: '+payDomains[i]})}
  var authExact=['accounts.google.com','login.microsoftonline.com','login.live.com'];
  for(var i=0;i<authExact.length;i++){if(h===authExact[i])return JSON.stringify({safe:false,reason:'Auth: '+authExact[i]})}
  if(endsWith(h,'icloud.com')&&u.pathname.startsWith('/account'))return JSON.stringify({safe:false,reason:'Auth: icloud.com/account'});
  var authSuffix=['okta.com','auth0.com','onelogin.com'];
  for(var i=0;i<authSuffix.length;i++){if(endsWith(h,authSuffix[i]))return JSON.stringify({safe:false,reason:'Auth: '+authSuffix[i]})}
  var cloudExact=['console.aws.amazon.com','console.cloud.google.com','portal.azure.com'];
  for(var i=0;i<cloudExact.length;i++){if(h===cloudExact[i])return JSON.stringify({safe:false,reason:'Cloud: '+cloudExact[i]})}
  window.__checkSafety=function(){return{safe:true}};
  return JSON.stringify({safe:true,reason:'OK'});
})()
    "
end tell
APPLESCRIPT
```

**Check if a specific element is safe to interact with** (password/payment protection):

```bash
osascript <<'APPLESCRIPT'
tell application "Google Chrome"
    execute active tab of front window javascript "
(function(idx){
  var el=window.__interactiveElements&&window.__interactiveElements[idx];
  if(!el)return JSON.stringify({safe:false,reason:'Element not found at index '+idx});
  if(el.type==='password'||/password|passwd/i.test(el.name||'')||el.autocomplete==='current-password'||el.autocomplete==='new-password')
    return JSON.stringify({safe:false,reason:'Password field'});
  var txt=(el.textContent||'').trim().toLowerCase();
  if(/\\b(pay|purchase|buy|checkout|place\\s*order|submit\\s*order|confirm\\s*payment|subscribe|upgrade|donate)\\b/i.test(txt)||/付款|支付|购买|下单|确认订单|立即购买/.test(txt))
    return JSON.stringify({safe:false,reason:'Payment button: '+txt.substring(0,50)});
  return JSON.stringify({safe:true,reason:'OK'});
})(TARGET_INDEX)
    "
end tell
APPLESCRIPT
```

Replace `TARGET_INDEX` with the element index number.

#### Wait for Element

Smart wait using MutationObserver — replaces blind `sleep` with condition-based waiting.

**Step 1: Inject the wait script (JXA):**

```bash
osascript -l JavaScript -e '
function run() {
    var chrome = Application("Google Chrome");
    var tab = chrome.windows[0].activeTab();
    chrome.execute(tab, {javascript: "(function(sel,timeout,cond){var start=Date.now();function vis(el){if(!el)return false;var r=el.getBoundingClientRect();if(r.width===0&&r.height===0)return false;var s=window.getComputedStyle(el);return s.display!==\"none\"&&s.visibility!==\"hidden\"&&s.opacity!==\"0\"}function chk(){var el=document.querySelector(sel);if(cond===\"attached\")return el!==null;if(cond===\"visible\")return el!==null&&vis(el);if(cond===\"hidden\")return el===null||!vis(el);if(cond===\"loaded\")return document.readyState===\"complete\"&&el!==null;return el!==null}if(chk()){window.__waitResult=JSON.stringify({found:true,elapsed:Date.now()-start});return}var ob=new MutationObserver(function(){if(chk()){ob.disconnect();clearTimeout(tm);window.__waitResult=JSON.stringify({found:true,elapsed:Date.now()-start})}});ob.observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:[\"style\",\"class\",\"hidden\"]});var tm=setTimeout(function(){ob.disconnect();window.__waitResult=JSON.stringify({found:false,elapsed:Date.now()-start})},timeout);window.__waitResult=null})(\"YOUR_SELECTOR\",5000,\"visible\")"});
    return "Wait injected. Poll window.__waitResult for result.";
}'
```

**Step 2: Poll for result:**

```bash
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "window.__waitResult"'
```

Repeat polling every 500ms until a non-null JSON result is returned. Parameters:
- Replace `YOUR_SELECTOR` with the target CSS selector
- `5000` = timeout in milliseconds
- `"visible"` = condition (`visible` | `hidden` | `attached` | `loaded`)

#### Read Console Logs

Inject a console interceptor **before** the target action to capture subsequent logs.

**Inject interceptor:**

```bash
osascript <<'APPLESCRIPT'
tell application "Google Chrome"
    execute active tab of front window javascript "
(function(){
  if(window.__consoleLogs)return 'already injected';
  window.__consoleLogs=[];
  var orig={log:console.log,warn:console.warn,error:console.error,info:console.info};
  ['log','warn','error','info'].forEach(function(m){
    console[m]=function(){
      var args=Array.prototype.slice.call(arguments).map(function(a){try{return typeof a==='object'?JSON.stringify(a):String(a)}catch(e){return String(a)}});
      window.__consoleLogs.push({level:m,msg:args.join(' '),ts:Date.now()});
      orig[m].apply(console,arguments);
    };
  });
  return 'Console interceptor injected';
})()
    "
end tell
APPLESCRIPT
```

**Read captured logs:**

```bash
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "JSON.stringify(window.__consoleLogs||[])"'
```

**Clear logs:**

```bash
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "window.__consoleLogs=[]; \"cleared\";"'
```

#### Monitor Network Requests

Inject a network interceptor to capture XHR and fetch requests.

**Inject interceptor:**

```bash
osascript <<'APPLESCRIPT'
tell application "Google Chrome"
    execute active tab of front window javascript "
(function(){
  if(window.__networkLogs)return 'already injected';
  window.__networkLogs=[];
  var origOpen=XMLHttpRequest.prototype.open;
  var origSend=XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open=function(method,url){
    this.__reqInfo={method:method,url:url,ts:Date.now()};
    return origOpen.apply(this,arguments);
  };
  XMLHttpRequest.prototype.send=function(){
    var info=this.__reqInfo;
    var xhr=this;
    xhr.addEventListener('loadend',function(){
      window.__networkLogs.push({method:info.method,url:info.url,status:xhr.status,timestamp:info.ts,duration:Date.now()-info.ts});
    });
    return origSend.apply(this,arguments);
  };
  var origFetch=window.fetch;
  window.fetch=function(input,init){
    var method=(init&&init.method)||'GET';
    var url=typeof input==='string'?input:input.url;
    var ts=Date.now();
    return origFetch.apply(this,arguments).then(function(resp){
      window.__networkLogs.push({method:method,url:url,status:resp.status,timestamp:ts,duration:Date.now()-ts});
      return resp;
    }).catch(function(err){
      window.__networkLogs.push({method:method,url:url,status:'error',timestamp:ts,duration:Date.now()-ts,error:err.message});
      throw err;
    });
  };
  return 'Network interceptor injected';
})()
    "
end tell
APPLESCRIPT
```

**Read captured requests:**

```bash
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "JSON.stringify(window.__networkLogs||[])"'
```

#### Capture Page Screenshot

AppleScript itself has no screenshot API, but macOS `screencapture` can capture a specific Chrome window.

**Basic screenshot:**

```bash
# Get Chrome front window ID
WINID=$(osascript -e 'tell application "Google Chrome" to id of front window')
# Capture the window
screencapture -l "$WINID" /tmp/chrome-screenshot.png
```

**Screenshot with interactive element annotations** (overlay index badges, then capture, then remove):

```bash
# Step 1: Inject visual annotations
osascript <<'APPLESCRIPT'
tell application "Google Chrome"
    execute active tab of front window javascript "
(function(){
  if(!window.__interactiveElements)return 'Run List Interactive Elements first';
  var container=document.createElement('div');
  container.id='__agentAnnotations';
  container.style.cssText='position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:2147483647';
  window.__interactiveElements.forEach(function(el,i){
    var rect=el.getBoundingClientRect();
    if(rect.width<=0||rect.height<=0)return;
    var badge=document.createElement('div');
    badge.style.cssText='position:fixed;left:'+(rect.left-2)+'px;top:'+(rect.top-2)+'px;width:'+(rect.width+4)+'px;height:'+(rect.height+4)+'px;border:2px solid rgba(255,0,0,0.6);background:rgba(255,0,0,0.08);pointer-events:none;z-index:2147483647';
    var label=document.createElement('span');
    label.textContent=i;
    label.style.cssText='position:absolute;top:-10px;left:-2px;background:red;color:white;font-size:10px;font-weight:bold;padding:1px 4px;border-radius:3px;font-family:monospace';
    badge.appendChild(label);
    container.appendChild(badge);
  });
  document.body.appendChild(container);
  return 'Annotations added: '+window.__interactiveElements.length+' elements';
})()
    "
end tell
APPLESCRIPT

# Step 2: Wait briefly for render, then capture
sleep 0.5
WINID=$(osascript -e 'tell application "Google Chrome" to id of front window')
screencapture -l "$WINID" /tmp/chrome-annotated.png

# Step 3: Remove annotations
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "var a=document.getElementById(\"__agentAnnotations\");if(a)a.remove();\"done\";"'
```

#### JXA Robust Process & Tab Targeting

When macOS has multiple Chrome processes running (sometimes due to PWAs, Chrome apps, or multiple desktops), AppleScript might fail with `invalid index` errors because of process name collision. In such cases, use JavaScript for Automation (JXA) to iterate over all windows and tabs to find the exact URL. This approach completely bypasses the need for the tab to be active or in the "front window".

```javascript
osascript -l JavaScript -e '
function run() {
    var chrome = Application("Google Chrome");
    var windows = chrome.windows();
    for (var i = 0; i < windows.length; i++) {
        var tabs = windows[i].tabs();
        for (var j = 0; j < tabs.length; j++) {
            if (tabs[j].url().indexOf("YOUR_TARGET_URL_PART") !== -1) {
                var targetTab = tabs[j];
                // Execute JS to read or change
                return chrome.execute(targetTab, {javascript: "document.title"});
            }
        }
    }
    return "Target tab not found.";
}
'
```

#### Virtual Scrolling & SPA Crawler

Modern web apps (like X/Twitter, React Virtualized) destroy DOM nodes when they scroll out of view. Simple `document.body.innerText` only captures the current viewport.
To extract content from these long pages, you MUST inject a crawler that scrolls down periodically and accumulates DOM data into a global variable or `Set` to prevent data loss.

**1. Inject the background scrolling crawler (JXA Example):**
```javascript
osascript -l JavaScript -e '
function run() {
    var chrome = Application("Google Chrome");
    var targetTab = null; // Find targetTab logic same as above
    
    // Smooth scroll to top
    chrome.execute(targetTab, {javascript: "window.scrollTo(0,0);"});
    delay(2);
    
    // Inject asynchronous background crawler
    chrome.execute(targetTab, {javascript: `
        window.__foundText = "";
        var scrollInterval = setInterval(() => {
            var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
            var node;
            while(node = walker.nextNode()) {
                // Example filter, change this based on target text
                if(node.nodeValue.includes("YOUR_TARGET_KEYWORD")) {
                    var parentBlock = node.parentElement;
                    while(parentBlock && !["DIV", "PRE", "CODE"].includes(parentBlock.tagName.toUpperCase())) {
                        parentBlock = parentBlock.parentElement;
                    }
                    if(parentBlock && !window.__foundText.includes(parentBlock.innerText)) {
                        window.__foundText += parentBlock.innerText + "\\n\\n---NEXT---\\n\\n";
                    }
                }
            }
            window.scrollBy(0, 800);  // Scroll down one viewport
            if(window.scrollY + window.innerHeight >= document.body.scrollHeight) clearInterval(scrollInterval);
        }, 500);
    `});
    
    return "Started async extraction in browser background.";
}
'
```

**2. Wait 5-10 seconds, then retrieve the accumulated text:**
```javascript
osascript -l JavaScript -e '
function run() {
    var chrome = Application("Google Chrome");
    var targetTab = null; // Find targetTab logic same as above
    return chrome.execute(targetTab, {javascript: "window.__foundText || \"Not ready\""});
}
'
```

## macOS Tips

- **`missing value` returned**: The JavaScript returned `undefined` or `null`. Ensure the JS expression explicitly returns a string.
- **Escaped quotes**: Inside AppleScript's JavaScript strings, use `\"` for double quotes. For complex JS, use heredoc: `osascript <<'EOF' ... EOF`.
- **Multiple windows**: Commands target `front window` by default. Use `window 2`, `window 3` for other windows.
- **`-1719` invalid index error on `front window`**: Chrome may have hidden/invisible windows (e.g., from PWAs, background apps, or multi-desktop setups). When `front window` points to a hidden window, AppleScript throws `error -1719`. Fix: use JXA to find a visible window:
  ```bash
  osascript -l JavaScript -e '
  function run() {
      var chrome = Application("Google Chrome");
      var wins = chrome.windows();
      for (var i = 0; i < wins.length; i++) {
          if (wins[i].visible()) {
              return chrome.execute(wins[i].activeTab(), {javascript: "document.title"});
          }
      }
      return "No visible Chrome window found";
  }'
  ```
- **Screenshots**: Use `screencapture -l <windowID>` where windowID comes from `osascript -e 'tell application "Google Chrome" to id of front window'`. See the `Capture Page Screenshot` section for annotated screenshot support.

---

# Windows Approach (Chrome CDP)

Uses Chrome's built-in remote debugging protocol (CDP). Requires a helper script to manage Chrome lifecycle.

## Windows Prerequisites

### One-time setup

Install agent-browser (requires Node.js):

```powershell
npm install -g agent-browser
agent-browser install
```

Chrome must also be running with remote debugging enabled for the current session.

## Windows Preflight

Run these checks before browser automation:

```powershell
Get-Command agent-browser
Invoke-RestMethod -Uri "http://127.0.0.1:9222/json/version"
```

Interpretation:

- If `agent-browser` is not found, Node.js or `agent-browser` is not installed correctly.
- If the CDP endpoint check fails, Chrome is not running with `--remote-debugging-port=9222`.
- In either case, stop and guide the user to fix the prerequisite before continuing.

### Create helper script

Save the following as `chrome-debug.ps1` in a convenient location (e.g., `~\scripts\chrome-debug.ps1`):

```powershell
# chrome-debug.ps1 — Start Chrome with remote debugging enabled
param(
    [int]$Port = 9222,
    [string]$Url = "about:blank"
)

$chromePaths = @(
    "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)

$chromePath = $chromePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $chromePath) {
    Write-Error "Chrome not found. Please install Google Chrome."
    exit 1
}

# Kill existing Chrome processes
Write-Host "Closing existing Chrome instances..."
Get-Process "chrome" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

# Verify Chrome is fully closed
$remaining = Get-Process "chrome" -ErrorAction SilentlyContinue
if ($remaining) {
    Write-Host "Waiting for Chrome to fully close..."
    Start-Sleep -Seconds 3
    Get-Process "chrome" -ErrorAction SilentlyContinue | Stop-Process -Force
}

# Start Chrome with debugging port
Write-Host "Starting Chrome with debugging on port $Port..."
Start-Process $chromePath -ArgumentList "--remote-debugging-port=$Port", "--no-first-run", "--no-default-browser-check", $Url

# Wait and verify
Start-Sleep -Seconds 5
try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/json/version" -TimeoutSec 5
    Write-Host "Chrome debugging active."
    Write-Host "Browser: $($response.Browser)"
    Write-Host "Ready for: agent-browser --cdp $Port"
} catch {
    Write-Error "Failed to connect to Chrome debugging port. Try running this script again."
    exit 1
}
```

## Windows Usage

### Step 1: Start Chrome in debug mode

```powershell
# Run the helper script (closes existing Chrome, restarts with debugging)
powershell -ExecutionPolicy Bypass -File ~\scripts\chrome-debug.ps1
```

Or manually:

```powershell
# Close Chrome completely
taskkill /F /IM chrome.exe 2>$null
timeout /t 3

# Start with debugging port
start chrome --remote-debugging-port=9222 --no-first-run
```

### Step 2: Log in normally

The user logs into the target page in the Chrome window that just opened.

### Step 3: Use agent-browser to interact

#### Observation

```bash
# Get page accessibility snapshot (best for AI to understand page structure)
agent-browser --cdp 9222 snapshot

# Get interactive elements only with @ref labels
agent-browser --cdp 9222 snapshot -i

# Get page text content
agent-browser --cdp 9222 get text

# Get current URL
agent-browser --cdp 9222 get url

# Get page title
agent-browser --cdp 9222 get title
```

#### Navigation

```bash
# Navigate to a URL
agent-browser --cdp 9222 open "https://example.com"

# List open tabs
agent-browser --cdp 9222 tab list

# Switch tab
agent-browser --cdp 9222 tab 2
```

#### Interaction

```bash
# Click an element by reference (from snapshot)
agent-browser --cdp 9222 click @e3

# Click by CSS selector
agent-browser --cdp 9222 click "#submit-btn"

# Fill a form field
agent-browser --cdp 9222 fill @e1 "search text"
```

#### Capture

```bash
# Take a screenshot
agent-browser --cdp 9222 screenshot /tmp/page.png

# Take a full-page screenshot
agent-browser --cdp 9222 screenshot --full /tmp/full-page.png

# Save as PDF
agent-browser --cdp 9222 pdf /tmp/page.pdf
```

#### Advanced

```bash
# Execute JavaScript
agent-browser --cdp 9222 eval "document.title"
agent-browser --cdp 9222 eval "window.scrollBy(0, window.innerHeight); 'done'"
agent-browser --cdp 9222 eval "window.scrollTo(0, document.body.scrollHeight); 'done'"
```

#### Read Page as Structured Markdown

```bash
agent-browser --cdp 9222 eval "(function(maxLen){var R=['script','style','noscript','svg','canvas','template','iframe','object','embed'];var S=['nav','footer','header','aside'];var out=[],cc=0,tr=false;function add(l){if(tr)return;if(cc+l.length+1>maxLen){var r=maxLen-cc;if(r>20)out.push(l.slice(0,r-12)+'…[truncated]');tr=true;return}out.push(l);cc+=l.length+1}function vis(e){if(!(e instanceof HTMLElement))return true;if(e.hidden||e.getAttribute('aria-hidden')==='true')return false;var s=e.style;return s.display!=='none'&&s.visibility!=='hidden'}function res(h){try{return new URL(h,document.baseURI).href}catch(e){return h}}function inl(el){var r='';for(var i=0;i<el.childNodes.length;i++){var c=el.childNodes[i];if(c.nodeType===3){r+=c.textContent.replace(/\s+/g,' ')}else if(c.nodeType===1){var t=c.tagName.toLowerCase(),tx=inl(c);if(t==='strong'||t==='b')r+='**'+tx.trim()+'**';else if(t==='em'||t==='i')r+='*'+tx.trim()+'*';else if(t==='code')r+='`'+tx.trim()+'`';else if(t==='a'){var hr=c.getAttribute('href')||'';if(hr&&!hr.startsWith('#')&&!hr.startsWith('javascript:'))r+='['+tx.trim()+']('+res(hr)+')';else r+=tx}else if(t==='img'){var sr=c.getAttribute('src')||'',al=c.getAttribute('alt')||'';if(sr)r+='!['+al+']('+res(sr)+')'}else if(t==='br')r+='\n';else r+=tx}}return r}function walk(node,d){if(tr)return;if(node.nodeType===3){var t=node.textContent.replace(/\s+/g,' ').trim();if(t)add(t);return}if(node.nodeType!==1)return;var el=node,tag=el.tagName.toLowerCase();if(R.indexOf(tag)!==-1)return;if(!vis(el))return;if(S.indexOf(tag)!==-1&&d<3)return;var m=tag.match(/^h([1-6])$/);if(m){var tx=(el.textContent||'').replace(/\s+/g,' ').trim();if(tx){add('');add('#'.repeat(parseInt(m[1]))+' '+tx);add('')}return}if(tag==='p'){var tx=inl(el).trim();if(tx){add('');add(tx)}return}if(tag==='a'){var hr=el.getAttribute('href')||'',tx=(el.textContent||'').replace(/\s+/g,' ').trim();if(tx&&hr&&!hr.startsWith('#')&&!hr.startsWith('javascript:'))add('['+tx+']('+res(hr)+')');else if(tx)add(tx);return}if(tag==='img'){var sr=el.getAttribute('src')||'',al=el.getAttribute('alt')||'';if(sr)add('!['+al+']('+res(sr)+')');return}if(tag==='table'){add('');var rows=[];var th=el.querySelector('thead');if(th){th.querySelectorAll('tr').forEach(function(r){var c=[];r.querySelectorAll('th,td').forEach(function(d){c.push((d.textContent||'').replace(/\s+/g,' ').trim())});if(c.length)rows.push(c)})}var bd=th?el.querySelector('tbody')||el:el;bd.querySelectorAll('tr').forEach(function(r){if(th&&r.closest('thead'))return;var c=[];r.querySelectorAll('th,td').forEach(function(d){c.push((d.textContent||'').replace(/\s+/g,' ').trim())});if(c.length)rows.push(c)});if(rows.length){var mc=Math.max.apply(null,rows.map(function(r){return r.length}));rows.forEach(function(r){while(r.length<mc)r.push('')});for(var i=0;i<rows.length;i++){add('| '+rows[i].join(' | ')+' |');if(i===0)add('| '+rows[i].map(function(){return'---'}).join(' | ')+' |')}}add('');return}if(tag==='pre'){var ce=el.querySelector('code'),lang=ce&&ce.className?ce.className.match(/language-(\w+)/):null;add('');add('\`\`\`'+(lang?lang[1]:''));(el.textContent||'').trimEnd().split('\n').forEach(function(l){add(l)});add('\`\`\`');add('');return}if(tag==='blockquote'){var tx=(el.textContent||'').replace(/\s+/g,' ').trim();if(tx){add('');add('> '+tx);add('')}return}if(tag==='ul'||tag==='ol'){add('');var ord=tag==='ol';var idx=1;for(var i=0;i<el.children.length;i++){var ch=el.children[i];if(ch.tagName.toLowerCase()==='li'){add((ord?idx+'. ':'- ')+(ch.textContent||'').replace(/\s+/g,' ').trim());idx++}}add('');return}for(var i=0;i<el.childNodes.length;i++){walk(el.childNodes[i],d+1)}}var root=document.querySelector('main')||document.querySelector('article')||document.querySelector('[role=main]')||document.body;if(!root)return '[Empty page]';walk(root,0);return out.join('\n').replace(/\n{3,}/g,'\n\n').trim()})(15000)"
```

#### List Interactive Elements

```bash
agent-browser --cdp 9222 eval "(function(){var SEL='a[href],button,input,select,textarea,[role=button],[onclick],[contenteditable=true],[tabindex]';var els=document.querySelectorAll(SEL);var result=[],cache=[];for(var i=0;i<els.length;i++){var el=els[i];if(el.tagName.toLowerCase()==='script'||el.tagName.toLowerCase()==='style')continue;if(el.closest('script,style'))continue;if(el.getAttribute('aria-hidden')==='true')continue;var rect=el.getBoundingClientRect();if(rect.width<=0||rect.height<=0)continue;var cs=window.getComputedStyle(el);if(cs.display==='none'||cs.visibility==='hidden'||cs.opacity==='0')continue;if(el.hidden)continue;var idx=cache.length;cache.push(el);var tag=el.tagName.toLowerCase();var parts='['+idx+'] <'+tag+'>';if(el.type)parts+=' type=\"'+el.type+'\"';if(el.name)parts+=' name=\"'+el.name+'\"';if(el.placeholder)parts+=' placeholder=\"'+el.placeholder+'\"';if(el.href)parts+=' href=\"'+el.href+'\"';var label=el.getAttribute('aria-label')||(el.textContent||'').replace(/\\s+/g,' ').trim();if(label)parts+=' \"'+label.substring(0,80)+'\"';result.push(parts)}window.__interactiveElements=cache;return result.join('\n')})()"
```

#### Click/Fill by Element Index

```bash
# Click element at index 3
agent-browser --cdp 9222 eval "window.__interactiveElements[3].click(); 'done'"

# Fill input at index 5
agent-browser --cdp 9222 eval "var el=window.__interactiveElements[5]; el.value='search text'; el.dispatchEvent(new Event('input',{bubbles:true})); 'done'"
```

#### Safety Check (Pre-action)

```bash
agent-browser --cdp 9222 eval "(function(){var href=location.href;if(/^chrome:|^chrome-extension:|^about:/.test(href))return JSON.stringify({safe:false,reason:'Chrome internal page'});var u;try{u=new URL(href)}catch(e){return JSON.stringify({safe:false,reason:'Invalid URL'})}var h=u.hostname.toLowerCase();function ew(host,sfx){return host===sfx||host.slice(-(sfx.length+1))==='.'+sfx}if(h.endsWith('.bank'))return JSON.stringify({safe:false,reason:'Banking domain (.bank)'});var bk=['chase.com','wellsfargo.com','bankofamerica.com','citi.com','citibank.com','capitalone.com','usbank.com','pnc.com','tdbank.com','hsbc.com'];for(var i=0;i<bk.length;i++){if(ew(h,bk[i]))return JSON.stringify({safe:false,reason:'Banking: '+bk[i]})}var py=['paypal.com','venmo.com','stripe.com','squareup.com','wise.com','revolut.com','robinhood.com','coinbase.com','binance.com'];for(var i=0;i<py.length;i++){if(ew(h,py[i]))return JSON.stringify({safe:false,reason:'Payment: '+py[i]})}var ax=['accounts.google.com','login.microsoftonline.com','login.live.com'];for(var i=0;i<ax.length;i++){if(h===ax[i])return JSON.stringify({safe:false,reason:'Auth: '+ax[i]})}if(ew(h,'icloud.com')&&u.pathname.startsWith('/account'))return JSON.stringify({safe:false,reason:'Auth: icloud.com/account'});var as=['okta.com','auth0.com','onelogin.com'];for(var i=0;i<as.length;i++){if(ew(h,as[i]))return JSON.stringify({safe:false,reason:'Auth: '+as[i]})}var cx=['console.aws.amazon.com','console.cloud.google.com','portal.azure.com'];for(var i=0;i<cx.length;i++){if(h===cx[i])return JSON.stringify({safe:false,reason:'Cloud: '+cx[i]})}return JSON.stringify({safe:true,reason:'OK'})})()"
```

#### Wait for Element

```bash
# Inject wait script (poll result with a second eval call)
agent-browser --cdp 9222 eval "(function(sel,timeout,cond){var start=Date.now();function vis(el){if(!el)return false;var r=el.getBoundingClientRect();if(r.width===0&&r.height===0)return false;var s=window.getComputedStyle(el);return s.display!=='none'&&s.visibility!=='hidden'&&s.opacity!=='0'}function chk(){var el=document.querySelector(sel);if(cond==='attached')return el!==null;if(cond==='visible')return el!==null&&vis(el);if(cond==='hidden')return el===null||!vis(el);if(cond==='loaded')return document.readyState==='complete'&&el!==null;return el!==null}if(chk()){window.__waitResult=JSON.stringify({found:true,elapsed:Date.now()-start});return window.__waitResult}var ob=new MutationObserver(function(){if(chk()){ob.disconnect();clearTimeout(tm);window.__waitResult=JSON.stringify({found:true,elapsed:Date.now()-start})}});ob.observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['style','class','hidden']});var tm=setTimeout(function(){ob.disconnect();window.__waitResult=JSON.stringify({found:false,elapsed:Date.now()-start})},timeout);window.__waitResult=null;return 'waiting...'})('YOUR_SELECTOR',5000,'visible')"

# Poll for result
agent-browser --cdp 9222 eval "window.__waitResult"
```

#### Read Console Logs

```bash
# Inject console interceptor
agent-browser --cdp 9222 eval "(function(){if(window.__consoleLogs)return 'already injected';window.__consoleLogs=[];var orig={log:console.log,warn:console.warn,error:console.error,info:console.info};['log','warn','error','info'].forEach(function(m){console[m]=function(){var args=Array.prototype.slice.call(arguments).map(function(a){try{return typeof a==='object'?JSON.stringify(a):String(a)}catch(e){return String(a)}});window.__consoleLogs.push({level:m,msg:args.join(' '),ts:Date.now()});orig[m].apply(console,arguments)}});return 'Console interceptor injected'})()"

# Read captured logs
agent-browser --cdp 9222 eval "JSON.stringify(window.__consoleLogs||[])"
```

#### Monitor Network Requests

```bash
# Inject network interceptor
agent-browser --cdp 9222 eval "(function(){if(window.__networkLogs)return 'already injected';window.__networkLogs=[];var origOpen=XMLHttpRequest.prototype.open;var origSend=XMLHttpRequest.prototype.send;XMLHttpRequest.prototype.open=function(m,u){this.__reqInfo={method:m,url:u,ts:Date.now()};return origOpen.apply(this,arguments)};XMLHttpRequest.prototype.send=function(){var info=this.__reqInfo;var xhr=this;xhr.addEventListener('loadend',function(){window.__networkLogs.push({method:info.method,url:info.url,status:xhr.status,timestamp:info.ts,duration:Date.now()-info.ts})});return origSend.apply(this,arguments)};var origFetch=window.fetch;window.fetch=function(input,init){var method=(init&&init.method)||'GET';var url=typeof input==='string'?input:input.url;var ts=Date.now();return origFetch.apply(this,arguments).then(function(resp){window.__networkLogs.push({method:method,url:url,status:resp.status,timestamp:ts,duration:Date.now()-ts});return resp}).catch(function(err){window.__networkLogs.push({method:method,url:url,status:'error',timestamp:ts,duration:Date.now()-ts,error:err.message});throw err})};return 'Network interceptor injected'})()"

# Read captured requests
agent-browser --cdp 9222 eval "JSON.stringify(window.__networkLogs||[])"
```

## Windows Tips

- **Chrome must be fully closed** before starting with `--remote-debugging-port`. If any Chrome process remains, the port will not bind.
- **Port conflict**: If 9222 is taken, use a different port (e.g., 9333) in both the startup command and `--cdp` flag.
- **First use**: After installing agent-browser, run `agent-browser install` once to download Chromium (used only as fallback; CDP connects to your real Chrome).
- **Snapshot for navigation**: Use `agent-browser --cdp 9222 snapshot -i` to get interactive elements only. Each element has a `@ref` (e.g., `@e2`) you can use in click/fill commands.

---

# Common Workflow: Access an Authenticated Page

This workflow applies to both platforms:

1. **Detect platform** with `uname -s`
2. **Run the platform-specific preflight check**
3. **If preflight fails, stop and guide the user through setup**
4. **Ask the user** to open the target URL in their Chrome and log in normally
5. **Confirm the page is loaded**:
   - macOS: `osascript -e 'tell application "Google Chrome" to return URL of active tab of front window'`
   - Windows: `agent-browser --cdp 9222 get url`
6. **If the page is long, lazy-loaded, or infinite-scroll, scroll the real page first**:
   - Scroll one viewport at a time
   - Wait 1-2 seconds after each scroll
   - Read again after new content appears
   - Prefer repeated scrolling over alternate fetch methods
7. **Extract content**:
   - macOS: `osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "document.body.innerText.substring(0, 15000)"'`
   - Windows: `agent-browser --cdp 9222 get text`
8. **Interact with the page** (click, navigate, fill) using platform-specific commands above
9. **Wait after navigation or scroll** — SPA pages and lazy-loaded pages need time before content updates. Prefer smart wait (use `Wait for Element` script); fall back to `sleep 2` only when no specific wait condition is available

---

## Best Practices

1. **Smart wait after navigation**: Prefer using the `Wait for Element` injectable script to wait for a specific target element to appear, rather than a blind `sleep 2`. Only fall back to `sleep 2` when you cannot determine a specific element or condition to wait for.

2. **Scroll before interacting**: If the target element might be below the fold, scroll down first. Off-screen elements may fail to click.

3. **Confirm actions succeeded**: After each action, verify the result:
   - After navigate: check the URL changed
   - After click: read content to see if the page updated
   - After fill: verify the field value

4. **One action at a time**: Execute one browser action, observe the result, then decide the next action. Do not chain multiple clicks or navigations without checking between them.

5. **Use snapshot on Windows**: Before interacting with elements, run `agent-browser --cdp 9222 snapshot -i` to see interactive elements with @ref labels. This is more reliable than guessing CSS selectors.

6. **Paginate long content**: On macOS, use `.substring(start, end)` to read content in chunks. Never try to read an entire very long page at once.

7. **Prefer scrolling over alternative methods**: When content isn't loaded yet (lazy-load, infinite scroll), scroll the real browser page first rather than switching to a different reading strategy.

8. **Avoid redundant reads**: If your last action was a pure read (did not change page state), do not re-read the same content. Only re-read after click, navigation, form submission, or scroll that loads new content. If you already know the exact selector or element index, operate directly without listing all elements first. Never execute the same read command twice in a row.

9. **Run safety check on unfamiliar pages**: Before interacting with a page you haven't verified, inject the `Safety Check (Pre-action)` script to confirm the URL is not on the sensitive site blacklist.

## Recovery Strategy

If a browser action fails or produces unexpected results:

1. **Observe first**: Read the page content or take a screenshot (Windows) to understand the current state
2. **Re-read elements**: The page may have changed — re-read to get fresh element references
3. **Try alternative targeting**: If CSS selector failed, try text match; if text match failed, try a different selector
4. **Check for popups/modals**: Dialogs, cookie banners, or overlays may be blocking the target element — dismiss them first
5. **Do NOT retry blindly**: Never repeat the exact same failed action more than twice. Change your approach instead

## Security Boundaries (Mandatory Rules)

The following are **enforced rules**, not suggestions. The agent MUST refuse operations that violate them.

### Sensitive Site Blacklist

On the following domains, **only read operations** (get text, get URL, get title, read markdown) are allowed. All click, fill, and execute operations are **forbidden**:

- **Banking**: chase, wellsfargo, bankofamerica, citi, capitalone, usbank, pnc, tdbank, hsbc, and any `.bank` domain
- **Payments**: paypal, venmo, stripe, squareup, wise, revolut, robinhood, coinbase, binance
- **Identity/Auth**: `accounts.google.com`, `login.microsoftonline.com`, `login.live.com`, `icloud.com/account`, `*.okta.com`, `*.auth0.com`, `*.onelogin.com`
- **Cloud Consoles**: `console.aws.amazon.com`, `console.cloud.google.com`, `portal.azure.com`
- **Chrome Internal**: `chrome://`, `chrome-extension://`, `about:`

### Password Field Protection

Before executing any fill or click action, check the target element. **Refuse** the operation if the target matches any of:

- `input[type="password"]`
- `input[name]` containing "password" or "passwd"
- `input[autocomplete="current-password"]` or `input[autocomplete="new-password"]`

### Payment Button Protection

**Never click** buttons whose text matches any of these patterns:

- English: pay, purchase, buy, checkout, place order, submit order, confirm payment, subscribe, upgrade, donate
- 中文: 付款, 支付, 购买, 下单, 确认订单, 立即购买

### Pre-action Safety Check

Before any interaction on an unfamiliar page, use the `Safety Check (Pre-action)` injectable script (see macOS/Windows Advanced sections above) to programmatically verify the current URL is not blacklisted. If the check returns `{safe: false}`, switch to read-only mode.

### General Rules

- Never execute untrusted or user-provided JavaScript — commands run in the user's authenticated session
- `chrome://` pages allow basic JS execution (e.g., `document.title`) but all meaningful content is inside closed shadow DOM — `innerText` returns empty, interactive elements are unreachable, and clicks have no effect. Treat these pages as effectively inaccessible.
- Cross-origin iframes cannot be accessed — inform the user if the target content is inside one
- If the user's page contains sensitive financial or medical data, confirm with the user before extracting content

# Common Limitations

- **Requires user login**: This skill cannot log in on behalf of the user. The user must be authenticated in Chrome first.
- **Long content**: For lazy-loaded pages, scroll the real page first to load more content. Use `.substring(start, end)` (macOS) or `eval "document.body.innerText.substring(0, 15000)"` (Windows) to paginate output after content has loaded.
- **SPA pages**: After clicking navigation elements, wait for the target content to appear (prefer smart wait) before reading. Fall back to `sleep 2` if no specific wait condition is available.
- **Security**: Commands execute JavaScript in the user's authenticated session. Never run untrusted scripts.
- **macOS-specific**: AppleScript itself has no screenshot API, but `screencapture -l <windowID>` can capture the Chrome window (see `Capture Page Screenshot` in the macOS Advanced section). Chrome must be in foreground.
- **Windows-specific**: Chrome must be restarted with debugging flag. Requires agent-browser + Node.js.
