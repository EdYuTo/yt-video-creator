import React from 'react';
import {
  AbsoluteFill,
  Img,
  interpolate,
  OffthreadVideo,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {loadFont as loadSerif} from '@remotion/google-fonts/Fraunces';
import {loadFont as loadSans} from '@remotion/google-fonts/Nunito';
import {FPS, Shot} from './edit';

export const SERIF = loadSerif('normal', {weights: ['600', '800'], subsets: ['latin']}).fontFamily;
export const SANS = loadSans('normal', {weights: ['600', '800'], subsets: ['latin']}).fontFamily;

export const C = {
  cream: '#FFF4E6',
  choc: '#2E1B10',
  caramel: '#D9913F',
  ink: 'rgba(30, 17, 9, 0.82)',
};

const cover: React.CSSProperties = {width: '100%', height: '100%', objectFit: 'cover'};

export const ShotView: React.FC<{shot: Shot}> = ({shot}) => {
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
    return <AbsoluteFill>{video(cover)}</AbsoluteFill>;
  }
  return (
    <AbsoluteFill style={{backgroundColor: C.choc}}>
      <AbsoluteFill style={{filter: 'blur(40px) brightness(0.55)', transform: 'scale(1.15)'}}>
        {video(cover)}
      </AbsoluteFill>
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        {video({height: '100%', aspectRatio: '1 / 1', boxShadow: '0 20px 80px rgba(0,0,0,0.5)'})}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const KenBurns: React.FC<{src: string; dur: number; zoomIn?: boolean}> = ({src, dur, zoomIn = true}) => {
  const frame = useCurrentFrame();
  const p = frame / (dur * FPS);
  const s = zoomIn ? 1.05 + 0.1 * p : 1.15 - 0.1 * p;
  return (
    <AbsoluteFill style={{backgroundColor: C.choc}}>
      <AbsoluteFill style={{filter: 'blur(40px) brightness(0.5)', transform: 'scale(1.2)'}}>
        <Img src={staticFile(src)} style={cover} />
      </AbsoluteFill>
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        <Img src={staticFile(src)} style={{height: '100%', transform: `scale(${s})`}} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// Fade out over the last `frames` frames of a sequence of length `dur` seconds.
export const useInOut = (dur: number, delay = 0) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame: frame - delay, fps, config: {damping: 200}, durationInFrames: 18});
  const exit = interpolate(frame, [dur * fps - 10, dur * fps], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return {enter, opacity: Math.min(enter, exit)};
};

export const BottomShade: React.FC = () => (
  <AbsoluteFill
    style={{background: 'linear-gradient(to top, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0) 38%)'}}
  />
);

export const Caption: React.FC<{step?: number; title: string; sub?: string; dur: number}> = ({
  step,
  title,
  sub,
  dur,
}) => {
  const {enter, opacity} = useInOut(dur, 4);
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', padding: '0 0 80px 96px', opacity}}>
      <div style={{transform: `translateY(${(1 - enter) * 40}px)`}}>
        {step !== undefined && (
          <div
            style={{
              display: 'inline-block',
              fontFamily: SANS,
              fontWeight: 800,
              fontSize: 26,
              letterSpacing: 4,
              color: C.choc,
              background: C.caramel,
              padding: '6px 16px',
              borderRadius: 999,
              marginBottom: 14,
            }}
          >
            STEP {step}
          </div>
        )}
        <div
          style={{
            fontFamily: SERIF,
            fontWeight: 800,
            fontSize: 84,
            lineHeight: 1.05,
            color: C.cream,
            textShadow: '0 4px 24px rgba(0,0,0,0.5)',
          }}
        >
          {title}
        </div>
        {sub && (
          <div
            style={{
              fontFamily: SANS,
              fontWeight: 600,
              fontSize: 38,
              color: C.cream,
              opacity: 0.92,
              marginTop: 10,
              textShadow: '0 2px 12px rgba(0,0,0,0.6)',
            }}
          >
            {sub}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};

export const AmountChip: React.FC<{amount: string; item: string; dur: number}> = ({amount, item, dur}) => {
  const {enter, opacity} = useInOut(dur, 6);
  return (
    <AbsoluteFill style={{alignItems: 'flex-end', padding: '72px 96px 0 0', opacity}}>
      <div
        style={{
          transform: `scale(${0.85 + 0.15 * enter})`,
          transformOrigin: 'top right',
          background: C.cream,
          color: C.choc,
          borderRadius: 28,
          padding: '18px 34px',
          textAlign: 'right',
          boxShadow: '0 12px 40px rgba(0,0,0,0.35)',
        }}
      >
        <div style={{fontFamily: SERIF, fontWeight: 800, fontSize: 72, lineHeight: 1}}>{amount}</div>
        <div style={{fontFamily: SANS, fontWeight: 800, fontSize: 30, color: C.caramel}}>{item}</div>
      </div>
    </AbsoluteFill>
  );
};

export const BakeTimer: React.FC<{dur: number}> = ({dur}) => {
  const frame = useCurrentFrame();
  const {opacity} = useInOut(dur, 6);
  // Timer runs across the whole bake section and lands on 22 min.
  const minutes = interpolate(frame, [FPS * 2, dur * FPS - FPS], [0, 22], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const r = 92;
  const circ = 2 * Math.PI * r;
  return (
    <AbsoluteFill style={{alignItems: 'flex-end', padding: '64px 96px 0 0', opacity}}>
      <div style={{position: 'relative', width: 240, height: 240}}>
        <svg width={240} height={240} style={{position: 'absolute'}}>
          <circle cx={120} cy={120} r={110} fill={C.ink} />
          <circle cx={120} cy={120} r={r} fill="none" stroke="rgba(255,244,230,0.2)" strokeWidth={12} />
          <circle
            cx={120}
            cy={120}
            r={r}
            fill="none"
            stroke={C.caramel}
            strokeWidth={12}
            strokeLinecap="round"
            strokeDasharray={circ}
            strokeDashoffset={circ * (1 - minutes / 25)}
            transform="rotate(-90 120 120)"
          />
        </svg>
        <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', color: C.cream}}>
          <div style={{fontFamily: SERIF, fontWeight: 800, fontSize: 64, lineHeight: 1}}>
            {Math.floor(minutes)}:00
          </div>
          <div style={{fontFamily: SANS, fontWeight: 800, fontSize: 26, color: C.caramel, marginTop: 6}}>
            200 °C
          </div>
        </AbsoluteFill>
      </div>
    </AbsoluteFill>
  );
};
