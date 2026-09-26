import React from 'react';
import {
  AbsoluteFill,
  Audio,
  getStaticFiles,
  Img,
  interpolate,
  OffthreadVideo,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {FPS} from './edit';
import {
  BEAT_OFFSET_SEC,
  BEAT_SEC,
  END_BEATS,
  END_PHOTO,
  HOOK,
  MUSIC_START_SEC,
  TAIL_SEC,
  V_SECTIONS,
  VSection,
  VShot,
} from './short-edit';
import {C, SANS, SERIF} from './ui';

// Frame at which beat `k` lands (beat 0 = start of the video).
const beatFrame = (k: number) => (k === 0 ? 0 : Math.round((BEAT_OFFSET_SEC + k * BEAT_SEC) * FPS));

type Placed<T> = T & {start: number; end: number};

const SECTIONS = [HOOK, ...V_SECTIONS];

const layout = () => {
  let beat = 0;
  const sections = SECTIONS.map((s) => {
    const sStart = beat;
    const shots = s.shots.map((shot) => {
      const start = beat;
      beat += shot.beats;
      return {...shot, start: beatFrame(start), end: beatFrame(beat)};
    });
    return {...s, shots, start: beatFrame(sStart), end: beatFrame(beat)};
  });
  const endStart = beatFrame(beat);
  const total = beatFrame(beat + END_BEATS) + Math.round(TAIL_SEC * FPS);
  return {sections, endStart, total};
};

const L = layout();
export const shortFrames = () => L.total;

const cover: React.CSSProperties = {width: '100%', height: '100%', objectFit: 'cover'};

const VShotView: React.FC<{shot: VShot}> = ({shot}) => {
  const video = (style: React.CSSProperties) => (
    <OffthreadVideo
      src={staticFile(shot.src)}
      trimBefore={Math.round(shot.from * FPS)}
      playbackRate={shot.speed ?? 1}
      muted
      style={style}
    />
  );
  if (!shot.square) {
    return <AbsoluteFill>{video({...cover, objectPosition: `${shot.x ?? 50}% 50%`})}</AbsoluteFill>;
  }
  return (
    <AbsoluteFill style={{backgroundColor: C.choc}}>
      <AbsoluteFill style={{filter: 'blur(50px) brightness(0.5)', transform: 'scale(1.2)'}}>
        {video(cover)}
      </AbsoluteFill>
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        {video({width: '100%', aspectRatio: '1 / 1', boxShadow: '0 20px 80px rgba(0,0,0,0.5)'})}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// Captions sit in the upper third: clear of the platform UI at the bottom and on the right.
const VCaption: React.FC<{big?: string; small?: string; frames: number}> = ({big, small, frames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame, fps, config: {damping: 12, stiffness: 180}, durationInFrames: 14});
  const out = interpolate(frame, [frames - 4, frames], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const smallIn = spring({frame: frame - 3, fps, config: {damping: 200}, durationInFrames: 10});
  return (
    <AbsoluteFill style={{alignItems: 'center', paddingTop: 250, opacity: out}}>
      <div style={{textAlign: 'center', maxWidth: 900}}>
        {big && (
          <div
            style={{
              fontFamily: SERIF,
              fontWeight: 800,
              fontSize: 150,
              lineHeight: 1,
              color: C.cream,
              transform: `scale(${0.6 + 0.4 * pop})`,
              textShadow: '0 6px 30px rgba(0,0,0,0.6), 0 2px 4px rgba(0,0,0,0.5)',
            }}
          >
            {big}
          </div>
        )}
        {small && (
          <div
            style={{
              display: 'inline-block',
              marginTop: 22,
              fontFamily: SANS,
              fontWeight: 800,
              fontSize: 52,
              color: C.choc,
              background: C.caramel,
              padding: '10px 30px',
              borderRadius: 999,
              opacity: smallIn,
              transform: `translateY(${(1 - smallIn) * 20}px)`,
            }}
          >
            {small}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};

const TopShade: React.FC = () => (
  <AbsoluteFill style={{background: 'linear-gradient(to bottom, rgba(0,0,0,0.5) 0%, rgba(0,0,0,0) 40%)'}} />
);

type PlacedSection = Omit<VSection, 'shots'> & {start: number; end: number; shots: Placed<VShot>[]};

const SectionView: React.FC<{section: PlacedSection}> = ({section}) => (
  <AbsoluteFill>
    {section.shots.map((shot, i) => (
      <Sequence key={i} from={shot.start - section.start} durationInFrames={shot.end - shot.start}>
        <VShotView shot={shot} />
      </Sequence>
    ))}
    {section.big && <TopShade />}
    {(section.big || section.small) && (
      <VCaption big={section.big} small={section.small} frames={section.end - section.start} />
    )}
  </AbsoluteFill>
);

const EndCard: React.FC<{frames: number}> = ({frames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame, fps, config: {damping: 14}, durationInFrames: 16});
  return (
    <AbsoluteFill style={{backgroundColor: C.choc}}>
      <Img
        src={staticFile(END_PHOTO)}
        style={{...cover, transform: `scale(${1.05 + 0.08 * (frame / frames)})`, filter: 'brightness(0.8)'}}
      />
      <TopShade />
      <AbsoluteFill style={{alignItems: 'center', paddingTop: 250, color: C.cream, textAlign: 'center'}}>
        <div style={{transform: `scale(${0.7 + 0.3 * pop})`}}>
          <div style={{fontFamily: SERIF, fontWeight: 800, fontSize: 120, lineHeight: 1, textShadow: '0 6px 30px rgba(0,0,0,0.6)'}}>
            Full recipe
            <br />
            in the caption
          </div>
          <div
            style={{
              display: 'inline-block',
              marginTop: 30,
              fontFamily: SANS,
              fontWeight: 800,
              fontSize: 52,
              color: C.choc,
              background: C.caramel,
              padding: '10px 30px',
              borderRadius: 999,
            }}
          >
            save it for later
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const Music: React.FC = () => {
  const {durationInFrames} = useVideoConfig();
  if (!getStaticFiles().some((f) => f.name === 'music.mp3')) {
    return null;
  }
  return (
    <Audio
      src={staticFile('music.mp3')}
      trimBefore={Math.round(MUSIC_START_SEC * FPS)}
      volume={(f) =>
        interpolate(f, [durationInFrames - 12, durationInFrames], [0.85, 0], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        })
      }
    />
  );
};

export const CookieShort: React.FC = () => (
  <AbsoluteFill style={{backgroundColor: C.choc}}>
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
