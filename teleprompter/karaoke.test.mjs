import test from 'node:test';
import assert from 'node:assert/strict';
import { scheduleLine, tap, advance } from './karaoke.mjs';

const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `${a} !~ ${b}`);

test('scheduleLine: two words at 120 wpm (pauses scale by 140/120)', () => {
  const s = scheduleLine('Olá mundo.', 120);
  assert.equal(s.words.length, 2);
  assert.equal(s.words[0].w, 'Olá');
  near(s.words[0].start, 0);
  near(s.words[0].end, 0.3);
  assert.equal(s.words[1].w, 'mundo.');
  near(s.words[1].start, 0.3);
  near(s.words[1].end, 0.8);
  near(s.dur, 0.8 + (0.45 + 0.6) * (140 / 120)); // 2.025
});

test('scheduleLine: pauses are unchanged at 140 wpm', () => {
  near(scheduleLine('Olá mundo.', 140).dur, 0.3 * (120 / 140) + 0.5 * (120 / 140) + 0.45 + 0.6);
  near(scheduleLine('a, b', 140).words[1].start, 60 / 140 * 0.6 + 0.25);
});

test('scheduleLine: comma pause goes after the word and scales', () => {
  const s = scheduleLine('a, b', 60);
  near(s.words[1].start, 0.6 + 0.25 * (140 / 60)); // 1.18333...
});

test('scheduleLine: 260 wpm shrinks words and pauses', () => {
  const s = scheduleLine('Olá mundo.', 260);
  const k = 140 / 260;
  near(s.words[0].end, (60 / 260) * 0.6);
  near(s.words[1].end, (60 / 260) * 0.6 + 60 / 260);
  near(s.dur, (60 / 260) * 1.6 + (0.45 + 0.6) * k); // ~0.9346
});

test('tap inside first second goes back one line', () => {
  assert.deepEqual(tap({ line: 3, lineStartedAt: 10 }, 10.5), { line: 2, lineStartedAt: 11.5 });
});

test('tap later restarts the same line', () => {
  assert.deepEqual(tap({ line: 3, lineStartedAt: 10 }, 12), { line: 3, lineStartedAt: 13 });
});

test('tap at line 0 stays at 0', () => {
  assert.equal(tap({ line: 0, lineStartedAt: 0 }, 0.2).line, 0);
});

test('double tap goes back two lines', () => {
  const a = tap({ line: 2, lineStartedAt: 10 }, 10.3);
  assert.equal(a.line, 1);
  const b = tap(a, 10.6);
  assert.equal(b.line, 0);
});

test('many rapid taps never go below 0', () => {
  let s = { line: 2, lineStartedAt: 0 };
  for (let i = 0; i < 10; i++) s = tap(s, 0.1 * i);
  assert.equal(s.line, 0);
});

test('advance moves to the next line when the current one is over', () => {
  const durs = [2, 2, 2];
  assert.deepEqual(advance({ line: 0, lineStartedAt: 0 }, 1, durs), { line: 0, lineStartedAt: 0, done: false });
  assert.deepEqual(advance({ line: 0, lineStartedAt: 0 }, 2, durs), { line: 1, lineStartedAt: 2, done: false });
});

test('advance past the last line is done', () => {
  const r = advance({ line: 2, lineStartedAt: 0 }, 2.5, [2, 2, 2]);
  assert.equal(r.done, true);
});
