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
import {BODY, C, DISPLAY, FPS} from './theme';

export type Shot = {
  src: string; // path under public/, e.g. 'footage/MVI_0576.mov'
  from: number; // source in-point, seconds
  speed?: number; // playback rate (timelapse = 4-30x)
  // 'cover' fills the frame (cropping), 'blur' letterboxes the whole shot over a blurred copy —
  // use 'blur' when the source aspect differs a lot from the output (phone clip in 16:9, etc.).
  fit?: 'cover' | 'blur';
  x?: number; // horizontal crop focus in % for 'cover' (0 = left, 100 = right). Key for 9:16.
  y?: number; // vertical crop focus in %
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
  if (shot.fit !== 'blur') {
    return <AbsoluteFill>{video({...cover, objectPosition: `${shot.x ?? 50}% ${shot.y ?? 50}%`})}</AbsoluteFill>;
  }
  return (
    <AbsoluteFill style={{backgroundColor: C.dark}}>
      <AbsoluteFill style={{filter: 'blur(45px) brightness(0.5)', transform: 'scale(1.2)'}}>{video(cover)}</AbsoluteFill>
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        {video({width: '100%', height: '100%', objectFit: 'contain', filter: 'drop-shadow(0 20px 60px rgba(0,0,0,0.5))'})}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// Still photo with slow zoom, letterboxed over a blurred copy so any aspect ratio works.
export const PhotoView: React.FC<{src: string; sec: number; zoomIn?: boolean; fill?: boolean}> = ({
  src,
  sec,
  zoomIn = true,
  fill = false,
}) => {
  const frame = useCurrentFrame();
  const p = frame / (sec * FPS);
  const s = zoomIn ? 1.04 + 0.08 * p : 1.12 - 0.08 * p;
  return (
    <AbsoluteFill style={{backgroundColor: C.dark}}>
      <AbsoluteFill style={{filter: 'blur(45px) brightness(0.5)', transform: 'scale(1.2)'}}>
        <Img src={staticFile(src)} style={cover} />
      </AbsoluteFill>
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        <Img
          src={staticFile(src)}
          style={{...cover, objectFit: fill ? 'cover' : 'contain', transform: `scale(${s})`}}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// Spring in at `delay`, fade out over the last 10 frames of a `sec`-long sequence.
export const useInOut = (sec: number, delay = 0) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame: frame - delay, fps, config: {damping: 200}, durationInFrames: 18});
  const exit = interpolate(frame, [sec * fps - 10, sec * fps], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return {enter, opacity: Math.min(enter, exit)};
};

export const Shade: React.FC<{from: 'top' | 'bottom'}> = ({from}) => (
  <AbsoluteFill
    style={{background: `linear-gradient(to ${from === 'bottom' ? 'top' : 'bottom'}, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0) 40%)`}}
  />
);

export const Pill: React.FC<{children: React.ReactNode; size: number; style?: React.CSSProperties}> = ({children, size, style}) => (
  <div
    style={{
      display: 'inline-block',
      fontFamily: BODY,
      fontWeight: 800,
      fontSize: size,
      color: C.dark,
      background: C.accent,
      padding: `${size * 0.2}px ${size * 0.6}px`,
      borderRadius: 999,
      ...style,
    }}
  >
    {children}
  </div>
);

// Lower-left caption for 16:9: optional "STEP n" pill, headline, subline.
export const Caption: React.FC<{step?: number; title: string; sub?: string; sec: number}> = ({step, title, sub, sec}) => {
  const {enter, opacity} = useInOut(sec, 4);
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', padding: '0 0 80px 96px', opacity}}>
      <div style={{transform: `translateY(${(1 - enter) * 40}px)`}}>
        {step !== undefined && (
          <Pill size={26} style={{letterSpacing: 4, marginBottom: 14}}>
            STEP {step}
          </Pill>
        )}
        <div style={{fontFamily: DISPLAY, fontWeight: 800, fontSize: 84, lineHeight: 1.05, color: C.light, textShadow: '0 4px 24px rgba(0,0,0,0.5)'}}>
          {title}
        </div>
        {sub && (
          <div style={{fontFamily: BODY, fontWeight: 600, fontSize: 38, color: C.light, opacity: 0.92, marginTop: 10, textShadow: '0 2px 12px rgba(0,0,0,0.6)'}}>
            {sub}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};

// Top-right card for a quantity/spec shown during one shot ("225 g" / "butter").
export const Chip: React.FC<{big: string; small: string; sec: number}> = ({big, small, sec}) => {
  const {enter, opacity} = useInOut(sec, 6);
  return (
    <AbsoluteFill style={{alignItems: 'flex-end', padding: '72px 96px 0 0', opacity}}>
      <div
        style={{
          transform: `scale(${0.85 + 0.15 * enter})`,
          transformOrigin: 'top right',
          background: C.light,
          color: C.dark,
          borderRadius: 28,
          padding: '18px 34px',
          textAlign: 'right',
          boxShadow: '0 12px 40px rgba(0,0,0,0.35)',
        }}
      >
        <div style={{fontFamily: DISPLAY, fontWeight: 800, fontSize: 72, lineHeight: 1}}>{big}</div>
        <div style={{fontFamily: BODY, fontWeight: 800, fontSize: 30, color: C.accent}}>{small}</div>
      </div>
    </AbsoluteFill>
  );
};

export type CounterSpec = {from: number; to: number; format: (v: number) => string; label: string; max?: number};

// Top-right ring that counts across a section (oven timer, km driven, hours elapsed...).
export const Counter: React.FC<{spec: CounterSpec; sec: number}> = ({spec, sec}) => {
  const frame = useCurrentFrame();
  const {opacity} = useInOut(sec, 6);
  const v = interpolate(frame, [FPS * 1.5, sec * FPS - FPS], [spec.from, spec.to], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const r = 92;
  const circ = 2 * Math.PI * r;
  const frac = (v - spec.from) / ((spec.max ?? spec.to) - spec.from || 1);
  return (
    <AbsoluteFill style={{alignItems: 'flex-end', padding: '64px 96px 0 0', opacity}}>
      <div style={{position: 'relative', width: 240, height: 240}}>
        <svg width={240} height={240} style={{position: 'absolute'}}>
          <circle cx={120} cy={120} r={110} fill={C.panel} />
          <circle cx={120} cy={120} r={r} fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth={12} />
          <circle
            cx={120}
            cy={120}
            r={r}
            fill="none"
            stroke={C.accent}
            strokeWidth={12}
            strokeLinecap="round"
            strokeDasharray={circ}
            strokeDashoffset={circ * (1 - frac)}
            transform="rotate(-90 120 120)"
          />
        </svg>
        <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', color: C.light}}>
          <div style={{fontFamily: DISPLAY, fontWeight: 800, fontSize: 60, lineHeight: 1}}>{spec.format(v)}</div>
          <div style={{fontFamily: BODY, fontWeight: 800, fontSize: 26, color: C.accent, marginTop: 6}}>{spec.label}</div>
        </AbsoluteFill>
      </div>
    </AbsoluteFill>
  );
};
