// Teleprompter server: node server.mjs --project <P> [--port 3918]
import http from 'node:http';
import { readFileSync, existsSync, mkdirSync, appendFileSync, writeFileSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const SAFE = /^[A-Za-z0-9_-][A-Za-z0-9_.-]*$/;
const DEFAULT_SETTINGS = { wpm: null, cameraId: null, micId: null };

const readBody = (req) => new Promise((ok, fail) => {
  const bufs = [];
  req.on('data', (b) => bufs.push(b));
  req.on('end', () => ok(Buffer.concat(bufs)));
  req.on('error', fail);
});

export function startServer({ project, port = 3918 }) {
  const root = resolve(project);
  const rec = join(root, 'recordings');
  const raw = join(rec, 'raw');
  const reply = (res, code, body, type = 'text/plain; charset=utf-8') => {
    res.writeHead(code, { 'content-type': type, 'cache-control': 'no-store' });
    res.end(body);
  };
  const json = (res, code, obj) => reply(res, code, JSON.stringify(obj), 'application/json');

  const server = http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url, 'http://localhost');
      const key = `${req.method} ${url.pathname}`;
      const reel = url.searchParams.get('reel') ?? '';
      const take = url.searchParams.get('take') ?? '';

      if (key === 'GET /') return reply(res, 200, readFileSync(join(HERE, 'index.html')), 'text/html; charset=utf-8');
      if (key === 'GET /karaoke.mjs') return reply(res, 200, readFileSync(join(HERE, 'karaoke.mjs')), 'text/javascript; charset=utf-8');
      if (key === 'GET /api/reels') {
        const f = join(root, 'scripts', 'reels.json');
        return existsSync(f) ? reply(res, 200, readFileSync(f), 'application/json') : json(res, 404, { error: 'scripts/reels.json not found' });
      }
      if (key === 'GET /api/settings') {
        const f = join(rec, 'settings.json');
        return json(res, 200, existsSync(f) ? { ...DEFAULT_SETTINGS, ...JSON.parse(readFileSync(f, 'utf8')) } : DEFAULT_SETTINGS);
      }
      if (key === 'POST /api/settings') {
        const { wpm = null, cameraId = null, micId = null } = JSON.parse((await readBody(req)).toString() || '{}');
        mkdirSync(rec, { recursive: true });
        writeFileSync(join(rec, 'settings.json'), JSON.stringify({ wpm, cameraId, micId }, null, 2));
        return json(res, 200, { ok: true });
      }
      if (key === 'POST /api/chunk' || key === 'POST /api/log') {
        if (!SAFE.test(reel) || !SAFE.test(take)) return json(res, 400, { error: 'bad reel/take' });
        const body = await readBody(req);
        mkdirSync(raw, { recursive: true });
        if (url.pathname === '/api/chunk') appendFileSync(join(raw, `${reel}-${take}.webm`), body);
        else writeFileSync(join(raw, `${reel}-${take}.log.json`), body);
        return json(res, 200, { ok: true });
      }
      return reply(res, 404, 'not found');
    } catch (e) {
      return json(res, 500, { error: String(e.message ?? e) });
    }
  });
  return new Promise((ok, fail) => {
    server.once('error', fail);
    server.listen(port, '127.0.0.1', () => ok(server));
  });
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);
  const opt = (name, d) => (args.includes(name) ? args[args.indexOf(name) + 1] : d);
  const project = opt('--project');
  if (!project) { console.error('usage: node server.mjs --project <P> [--port 3918]'); process.exit(2); }
  const srv = await startServer({ project, port: Number(opt('--port', 3918)) });
  console.log(`Teleprompter: http://localhost:${srv.address().port}  (project ${resolve(project)})`);
}
