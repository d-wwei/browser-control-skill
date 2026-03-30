# Advanced AppleScript Techniques

Advanced macOS-specific patterns for robust tab targeting and element waiting.

## JXA Robust Tab Targeting

When macOS has multiple Chrome processes (PWAs, multiple desktops), use JXA to find the exact tab:

```bash
osascript -l JavaScript -e '
function run() {
    var chrome = Application("Google Chrome");
    var windows = chrome.windows();
    for (var i = 0; i < windows.length; i++) {
        var tabs = windows[i].tabs();
        for (var j = 0; j < tabs.length; j++) {
            if (tabs[j].url().indexOf("YOUR_URL_PART") !== -1) {
                return chrome.execute(tabs[j], {javascript: "document.title"});
            }
        }
    }
    return "Target tab not found.";
}'
```

## Wait for Element (MutationObserver)

MutationObserver-based wait — replaces blind `sleep`:

```bash
# Step 1: Inject wait
osascript -l JavaScript -e '
function run() {
    var chrome = Application("Google Chrome");
    var tab = chrome.windows[0].activeTab();
    chrome.execute(tab, {javascript: "(function(sel,timeout,cond){var start=Date.now();function vis(el){if(!el)return false;var r=el.getBoundingClientRect();if(r.width===0&&r.height===0)return false;var s=window.getComputedStyle(el);return s.display!==\"none\"&&s.visibility!==\"hidden\"&&s.opacity!==\"0\"}function chk(){var el=document.querySelector(sel);if(cond===\"attached\")return el!==null;if(cond===\"visible\")return el!==null&&vis(el);if(cond===\"hidden\")return el===null||!vis(el);if(cond===\"loaded\")return document.readyState===\"complete\"&&el!==null;return el!==null}if(chk()){window.__waitResult=JSON.stringify({found:true,elapsed:Date.now()-start});return}var ob=new MutationObserver(function(){if(chk()){ob.disconnect();clearTimeout(tm);window.__waitResult=JSON.stringify({found:true,elapsed:Date.now()-start})}});ob.observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:[\"style\",\"class\",\"hidden\"]});var tm=setTimeout(function(){ob.disconnect();window.__waitResult=JSON.stringify({found:false,elapsed:Date.now()-start})},timeout);window.__waitResult=null})(\"YOUR_SELECTOR\",5000,\"visible\")"});
    return "Wait injected. Poll window.__waitResult.";
}'

# Step 2: Poll result
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "window.__waitResult"'
```

Conditions: `visible` | `hidden` | `attached` | `loaded`
