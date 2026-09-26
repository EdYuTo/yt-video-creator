// 16:9 long-form edit. All creative decisions live here; LongForm.tsx is layout only.
// `from` = source in-point (s), `dur` = seconds on the timeline, `speed` = playback rate.
// EXAMPLE DATA — replace with the real edit for this footage.
import type {CounterSpec, Shot} from './components';

export type LongShot = Shot & {
  dur: number;
  chip?: {big: string; small: string}; // top-right spec card during this shot
};

export type LongSection = {
  step?: number; // shows a "STEP n" pill
  title?: string; // lower-left caption spanning the whole section
  sub?: string;
  counter?: CounterSpec; // ring counter spanning the section
  shots: LongShot[];
};

export const MUSIC = {
  file: 'music.mp3', // in public/; silently skipped if missing
  startSec: 0,
  volume: 0.8,
};

// Set to the song length to make the video end with the music: the outro card absorbs the
// difference. null = outro is exactly OUTRO.minSec.
export const TARGET_SEC: number | null = null;

export const INTRO = {
  sec: 4,
  kicker: 'KICKER',
  title: 'Video\nTitle',
  subtitle: 'One line on what this is',
  photo: 'footage/hero.jpg', // hero still (or swap for a shot in LongForm.tsx)
};

// Optional list card after the intro (ingredients, parts, gear...). null to skip.
export const LIST_CARD: {sec: number; title: string; rows: [string, string][]; photo?: string} | null = {
  sec: 6.5,
  title: "You'll need",
  rows: [
    ['2', 'things'],
    ['1', 'other thing'],
  ],
};

const f = (n: string) => `footage/${n}`;

export const SECTIONS: LongSection[] = [
  {
    title: 'First part',
    shots: [{src: f('clip01.mov'), from: 10, dur: 3, speed: 4, chip: {big: '2', small: 'things'}}],
  },
  {
    step: 1,
    title: 'Do the thing',
    sub: 'Short helpful detail',
    counter: {from: 0, to: 20, max: 25, format: (v) => `${Math.floor(v)}:00`, label: 'minutes'},
    shots: [
      {src: f('clip02.mov'), from: 30, dur: 3, speed: 10},
      {src: f('phone.mp4'), from: 0, dur: 4, fit: 'blur'},
    ],
  },
];

export const MONTAGE = {secEach: 1.2, photos: [] as string[]};

export const OUTRO = {
  minSec: 7,
  photo: undefined as string | undefined,
  columns: [
    {title: 'Column A', numbered: false, items: ['item one', 'item two']},
    {title: 'Column B', numbered: true, items: ['First step.', 'Second step.']},
  ],
};
