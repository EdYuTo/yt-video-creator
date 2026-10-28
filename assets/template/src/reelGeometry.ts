// Pure layout maths for reels (no imports, so `node --test` can load it directly).
export type RectF = [number, number, number, number]; // x0, y0, x1, y1 as fractions of the source

// Scale a source rect to the full reel width and put its vertical centre at `cy` of the height.
// Apply as: position the source (srcW x srcH) at its top-left, translate(left, top) scale(scale).
export const cropTransform = (rect: RectF, srcW: number, srcH: number, outW = 1080, outH = 1920, cy = 0.42) => {
  const [x0, y0, x1, y1] = rect;
  const scale = outW / ((x1 - x0) * srcW);
  return {scale, left: -x0 * srcW * scale, top: cy * outH - ((y0 + y1) / 2) * srcH * scale};
};

export const lerpRect = (a: RectF, b: RectF, t: number): RectF =>
  [0, 1, 2, 3].map((i) => a[i] + (b[i] - a[i]) * t) as RectF;

// Head bubble: circle centre (cx, cy) and diameter d, in reel pixels. The bubble video is
// d wide and 1.3d tall with the circle at its bottom, so the head can break out above the rim.
export type HeadPos = 'bl' | 'tl' | 'big';
const HEAD: Record<HeadPos, {cx: number; cy: number; d: number}> = {
  bl: {cx: 200, cy: 1230, d: 300}, // circle bottom 1380: clear of two-line subtitles (top ≈1442)
  tl: {cx: 200, cy: 400, d: 300},
  big: {cx: 540, cy: 1050, d: 640},
};
export const headBox = (pos: HeadPos) => ({...HEAD[pos]});
