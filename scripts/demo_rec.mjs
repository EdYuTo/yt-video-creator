#!/usr/bin/env node
// Web demo recorder: 9:16 screen captures of a site, through a Playwright browser and CDP screencast.
//
//   node demo_rec.mjs login  --urls <url,url,...> [--profile <dir>]
//       Starts your real Google Chrome (no Playwright) on the recording profile, one tab per URL, and returns.
//       You sign in BY HAND, then QUIT that Chrome (⌘Q / Chrome → Quit; on macOS closing its window leaves it running
//       and holding the profile). Nothing here ever types credentials.
//   node demo_rec.mjs record --id <beatId> --beats <beats.mjs> [--project <P>] [--seconds N] [--profile <dir>] [--headless] [--channel chrome|chromium]
//       Runs one beat in real Chrome on the same profile (so the sites are logged in) and writes
//       <P>/recordings/demos/<beatId>.mp4 (1080x1920, CFR 30), then registers the clip demo-<beatId> in <P>/plan.json
//       (symlink in <P>/source/, media "link", audio false). Fails fast if that Chrome is still open on the profile.
//       --channel chromium uses Playwright's bundled Chromium instead (tests; never for logged-in sites); it needs
//       `npx playwright install chromium` in <P> once (`npm i -D playwright` does not download it).
//
// Beats file: export default { "<id>": { url, async run(page, h) } } with h = helpers(page) from demo_helpers.mjs.
// The project <P> supplies Playwright (the toolkit has no node_modules) and Remotion's bundled ffmpeg:
// --project, else $DEMO_REC_PROJECT, else the current directory if it has node_modules/playwright.
// `login` starts Chrome with `open -na` on macOS; on other systems it prints the command to run by hand.
import { createRequire } from 'node:module';
import { mkdirSync, mkdtempSync, writeFileSync, readFileSync, readdirSync, rmSync, existsSync, lstatSync, unlinkSync, symlinkSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';
import { helpers } from './demo_helpers.mjs';
import { profileDir, projectDir, launchOptions, chromeLoginCommand, assertProfileFree, launchError } from './demo_launch.mjs';

const W = 432, H = 768, SCALE = 2.5, FPS = 30;

function parseArgs(argv) {
  const [cmd, ...rest] = argv;
  const o = { _: cmd };
  for (let i = 0; i < rest.length; i++) {
    if (!rest[i].startsWith('--')) throw new Error(`unexpected argument ${rest[i]}`);
    const k = rest[i].slice(2);
    o[k] = rest[i + 1] === undefined || rest[i + 1].startsWith('--') ? true : rest[++i];
  }
  return o;
}

function need(o, k) { if (!o[k] || o[k] === true) throw new Error(`missing --${k}`); return o[k]; }

function playwright(project) {
  return createRequire(join(resolve(project), 'package.json'))('playwright');
}

function ffTools(project) {
  const base = join(resolve(project), 'node_modules', '@remotion');
  const sub = existsSync(base) ? readdirSync(base).find((d) => d.startsWith('compositor-')) : null;
  if (!sub) throw new Error(`no Remotion compositor in ${base}; run npm install in the project`);
  const dir = join(base, sub);
  return { ff: join(dir, 'ffmpeg'), fp: join(dir, 'ffprobe'), env: { ...process.env, DYLD_LIBRARY_PATH: dir, LD_LIBRARY_PATH: dir } };
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function login(o) {
  const urls = need(o, 'urls').split(',').filter(Boolean);
  const profile = profileDir(o);
  mkdirSync(profile, { recursive: true });
  const { cmd, args, manual } = chromeLoginCommand(profile, urls);
  if (manual) {
    const q = (a) => (/^[\w@%+=:,./-]+$/.test(a) ? a : `'${a.replace(/'/g, `'\\''`)}'`);
    console.log(`Start Google Chrome yourself with the recording profile (use your Chrome binary's name/path):\n  ${[cmd, ...args].map(q).join(' ')}\n` +
      'Sign in by hand, then QUIT that Chrome (close all its windows / Chrome menu → Exit) before recording: Chrome locks the profile while it runs.');
    return;
  }
  const r = spawnSync(cmd, args, { encoding: 'utf8' });
  if (r.status !== 0) throw new Error(`could not start Google Chrome: ${r.stderr}`);
  console.log(`Chrome started on ${profile}.\nSign in by hand (never through automation), then QUIT that Chrome (⌘Q / Chrome → Quit) before recording: Chrome locks the profile while it runs, and on macOS closing its window does not quit it.`);
}

// Frames arrive only when the page changes, so every frame is held until the next timestamp.
function assemble({ project, frames, endTs, seconds, out }) {
  const { ff, env } = ffTools(project);
  const work = mkdtempSync(join(tmpdir(), 'demo-rec-asm-'));
  try {
    const t0 = frames[0].ts;
    const total = seconds ?? Math.max(endTs - t0, 0.1);
    const kept = frames.filter((f) => f.ts - t0 < total); // frames past the requested length are dropped (ffmpeg -t truncates this list badly)
    const lines = [];
    kept.forEach((f, i) => {
      const next = i + 1 < kept.length ? kept[i + 1].ts : t0 + total;
      lines.push(`file '${f.file}'`, `duration ${Math.max(next - f.ts, 0.001).toFixed(6)}`);
    });
    lines.push(`file '${kept.at(-1).file}'`); // concat ignores the last duration unless the last file is listed again
    const list = join(work, 'frames.txt');
    writeFileSync(list, lines.join('\n') + '\n');
    mkdirSync(join(out, '..'), { recursive: true });
    const r = spawnSync(ff, ['-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', list,
      '-vf', `scale=${W * SCALE}:${H * SCALE}:flags=lanczos:in_range=pc:out_range=tv,format=yuv420p`, '-r', String(FPS), '-fps_mode', 'cfr',
      '-c:v', 'libx264', '-crf', '16', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], { env, encoding: 'utf8' });
    if (r.status !== 0) throw new Error(`ffmpeg failed:\n${r.stderr.slice(-2000)}`);
  } finally {
    rmSync(work, { recursive: true, force: true });
  }
}

function duration(project, file) {
  const { fp, env } = ffTools(project);
  const r = spawnSync(fp, ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', file], { env, encoding: 'utf8' });
  return Number(r.stdout);
}

// Same registration as import_take.py: symlink in source/, "link" clip in plan.json (here without audio).
// import_take.py has no reusable function (registration is inline in main), so this is a minimal Node copy.
function register(project, clipId, mp4, dur) {
  mkdirSync(join(project, 'source'), { recursive: true });
  const link = join(project, 'source', `${clipId}.mp4`);
  if (existsSync(link) || lstatSync(link, { throwIfNoEntry: false })) unlinkSync(link);
  symlinkSync(mp4, link);
  const planPath = join(project, 'plan.json');
  const plan = JSON.parse(readFileSync(planPath, 'utf8'));
  (plan.clips ??= {})[clipId] = { file: `${clipId}.mp4`, media: 'link', dur: Math.round(dur * 100) / 100, audio: false };
  writeFileSync(planPath, JSON.stringify(plan, null, 1));
}

async function record(o) {
  const project = projectDir(o);
  const id = need(o, 'id');
  const seconds = o.seconds ? Number(o.seconds) : null;
  if (o.seconds && !(seconds > 0)) throw new Error('--seconds must be a positive number');
  const beats = (await import(pathToFileURL(resolve(need(o, 'beats'))).href)).default;
  const beat = beats[id];
  if (!beat) throw new Error(`no beat "${id}" in ${o.beats} (have: ${Object.keys(beats).join(', ')})`);

  const { chromium } = playwright(project);
  const profile = profileDir(o);
  assertProfileFree(profile);
  const framesDir = mkdtempSync(join(tmpdir(), 'demo-rec-frames-'));
  const opts = launchOptions(o, { width: W, height: H }, SCALE);
  let ctx;
  try {
    ctx = await chromium.launchPersistentContext(profile, opts);
  } catch (e) {
    rmSync(framesDir, { recursive: true, force: true });
    throw launchError(e, { channel: opts.channel ?? 'chromium', project });
  }
  const frames = [];
  let skew = 0, endWall = 0;
  try {
    const page = await ctx.newPage();
    const h = helpers(page);
    await h.ready;
    await page.goto(beat.url, { waitUntil: 'load' });
    const cdp = await ctx.newCDPSession(page);
    cdp.on('Page.screencastFrame', ({ data, metadata, sessionId }) => {
      cdp.send('Page.screencastFrameAck', { sessionId }).catch(() => {}); // no ack, no more frames
      if (!frames.length) skew = metadata.timestamp - Date.now() / 1000;
      const file = join(framesDir, `${String(frames.length).padStart(6, '0')}.jpg`);
      writeFileSync(file, Buffer.from(data, 'base64'));
      frames.push({ ts: metadata.timestamp, file });
    });
    await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 95, maxWidth: W * SCALE, maxHeight: H * SCALE, everyNthFrame: 1 });
    for (let i = 0; !frames.length && i < 50; i++) await sleep(20);
    if (!frames.length) { // static page and no initial frame: force a repaint
      await page.evaluate(() => { document.body.style.outline = '1px solid transparent'; });
      for (let i = 0; !frames.length && i < 100; i++) await sleep(20);
    }
    if (!frames.length) throw new Error('screencast produced no frames');

    await beat.run(page, h);
    endWall = Date.now() / 1000;
    if (seconds) { // keep recording only as long as needed; frames past the requested length are dropped in assemble()
      const wait = frames[0].ts - skew + seconds - endWall;
      if (wait < 0) console.log(`WARN beat ${id} overran --seconds (cut at ${seconds}s)`);
      if (wait > 0) await sleep(Math.min(wait * 1000, 60000));
    }
    await cdp.send('Page.stopScreencast');
    await sleep(100);

    const out = join(project, 'recordings', 'demos', `${id}.mp4`);
    assemble({ project, frames, endTs: endWall + skew, seconds, out });
    const dur = duration(project, out);
    register(project, `demo-${id}`, out, dur);
    console.log(`demo-${id}: ${dur.toFixed(2)} s, ${frames.length} frames -> ${out}`);
  } finally {
    await ctx.close();
    rmSync(framesDir, { recursive: true, force: true });
  }
}

const o = parseArgs(process.argv.slice(2));
const cmds = { login, record };
if (!cmds[o._]) { console.error('usage: demo_rec.mjs login|record (see header of this file)'); process.exit(2); }
Promise.resolve().then(() => cmds[o._](o)).catch((e) => { console.error(e.message); process.exit(1); });
