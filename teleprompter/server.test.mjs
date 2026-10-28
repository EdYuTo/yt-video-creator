import test, { before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { startServer } from './server.mjs';

const fixture = { wpm: 140, reels: [{ id: 'r1', title: 'T', lines: [{ text: 'Olá.' }] }] };
let dir, srv, base;

before(async () => {
  dir = mkdtempSync(join(tmpdir(), 'tp-test-'));
  mkdirSync(join(dir, 'scripts'));
  writeFileSync(join(dir, 'scripts', 'reels.json'), JSON.stringify(fixture));
  srv = await startServer({ project: dir, port: 0 });
  base = `http://127.0.0.1:${srv.address().port}`;
});
after(() => { srv.close(); rmSync(dir, { recursive: true, force: true }); });

const post = (path, body) => fetch(base + path, { method: 'POST', body });

test('GET / serves the page', async () => {
  const r = await fetch(base + '/');
  assert.equal(r.status, 200);
  assert.match(r.headers.get('content-type'), /html/);
  assert.match(await r.text(), />Record</);
});

test('GET /api/reels returns the fixture', async () => {
  assert.deepEqual(await (await fetch(base + '/api/reels')).json(), fixture);
});

test('settings round trip', async () => {
  assert.equal((await fetch(base + '/api/settings')).status, 200); // defaults when no file
  await post('/api/settings', JSON.stringify({ wpm: 150, cameraId: 'c', micId: 'm' }));
  assert.deepEqual(await (await fetch(base + '/api/settings')).json(), { wpm: 150, cameraId: 'c', micId: 'm' });
  assert.deepEqual(JSON.parse(readFileSync(join(dir, 'recordings', 'settings.json'), 'utf8')), { wpm: 150, cameraId: 'c', micId: 'm' });
});

test('chunks are appended in order', async () => {
  await post('/api/chunk?reel=r1&take=T1', 'ab');
  await post('/api/chunk?reel=r1&take=T1', 'cd');
  assert.equal(readFileSync(join(dir, 'recordings', 'raw', 'r1-T1.webm'), 'utf8'), 'abcd');
});

test('log is written on every event (overwrite)', async () => {
  const p = join(dir, 'recordings', 'raw', 'r1-T2.log.json');
  await post('/api/log?reel=r1&take=T2', JSON.stringify({ v: 1 }));
  assert.deepEqual(JSON.parse(readFileSync(p, 'utf8')), { v: 1 });
  await post('/api/log?reel=r1&take=T2', JSON.stringify({ v: 2, more: true }));
  assert.deepEqual(JSON.parse(readFileSync(p, 'utf8')), { v: 2, more: true });
});

test('path traversal in reel/take is rejected', async () => {
  const r = await post('/api/chunk?reel=../x&take=T', 'zz');
  assert.equal(r.status, 400);
});
