// node --test assets/template/tests/  (Node runs .ts natively)
import assert from 'node:assert/strict';
import {test} from 'node:test';
import {cropTransform, headBox, lerpRect} from '../src/reelGeometry.ts';

const near = (a: number, b: number) => assert.ok(Math.abs(a - b) < 1e-9, `${a} != ${b}`);

test('cropTransform fills the width with the rect and puts its centre at cy', () => {
  const t = cropTransform([0.25, 0.5, 0.75, 0.6], 2000, 1000);
  near(t.scale, 1.08);
  near(t.left, -540);
  near(t.top, 0.42 * 1920 - 550 * 1.08);
});

test('headBox positions are pinned', () => {
  assert.deepEqual(headBox('bl'), {cx: 200, cy: 1230, d: 300});
  assert.deepEqual(headBox('tl'), {cx: 200, cy: 400, d: 300});
  assert.deepEqual(headBox('big'), {cx: 540, cy: 1050, d: 640});
});

test('lerpRect at 0.5 is the midpoint', () => {
  const m = lerpRect([0, 0.2, 0.5, 0.6], [0.2, 0.4, 0.9, 1], 0.5);
  [0.1, 0.3, 0.7, 0.8].forEach((v, i) => near(m[i], v));
});
