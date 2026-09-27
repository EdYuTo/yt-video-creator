import React from 'react';
import {Composition, Still} from 'remotion';
import {LONG, SHORT, THUMB} from './edit-data';
import {LongForm} from './LongForm';
import {Short} from './Short';
import {SHORTS} from './shorts-data';
import {StreamShort} from './stream/StreamShort';
import {Thumbnail} from './Thumbnail';

// yt-video-creator compositions (from plan.json) + one composition per stream Short (from shorts.json).
export const RemotionRoot: React.FC = () => (
  <>
    {LONG && <Composition id="LongForm" component={LongForm} durationInFrames={LONG.total} fps={LONG.fps} width={1920} height={1080} />}
    {THUMB && <Still id="Thumbnail" component={Thumbnail} width={1280} height={720} />}
    {SHORT && <Composition id="Short" component={Short} durationInFrames={SHORT.total} fps={SHORT.fps} width={1080} height={1920} />}
    {SHORTS.map((d) => (
      <Composition key={d.id} id={d.id} component={StreamShort} defaultProps={{d}} durationInFrames={d.total} fps={d.fps} width={1080} height={1920} />
    ))}
  </>
);
