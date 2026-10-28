// Browser smoke test (no human needed): DEMO_REC_PROJECT=<P> node smoke.mjs
// Playwright Chromium with fake camera/mic against a temp project. Playwright and ffprobe are
// loaded from a video project <P> whose node_modules has playwright and Remotion (env DEMO_REC_PROJECT,
// or YVC_TEST_PROJECT), because the toolkit has no node_modules; Playwright's Chromium must be installed there
// (`npx playwright install chromium`). Without either variable it prints SKIP and exits 0.
import { createRequire } from 'node:module';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, readdirSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import assert from 'node:assert/strict';
import { startServer } from './server.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const P = process.env.DEMO_REC_PROJECT || process.env.YVC_TEST_PROJECT;
if (!P) {
  console.log('SKIP teleprompter smoke: set DEMO_REC_PROJECT to a video project with node_modules (playwright + Remotion)');
  process.exit(0);
}
const VPY = process.env.VPY ?? `${process.env.HOME}/.cache/yt-video-creator/venv/bin/python`;
const { chromium } = createRequire(join(P, 'package.json'))('playwright');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// At 180 wpm: lines 0 and 1 last about 2.5 s each, line 2 about 5 s.
const REELS = { wpm: 180, reels: [{ id: 'r1', title: 'Smoke', lines: [
  { text: 'Um dois três quatro cinco.' },
  { text: 'Seis sete oito nove dez.' },
  { text: 'Esta é a terceira linha, que é bem mais longa para dar tempo aos toques do teste.' },
] }] };

function probe(webm) {
  const code = `import sys,json,subprocess
sys.path.insert(0, ${JSON.stringify(join(HERE, '..', 'scripts'))})
import _ff
ff, fp, env = _ff.tools(${JSON.stringify(P)})
r = subprocess.run([fp,'-v','error','-show_entries','stream=codec_type,codec_name,width,height','-of','json',sys.argv[1]],capture_output=True,text=True,env=env)
print(json.dumps({'rc': r.returncode, 'err': r.stderr, 'streams': json.loads(r.stdout or '{}').get('streams', [])}))`;
  const out = JSON.parse(execFileSync(VPY, ['-I', '-c', code, webm], { encoding: 'utf8' }));
  assert.equal(out.rc, 0, `ffprobe failed: ${out.err}`);
  return out.streams;
}

async function scenario(name, fn) {
  const dir = mkdtempSync(join(tmpdir(), 'tp-smoke-'));
  mkdirSync(join(dir, 'scripts'));
  writeFileSync(join(dir, 'scripts', 'reels.json'), JSON.stringify(REELS));
  const srv = await startServer({ project: dir, port: 0 });
  const browser = await chromium.launch({ args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'] });
  try {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 }, permissions: ['camera', 'microphone'] });
    const page = await ctx.newPage();
    page.on('pageerror', (e) => { throw e; });
    const ctl = {
      page, dir,
      url: () => `http://127.0.0.1:${srv.address().port}`,
      raw: () => join(dir, 'recordings', 'raw'),
      files: (ext) => { try { return readdirSync(join(dir, 'recordings', 'raw')).filter((f) => f.endsWith(ext)); } catch { return []; } },
      log() { const f = this.files('.log.json')[0]; return f ? JSON.parse(readFileSync(join(this.raw(), f), 'utf8')) : { events: [] }; },
      async waitFor(pred, what, ms = 20000) {
        const t0 = Date.now();
        for (;;) {
          const hit = pred(this.log().events);
          if (hit) return hit;
          if (Date.now() - t0 > ms) throw new Error(`timeout waiting for ${what}: ${JSON.stringify(this.log().events)}`);
          await sleep(40);
        }
      },
      async start() {
        await page.goto(`http://127.0.0.1:${srv.address().port}`);
        await page.waitForFunction(() => !document.getElementById('rec').disabled, null, { polling: 100 });
        await page.evaluate(() => { const w = document.getElementById('wpm'); w.value = 180; w.dispatchEvent(new Event('input')); });
        await page.click('#rec');
        await page.waitForFunction(() => document.body.classList.contains('recording'), null, { polling: 100 }); // default polling uses rAF, which scenario 2 stubs out
      },
      async done() { await page.waitForFunction(() => !document.body.classList.contains('recording'), null, { timeout: 20000, polling: 100 }); },
    };
    await fn(ctl);
    console.log(`PASS ${name}`);
  } finally {
    await browser.close();
    srv.close();
    rmSync(dir, { recursive: true, force: true });
  }
}

