# Interactive Elements Module

> Part of browser-control skill. Load when needed, not by default.

## Advanced: List Interactive Elements

Scans all interactive elements, filters hidden ones, assigns numeric indices, caches references in `window.__interactiveElements`.

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

## Click/Fill by Element Index

After listing, use by index:

```bash
# Click element at index 3
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "window.__interactiveElements[3].click(); \"done\";"'

# Fill input at index 5
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "var el=window.__interactiveElements[5]; el.value=\"search text\"; el.dispatchEvent(new Event(\"input\",{bubbles:true})); \"done\";"'
```

> Element indices become stale after page navigation or DOM changes. Re-run to refresh.

## Advanced: Screenshots

```bash
# Get Chrome window ID and capture
WINID=$(osascript -e 'tell application "Google Chrome" to id of front window')
screencapture -l "$WINID" /tmp/chrome-screenshot.png

# Annotated screenshot (with element index badges)
# Step 1: Inject annotations (run List Interactive Elements first)
osascript <<'AS'
tell application "Google Chrome"
    execute active tab of front window javascript "
(function(){
  if(!window.__interactiveElements)return 'Run List Interactive Elements first';
  var c=document.createElement('div');c.id='__agentAnnotations';
  c.style.cssText='position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:2147483647';
  window.__interactiveElements.forEach(function(el,i){
    var r=el.getBoundingClientRect();if(r.width<=0||r.height<=0)return;
    var b=document.createElement('div');b.style.cssText='position:fixed;left:'+(r.left-2)+'px;top:'+(r.top-2)+'px;width:'+(r.width+4)+'px;height:'+(r.height+4)+'px;border:2px solid rgba(255,0,0,0.6);background:rgba(255,0,0,0.08);pointer-events:none;z-index:2147483647';
    var l=document.createElement('span');l.textContent=i;l.style.cssText='position:absolute;top:-10px;left:-2px;background:red;color:white;font-size:10px;font-weight:bold;padding:1px 4px;border-radius:3px;font-family:monospace';
    b.appendChild(l);c.appendChild(b);
  });
  document.body.appendChild(c);
  return 'Annotations added';
})()"
end tell
AS
# Step 2: Capture
sleep 0.5 && WINID=$(osascript -e 'tell application "Google Chrome" to id of front window') && screencapture -l "$WINID" /tmp/chrome-annotated.png
# Step 3: Remove annotations
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "var a=document.getElementById(\"__agentAnnotations\");if(a)a.remove();\"done\";"'
```
