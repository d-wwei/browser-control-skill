/**
 * Tests for the browser-control DOM-to-Markdown converter.
 *
 * Extracted from: skills/browser-control/SKILL.md ("Read Page as Structured Markdown")
 *
 * Requires: npm install --save-dev jsdom
 * Run:      node --test tests/test_dom_to_markdown.mjs
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';

// ---------------------------------------------------------------------------
// Extracted DOM-to-Markdown converter, adapted to run in jsdom.
//
// The original is an IIFE injected into a browser page.  Here we wrap it as a
// function that receives a jsdom `document` and an optional `maxLen`.
// ---------------------------------------------------------------------------

function domToMarkdown(document, maxLen = 15000) {
  const R = ['script','style','noscript','svg','canvas','template','iframe','object','embed'];
  const S = ['nav','footer','header','aside'];
  const out = [];
  let cc = 0;
  let tr = false;

  function add(l) {
    if (tr) return;
    if (cc + l.length + 1 > maxLen) {
      const r = maxLen - cc;
      if (r > 20) out.push(l.slice(0, r - 12) + '...[truncated]');
      tr = true;
      return;
    }
    out.push(l);
    cc += l.length + 1;
  }

  function vis(e) {
    if (!(e instanceof document.defaultView.HTMLElement)) return true;
    if (e.hidden || e.getAttribute('aria-hidden') === 'true') return false;
    const s = e.style;
    return s.display !== 'none' && s.visibility !== 'hidden';
  }

  function res(h) {
    try { return new URL(h, document.baseURI).href; }
    catch (_e) { return h; }
  }

  function inl(el) {
    let r = '';
    for (let i = 0; i < el.childNodes.length; i++) {
      const c = el.childNodes[i];
      if (c.nodeType === 3) {
        r += c.textContent.replace(/\s+/g, ' ');
      } else if (c.nodeType === 1) {
        const t = c.tagName.toLowerCase();
        const tx = inl(c);
        if (t === 'strong' || t === 'b') r += '**' + tx.trim() + '**';
        else if (t === 'em' || t === 'i') r += '*' + tx.trim() + '*';
        else if (t === 'code') r += '`' + tx.trim() + '`';
        else if (t === 'a') {
          const hr = c.getAttribute('href') || '';
          if (hr && !hr.startsWith('#') && !hr.startsWith('javascript:'))
            r += '[' + tx.trim() + '](' + res(hr) + ')';
          else r += tx;
        } else if (t === 'img') {
          const sr = c.getAttribute('src') || '';
          const al = c.getAttribute('alt') || '';
          if (sr) r += '![' + al + '](' + res(sr) + ')';
        } else if (t === 'br') {
          r += '\n';
        } else {
          r += tx;
        }
      }
    }
    return r;
  }

  function li(el, ord, ind) {
    let idx = 1;
    for (let i = 0; i < el.children.length; i++) {
      if (tr) return;
      const ch = el.children[i];
      if (ch.tagName.toLowerCase() === 'li') {
        const pf = '  '.repeat(ind) + (ord ? idx + '. ' : '- ');
        const pts = [];
        for (let j = 0; j < ch.childNodes.length; j++) {
          const n = ch.childNodes[j];
          if (n.nodeType === 3) {
            const t = n.textContent.replace(/\s+/g, ' ').trim();
            if (t) pts.push(t);
          } else if (n.nodeType === 1) {
            const nt = n.tagName.toLowerCase();
            if (nt !== 'ul' && nt !== 'ol') {
              const t = (n.textContent || '').replace(/\s+/g, ' ').trim();
              if (t) pts.push(t);
            }
          }
        }
        if (pts.length) add(pf + pts.join(' '));
        const nl = ch.querySelector(':scope>ul,:scope>ol');
        if (nl) li(nl, nl.tagName.toLowerCase() === 'ol', ind + 1);
        idx++;
      }
    }
  }

  function tbl(el) {
    const rows = [];
    const th = el.querySelector('thead');
    if (th) {
      th.querySelectorAll('tr').forEach(function(trEl) {
        const c = [];
        trEl.querySelectorAll('th,td').forEach(function(d) {
          c.push((d.textContent || '').replace(/\s+/g, ' ').trim());
        });
        if (c.length) rows.push(c);
      });
    }
    const bd = th ? el.querySelector('tbody') || el : el;
    bd.querySelectorAll('tr').forEach(function(trEl) {
      if (th && trEl.closest('thead')) return;
      const c = [];
      trEl.querySelectorAll('th,td').forEach(function(d) {
        c.push((d.textContent || '').replace(/\s+/g, ' ').trim());
      });
      if (c.length) rows.push(c);
    });
    if (!rows.length) return;
    const mc = Math.max.apply(null, rows.map(function(r) { return r.length; }));
    rows.forEach(function(r) { while (r.length < mc) r.push(''); });
    for (let i = 0; i < rows.length; i++) {
      add('| ' + rows[i].join(' | ') + ' |');
      if (i === 0) add('| ' + rows[i].map(function() { return '---'; }).join(' | ') + ' |');
      if (tr) return;
    }
  }

  function walk(node, d, sel) {
    if (tr) return;
    if (node.nodeType === 3) {
      const t = node.textContent.replace(/\s+/g, ' ').trim();
      if (t) add(t);
      return;
    }
    if (node.nodeType !== 1) return;
    const el = node;
    const tag = el.tagName.toLowerCase();
    if (R.indexOf(tag) !== -1) return;
    if (!vis(el)) return;
    if (!sel && S.indexOf(tag) !== -1 && d < 3) return;
    const m = tag.match(/^h([1-6])$/);
    if (m) {
      const tx = (el.textContent || '').replace(/\s+/g, ' ').trim();
      if (tx) { add(''); add('#'.repeat(parseInt(m[1])) + ' ' + tx); add(''); }
      return;
    }
    if (tag === 'p') {
      const tx = inl(el).trim();
      if (tx) { add(''); add(tx); }
      return;
    }
    if (tag === 'a') {
      const hr = el.getAttribute('href') || '';
      const tx = (el.textContent || '').replace(/\s+/g, ' ').trim();
      if (tx && hr && !hr.startsWith('#') && !hr.startsWith('javascript:'))
        add('[' + tx + '](' + res(hr) + ')');
      else if (tx) add(tx);
      return;
    }
    if (tag === 'img') {
      const sr = el.getAttribute('src') || '';
      const al = el.getAttribute('alt') || '';
      if (sr) add('![' + al + '](' + res(sr) + ')');
      return;
    }
    if (tag === 'hr') { add(''); add('---'); add(''); return; }
    if (tag === 'br') { add(''); return; }
    if (tag === 'ul' || tag === 'ol') { add(''); li(el, tag === 'ol', 0); add(''); return; }
    if (tag === 'table') { add(''); tbl(el); add(''); return; }
    if (tag === 'pre') {
      const ce = el.querySelector('code');
      const lang = ce && ce.className ? ce.className.match(/language-(\w+)/) : null;
      add('');
      add('```' + (lang ? lang[1] : ''));
      (el.textContent || '').trimEnd().split('\n').forEach(function(l) { add(l); });
      add('```');
      add('');
      return;
    }
    if (tag === 'blockquote') {
      const tx = (el.textContent || '').replace(/\s+/g, ' ').trim();
      if (tx) { add(''); tx.split('\n').forEach(function(l) { add('> ' + l.trim()); }); add(''); }
      return;
    }
    for (let i = 0; i < el.childNodes.length; i++) {
      walk(el.childNodes[i], d + 1, sel);
      if (tr) return;
    }
  }

  const root = document.querySelector('main')
    || document.querySelector('article')
    || document.querySelector('[role=main]')
    || document.body;
  if (!root) return '[Empty page]';
  walk(root, 0, false);
  return out.join('\n').replace(/\n{3,}/g, '\n\n').trim();
}

// ---------------------------------------------------------------------------
// Helper: create a jsdom document from an HTML body string.
// Wraps content in <body> within a <main> so the walker finds it.
// ---------------------------------------------------------------------------

function makeDoc(bodyHtml) {
  const dom = new JSDOM(`<!DOCTYPE html><html><body><main>${bodyHtml}</main></body></html>`, {
    url: 'https://example.com/',
  });
  return dom.window.document;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('DOM-to-Markdown: Heading conversion', () => {
  it('converts h1 to # prefix', () => {
    const doc = makeDoc('<h1>Title</h1>');
    const md = domToMarkdown(doc);
    assert.ok(md.includes('# Title'));
  });

  it('converts h2 to ## prefix', () => {
    const doc = makeDoc('<h2>Subtitle</h2>');
    const md = domToMarkdown(doc);
    assert.ok(md.includes('## Subtitle'));
  });

  it('converts h3 to ### prefix', () => {
    const doc = makeDoc('<h3>Section</h3>');
    const md = domToMarkdown(doc);
    assert.ok(md.includes('### Section'));
  });

  it('converts h4-h6', () => {
    const doc = makeDoc('<h4>H4</h4><h5>H5</h5><h6>H6</h6>');
    const md = domToMarkdown(doc);
    assert.ok(md.includes('#### H4'));
    assert.ok(md.includes('##### H5'));
    assert.ok(md.includes('###### H6'));
  });
});

describe('DOM-to-Markdown: Paragraph extraction', () => {
  it('extracts paragraph text', () => {
    const doc = makeDoc('<p>Hello World</p>');
    const md = domToMarkdown(doc);
    assert.ok(md.includes('Hello World'));
  });

  it('preserves bold within paragraphs', () => {
    const doc = makeDoc('<p>This is <strong>bold</strong> text</p>');
    const md = domToMarkdown(doc);
    assert.ok(md.includes('**bold**'));
  });

  it('preserves italic within paragraphs', () => {
    const doc = makeDoc('<p>This is <em>italic</em> text</p>');
    const md = domToMarkdown(doc);
    assert.ok(md.includes('*italic*'));
  });

  it('preserves inline code within paragraphs', () => {
    const doc = makeDoc('<p>Use <code>console.log</code> here</p>');
    const md = domToMarkdown(doc);
    assert.ok(md.includes('`console.log`'));
  });
});

describe('DOM-to-Markdown: Link conversion', () => {
  it('converts <a> with href to markdown link', () => {
    const doc = makeDoc('<p>Visit <a href="https://github.com">GitHub</a> now</p>');
    const md = domToMarkdown(doc);
    assert.ok(md.includes('[GitHub](https://github.com/)'));
  });

  it('skips anchor-only links (href="#...")', () => {
    const doc = makeDoc('<p>See <a href="#section">section</a></p>');
    const md = domToMarkdown(doc);
    // Should not produce [section](#section) — just plain text
    assert.ok(!md.includes('](#'));
    assert.ok(md.includes('section'));
  });

  it('skips javascript: links', () => {
    const doc = makeDoc('<p><a href="javascript:void(0)">Click</a></p>');
    const md = domToMarkdown(doc);
    assert.ok(!md.includes('javascript:'));
    assert.ok(md.includes('Click'));
  });

  it('resolves relative URLs against baseURI', () => {
    const doc = makeDoc('<p><a href="/docs/api">API Docs</a></p>');
    const md = domToMarkdown(doc);
    assert.ok(md.includes('[API Docs](https://example.com/docs/api)'));
  });
});

describe('DOM-to-Markdown: Table conversion', () => {
  it('converts simple table to markdown table', () => {
    const doc = makeDoc(`
      <table>
        <thead><tr><th>Name</th><th>Value</th></tr></thead>
        <tbody>
          <tr><td>alpha</td><td>1</td></tr>
          <tr><td>beta</td><td>2</td></tr>
        </tbody>
      </table>
    `);
    const md = domToMarkdown(doc);
    assert.ok(md.includes('| Name | Value |'));
    assert.ok(md.includes('| --- | --- |'));
    assert.ok(md.includes('| alpha | 1 |'));
    assert.ok(md.includes('| beta | 2 |'));
  });

  it('handles table without thead', () => {
    const doc = makeDoc(`
      <table>
        <tr><td>A</td><td>B</td></tr>
        <tr><td>C</td><td>D</td></tr>
      </table>
    `);
    const md = domToMarkdown(doc);
    assert.ok(md.includes('| A | B |'));
    assert.ok(md.includes('| C | D |'));
  });
});

describe('DOM-to-Markdown: Code block conversion', () => {
  it('converts pre/code to fenced code block', () => {
    const doc = makeDoc('<pre><code>const x = 1;\nconsole.log(x);</code></pre>');
    const md = domToMarkdown(doc);
    assert.ok(md.includes('```'));
    assert.ok(md.includes('const x = 1;'));
    assert.ok(md.includes('console.log(x);'));
  });

  it('detects language class on code element', () => {
    const doc = makeDoc('<pre><code class="language-javascript">const y = 2;</code></pre>');
    const md = domToMarkdown(doc);
    assert.ok(md.includes('```javascript'));
  });

  it('outputs plain ``` when no language class', () => {
    const doc = makeDoc('<pre><code>plain code</code></pre>');
    const md = domToMarkdown(doc);
    // Should have ``` without a language tag right after
    const lines = md.split('\n');
    const fenceIdx = lines.findIndex(l => l.startsWith('```'));
    assert.ok(fenceIdx !== -1);
    assert.equal(lines[fenceIdx], '```');
  });
});

describe('DOM-to-Markdown: List conversion', () => {
  it('converts unordered list', () => {
    const doc = makeDoc('<ul><li>Apple</li><li>Banana</li><li>Cherry</li></ul>');
    const md = domToMarkdown(doc);
    assert.ok(md.includes('- Apple'));
    assert.ok(md.includes('- Banana'));
    assert.ok(md.includes('- Cherry'));
  });

  it('converts ordered list', () => {
    const doc = makeDoc('<ol><li>First</li><li>Second</li><li>Third</li></ol>');
    const md = domToMarkdown(doc);
    assert.ok(md.includes('1. First'));
    assert.ok(md.includes('2. Second'));
    assert.ok(md.includes('3. Third'));
  });

  it('handles nested lists', () => {
    const doc = makeDoc(`
      <ul>
        <li>Fruits
          <ul>
            <li>Apple</li>
            <li>Banana</li>
          </ul>
        </li>
        <li>Vegetables</li>
      </ul>
    `);
    const md = domToMarkdown(doc);
    assert.ok(md.includes('- Fruits'));
    assert.ok(md.includes('  - Apple'));
    assert.ok(md.includes('  - Banana'));
    assert.ok(md.includes('- Vegetables'));
  });
});

describe('DOM-to-Markdown: maxLen truncation', () => {
  it('truncates output when maxLen is exceeded', () => {
    // Build a page with lots of paragraphs
    const paras = Array.from({ length: 100 }, (_, i) =>
      `<p>Paragraph number ${i} with some filler text to make it long enough to trigger truncation.</p>`
    ).join('');
    const doc = makeDoc(paras);
    const md = domToMarkdown(doc, 200);
    assert.ok(md.length <= 220); // some slack for final line
    assert.ok(md.includes('[truncated]'));
  });

  it('does not truncate small content', () => {
    const doc = makeDoc('<p>Short text</p>');
    const md = domToMarkdown(doc, 15000);
    assert.ok(!md.includes('[truncated]'));
    assert.ok(md.includes('Short text'));
  });
});

describe('DOM-to-Markdown: Hidden element filtering', () => {
  it('skips elements with hidden attribute', () => {
    const doc = makeDoc('<p>Visible</p><div hidden><p>Hidden</p></div>');
    const md = domToMarkdown(doc);
    assert.ok(md.includes('Visible'));
    assert.ok(!md.includes('Hidden'));
  });

  it('skips elements with aria-hidden="true"', () => {
    const doc = makeDoc('<p>Shown</p><div aria-hidden="true"><p>Screen-reader hidden</p></div>');
    const md = domToMarkdown(doc);
    assert.ok(md.includes('Shown'));
    assert.ok(!md.includes('Screen-reader hidden'));
  });

  it('skips elements with style display:none', () => {
    const doc = makeDoc('<p>Here</p><div style="display:none"><p>Gone</p></div>');
    const md = domToMarkdown(doc);
    assert.ok(md.includes('Here'));
    assert.ok(!md.includes('Gone'));
  });

  it('skips elements with style visibility:hidden', () => {
    const doc = makeDoc('<p>Visible</p><div style="visibility:hidden"><p>Invisible</p></div>');
    const md = domToMarkdown(doc);
    assert.ok(md.includes('Visible'));
    assert.ok(!md.includes('Invisible'));
  });

  it('skips script tags', () => {
    const doc = makeDoc('<p>Content</p><script>var x = 1;</script>');
    const md = domToMarkdown(doc);
    assert.ok(md.includes('Content'));
    assert.ok(!md.includes('var x = 1'));
  });

  it('skips style tags', () => {
    const doc = makeDoc('<p>Content</p><style>.foo { color: red; }</style>');
    const md = domToMarkdown(doc);
    assert.ok(md.includes('Content'));
    assert.ok(!md.includes('.foo'));
  });
});
