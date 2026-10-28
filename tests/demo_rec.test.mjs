// node --test tests/demo_rec.test.mjs
// Records the tall.html fixture headless into a temp project (never the owner's profile or windows).
// Playwright and ffmpeg come from a video project given by env DEMO_REC_PROJECT (a dir whose node_modules has
// playwright and @remotion/compositor-*, plus `npx playwright install chromium` run there), through a node_modules
// symlink. Every test is skipped when it is unset.
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, symlinkSync, readFileSync, copyFileSync, lstatSync, existsSync, rmSync } from 'node:fs';
import { tmpdir, hostname } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { execFileSync, spawnSync } from 'node:child_process';

const HERE = dirname(fileURLToPath(import.meta.url));
const T = join(HERE, '..');
const P = process.env.DEMO_REC_PROJECT;
const SKIP = P ? false : 'set DEMO_REC_PROJECT to a video project with node_modules (playwright + Remotion) to run the recorder tests';
const VPY = process.env.VPY ?? `${process.env.HOME}/.cache/yt-video-creator/venv/bin/python`;
const FIXTURE = pathToFileURL(join(HERE, 'fixtures', 'tall.html')).href;
const SMOOTH = pathToFileURL(join(HERE, 'fixtures', 'smooth.html')).href;

const ffdir = P ? execFileSync('sh', ['-c', `ls -d "${P}"/node_modules/@remotion/compositor-*/ | head -1`], { encoding: 'utf8' }).trim() : '';
const ffenv = { ...process.env, DYLD_LIBRARY_PATH: ffdir, LD_LIBRARY_PATH: ffdir };
const probe = (f) => JSON.parse(execFileSync(`${ffdir}/ffprobe`, ['-v', 'error', '-select_streams', 'v:0',
  '-show_entries', 'stream=width,height,r_frame_rate,codec_name,pix_fmt:format=duration', '-of', 'json', f], { env: ffenv, encoding: 'utf8' }));

function tempProject() {
  const dir = mkdtempSync(join(tmpdir(), 'demo-rec-'));
  symlinkSync(join(P, 'node_modules'), join(dir, 'node_modules'));
  writeFileSync(join(dir, 'package.json'), '{"name":"demo-rec-test","private":true}');
  writeFileSync(join(dir, 'plan.json'), JSON.stringify({ fps: 30, clips: {} }));
  writeFileSync(join(dir, 'beats.mjs'), `export default {
    scroll: { url: ${JSON.stringify(FIXTURE)}, async run(page, h) { await h.pause(300); await h.scrollTo('#s10', 1500); await h.pause(300); } },
  };\n`);
  return dir;
}

function recordRaw(dir, profile, id, extra = [], { project = true, headless = true, env = {} } = {}) {
  return spawnSync('node', [join(T, 'scripts', 'demo_rec.mjs'), 'record', ...(project ? ['--project', dir] : []), '--beats', join(dir, 'beats.mjs'),
    '--id', id, '--profile', profile, '--channel', 'chromium', ...(headless ? ['--headless'] : []), ...extra], { encoding: 'utf8', timeout: 120000, env: { ...process.env, ...env } });
}
function record(dir, profile, id, extra = []) {
  const r = recordRaw(dir, profile, id, extra);
  assert.equal(r.status, 0, r.stderr);
  return r.stdout;
}
const withBeats = (dir, body) => writeFileSync(join(dir, 'beats.mjs'), `export default { t: { url: ${JSON.stringify(body.url)}, async run(page, h) { ${body.run} } } };\n`);

function extractFrame(mp4, at, png) {
  execFileSync(`${ffdir}/ffmpeg`, ['-v', 'error', '-y', '-ss', String(at), '-i', mp4, '-frames:v', '1', png], { env: ffenv });
}

