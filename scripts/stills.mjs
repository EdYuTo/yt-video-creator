// Render a few stills of a composition, bundling only once (much faster than `remotion still` per frame).
// Run from inside the Remotion project:
//   node <skill>/scripts/stills.mjs <CompositionId> <outDir> <frame> [frame...]
// Prints the composition length. Stills are rendered at 40% scale (enough to judge layout).
import {createRequire} from 'module';
import path from 'path';

const require = createRequire(path.join(process.cwd(), 'package.json'));
const {bundle} = require('@remotion/bundler');
const {renderStill, selectComposition} = require('@remotion/renderer');

const [id, out, ...frames] = process.argv.slice(2);
const serveUrl = await bundle({entryPoint: path.join(process.cwd(), 'src/index.ts'), symlinkPublicDir: true});
const composition = await selectComposition({serveUrl, id});
console.log(`${id}: ${composition.durationInFrames} frames = ${(composition.durationInFrames / composition.fps).toFixed(2)}s`);
for (const f of frames.map(Number)) {
  const output = path.join(out, `${id}_f${f}.jpg`);
  await renderStill({composition, serveUrl, frame: f, output, imageFormat: 'jpeg', scale: 0.4});
  console.log(output);
}
