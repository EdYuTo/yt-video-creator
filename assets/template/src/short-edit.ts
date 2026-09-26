// 9:16 Short edit. Every cut lands on a beat: shot lengths are in beats.
// Get BEAT_SEC / offsets / a good MUSIC_START_SEC from scripts/music.py.
// EXAMPLE DATA — replace with the real edit for this footage.
import type {Shot} from './components';

export const MUSIC = {file: 'music.mp3', volume: 0.85};
export const MUSIC_START_SEC = 0; // ideally the hard onset right after a break in the song
export const BEAT_SEC = 0.566; // 60 / BPM
export const BEAT_OFFSET_SEC = 0.05; // first beat relative to MUSIC_START_SEC
export const TAIL_SEC = 0.4; // let the last note ring after the final beat

export type VShot = Shot & {beats: number};

export type VSection = {
  big?: string; // large headline in the upper third
  small?: string; // pill under it
  shots: VShot[];
};

const f = (n: string) => `footage/${n}`;

// First 1-3 s decide whether people keep watching: open on the payoff, not the setup.
export const HOOK: VSection = {
  big: 'Hook line',
  small: 'what you get',
  shots: [{src: f('phone.mp4'), from: 0, beats: 6, fit: 'blur'}],
};

export const V_SECTIONS: VSection[] = [
  {big: '2', small: 'things', shots: [{src: f('clip01.mov'), from: 10, beats: 2, speed: 4, x: 47}]},
  {
    big: 'Do it',
    shots: [
      {src: f('clip02.mov'), from: 30, beats: 2, speed: 8, x: 40},
      {src: f('clip02.mov'), from: 60, beats: 2, speed: 8, x: 55},
    ],
  },
];

export const END = {beats: 4, photo: 'footage/hero.jpg', big: 'Details\nin the caption', small: 'save it for later'};
