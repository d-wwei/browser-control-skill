# DOM Extraction Module

> Part of browser-control skill. Load when needed, not by default.

## Advanced: Read Page as Structured Markdown

Converts DOM into clean Markdown preserving headings, lists, tables, links, code blocks, images. Far better than `innerText` when structure matters.

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

Custom maxLength: replace the `15000` parameter.

## Advanced: Virtual Scrolling & SPA Crawler

Modern apps (X/Twitter, React Virtualized) destroy DOM nodes when scrolled out of view. Inject a crawler that scrolls and accumulates data:

```bash
osascript -l JavaScript -e '
function run() {
    var chrome = Application("Google Chrome");
    var tab = chrome.windows[0].activeTab();
    chrome.execute(tab, {javascript: "window.scrollTo(0,0);"});
    delay(2);
    chrome.execute(tab, {javascript: "window.__foundText=\"\";var si=setInterval(()=>{var w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT,null,false);var n;while(n=w.nextNode()){if(n.nodeValue.includes(\"YOUR_KEYWORD\")){var p=n.parentElement;while(p&&![\"DIV\",\"PRE\",\"CODE\"].includes(p.tagName))p=p.parentElement;if(p&&!window.__foundText.includes(p.innerText))window.__foundText+=p.innerText+\"\\n\\n---\\n\\n\"}}window.scrollBy(0,800);if(window.scrollY+window.innerHeight>=document.body.scrollHeight)clearInterval(si)},500);"});
    return "Started. Poll window.__foundText after 5-10s.";
}'
```
