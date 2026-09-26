// Render a composition to MP4.
//   node render.mjs <CompositionId> <out.mp4>      (a Still, e.g. Thumbnail, renders to <out.jpg>)
// Why not `npx remotion render`: the CLI bundler COPIES public/ into a temp dir on every render
// (tens of GB with raw footage). The Node API can symlink it instead.
import {bundle} from '@remotion/bundler';
import {renderMedia, renderStill, selectComposition} from '@remotion/renderer';
import path from 'path';

const [id, output] = process.argv.slice(2);
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts'), symlinkPublicDir: true});
const composition = await selectComposition({serveUrl, id});
console.log(`${id}: ${composition.width}x${composition.height}, ${(composition.durationInFrames / composition.fps).toFixed(1)}s`);
if (composition.durationInFrames === 1) {
  await renderStill({composition, serveUrl, frame: 0, output, imageFormat: 'jpeg', jpegQuality: 92});
  console.log(`done: ${output}`);
  process.exit(0);
}
let last = -1;
await renderMedia({
  composition,
  serveUrl,
  codec: 'h264',
  crf: 16, // YouTube re-encodes anyway; give it a clean master
  imageFormat: 'jpeg',
  outputLocation: output,
  onProgress: ({progress}) => {
    const p = Math.floor(progress * 20);
    if (p !== last) {
      last = p;
      console.log(`${Math.round(progress * 100)}%`);
    }
  },
});
console.log(`done: ${output}`);
