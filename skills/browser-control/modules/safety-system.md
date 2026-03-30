# Security Boundaries — Full Reference

Three-layer safety system. These are **enforced rules**, not suggestions.

## Layer 1: Domain Blacklist

On these domains, **only read operations** are allowed. All click, fill, and execute operations are **forbidden**:

- **Banking**: chase, wellsfargo, bankofamerica, citi, capitalone, usbank, pnc, tdbank, hsbc, and any `.bank` domain
- **Payments**: paypal, venmo, stripe, squareup, wise, revolut, robinhood, coinbase, binance
- **Identity/Auth**: `accounts.google.com`, `login.microsoftonline.com`, `login.live.com`, `icloud.com/account`, `*.okta.com`, `*.auth0.com`, `*.onelogin.com`
- **Cloud Consoles**: `console.aws.amazon.com`, `console.cloud.google.com`, `portal.azure.com`
- **Chrome Internal**: `chrome://`, `chrome-extension://`, `about:`

### Safety Check Script

Before interacting with an unfamiliar page, inject the safety check:

```bash
# macOS
osascript <<'AS'
tell application "Google Chrome"
    execute active tab of front window javascript "
(function(){
  var href=location.href;
  if(/^chrome:|^chrome-extension:|^about:/.test(href))return JSON.stringify({safe:false,reason:'Chrome internal page'});
  var u;try{u=new URL(href)}catch(e){return JSON.stringify({safe:false,reason:'Invalid URL'})}
  var h=u.hostname.toLowerCase();
  function ew(host,sfx){return host===sfx||host.slice(-(sfx.length+1))==='.'+ sfx}
  if(h.endsWith('.bank'))return JSON.stringify({safe:false,reason:'Banking domain'});
  var bk=['chase.com','wellsfargo.com','bankofamerica.com','citi.com','citibank.com','capitalone.com','usbank.com','pnc.com','tdbank.com','hsbc.com'];
  for(var i=0;i<bk.length;i++){if(ew(h,bk[i]))return JSON.stringify({safe:false,reason:'Banking: '+bk[i]})}
  var py=['paypal.com','venmo.com','stripe.com','squareup.com','wise.com','revolut.com','robinhood.com','coinbase.com','binance.com'];
  for(var i=0;i<py.length;i++){if(ew(h,py[i]))return JSON.stringify({safe:false,reason:'Payment: '+py[i]})}
  var ax=['accounts.google.com','login.microsoftonline.com','login.live.com'];
  for(var i=0;i<ax.length;i++){if(h===ax[i])return JSON.stringify({safe:false,reason:'Auth: '+ax[i]})}
  if(ew(h,'icloud.com')&&u.pathname.startsWith('/account'))return JSON.stringify({safe:false,reason:'Auth: icloud.com'});
  var as=['okta.com','auth0.com','onelogin.com'];
  for(var i=0;i<as.length;i++){if(ew(h,as[i]))return JSON.stringify({safe:false,reason:'Auth: '+as[i]})}
  var cx=['console.aws.amazon.com','console.cloud.google.com','portal.azure.com'];
  for(var i=0;i<cx.length;i++){if(h===cx[i])return JSON.stringify({safe:false,reason:'Cloud: '+cx[i]})}
  return JSON.stringify({safe:true,reason:'OK'});
})()"
end tell
AS

# CDP Proxy
curl -s -X POST "http://localhost:3456/eval?target=ID" -d '(function(){var href=location.href;if(/^chrome:|^chrome-extension:|^about:/.test(href))return JSON.stringify({safe:false,reason:"Chrome internal"});var u;try{u=new URL(href)}catch(e){return JSON.stringify({safe:false,reason:"Invalid URL"})}var h=u.hostname.toLowerCase();function ew(host,sfx){return host===sfx||host.slice(-(sfx.length+1))==="."+sfx}if(h.endsWith(".bank"))return JSON.stringify({safe:false,reason:"Banking"});var bk=["chase.com","wellsfargo.com","bankofamerica.com","citi.com","citibank.com","capitalone.com","usbank.com","pnc.com","tdbank.com","hsbc.com"];for(var i=0;i<bk.length;i++)if(ew(h,bk[i]))return JSON.stringify({safe:false,reason:"Banking: "+bk[i]});var py=["paypal.com","venmo.com","stripe.com","squareup.com","wise.com","revolut.com","robinhood.com","coinbase.com","binance.com"];for(var i=0;i<py.length;i++)if(ew(h,py[i]))return JSON.stringify({safe:false,reason:"Payment: "+py[i]});var ax=["accounts.google.com","login.microsoftonline.com","login.live.com"];for(var i=0;i<ax.length;i++)if(h===ax[i])return JSON.stringify({safe:false,reason:"Auth: "+ax[i]});if(ew(h,"icloud.com")&&u.pathname.startsWith("/account"))return JSON.stringify({safe:false,reason:"Auth: icloud.com"});var as=["okta.com","auth0.com","onelogin.com"];for(var i=0;i<as.length;i++)if(ew(h,as[i]))return JSON.stringify({safe:false,reason:"Auth: "+as[i]});var cx=["console.aws.amazon.com","console.cloud.google.com","portal.azure.com"];for(var i=0;i<cx.length;i++)if(h===cx[i])return JSON.stringify({safe:false,reason:"Cloud: "+cx[i]});return JSON.stringify({safe:true,reason:"OK"})})()'
```

## Layer 2: Element-Level Protection

Before interacting with any element, check:

- **Password fields**: Refuse if target is `input[type=password]`, `input[name*=password]`, `input[autocomplete=current-password]`, or `input[autocomplete=new-password]`
- **Payment buttons**: Never click buttons containing: pay, purchase, buy, checkout, place order, submit order, confirm payment, subscribe, upgrade, donate, 付款, 支付, 购买, 下单, 确认订单, 立即购买

## Layer 3: Operation Confirmation

For write operations on sensitive pages, confirm with the user before executing:

```
I'm about to:
- Click "Submit Application" on example.com/apply
- This will submit the form with the data filled above

Should I proceed? (yes/no)
```

**Require confirmation for**: form submissions, actions with words submit/send/post/publish/create/delete/remove, file uploads to external services, actions on pages not previously visited in this session.

## General Security Rules

- Never execute untrusted or user-provided JavaScript in authenticated sessions
- `chrome://` pages: basic JS works but meaningful content is in closed shadow DOM — treat as inaccessible
- Cross-origin iframes cannot be accessed — inform the user
- Sensitive financial/medical data: confirm with user before extracting
