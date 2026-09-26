// Render a composition, keeping every previous version.
//   node render.mjs <CompositionId> <out/file.mp4|.jpg> [--note "why this render"] [--plan plan.json]
// --plan: the edit file snapshotted with each version (default plan.json; stream shorts use shorts.json).
// A Still (e.g. Thumbnail) renders to a JPEG.
//
// Versioning (never lose a render the user may already have reviewed or uploaded):
//   1. render into out/.<name>.rendering.<ext> — a failed/interrupted render touches nothing
//   2. on success, move the existing out/<name>.<ext> to out/versions/<name>-v<N>.<ext>,
//      together with the plan.json snapshot that produced it (<name>-v<N>.plan.json)
//   3. move the new render into place and snapshot the current plan.json as out/<name>.plan.json
//   4. append {version, file, date, seconds, note} to out/versions/log.jsonl
// Old versions are only deleted when the user asks.
//
// Why the Node API and not `npx remotion render`: the CLI bundler COPIES public/ into a temp dir
// on every render (tens of GB with raw footage). The Node API can symlink it instead.
import {bundle} from '@remotion/bundler';
import {renderMedia, renderStill, selectComposition} from '@remotion/renderer';
import fs from 'fs';
import path from 'path';

const args = process.argv.slice(2);
const noteAt = args.indexOf('--note');
const note = noteAt >= 0 ? args.splice(noteAt, 2)[1] : '';
const planAt = args.indexOf('--plan');
const planFile = planAt >= 0 ? args.splice(planAt, 2)[1] : 'plan.json';
const [id, output] = args;
if (!id || !output) {
  console.error('usage: node render.mjs <CompositionId> <out/file.ext> [--note "..."] [--plan plan.json]');
  process.exit(1);
}

const dir = path.dirname(path.resolve(output));
const ext = path.extname(output);
const name = path.basename(output, ext);
const tmp = path.join(dir, `.${name}.rendering${ext}`);
const versions = path.join(dir, 'versions');
fs.mkdirSync(dir, {recursive: true});

const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts'), symlinkPublicDir: true});
const composition = await selectComposition({serveUrl, id});
const seconds = +(composition.durationInFrames / composition.fps).toFixed(2);
console.log(`${id}: ${composition.width}x${composition.height}, ${seconds}s`);

if (composition.durationInFrames === 1) {
  await renderStill({composition, serveUrl, frame: 0, output: tmp, imageFormat: 'jpeg', jpegQuality: 92});
} else {
  let last = -1;
  await renderMedia({
    composition,
    serveUrl,
    codec: 'h264',
    crf: 16, // YouTube re-encodes anyway; give it a clean master
    imageFormat: 'jpeg',
    outputLocation: tmp,
    onProgress: ({progress}) => {
      const p = Math.floor(progress * 20);
      if (p !== last) {
        last = p;
        console.log(`${Math.round(progress * 100)}%`);
      }
    },
  });
}

// Keep the previous render (and the plan that made it) instead of overwriting it.
const planSnap = path.join(dir, `${name}.plan.json`);
let kept = null;
if (fs.existsSync(output)) {
  fs.mkdirSync(versions, {recursive: true});
  const taken = fs.readdirSync(versions).map((f) => f.match(new RegExp(`^${name}-v(\\d+)\\.`))).filter(Boolean).map((m) => +m[1]);
  const n = (taken.length ? Math.max(...taken) : 0) + 1;
  kept = path.join(versions, `${name}-v${n}${ext}`);
  fs.renameSync(output, kept);
  if (fs.existsSync(planSnap)) fs.renameSync(planSnap, path.join(versions, `${name}-v${n}.plan.json`));
}
fs.renameSync(tmp, output);
if (fs.existsSync(planFile)) fs.copyFileSync(planFile, planSnap);

const logPath = path.join(versions, 'log.jsonl');
fs.mkdirSync(versions, {recursive: true});
fs.appendFileSync(logPath, JSON.stringify({file: path.relative('.', output), date: new Date().toISOString(), seconds, note, previous: kept && path.relative('.', kept)}) + '\n');
console.log(`done: ${output}` + (kept ? ` (previous version kept as ${path.relative('.', kept)})` : ''));
