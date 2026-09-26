// Vertical short (TikTok / Reels / Shorts). Every cut lands on a beat of the music.
// `beats` = shot length in beats, `x` = horizontal crop focus in % (0 = left edge, 100 = right edge).

export const MUSIC_START_SEC = 27.7; // hard downbeat right after the song's first break
export const BEAT_SEC = 0.566; // ~106 BPM
export const BEAT_OFFSET_SEC = 0.05; // first beat, relative to MUSIC_START_SEC
export const TAIL_SEC = 0.4; // let the phrase ring out after the last beat

export type VShot = {
  src: string;
  from: number;
  beats: number;
  speed?: number;
  x?: number;
  square?: boolean;
};

export type VSection = {
  // Big line (amount or headline) and small line under it.
  big?: string;
  small?: string;
  shots: VShot[];
};

const f = (n: string) => `footage/${n}`;

export const HOOK: VSection = {
  big: 'Freezer cookies',
  small: 'bake one whenever you want',
  shots: [{src: f('phone.mp4'), from: 7.5, beats: 6, square: true}],
};

export const V_SECTIONS: VSection[] = [
  {big: '225 g', small: 'butter', shots: [{src: f('0576.mov'), from: 45, beats: 2, speed: 3, x: 47}]},
  {big: '320 g', small: 'flour', shots: [{src: f('0577.mov'), from: 34, beats: 2, speed: 5, x: 46}]},
  {big: '220 g', small: 'brown sugar', shots: [{src: f('0578.mov'), from: 42, beats: 2, speed: 4, x: 49}]},
  {big: '100 g', small: 'sugar', shots: [{src: f('0579.mov'), from: 97, beats: 2, speed: 4, x: 48}]},
  {big: '2 tbsp', small: 'vanilla', shots: [{src: f('0581.mov'), from: 44, beats: 2, speed: 4, x: 49}]},
  {big: '1–2', small: 'eggs', shots: [{src: f('0582.mov'), from: 64, beats: 2, speed: 4, x: 38}]},
  {big: '240 g', small: 'chocolate, chopped', shots: [{src: f('0580.mov'), from: 116, beats: 3, speed: 12, x: 44}]},
  {
    big: 'Mix',
    small: 'sugars + melted butter',
    shots: [
      {src: f('0583.mov'), from: 26, beats: 2, speed: 4, x: 43},
      {src: f('0583.mov'), from: 80, beats: 2, speed: 12, x: 43},
    ],
  },
  {big: '+ eggs', small: '& vanilla', shots: [{src: f('0583.mov'), from: 213, beats: 3, speed: 3, x: 31}]},
  {big: '+ salt', shots: [{src: f('0584.mov'), from: 19, beats: 2, speed: 3, x: 48}]},
  {
    big: '+ flour',
    small: 'a little at a time',
    shots: [
      {src: f('0584.mov'), from: 88, beats: 2, speed: 4, x: 42},
      {src: f('0584.mov'), from: 125, beats: 2, speed: 16, x: 48},
    ],
  },
  {big: '+ chocolate', shots: [{src: f('0584.mov'), from: 374, beats: 3, speed: 4, x: 40}]},
  {
    big: 'Chill',
    small: '30 min+ (overnight is best)',
    shots: [
      {src: f('0584.mov'), from: 552, beats: 2, speed: 8, x: 45},
      {src: f('0585.mov'), from: 8, beats: 3, speed: 6, x: 68},
    ],
  },
  {
    big: 'Roll',
    small: 'into balls',
    shots: [
      {src: f('0586.mov'), from: 65, beats: 3, speed: 20, x: 55},
      {src: f('0586.mov'), from: 496, beats: 2, speed: 4, x: 54},
    ],
  },
  {big: 'Freeze', shots: [{src: f('0587.mov'), from: 6, beats: 3, speed: 4, x: 62}]},
  {big: 'Craving?', small: 'bake straight from frozen', shots: [{src: f('0590.mov'), from: 27, beats: 3, speed: 4, x: 42}]},
  {
    big: '200 °C',
    small: '20–25 min',
    shots: [
      {src: f('0592.mov'), from: 21.5, beats: 2, speed: 3, x: 40},
      {src: f('0592.mov'), from: 30, beats: 3, speed: 30, x: 40},
      {src: f('0597.mov'), from: 14.5, beats: 2, speed: 2, x: 30},
    ],
  },
  {shots: [{src: f('0598.mov'), from: 101, beats: 3, x: 58}]},
  {
    shots: [
      {src: f('0610.mov'), from: 69, beats: 4, x: 50},
      {src: f('phone.mp4'), from: 36, beats: 2, square: true},
    ],
  },
  {big: 'Taste tester', small: 'approved', shots: [{src: f('phone.mp4'), from: 47.5, beats: 4, square: true}]},
];

export const END_BEATS = 4;
export const END_PHOTO = 'footage/photo2.jpeg';
