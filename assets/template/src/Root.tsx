import React from 'react';
import {Composition} from 'remotion';
import {FPS} from './theme';
import {LongForm, longFormFrames} from './LongForm';
import {Short, shortFrames} from './Short';

// Both formats live in one project; render only the one(s) the user asked for.
export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="LongForm" component={LongForm} durationInFrames={longFormFrames()} fps={FPS} width={1920} height={1080} />
    <Composition id="Short" component={Short} durationInFrames={shortFrames()} fps={FPS} width={1080} height={1920} />
  </>
);
