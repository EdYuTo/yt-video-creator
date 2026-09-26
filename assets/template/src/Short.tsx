import React from 'react';
import {AbsoluteFill, Audio, getStaticFiles, Img, interpolate, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Pill, Shade, ShotView} from './components';
import {BEAT_OFFSET_SEC, BEAT_SEC, END, HOOK, MUSIC, MUSIC_START_SEC, TAIL_SEC, V_SECTIONS, VSection, VShot} from './short-edit';
import {C, DISPLAY, FPS} from './theme';

// Frame on which beat k lands (beat 0 = video start).
const beatFrame = (k: number) => (k === 0 ? 0 : Math.round((BEAT_OFFSET_SEC + k * BEAT_SEC) * FPS));

type Placed = {start: number; end: number};
type PlacedSection = Omit<VSection, 'shots'> & Placed & {shots: (VShot & Placed)[]};

const layout = () => {
  let beat = 0;
  const sections: PlacedSection[] = [HOOK, ...V_SECTIONS].map((s) => {
    const first = beat;
    const shots = s.shots.map((shot) => {
      const b = beat;
      beat += shot.beats;
      return {...shot, start: beatFrame(b), end: beatFrame(beat)};
    });
    return {...s, shots, start: beatFrame(first), end: beatFrame(beat)};
  });
  return {sections, endStart: beatFrame(beat), total: beatFrame(beat + END.beats) + Math.round(TAIL_SEC * FPS)};
};

const L = layout();
export const shortFrames = () => L.total;

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// Upper third: TikTok/Reels/Shorts cover the bottom ~25% and the right edge with UI.
const Headline: React.FC<{big?: string; small?: string; frames: number}> = ({big, small, frames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame, fps, config: {damping: 12, stiffness: 180}, durationInFrames: 14});
  const smallIn = spring({frame: frame - 3, fps, config: {damping: 200}, durationInFrames: 10});
  const out = interpolate(frame, [frames - 4, frames], [1, 0], clamp);
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

const SectionView: React.FC<{section: PlacedSection}> = ({section}) => (
  <AbsoluteFill>
    {section.shots.map((shot, i) => (
      <Sequence key={i} from={shot.start - section.start} durationInFrames={shot.end - shot.start}>
        <ShotView shot={shot} />
      </Sequence>
    ))}
    {section.big && <Shade from="top" />}
    {(section.big || section.small) && <Headline big={section.big} small={section.small} frames={section.end - section.start} />}
  </AbsoluteFill>
);

const EndCard: React.FC<{frames: number}> = ({frames}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{backgroundColor: C.dark}}>
      <Img
        src={staticFile(END.photo)}
        style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${1.05 + 0.08 * (frame / frames)})`, filter: 'brightness(0.8)'}}
      />
      <Shade from="top" />
      <Headline big={END.big} small={END.small} frames={frames + 10} />
    </AbsoluteFill>
  );
};

const Music: React.FC = () => {
  const {durationInFrames} = useVideoConfig();
  if (!getStaticFiles().some((s) => s.name === MUSIC.file)) return null;
  return (
    <Audio
      src={staticFile(MUSIC.file)}
      trimBefore={Math.round(MUSIC_START_SEC * FPS)}
      volume={(f) => interpolate(f, [durationInFrames - 12, durationInFrames], [MUSIC.volume, 0], clamp)}
    />
  );
};

export const Short: React.FC = () => (
  <AbsoluteFill style={{backgroundColor: C.dark}}>
    {L.sections.map((s, i) => (
      <Sequence key={i} from={s.start} durationInFrames={s.end - s.start}>
        <SectionView section={s} />
      </Sequence>
    ))}
    <Sequence from={L.endStart} durationInFrames={L.total - L.endStart}>
      <EndCard frames={L.total - L.endStart} />
    </Sequence>
    <Music />
  </AbsoluteFill>
);
