// Render a few stills of a composition with one bundle (much faster than `remotion still` per frame).
//   node stills.mjs <CompositionId> <outDir> <frame> [frame...]
// Stills are 40% scale — enough to judge layout. Prints the composition length.
import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';
import path from 'path';
// Optional browser settings, both read from the environment and omitted (Remotion's defaults) when unset:
//   REMOTION_PORT=3123      another local server already listens on Remotion's default port (3000) and the
//                           render then 404s or hangs on "Waiting for root component to load".
//   REMOTION_BROWSER=/path  use this Chrome / chrome-headless-shell binary instead of the one Remotion
//                           downloads, e.g. when that build hangs loading the root component.
const browserOpts = {
  ...(process.env.REMOTION_PORT ? {port: Number(process.env.REMOTION_PORT)} : {}),
  ...(process.env.REMOTION_BROWSER ? {browserExecutable: process.env.REMOTION_BROWSER} : {}),
};

const [id, out, ...frames] = process.argv.slice(2);
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts'), symlinkPublicDir: true});
const composition = await selectComposition({serveUrl, id, ...browserOpts, timeoutInMilliseconds: 120000});
console.log(`${id}: ${composition.durationInFrames} frames = ${(composition.durationInFrames / composition.fps).toFixed(2)}s`);
for (const f of frames.map(Number)) {
  const output = path.join(out, `${id}_f${f}.jpg`);
  await renderStill({composition, serveUrl, ...browserOpts, frame: f, output, imageFormat: 'jpeg', scale: 0.4});
  console.log(output);
}
