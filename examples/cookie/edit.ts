// The whole edit lives here: tweak in/out points, speeds and captions without touching layout code.
// `from` = source timestamp in seconds, `dur` = seconds on the final timeline, `speed` = playback rate.

export const FPS = 30;

export type Shot = {
  src: string;
  from: number;
  dur: number;
  speed?: number;
  // Small amount chip shown during the shot, e.g. "225 g" + "butter".
  amount?: string;
  item?: string;
  // Square phone video: letterboxed over a blurred copy of itself.
  square?: boolean;
};

export type Section = {
  step?: number;
  title?: string;
  sub?: string;
  overlay?: 'bake-timer';
  shots: Shot[];
};

export const INGREDIENTS: [string, string][] = [
  ['320 g', 'white flour'],
  ['2 pinches', 'salt'],
  ['1 tsp', 'baking powder'],
  ['225 g', 'butter'],
  ['220 g', 'brown sugar'],
  ['100 g', 'sugar'],
  ['2 tbsp', 'vanilla extract'],
  ['1–2', 'eggs'],
  ['240 g', 'chocolate, in chunks'],
];

export const STEPS: string[] = [
  'Melt the butter in the microwave.',
  'Cut the chocolate into pieces.',
  'Mix both sugars with the melted butter for 2–3 min, until smooth.',
  'Add eggs and vanilla; mix until homogeneous.',
  'Add salt and mix.',
  'Add the flour slowly, a little at a time, to avoid lumps.',
  'Fold in the chocolate pieces.',
  'Wrap in plastic and chill at least 30 min (overnight is best).',
  'Roll into balls and freeze.',
  'Bake straight from the freezer: 200 °C for 20–25 min.',
];

const f = (n: string) => `footage/${n}`;

export const SECTIONS: Section[] = [
  {
    title: 'Weigh everything first',
    shots: [
      {src: f('0576.mov'), from: 34, dur: 2.4, speed: 6, amount: '225 g', item: 'butter'},
      {src: f('0577.mov'), from: 30, dur: 2.4, speed: 7, amount: '320 g', item: 'white flour'},
      {src: f('0578.mov'), from: 38, dur: 2.4, speed: 5, amount: '220 g', item: 'brown sugar'},
      {src: f('0579.mov'), from: 95, dur: 2.4, speed: 5, amount: '100 g', item: 'sugar'},
      {src: f('0581.mov'), from: 40, dur: 2.4, speed: 4, amount: '2 tbsp', item: 'vanilla extract'},
      {src: f('0582.mov'), from: 50, dur: 2.4, speed: 6, amount: '1–2', item: 'eggs'},
    ],
  },
  {
    step: 1,
    title: 'Melt the butter',
    sub: 'A quick spin in the microwave',
    shots: [{src: f('0576.mov'), from: 98, dur: 2.5, speed: 3}],
  },
  {
    step: 2,
    title: 'Chop the chocolate',
    sub: '240 g, into chunks',
    shots: [
      {src: f('0580.mov'), from: 112, dur: 2.5, speed: 16},
      {src: f('0580.mov'), from: 272, dur: 2, speed: 12},
    ],
  },
  {
    step: 3,
    title: 'Sugars + melted butter',
    sub: 'Mix 2–3 min until smooth',
    shots: [
      {src: f('0583.mov'), from: 22, dur: 2.2, speed: 5},
      {src: f('0583.mov'), from: 70, dur: 2.3, speed: 12},
    ],
  },
  {
    step: 4,
    title: 'Add eggs & vanilla',
    sub: 'Mix again until homogeneous',
    shots: [
      {src: f('0583.mov'), from: 212, dur: 2, speed: 3},
      {src: f('0583.mov'), from: 300, dur: 1.5, speed: 16},
      {src: f('0583.mov'), from: 396, dur: 1.5, speed: 2},
    ],
  },
  {
    step: 5,
    title: 'Add the salt',
    sub: 'Two pinches, then mix',
    shots: [{src: f('0584.mov'), from: 18, dur: 2.5, speed: 2.5}],
  },
  {
    step: 6,
    title: 'Add the flour slowly',
    sub: 'Not all at once, so no lumps',
    shots: [
      {src: f('0584.mov'), from: 86, dur: 2, speed: 4},
      {src: f('0584.mov'), from: 120, dur: 2.5, speed: 18},
    ],
  },
  {
    step: 7,
    title: 'Fold in the chocolate',
    shots: [
      {src: f('0584.mov'), from: 372, dur: 2, speed: 4},
      {src: f('0584.mov'), from: 420, dur: 2, speed: 14},
    ],
  },
  {
    step: 8,
    title: 'Wrap & chill',
    sub: '30 min minimum, overnight is best',
    shots: [
      {src: f('0584.mov'), from: 544, dur: 3, speed: 8},
      {src: f('0585.mov'), from: 6, dur: 3.5, speed: 4.5},
    ],
  },
  {
    step: 9,
    title: 'Roll into balls, then freeze',
    shots: [
      {src: f('0586.mov'), from: 60, dur: 2.5, speed: 20},
      {src: f('0586.mov'), from: 200, dur: 2.5, speed: 22},
      {src: f('0586.mov'), from: 490, dur: 1.5, speed: 4},
      {src: f('0587.mov'), from: 4, dur: 3, speed: 3.5},
    ],
  },
  {
    title: 'Whenever the craving hits…',
    sub: 'Straight from the freezer, no thawing',
    shots: [
      {src: f('0590.mov'), from: 18, dur: 4.5, speed: 2.4},
      {src: f('0591.mov'), from: 25, dur: 1.75, speed: 12},
      {src: f('0591.mov'), from: 90, dur: 1.75, speed: 10},
    ],
  },
  {
    step: 10,
    title: 'Bake at 200 °C',
    sub: '20–25 minutes',
    overlay: 'bake-timer',
    shots: [
      {src: f('0592.mov'), from: 18, dur: 2, speed: 3},
      {src: f('0592.mov'), from: 30, dur: 3, speed: 25},
      {src: f('0596.mov'), from: 6, dur: 2.2, speed: 5},
      {src: f('0597.mov'), from: 14, dur: 1.8, speed: 2.5},
    ],
  },
  {
    shots: [
      {src: f('0598.mov'), from: 0, dur: 2, speed: 4},
      {src: f('0598.mov'), from: 100, dur: 3},
    ],
  },
  {
    title: 'The best part',
    shots: [
      {src: f('phone.mp4'), from: 0, dur: 5.5, speed: 1.3, square: true},
      {src: f('0610.mov'), from: 68, dur: 3.2},
      {src: f('phone.mp4'), from: 35, dur: 3.3, square: true},
    ],
  },
];

export const PHOTOS = ['photo1.jpeg', 'photo2.jpeg', 'photo4.jpeg', 'photo5.jpeg'].map(f);
export const DOG: Shot = {src: f('phone.mp4'), from: 47.5, dur: 3.5, square: true};

export const INTRO_SEC = 4;
export const INGREDIENTS_SEC = 6.5;
export const PHOTO_SEC = 1.1;
// Whole video matches the song ("Spring In My Step", 1:58.9); the outro card absorbs whatever is left.
export const TARGET_SEC = 118.9;
export const MIN_OUTRO_SEC = 7;
