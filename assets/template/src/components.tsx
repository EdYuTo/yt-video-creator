import React from 'react';
import {
  AbsoluteFill,
  Img,
  interpolate,
  OffthreadVideo,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {BODY, C, DISPLAY} from './theme';
import type {CounterSpec, Shot, Sub} from './types';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const cover: React.CSSProperties = {width: '100%', height: '100%', objectFit: 'cover'};

// Still photo with slow zoom, over a blurred copy so any aspect ratio works. `fill` crops instead.
export const PhotoView: React.FC<{src: string; len: number; zoomIn?: boolean; fill?: boolean}> = ({src, len, zoomIn = true, fill}) => {
  const frame = useCurrentFrame();
  const p = frame / Math.max(1, len);
  const s = zoomIn ? 1.04 + 0.08 * p : 1.12 - 0.08 * p;
  return (
    <AbsoluteFill style={{backgroundColor: C.dark}}>
      <AbsoluteFill style={{filter: 'blur(45px) brightness(0.5)', transform: 'scale(1.2)'}}>
        <Img src={staticFile(src)} style={cover} />
      </AbsoluteFill>
      <Img src={staticFile(src)} style={{...cover, objectFit: fill ? 'cover' : 'contain', transform: `scale(${s})`}} />
    </AbsoluteFill>
  );
};

// One shot: video (optionally with source audio) or photo; crop focus, letterbox, privacy blur, grayscale.
export const ShotView: React.FC<{shot: Shot; gray?: boolean; index?: number}> = ({shot, gray, index = 0}) => {
  const {fps} = useVideoConfig();
  const n = shot.len;
  const filter = gray ? 'grayscale(1) contrast(1.08)' : undefined;
  if (shot.photo) {
    return (
      <AbsoluteFill style={{filter}}>
        <PhotoView src={shot.photo} len={n} zoomIn={index % 2 === 0} fill={shot.fit === 'cover'} />
      </AbsoluteFill>
    );
  }
  const vol = shot.vol ?? 0;
  const video = (style: React.CSSProperties, withAudio: boolean) => (
    <OffthreadVideo
      src={staticFile(shot.src!)}
      trimBefore={Math.round((shot.from ?? 0) * fps)}
      playbackRate={shot.speed ?? 1}
      muted={!withAudio || vol === 0}
      // 2-frame ramps at every cut: jump cuts in speech click otherwise
      volume={(f) => interpolate(f, [0, 2, n - 2, n], [0, vol, vol, 0], clamp)}
      style={style}
    />
  );
  if (shot.fit === 'blur') {
    return (
      <AbsoluteFill style={{filter, backgroundColor: C.dark}}>
        <AbsoluteFill style={{filter: 'blur(45px) brightness(0.5)', transform: 'scale(1.2)'}}>{video(cover, false)}</AbsoluteFill>
        {video({...cover, objectFit: 'contain', filter: 'drop-shadow(0 20px 60px rgba(0,0,0,0.5))'}, true)}
      </AbsoluteFill>
    );
  }
  const framed = {...cover, objectPosition: `${shot.x ?? 50}% ${shot.y ?? 50}%`};
  return (
    <AbsoluteFill style={{filter}}>
      {video(framed, true)}
      {/* Privacy: a heavily blurred copy of the same frame, clipped to each box */}
      {(shot.blur ?? []).map(([x, y, w, h], i) => (
        <AbsoluteFill key={i} style={{clipPath: `inset(${y}% ${100 - x - w}% ${100 - y - h}% ${x}%)`}}>
          <AbsoluteFill style={{filter: 'blur(38px)', transform: 'scale(1.06)'}}>{video(framed, false)}</AbsoluteFill>
        </AbsoluteFill>
      ))}
    </AbsoluteFill>
  );
};

// Spring in at `delay`, fade out over the last 10 frames of a `len`-frame sequence.
export const useInOut = (len: number, delay = 0) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame: frame - delay, fps, config: {damping: 200}, durationInFrames: 18});
  const exit = interpolate(frame, [len - 10, len], [1, 0], clamp);
  return {enter, opacity: Math.min(enter, exit)};
};

export const Shade: React.FC<{from: 'top' | 'bottom'}> = ({from}) => (
  <AbsoluteFill
    style={{background: `linear-gradient(to ${from === 'bottom' ? 'top' : 'bottom'}, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0) 40%)`}}
  />
);

export const FadeBlack: React.FC<{len: number; out?: boolean}> = ({len, out}) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [0, len], out ? [0, 1] : [1, 0], clamp);
  return <AbsoluteFill style={{backgroundColor: 'black', opacity: o}} />;
};

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

