# Console & Network Interception Module

> Part of browser-control skill. Load when needed, not by default.

## Advanced: Console & Network Interception

```bash
# Inject console interceptor
osascript <<'AS'
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
})()"
end tell
AS

# Read logs
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "JSON.stringify(window.__consoleLogs||[])"'

# Inject network interceptor
osascript <<'AS'
tell application "Google Chrome"
    execute active tab of front window javascript "
(function(){
  if(window.__networkLogs)return 'already injected';
  window.__networkLogs=[];
  var origOpen=XMLHttpRequest.prototype.open;var origSend=XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open=function(m,u){this.__reqInfo={method:m,url:u,ts:Date.now()};return origOpen.apply(this,arguments)};
  XMLHttpRequest.prototype.send=function(){var info=this.__reqInfo;var xhr=this;xhr.addEventListener('loadend',function(){window.__networkLogs.push({method:info.method,url:info.url,status:xhr.status,timestamp:info.ts,duration:Date.now()-info.ts})});return origSend.apply(this,arguments)};
  var origFetch=window.fetch;
  window.fetch=function(input,init){var method=(init&&init.method)||'GET';var url=typeof input==='string'?input:input.url;var ts=Date.now();return origFetch.apply(this,arguments).then(function(resp){window.__networkLogs.push({method:method,url:url,status:resp.status,timestamp:ts,duration:Date.now()-ts});return resp}).catch(function(err){window.__networkLogs.push({method:method,url:url,status:'error',timestamp:ts,duration:Date.now()-ts,error:err.message});throw err})};
  return 'Network interceptor injected';
})()"
end tell
AS

# Read network logs
osascript -e 'tell application "Google Chrome" to execute active tab of front window javascript "JSON.stringify(window.__networkLogs||[])"'
```
