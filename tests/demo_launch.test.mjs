// node --test tests/demo_launch.test.mjs : pure pieces of the recorder's browser launch (nothing is launched here).
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, symlinkSync, rmSync } from 'node:fs';
import { tmpdir, hostname, homedir } from 'node:os';
import { join } from 'node:path';
import { spawn } from 'node:child_process';
import { DEFAULT_PROFILE, profileDir, projectDir, launchOptions, chromeLoginCommand, assertProfileFree, launchError } from '../scripts/demo_launch.mjs';

const view = { width: 432, height: 768 };

test('default profile is the dedicated real-Chrome one', () => {
  assert.equal(DEFAULT_PROFILE, join(homedir(), '.cache', 'yt-video-creator', 'browser-profile-chrome'));
  assert.equal(profileDir({}), DEFAULT_PROFILE);
  assert.equal(profileDir({ profile: '/tmp/x' }), '/tmp/x');
});

test('chrome channel by default: real Chrome, keychain-compatible, headed', () => {
  const o = launchOptions({}, view, 2.5);
  assert.equal(o.channel, 'chrome');
  assert.equal(o.headless, false);
  assert.deepEqual(o.viewport, view);
  assert.equal(o.deviceScaleFactor, 2.5);
  // Playwright's defaults would make Chrome unable to read the real, keychain-encrypted cookies.
  assert.ok(o.ignoreDefaultArgs.includes('--use-mock-keychain'));
  assert.ok(o.ignoreDefaultArgs.includes('--password-store=basic'));
  assert.ok(o.args.includes('--hide-scrollbars'));
});

test('--channel chromium: bundled Chromium, default args untouched; --headless honoured', () => {
  const o = launchOptions({ channel: 'chromium', headless: true }, view, 2.5);
  assert.equal(o.channel, undefined);
  assert.equal(o.ignoreDefaultArgs, undefined);
  assert.equal(o.headless, true);
});

test('project: --project, else $DEMO_REC_PROJECT, else a cwd with Playwright, else a clear error', () => {
  const dir = mkdtempSync(join(tmpdir(), 'demo-proj-'));
  try {
    assert.equal(projectDir({ project: '/tmp/a' }, { DEMO_REC_PROJECT: '/tmp/b' }, dir), '/tmp/a');
    assert.equal(projectDir({}, { DEMO_REC_PROJECT: '/tmp/b' }, dir), '/tmp/b');
    assert.throws(() => projectDir({}, {}, dir), /pass --project <P>, set DEMO_REC_PROJECT/);
    mkdirSync(join(dir, 'node_modules', 'playwright'), { recursive: true });
    assert.equal(projectDir({ project: true }, {}, dir), dir);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});

test('launch errors say how to get the browser', () => {
  const pw = new Error("browserType.launchPersistentContext: Executable doesn't exist at /x/chrome\n╔═══ long banner");
  const e = launchError(pw, { channel: 'chromium', project: '/p' });
  assert.match(e.message, /npx playwright install chromium` in \/p/);
  assert.match(e.message, /Executable doesn't exist at \/x\/chrome$/m);
  assert.doesNotMatch(e.message, /banner/);
  assert.match(launchError(pw, { channel: 'chrome' }).message, /is Google Chrome installed\?/);
});

test('login on other systems: the same flags, flagged to be run by hand', () => {
  const l = chromeLoginCommand('/p/prof', ['https://a.example'], 'linux');
  assert.equal(l.manual, true);
  assert.equal(l.cmd, 'google-chrome');
  assert.deepEqual(l.args, ['--user-data-dir=/p/prof', '--no-first-run', '--no-default-browser-check', 'https://a.example']);
});

test('login spawns real Chrome with the profile and the urls, no automation flags', () => {
  const { cmd, args } = chromeLoginCommand('/p/prof', ['https://a.example', 'https://b.example'], 'darwin');
  assert.equal(cmd, 'open');
  assert.deepEqual(args, ['-na', 'Google Chrome', '--args', '--user-data-dir=/p/prof', '--no-first-run', '--no-default-browser-check',
    'https://a.example', 'https://b.example']);
  assert.ok(!args.some((a) => /remote-debugging|enable-automation/.test(a)));
});

test('assertProfileFree: no lock, stale lock ok; live lock fails with a clear message', async () => {
  const dir = mkdtempSync(join(tmpdir(), 'demo-lock-'));
  const child = spawn('sleep', ['30']);
  try {
    assertProfileFree(dir); // no SingletonLock
    symlinkSync(`${hostname()}-99999999`, join(dir, 'SingletonLock')); // pid that cannot exist
    assertProfileFree(dir);
    rmSync(join(dir, 'SingletonLock'));
    symlinkSync(`${hostname()}-${child.pid}`, join(dir, 'SingletonLock'));
    assert.throws(() => assertProfileFree(dir), /quit the Chrome using the recording profile first \(⌘Q \/ Chrome → Quit/);
    assertProfileFree(join(dir, 'does-not-exist-yet'));
  } finally {
    child.kill();
    rmSync(dir, { recursive: true, force: true });
  }
});