// Section caption. 'bottom' = lower-left (music-driven videos); 'top' = upper-left, because
// subtitles own the bottom of the frame in talk videos. Top captions leave after ~4.5 s.
export const Caption: React.FC<{step?: number; title: string; sub?: string; len: number; pos: 'top' | 'bottom'}> = ({
  step,
  title,
  sub,
  len,
  pos,
}) => {
  const {enter, opacity} = useInOut(len, 4);
  const top = pos === 'top';
  return (
    <AbsoluteFill
      style={{justifyContent: top ? 'flex-start' : 'flex-end', padding: top ? '64px 0 0 88px' : '0 0 80px 96px', opacity}}
    >
      <div style={{transform: top ? `translateX(${(1 - enter) * -40}px)` : `translateY(${(1 - enter) * 40}px)`}}>
        {step !== undefined && (
          <Pill size={26} style={{letterSpacing: 4, marginBottom: 14}}>
            STEP {step}
          </Pill>
        )}
        <div style={{fontFamily: DISPLAY, fontWeight: 800, fontSize: top ? 76 : 84, lineHeight: 1.05, color: C.light, textShadow: '0 4px 24px rgba(0,0,0,0.55)'}}>
          {title}
        </div>
        {sub &&
          (top ? (
            <Pill size={30} style={{marginTop: 14}}>
              {sub}
            </Pill>
          ) : (
            <div style={{fontFamily: BODY, fontWeight: 600, fontSize: 38, color: C.light, opacity: 0.92, marginTop: 10, textShadow: '0 2px 12px rgba(0,0,0,0.6)'}}>
              {sub}
            </div>
          ))}
      </div>
    </AbsoluteFill>
  );
};

const Subtitle: React.FC<{text: string; len: number; bottom: number}> = ({text, len, bottom}) => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [0, 3, len - 3, len], [0, 1, 1, 0], clamp);
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: bottom, opacity: o}}>
      <div
        style={{
          maxWidth: '75%',
          textAlign: 'center',
          fontFamily: BODY,
          fontWeight: 800,
          fontSize: 44,
          lineHeight: 1.25,
          color: '#fff',
          background: 'rgba(0,0,0,0.55)',
          padding: '10px 26px',
          borderRadius: 14,
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};

// Subtitles of one shot, placed on the absolute timeline.
export const ShotSubs: React.FC<{shot: Shot; bottom?: number}> = ({shot, bottom = 64}) => (
  <>
    {(shot.subs ?? []).map((s: Sub, i) =>
      s.len > 3 ? (
        <Sequence key={i} from={shot.start + s.from} durationInFrames={s.len} layout="none">
          <Subtitle text={s.text} len={s.len} bottom={bottom} />
        </Sequence>
      ) : null,
    )}
  </>
);

// Top-right spec card for one shot ("225 g" / "butter").
export const Chip: React.FC<{big: string; small: string; len: number}> = ({big, small, len}) => {
  const {enter, opacity} = useInOut(len, 6);
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

const fmt = (v: number, f: CounterSpec['format']) =>
  f === 'min' ? `${Math.floor(v)}:00` : f === 'dec1' ? v.toFixed(1) : `${Math.round(v)}`;

// Top-right ring counting across a section (oven timer, km, hours...).
export const Counter: React.FC<{spec: CounterSpec; len: number}> = ({spec, len}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const {opacity} = useInOut(len, 6);
  const v = interpolate(frame, [fps * 1.5, len - fps], [spec.from, spec.to], clamp);
  const r = 92;
  const circ = 2 * Math.PI * r;
  const frac = (v - spec.from) / ((spec.max ?? spec.to) - spec.from || 1);
  return (
    <AbsoluteFill style={{alignItems: 'flex-end', padding: '64px 96px 0 0', opacity}}>
      <div style={{position: 'relative', width: 240, height: 240}}>
        <svg width={240} height={240} style={{position: 'absolute'}}>
          <circle cx={120} cy={120} r={110} fill={C.panel} />
          <circle cx={120} cy={120} r={r} fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth={12} />
          <circle cx={120} cy={120} r={r} fill="none" stroke={C.accent} strokeWidth={12} strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={circ * (1 - frac)} transform="rotate(-90 120 120)" />
        </svg>
        <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', color: C.light}}>
          <div style={{fontFamily: DISPLAY, fontWeight: 800, fontSize: 60, lineHeight: 1}}>{fmt(v, spec.format)}</div>
          <div style={{fontFamily: BODY, fontWeight: 800, fontSize: 26, color: C.accent, marginTop: 6}}>{spec.label}</div>
        </AbsoluteFill>
      </div>
    </AbsoluteFill>
  );
};
