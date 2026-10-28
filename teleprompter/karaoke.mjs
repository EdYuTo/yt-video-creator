// Pure karaoke timing and tap logic (no DOM). Times are in seconds.

const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
const LINE_TAIL = 0.6;
const TAP_BEAT = 1.0;

// Pauses are the 140-wpm values; they shrink in proportion as the speed goes up.
const PAUSE_REF_WPM = 140;

function pauseAfter(word) {
  if (/[.!?]["'”’)»]*$/.test(word)) return 0.45;
  if (/[,;:]["'”’)»]*$/.test(word)) return 0.25;
  return 0;
}

export function scheduleLine(text, wpm) {
  const words = [];
  let t = 0;
  let pause = 0;
  const k = PAUSE_REF_WPM / wpm;
  for (const w of text.split(/\s+/).filter(Boolean)) {
    const letters = [...w].filter((c) => /[\p{L}\p{N}]/u.test(c)).length;
    const start = t + pause;
    const end = start + (60 / wpm) * clamp(letters / 5, 0.6, 1.8);
    words.push({ w, start, end });
    t = end;
    pause = pauseAfter(w) * k;
  }
  return { words, dur: t + pause + LINE_TAIL * k };
}

// A tap within the first second of a line goes back one line; later it restarts
// the same line. Either way the line restarts after a one second beat.
export function tap(state, now) {
  const back = now - state.lineStartedAt < TAP_BEAT && state.line > 0;
  return { line: back ? state.line - 1 : state.line, lineStartedAt: now + TAP_BEAT };
}

export function advance(state, now, durs) {
  const end = state.lineStartedAt + durs[state.line];
  if (now < end) return { ...state, done: false };
  if (state.line >= durs.length - 1) return { ...state, done: true };
  return { line: state.line + 1, lineStartedAt: end, done: false };
}
