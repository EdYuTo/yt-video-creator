import React from 'react';
import {AbsoluteFill, Audio, getStaticFiles, Img, interpolate, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Pill, Shade, ShotView} from './components';
import {SHORT} from './edit-data';
import {C, DISPLAY} from './theme';
import type {ShortData} from './types';

// Beat-synced layout is precomputed by build_edit.py; this file only draws it.
const D = SHORT as ShortData;
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// Upper third: TikTok/Reels/Shorts cover the bottom ~25% and the right edge with UI.
const Headline: React.FC<{big?: string; small?: string; len: number}> = ({big, small, len}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame, fps, config: {damping: 12, stiffness: 180}, durationInFrames: 14});
  const smallIn = spring({frame: frame - 3, fps, config: {damping: 200}, durationInFrames: 10});
  const out = interpolate(frame, [len - 4, len], [1, 0], clamp);
  return (
    <AbsoluteFill style={{alignItems: 'center', paddingTop: 250, opacity: out}}>
      <div style={{textAlign: 'center', maxWidth: 900}}>
        {big && (
          <div
            style={{
              fontFamily: DISPLAY,
              fontWeight: 800,
              fontSize: 150,
              lineHeight: 1,
              color: C.light,
              whiteSpace: 'pre-line',
              transform: `scale(${0.6 + 0.4 * pop})`,
              textShadow: '0 6px 30px rgba(0,0,0,0.6), 0 2px 4px rgba(0,0,0,0.5)',
            }}
          >
            {big}
          </div>
        )}
        {small && (
          <Pill size={52} style={{marginTop: 22, opacity: smallIn, transform: `translateY(${(1 - smallIn) * 20}px)`}}>
            {small}
          </Pill>
        )}
      </div>
    </AbsoluteFill>
  );
};

export const Short: React.FC = () => {
  const frame = useCurrentFrame();
  const hasMusic = D.music && getStaticFiles().some((s) => s.name === D.music!.file);
  const e = D.end;
  return (
    <AbsoluteFill style={{backgroundColor: C.dark}}>
      {D.sections.flatMap((s) => s.shots).map((shot, i) => (
        <Sequence key={i} from={shot.start} durationInFrames={shot.len}>
          <ShotView shot={shot} index={i} />
        </Sequence>
      ))}
      {D.sections.map((s, i) =>
        s.big || s.small ? (
          <Sequence key={`h${i}`} from={s.start} durationInFrames={s.len}>
            <Shade from="top" />
            <Headline big={s.big} small={s.small} len={s.len} />
          </Sequence>
        ) : null,
      )}
      <Sequence from={e.start} durationInFrames={e.len}>
        <AbsoluteFill style={{backgroundColor: C.dark}}>
          {e.photo && (
            <Img
              src={staticFile(e.photo)}
              style={{width: '100%', height: '100%', objectFit: 'cover', filter: 'brightness(0.8)', transform: `scale(${1.05 + 0.08 * ((frame - e.start) / e.len)})`}}
            />
          )}
          <Shade from="top" />
          <Headline big={e.big} small={e.small} len={e.len + 10} />
        </AbsoluteFill>
      </Sequence>
      {hasMusic && (
        <Audio
          src={staticFile(D.music!.file)}
          trimBefore={Math.round(D.music!.startSec * D.fps)}
          volume={(f) => interpolate(f, [D.total - 12, D.total], [D.music!.volume, 0], clamp)}
        />
      )}
    </AbsoluteFill>
  );
};
