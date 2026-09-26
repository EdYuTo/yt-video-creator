// Per-video look. Change fonts/colors to fit the subject (warm for food, clean for tech, etc.).
import {loadFont as loadDisplay} from '@remotion/google-fonts/Fraunces';
import {loadFont as loadBody} from '@remotion/google-fonts/Nunito';


export const DISPLAY = loadDisplay('normal', {weights: ['600', '800'], subsets: ['latin']}).fontFamily;
export const BODY = loadBody('normal', {weights: ['600', '800'], subsets: ['latin']}).fontFamily;

export const C = {
  light: '#FFF4E6', // main text
  dark: '#2E1B10', // backgrounds, text on accent
  accent: '#D9913F', // pills, highlights, numbers
  panel: 'rgba(30, 17, 9, 0.82)', // translucent overlay panels
};
