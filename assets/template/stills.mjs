// Render a few stills of a composition with one bundle (much faster than `remotion still` per frame).
//   node stills.mjs <CompositionId> <outDir> <frame> [frame...]
// Stills are 40% scale — enough to judge layout. Prints the composition length.
import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';
import path from 'path';

const [id, out, ...frames] = process.argv.slice(2);
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts'), symlinkPublicDir: true});
const composition = await selectComposition({serveUrl, id});
console.log(`${id}: ${composition.durationInFrames} frames = ${(composition.durationInFrames / composition.fps).toFixed(2)}s`);
for (const f of frames.map(Number)) {
  const output = path.join(out, `${id}_f${f}.jpg`);
  await renderStill({composition, serveUrl, frame: f, output, imageFormat: 'jpeg', scale: 0.4});
  console.log(output);
}