test('record scroll beat: 1080x1920 CFR 30, ~3 s, picture changes, clip registered', { skip: SKIP }, () => {
  const dir = tempProject();
  const profile = join(dir, 'profile');
  try {
    const out = record(dir, profile, 'scroll', ['--seconds', '3']);
    const mp4 = join(dir, 'recordings', 'demos', 'scroll.mp4');
    assert.ok(existsSync(mp4), out);
    const info = probe(mp4);
    const s = info.streams[0];
    assert.equal(s.width, 1080);
    assert.equal(s.height, 1920);
    assert.equal(s.r_frame_rate, '30/1');
    assert.equal(s.codec_name, 'h264');
    assert.equal(s.pix_fmt, 'yuv420p');
    const dur = Number(info.format.duration);
    assert.ok(Math.abs(dur - 3.0) <= 0.3, `duration ${dur}`);

    const first = join(dir, 'first.png'), last = join(dir, 'last.png');
    extractFrame(mp4, 0, first);
    extractFrame(mp4, dur - 0.1, last);
    const diff = Number(execFileSync(VPY, ['-I', '-c',
      'import sys,numpy as np;from PIL import Image\n' +
      'a,b=[np.asarray(Image.open(p).convert("L"),dtype=float) for p in sys.argv[1:3]]\n' +
      'print(abs(a-b).mean())', first, last], { encoding: 'utf8' }));
    assert.ok(diff > 5, `first/last mean abs diff ${diff}`);
    if (process.env.DEMO_REC_LASTFRAME) copyFileSync(last, process.env.DEMO_REC_LASTFRAME);

    // Registered like import_take.py: symlink in source/ and a link clip without audio.
    const link = join(dir, 'source', 'demo-scroll.mp4');
    assert.ok(lstatSync(link).isSymbolicLink());
    const clip = JSON.parse(readFileSync(join(dir, 'plan.json'), 'utf8')).clips['demo-scroll'];
    assert.deepEqual({ ...clip, dur: undefined }, { file: 'demo-scroll.mp4', media: 'link', dur: undefined, audio: false });
    assert.ok(Math.abs(clip.dur - dur) < 0.1);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('static page still reaches --seconds by holding the last frame', { skip: SKIP }, () => {
  const dir = tempProject();
  writeFileSync(join(dir, 'beats.mjs'), `export default { still: { url: ${JSON.stringify(FIXTURE)}, async run(page, h) { await h.pause(200); } } };\n`);
  try {
    record(dir, join(dir, 'profile'), 'still', ['--seconds', '2']);
    const dur = Number(probe(join(dir, 'recordings', 'demos', 'still.mp4')).format.duration);
    assert.ok(Math.abs(dur - 2.0) <= 0.3, `duration ${dur}`);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('scrollTo ignores scroll-behavior: smooth, on the page and in an inner pane', { skip: SKIP }, () => {
  const dir = tempProject();
  withBeats(dir, { url: SMOOTH, run: `
    await h.scrollTo('#end', 600);
    const y = await page.evaluate(() => scrollY), max = await page.evaluate(() => document.scrollingElement.scrollHeight - innerHeight);
    if (Math.abs(y - max) > 1) throw new Error('page scroll ended at ' + y + ', expected ' + max);
    await h.scrollTo('#top', 600);
    if (await page.evaluate(() => scrollY) !== 0) throw new Error('did not return to top');
    await h.scrollTo('#p20', 600, '#pane');
    const r = await page.evaluate(() => [document.getElementById('pane').scrollTop, document.getElementById('p20').offsetTop - document.getElementById('pane').offsetTop - 2 /* border */ - 24]);
    if (Math.abs(r[0] - r[1]) > 1) throw new Error('pane scrollTop ' + r[0] + ', expected ' + r[1]);
    if (await page.evaluate(() => scrollY) !== 0) throw new Error('inner scroll moved the page');
  ` });
  try { record(dir, join(dir, 'profile'), 't', ['--seconds', '3']); } finally { rmSync(dir, { recursive: true, force: true }); }
});

test('type refuses password fields, types into normal ones', { skip: SKIP }, () => {
  for (const sel of ['#pw', '#cur']) {
    const dir = tempProject();
    withBeats(dir, { url: SMOOTH, run: `await h.type(${JSON.stringify(sel)}, 'hunter2');` });
    try {
      const r = recordRaw(dir, join(dir, 'profile'), 't');
      assert.notEqual(r.status, 0);
      assert.match(r.stderr, /refusing to type into a password field/);
      assert.ok(!existsSync(join(dir, 'recordings', 'demos', 't.mp4')));
    } finally { rmSync(dir, { recursive: true, force: true }); }
  }
  const dir = tempProject();
  withBeats(dir, { url: SMOOTH, run: `await h.type('#txt', 'ola', 30); if (await page.inputValue('#txt') !== 'ola') throw new Error('not typed');` });
  try { record(dir, join(dir, 'profile'), 't'); } finally { rmSync(dir, { recursive: true, force: true }); }
});

test('beat longer than --seconds warns and is cut', { skip: SKIP }, () => {
  const dir = tempProject();
  withBeats(dir, { url: FIXTURE, run: `await h.pause(2000);` });
  try {
    const out = record(dir, join(dir, 'profile'), 't', ['--seconds', '1']);
    assert.match(out, /WARN beat t overran --seconds \(cut at 1s\)/);
    const dur = Number(probe(join(dir, 'recordings', 'demos', 't.mp4')).format.duration);
    assert.ok(Math.abs(dur - 1.0) <= 0.3, `duration ${dur}`);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});

test('--project is optional: falls back to $DEMO_REC_PROJECT, else a clear error; login needs only --urls', { skip: SKIP }, () => {
  const dir = tempProject();
  withBeats(dir, { url: FIXTURE, run: `await h.pause(100);` });
  try {
    const r = recordRaw(dir, join(dir, 'profile'), 't', ['--seconds', '1'], { project: false, env: { DEMO_REC_PROJECT: dir } });
    assert.equal(r.status, 0, r.stderr);
    assert.ok(existsSync(join(dir, 'recordings', 'demos', 't.mp4')));
    const l = spawnSync('node', [join(T, 'scripts', 'demo_rec.mjs'), 'login'], { encoding: 'utf8' });
    assert.match(l.stderr, /missing --urls/); // not "missing --project"
    const env = { ...process.env }; delete env.DEMO_REC_PROJECT;
    const n = spawnSync('node', [join(T, 'scripts', 'demo_rec.mjs'), 'record', '--beats', join(dir, 'beats.mjs'), '--id', 't'], { encoding: 'utf8', cwd: tmpdir(), env });
    assert.notEqual(n.status, 0);
    assert.match(n.stderr, /pass --project <P>, set DEMO_REC_PROJECT/);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});

test('record fails fast when a live Chrome holds the profile (fake SingletonLock)', { skip: SKIP }, () => {
  const dir = tempProject();
  const profile = join(dir, 'profile');
  mkdirSync(profile);
  symlinkSync(`${hostname()}-${process.pid}`, join(profile, 'SingletonLock')); // this test process is alive
  withBeats(dir, { url: FIXTURE, run: `await h.pause(100);` });
  try {
    const t0 = Date.now();
    const r = recordRaw(dir, profile, 't');
    assert.notEqual(r.status, 0);
    assert.match(r.stderr, /quit the Chrome using the recording profile first \(⌘Q \/ Chrome → Quit/);
    assert.ok(Date.now() - t0 < 5000, 'must not hang');
  } finally { rmSync(dir, { recursive: true, force: true }); }
});
