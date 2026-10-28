#!/usr/bin/env node
// Check a built code page at the recorder's viewport (432x768 CSS px, as demo_rec.mjs uses): no sideways
// scroll, every line has its #L<n> anchor, mark() highlights. Optional screenshot.
//
//   node verify_viewer.mjs <viewer.html> [screenshot.png] [--line N] [--project <P>]
//
// Playwright comes from --project, else $DEMO_REC_PROJECT, else the current directory, and uses its own Chromium:
// run `npx playwright install chromium` there once (`npm i -D playwright` does not download it). Exit 1 on a problem.
import { createRequire } from 'node:module';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const argv = process.argv.slice(2);
const opt = (k) => { const i = argv.indexOf(k); return i >= 0 ? argv.splice(i, 2)[1] : undefined; };
const line = Number(opt('--line') ?? 1);
const project = opt('--project') ?? process.env.DEMO_REC_PROJECT ?? process.cwd();
const [page, shot] = argv;
if (!page) { console.error('usage: node verify_viewer.mjs <viewer.html> [screenshot.png] [--line N] [--project <P>]'); process.exit(2); }
let chromium;
try {
  ({ chromium } = createRequire(join(resolve(project), 'package.json'))('playwright'));
} catch {
  console.error(`playwright not found from ${resolve(project)}: pass --project <P> or set DEMO_REC_PROJECT`);
  process.exit(2);
}

const W = 432;
let b;
try {
  b = await chromium.launch();
} catch (e) {
  console.error(`could not launch Playwright's Chromium: run \`npx playwright install chromium\` in ${resolve(project)}\n${String(e.message).split('\n')[0]}`);
  process.exit(2);
}
try {
  const pg = await b.newPage({ viewport: { width: W, height: 768 }, deviceScaleFactor: 2.5 });
  const errs = [];
  pg.on('pageerror', (e) => errs.push(String(e)));
  pg.on('requestfailed', (r) => errs.push(`request failed: ${r.url()}`));
  await pg.goto(pathToFileURL(resolve(page)).href);
  await pg.evaluate((n) => { window.scrollToLine(Math.max(1, n - 8)); window.mark(n, n); }, line);
  await pg.waitForTimeout(400);
  const r = await pg.evaluate(() => {
    const c = document.getElementById('code');
    const tx = [...document.querySelectorAll('.tx')];
    return {
      scrollWidth: c.scrollWidth, clientWidth: c.clientWidth, docScrollW: document.documentElement.scrollWidth,
      maxRight: Math.max(...tx.map((e) => e.getBoundingClientRect().right)),
      lines: tx.length, ids: document.querySelectorAll('.ln[id^=L]').length, marked: document.querySelectorAll('.mk').length,
    };
  });
  console.log(JSON.stringify(r), errs.length ? errs : '');
  if (shot) await pg.screenshot({ path: shot });
  const ok = r.scrollWidth <= r.clientWidth && r.docScrollW <= W && r.maxRight <= W - 8 && r.ids === r.lines && r.marked === 1 && !errs.length;
  if (!ok) console.error('FAIL: sideways overflow, missing anchors, mark() not applied, or page errors (see above)');
  process.exitCode = ok ? 0 : 1;
} finally {
  await b.close();
}