const shape = (events) => events.map((e) => (e.type === 'tap' ? `tap ${e.line}>${e.to}` : e.type === 'line' ? `line ${e.line}` : e.type));

// 1. Auto-advance over lines, tap early (back one line), tap late (restart), stop with Stop.
await scenario('auto-advance, tap back, tap restart', async (c) => {
  await c.start();
  await c.waitFor((ev) => ev.some((e) => e.type === 'line' && e.line === 2), 'auto-advance to line 2');
  await sleep(300);
  await c.page.mouse.click(640, 400); // 0.3 s into line 2 -> back to line 1
  await c.waitFor((ev) => ev.filter((e) => e.type === 'line' && e.line === 1).length === 2, 'line 1 restarted after tap back');
  await sleep(1400);
  await c.page.mouse.click(640, 400); // 1.4 s into line 1 -> restart same line
  await c.waitFor((ev) => ev.filter((e) => e.type === 'line' && e.line === 1).length === 3, 'line 1 restarted after late tap');
  await sleep(300);
  await c.page.click('#stop');
  await c.done();
  const log = c.log();
  console.log(JSON.stringify(shape(log.events)));
  assert.deepEqual(shape(log.events), ['line 0', 'line 1', 'line 2', 'tap 2>1', 'line 1', 'tap 1>1', 'line 1', 'stop']);
  const ts = log.events.map((e) => e.t);
  assert.deepEqual(ts, [...ts].sort((a, b) => a - b), 'events in time order');
  assert.equal(log.events[0].t, 0);
  assert.equal(log.wpm, 180);
  const [webm] = c.files('.webm');
  const kinds = probe(join(c.raw(), webm)).map((s) => `${s.codec_type}:${s.codec_name}`).sort();
  assert.deepEqual(kinds, ['audio:opus', 'video:vp9']);
  assert.match(await c.page.textContent('#msg'), /^Saved: recordings\/raw\/r1-/);
});

// 2. rAF never fires (hidden tab): Esc must still stop and the log must still progress.
await scenario('Esc stops with requestAnimationFrame stalled', async (c) => {
  await c.page.addInitScript(() => { window.requestAnimationFrame = () => 0; });
  await c.start();
  await c.waitFor((ev) => ev.some((e) => e.type === 'line' && e.line === 1), 'timer fallback keeps advancing lines');
  await c.page.keyboard.press('Escape');
  await c.done();
  const log = c.log();
  assert.equal(log.events.at(-1).type, 'stop');
  assert.equal(log.events.filter((e) => e.type === 'stop').length, 1);
  assert.ok(probe(join(c.raw(), c.files('.webm')[0])).length === 2);
});

// 3. Chunk uploads fail: a persistent warning, and no "Saved".
await scenario('failed chunk upload raises a persistent warning', async (c) => {
  await c.page.route('**/api/chunk*', (r) => r.abort());
  await c.start();
  await sleep(2500);
  await c.page.click('#stop');
  await c.done();
  assert.equal(await c.page.isVisible('#alert'), true);
  assert.match(await c.page.textContent('#alert'), /Saving failed — don't close this page/);
  assert.doesNotMatch(await c.page.textContent('#msg'), /Saved/);
});

// 4. A saved speed outside the slider's range/step: the label shows what the slider holds (and records with).
await scenario('wpm label shows the clamped/snapped slider value', async (c) => {
  mkdirSync(join(c.dir, 'recordings'), { recursive: true });
  for (const [saved, shown] of [[300, '260'], [143, '145'], [90, '110']]) {
    writeFileSync(join(c.dir, 'recordings', 'settings.json'), JSON.stringify({ wpm: saved, cameraId: null, micId: null }));
    await c.page.goto(c.url());
    await c.page.waitForFunction(() => !document.getElementById('rec').disabled, null, { polling: 100 });
    assert.equal(await c.page.textContent('#wpmv'), shown, `saved ${saved}`);
    assert.equal(await c.page.inputValue('#wpm'), shown);
  }
  for (const [sel, label] of [['#rec', 'Record'], ['#stop', 'Stop']]) assert.equal(await c.page.textContent(sel), label);
});
