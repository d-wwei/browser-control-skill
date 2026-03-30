/**
 * Tests for the browser-control safety check function.
 *
 * Extracted from: skills/browser-control/SKILL.md (Safety Check Script)
 *
 * Run: node --test tests/test_safety.mjs
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

// ---------------------------------------------------------------------------
// Extract the core safety-check logic into a testable function.
// The original runs as an IIFE reading `location.href`; here we accept
// a URL string as a parameter instead.
// ---------------------------------------------------------------------------

function safetyCheck(href) {
  if (/^chrome:|^chrome-extension:|^about:/.test(href))
    return { safe: false, reason: 'Chrome internal page' };

  let u;
  try {
    u = new URL(href);
  } catch (_e) {
    return { safe: false, reason: 'Invalid URL' };
  }

  const h = u.hostname.toLowerCase();

  function ew(host, sfx) {
    return host === sfx || host.slice(-(sfx.length + 1)) === '.' + sfx;
  }

  // .bank TLD
  if (h.endsWith('.bank'))
    return { safe: false, reason: 'Banking domain' };

  // Banking domains
  const bk = [
    'chase.com', 'wellsfargo.com', 'bankofamerica.com', 'citi.com',
    'citibank.com', 'capitalone.com', 'usbank.com', 'pnc.com',
    'tdbank.com', 'hsbc.com',
  ];
  for (let i = 0; i < bk.length; i++) {
    if (ew(h, bk[i])) return { safe: false, reason: 'Banking: ' + bk[i] };
  }

  // Payment domains
  const py = [
    'paypal.com', 'venmo.com', 'stripe.com', 'squareup.com', 'wise.com',
    'revolut.com', 'robinhood.com', 'coinbase.com', 'binance.com',
  ];
  for (let i = 0; i < py.length; i++) {
    if (ew(h, py[i])) return { safe: false, reason: 'Payment: ' + py[i] };
  }

  // Auth domains (exact match)
  const ax = [
    'accounts.google.com', 'login.microsoftonline.com', 'login.live.com',
  ];
  for (let i = 0; i < ax.length; i++) {
    if (h === ax[i]) return { safe: false, reason: 'Auth: ' + ax[i] };
  }

  // iCloud account path
  if (ew(h, 'icloud.com') && u.pathname.startsWith('/account'))
    return { safe: false, reason: 'Auth: icloud.com' };

  // Auth wildcard suffixes (*.okta.com, etc.)
  const as = ['okta.com', 'auth0.com', 'onelogin.com'];
  for (let i = 0; i < as.length; i++) {
    if (ew(h, as[i])) return { safe: false, reason: 'Auth: ' + as[i] };
  }

  // Cloud consoles (exact match)
  const cx = [
    'console.aws.amazon.com', 'console.cloud.google.com',
    'portal.azure.com',
  ];
  for (let i = 0; i < cx.length; i++) {
    if (h === cx[i]) return { safe: false, reason: 'Cloud: ' + cx[i] };
  }

  return { safe: true, reason: 'OK' };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('Safety Check: Banking domains blocked', () => {
  it('blocks chase.com', () => {
    const r = safetyCheck('https://chase.com/accounts');
    assert.equal(r.safe, false);
    assert.match(r.reason, /Banking/);
  });

  it('blocks wellsfargo.com', () => {
    const r = safetyCheck('https://www.wellsfargo.com/');
    assert.equal(r.safe, false);
    assert.match(r.reason, /Banking/);
  });

  it('blocks bankofamerica.com', () => {
    const r = safetyCheck('https://bankofamerica.com/login');
    assert.equal(r.safe, false);
    assert.match(r.reason, /Banking/);
  });

  it('blocks subdomain.chase.com', () => {
    const r = safetyCheck('https://secure.chase.com/web/auth/');
    assert.equal(r.safe, false);
    assert.match(r.reason, /Banking.*chase/);
  });
});

describe('Safety Check: Payment domains blocked', () => {
  it('blocks paypal.com', () => {
    const r = safetyCheck('https://www.paypal.com/myaccount');
    assert.equal(r.safe, false);
    assert.match(r.reason, /Payment.*paypal/);
  });

  it('blocks stripe.com', () => {
    const r = safetyCheck('https://dashboard.stripe.com/payments');
    assert.equal(r.safe, false);
    assert.match(r.reason, /Payment.*stripe/);
  });

  it('blocks coinbase.com', () => {
    const r = safetyCheck('https://coinbase.com/trade');
    assert.equal(r.safe, false);
    assert.match(r.reason, /Payment.*coinbase/);
  });
});

describe('Safety Check: Auth domains blocked', () => {
  it('blocks accounts.google.com', () => {
    const r = safetyCheck('https://accounts.google.com/signin');
    assert.equal(r.safe, false);
    assert.match(r.reason, /Auth.*accounts\.google/);
  });

  it('blocks login.microsoftonline.com', () => {
    const r = safetyCheck('https://login.microsoftonline.com/common/oauth2');
    assert.equal(r.safe, false);
    assert.match(r.reason, /Auth.*microsoftonline/);
  });

  it('blocks *.okta.com (subdomain)', () => {
    const r = safetyCheck('https://mycompany.okta.com/app/sso');
    assert.equal(r.safe, false);
    assert.match(r.reason, /Auth.*okta/);
  });

  it('blocks okta.com itself', () => {
    const r = safetyCheck('https://okta.com/');
    assert.equal(r.safe, false);
    assert.match(r.reason, /Auth.*okta/);
  });

  it('blocks *.auth0.com', () => {
    const r = safetyCheck('https://tenant.auth0.com/authorize');
    assert.equal(r.safe, false);
    assert.match(r.reason, /Auth.*auth0/);
  });

  it('blocks login.live.com', () => {
    const r = safetyCheck('https://login.live.com/');
    assert.equal(r.safe, false);
    assert.match(r.reason, /Auth/);
  });
});

describe('Safety Check: Cloud consoles blocked', () => {
  it('blocks console.aws.amazon.com', () => {
    const r = safetyCheck('https://console.aws.amazon.com/ec2/');
    assert.equal(r.safe, false);
    assert.match(r.reason, /Cloud.*aws/);
  });

  it('blocks console.cloud.google.com', () => {
    const r = safetyCheck('https://console.cloud.google.com/iam');
    assert.equal(r.safe, false);
    assert.match(r.reason, /Cloud.*google/);
  });

  it('blocks portal.azure.com', () => {
    const r = safetyCheck('https://portal.azure.com/#home');
    assert.equal(r.safe, false);
    assert.match(r.reason, /Cloud.*azure/);
  });
});

describe('Safety Check: Chrome internals blocked', () => {
  it('blocks chrome://settings', () => {
    const r = safetyCheck('chrome://settings');
    assert.equal(r.safe, false);
    assert.match(r.reason, /Chrome internal/);
  });

  it('blocks chrome-extension://xxx', () => {
    const r = safetyCheck('chrome-extension://abcdefghijklmnop/popup.html');
    assert.equal(r.safe, false);
    assert.match(r.reason, /Chrome internal/);
  });

  it('blocks about:blank', () => {
    const r = safetyCheck('about:blank');
    assert.equal(r.safe, false);
    assert.match(r.reason, /Chrome internal/);
  });

  it('blocks about:version', () => {
    const r = safetyCheck('about:version');
    assert.equal(r.safe, false);
    assert.match(r.reason, /Chrome internal/);
  });
});

describe('Safety Check: Normal domains allowed', () => {
  it('allows example.com', () => {
    const r = safetyCheck('https://example.com/');
    assert.equal(r.safe, true);
    assert.equal(r.reason, 'OK');
  });

  it('allows github.com', () => {
    const r = safetyCheck('https://github.com/user/repo');
    assert.equal(r.safe, true);
    assert.equal(r.reason, 'OK');
  });

  it('allows google.com (not accounts.google.com)', () => {
    const r = safetyCheck('https://www.google.com/search?q=test');
    assert.equal(r.safe, true);
    assert.equal(r.reason, 'OK');
  });

  it('allows mail.google.com (not accounts.google.com)', () => {
    const r = safetyCheck('https://mail.google.com/mail/');
    assert.equal(r.safe, true);
    assert.equal(r.reason, 'OK');
  });

  it('allows docs.google.com', () => {
    const r = safetyCheck('https://docs.google.com/document/d/123');
    assert.equal(r.safe, true);
    assert.equal(r.reason, 'OK');
  });

  it('allows stackoverflow.com', () => {
    const r = safetyCheck('https://stackoverflow.com/questions');
    assert.equal(r.safe, true);
    assert.equal(r.reason, 'OK');
  });
});

describe('Safety Check: iCloud edge cases', () => {
  it('blocks icloud.com/account', () => {
    const r = safetyCheck('https://www.icloud.com/account/');
    assert.equal(r.safe, false);
    assert.match(r.reason, /Auth.*icloud/);
  });

  it('blocks icloud.com/account/settings', () => {
    const r = safetyCheck('https://www.icloud.com/account/settings');
    assert.equal(r.safe, false);
    assert.match(r.reason, /Auth.*icloud/);
  });

  it('allows icloud.com/photos', () => {
    const r = safetyCheck('https://www.icloud.com/photos/');
    assert.equal(r.safe, true);
    assert.equal(r.reason, 'OK');
  });

  it('allows icloud.com root', () => {
    const r = safetyCheck('https://www.icloud.com/');
    assert.equal(r.safe, true);
    assert.equal(r.reason, 'OK');
  });
});

describe('Safety Check: .bank TLD blocked', () => {
  it('blocks any .bank TLD', () => {
    const r = safetyCheck('https://mybank.bank/');
    assert.equal(r.safe, false);
    assert.match(r.reason, /Banking domain/);
  });

  it('blocks subdomain of .bank TLD', () => {
    const r = safetyCheck('https://www.secure.mybank.bank/login');
    assert.equal(r.safe, false);
    assert.match(r.reason, /Banking domain/);
  });
});

describe('Safety Check: Invalid URLs', () => {
  it('rejects garbage input', () => {
    const r = safetyCheck('not-a-url');
    assert.equal(r.safe, false);
    assert.match(r.reason, /Invalid URL/);
  });
});
