// node --test tests/code_viewer.test.mjs : the code page builder (assets/code-viewer).
// highlight.js and Playwright come from env DEMO_REC_PROJECT (a video project with them in node_modules, and
// `npx playwright install chromium` run there);
// the tests that need them are skipped when it is unset.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { mkdtempSync, writeFileSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';
import { splitLines, buildViewer, loadHljs, parseArgs } from '../assets/code-viewer/build_viewer.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const CV = join(HERE, '..', 'assets', 'code-viewer');
const P = process.env.DEMO_REC_PROJECT;
const SKIP = P ? false : 'set DEMO_REC_PROJECT to a video project with highlight.js and playwright in node_modules';

const SRC = 'struct A {\n  let s = """\n  two\n  lines\n  """ // <b>\n}\n';

test('splitLines closes and reopens spans across line breaks', () => {
  const lines = splitLines('<span class="a">x\n<span class="b">y\nz</span></span>\nw');
  assert.deepEqual(lines, ['<span class="a">x</span>', '<span class="a"><span class="b">y</span></span>', '<span class="a"><span class="b">z</span></span>', 'w']);
});

test('parseArgs', () => {
  assert.deepEqual(parseArgs(['a.swift', 'o.html', '--lang', 'swift', '--title', 'T', '--no-wrap']),
    { _: ['a.swift', 'o.html'], lang: 'swift', title: 'T', wrap: false });
  assert.throws(() => parseArgs(['--lang']), /needs a value/);
  assert.throws(() => parseArgs(['--bogus']), /unknown option/);
});

test('missing highlight.js is a clear error', () => {
  const dir = mkdtempSync(join(tmpdir(), 'cv-nohljs-'));
  try { assert.throws(() => loadHljs(dir), /npm i -D highlight.js/); } finally { rmSync(dir, { recursive: true, force: true }); }
});

test('one anchored line per source line, spans balanced, title escaped, language from extension', { skip: SKIP }, () => {
  const hljs = loadHljs(P);
  const { page, lines, lang } = buildViewer({ src: SRC, title: 'A<1>.swift', file: 'A.swift', hljs });
  assert.equal(lines, 6);
  assert.equal(lang, 'swift');
  for (let n = 1; n <= 6; n++) assert.match(page, new RegExp(`id="L${n}"`));
  assert.doesNotMatch(page, /id="L7"/);
  for (const m of page.matchAll(/<div class="ln" id="L\d+">(.*?)<\/div>/g)) {
    assert.equal((m[1].match(/<span/g) ?? []).length, (m[1].match(/<\/span>/g) ?? []).length, m[1]);
  }
  assert.match(page, /<title>A&lt;1&gt;\.swift<\/title>/);
  assert.match(page, /&lt;b&gt;/); // source text is escaped
  assert.match(page, /<body class="wrap">/);
  assert.doesNotMatch(page, /\{\{|<script src=|<link /); // all placeholders filled, nothing loaded at runtime
  assert.throws(() => buildViewer({ src: SRC, title: 't', lang: 'nope', hljs }), /no language "nope"/);
});

test('CLI writes the page; mark/unmark/scrollToLine work at phone width', { skip: SKIP }, async () => {
  const dir = mkdtempSync(join(tmpdir(), 'cv-'));
  try {
    const src = join(dir, 'long.txt');
    writeFileSync(src, Array.from({ length: 150 }, (_, i) => `line ${i + 1} ` + 'x'.repeat(i === 40 ? 300 : 10)).join('\n') + '\n');
    const out = join(dir, 'v.html');
    const r = spawnSync('node', [join(CV, 'build_viewer.mjs'), src, out, '--lang', 'plaintext', '--title', 'Long', '--project', P], { encoding: 'utf8' });
    assert.equal(r.status, 0, r.stderr);
    assert.match(r.stdout, /150 lines \(plaintext\)/);
    assert.match(readFileSync(out, 'utf8'), /width: 3ch/); // number column fits 3 digits

    const v = spawnSync('node', [join(CV, 'verify_viewer.mjs'), out, '--line', '41', '--project', P], { encoding: 'utf8' });
    assert.equal(v.status, 0, v.stdout + v.stderr); // the 300-char line wraps instead of overflowing

    const { chromium } = createRequire(join(P, 'package.json'))('playwright');
    const b = await chromium.launch();
    try {
      const pg = await b.newPage({ viewport: { width: 432, height: 768 } });
      await pg.goto(pathToFileURL(out).href);
      await pg.evaluate(() => window.mark(10, 12));
      assert.deepEqual(await pg.evaluate(() => [...document.querySelectorAll('.mk')].map((e) => e.id)), ['L10', 'L11', 'L12']);
      await pg.evaluate(() => window.mark(5));
      assert.deepEqual(await pg.evaluate(() => [...document.querySelectorAll('.mk')].map((e) => e.id)), ['L5']);
      await pg.evaluate(() => window.unmark());
      assert.equal(await pg.evaluate(() => document.querySelectorAll('.mk').length), 0);
      await pg.evaluate(() => window.scrollToLine(100));
      const top = await pg.evaluate(() => document.getElementById('L100').getBoundingClientRect().top);
      assert.ok(top >= 40 && top <= 60, `L100 at ${top}px (below the sticky tab)`);
    } finally { await b.close(); }

    const nw = spawnSync('node', [join(CV, 'build_viewer.mjs'), src, out, '--lang', 'plaintext', '--no-wrap', '--project', P], { encoding: 'utf8' });
    assert.equal(nw.status, 0, nw.stderr);
    const v2 = spawnSync('node', [join(CV, 'verify_viewer.mjs'), out, '--project', P], { encoding: 'utf8' });
    assert.equal(v2.status, 1, 'unwrapped 300-char line overflows the phone width');
  } finally { rmSync(dir, { recursive: true, force: true }); }
});
