// Browser launch pieces for demo_rec.mjs, kept pure so they can be tested without opening a browser.
//
// Why real Chrome: Google refuses sign-in inside Playwright's automated Chromium. You log in by hand in your real
// Google Chrome on a dedicated profile (`login`), and `record` then drives that same profile through Playwright's
// `channel: 'chrome'`.
import { homedir } from 'node:os';
import { join, resolve } from 'node:path';
import { readlinkSync, existsSync } from 'node:fs';

export const DEFAULT_PROFILE = join(homedir(), '.cache', 'yt-video-creator', 'browser-profile-chrome');

export const profileDir = (o) => resolve(o.profile && o.profile !== true ? o.profile : DEFAULT_PROFILE);

// The video project supplies Playwright and Remotion's bundled ffmpeg (the toolkit has no node_modules):
// --project, else $DEMO_REC_PROJECT, else the current directory if it has node_modules/playwright.
export function projectDir(o, env = process.env, cwd = process.cwd()) {
  if (o.project && o.project !== true) return resolve(o.project);
  if (env.DEMO_REC_PROJECT) return resolve(env.DEMO_REC_PROJECT);
  if (existsSync(join(cwd, 'node_modules', 'playwright'))) return resolve(cwd);
  throw new Error('no video project: pass --project <P>, set DEMO_REC_PROJECT, or run from a project with Playwright installed (npm i -D playwright)');
}

// Playwright's default Chrome args (chromiumSwitches in playwright-core) that would break a keychain-backed profile:
// --use-mock-keychain and --password-store=basic make Chrome ignore the macOS keychain, so the cookies written by the
// real Chrome could not be decrypted and every site would look logged out. The other defaults don't touch profile data.
const KEYCHAIN_ARGS = ['--use-mock-keychain', '--password-store=basic'];

export function launchOptions(o, viewport, deviceScaleFactor) {
  const chrome = (o.channel && o.channel !== true ? o.channel : 'chrome') !== 'chromium';
  return {
    headless: !!o.headless,
    viewport, deviceScaleFactor,
    args: ['--hide-scrollbars'], // headed Chrome otherwise paints an overlay scrollbar into the capture
    ...(chrome ? { channel: 'chrome', ignoreDefaultArgs: KEYCHAIN_ARGS } : {}),
  };
}

// `login` must not use Playwright (its automation flags make Google block the sign-in): plain Chrome, started like by hand.
// On macOS it is started with `open -na`; elsewhere `manual` is set and demo_rec prints the command for you to run.
export function chromeLoginCommand(profile, urls, platform = process.platform) {
  const flags = [`--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check', ...urls];
  if (platform === 'darwin') return { cmd: 'open', args: ['-na', 'Google Chrome', '--args', ...flags] };
  const cmd = platform === 'win32' ? 'chrome.exe' : 'google-chrome';
  return { cmd, args: flags, manual: true };
}

// A failed browser launch, with the fix spelled out. `npm i -D playwright` does not download Playwright's own Chromium
// (--channel chromium, tests, verify_viewer.mjs): that takes `npx playwright install chromium` in the project.
export function launchError(err, { channel = 'chromium', project = '.' } = {}) {
  const msg = String(err?.message ?? err);
  const hint = channel === 'chrome'
    ? 'is Google Chrome installed? (or use --channel chromium, after `npx playwright install chromium`)'
    : `run \`npx playwright install chromium\` in ${project} (npm i -D playwright does not download the browser)`;
  return new Error(`could not launch ${channel === 'chrome' ? 'Google Chrome' : "Playwright's Chromium"}: ${hint}\n${msg.split('\n')[0]}`);
}

// Chrome keeps a profile dir locked while it runs: SingletonLock is a symlink "<host>-<pid>". A live pid means a
// running Chrome (a stale link from a crash is fine, Chrome clears it).
export function assertProfileFree(profile) {
  let target;
  try { target = readlinkSync(join(profile, 'SingletonLock')); } catch { return; }
  const pid = Number(target.split('-').at(-1));
  if (!Number.isInteger(pid) || pid <= 0) return;
  try { process.kill(pid, 0); } catch (e) { if (e.code === 'ESRCH') return; }
  throw new Error(`the profile ${profile} is in use by a running Chrome (pid ${pid}): quit the Chrome using the recording profile first (⌘Q / Chrome → Quit; closing its window is not enough on macOS)`);
}
