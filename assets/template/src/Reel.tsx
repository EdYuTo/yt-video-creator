import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Easing,
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
import {ShotView} from './components';
import {cropTransform, headBox, lerpRect} from './reelGeometry';
import {BODY, C, DISPLAY, HAND} from './theme';
import type {Ann, Demo, Head, ReelData, Shot, Sub} from './types';

// 1080x1920 talking-head reel: one flat shot list (silence-cut speech), big subtitles clear of the
// platform UI, and annotations drawn into the empty space the speaker leaves beside them.
// Layout is precomputed by build_edit.py; this file only draws it.
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const W = 1080;
const H = 1920;
const pct = (v: number, total: number) => (v / 100) * total;

// Instagram/TikTok cover the bottom ~25% (caption, handle, audio ticker) and the right ~12%.
const SAFE_BOTTOM = 300;

// ---------------------------------------------------------------- transitions
// In-place entry effects: no sequence overlap, so cut speech audio stays aligned to the picture.
const Transition: React.FC<{kind: Shot['trans']; children: React.ReactNode}> = ({kind, children}) => {
  const frame = useCurrentFrame();
  if (!kind || kind === 'cut') return <>{children}</>;
  const n = kind === 'whip' ? 7 : 9;
  const p = interpolate(frame, [0, n], [0, 1], clamp);
  if (kind === 'fade') {
    return <AbsoluteFill style={{opacity: p}}>{children}</AbsoluteFill>;
  }
  if (kind === 'zoom') {
    return <AbsoluteFill style={{opacity: Math.min(1, p * 2), transform: `scale(${1.14 - 0.14 * p})`}}>{children}</AbsoluteFill>;
  }
  // whip: a short horizontal smear, as if the camera snapped across to the next idea
  return (
    <AbsoluteFill style={{opacity: Math.min(1, p * 2.5), transform: `translateX(${(1 - p) * 140}px)`, filter: `blur(${(1 - p) * 18}px)`}}>
      {children}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- demo picture + head bubble (v2)
// The demo replaces the speaker's own picture; it is always muted (the voice is a separate <Audio>).
const DemoView: React.FC<{demo: Demo; len: number}> = ({demo, len}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (demo.kind === 'card') {
    return <AbsoluteFill style={{background: `linear-gradient(${C.dark} 0%, ${C.panel} 100%)`}} />;
  }
  if (demo.kind === 'still') {
    return (
      <AbsoluteFill style={{backgroundColor: '#111'}}>
        <Img src={staticFile(demo.photo)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      </AbsoluteFill>
    );
  }
  if (demo.kind === 'video') {
    // same framing as a v1 shot (x/y/zoom over objectFit cover); no vol = muted
    return <ShotView shot={{start: 0, len, src: demo.src, from: demo.from, speed: demo.speed, x: demo.x, y: demo.y, zoom: demo.zoom}} />;
  }
  // crop: the source rect fills the width, centred at cy; build_edit splits the line's rect -> rectTo
  // motion across its shots, so each shot moves its own slice of it
  const r = demo.rectTo ? lerpRect(demo.rect, demo.rectTo, frame / Math.max(1, len)) : demo.rect;
  const {scale, left, top} = cropTransform(r, demo.srcW, demo.srcH, W, H, demo.cy);
  return (
    <AbsoluteFill style={{backgroundColor: '#111', overflow: 'hidden'}}>
      <OffthreadVideo
        src={staticFile(demo.src)}
        trimBefore={Math.round(demo.from * fps)}
        muted
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: demo.srcW,
          height: demo.srcH,
          maxWidth: 'none',
          transformOrigin: '0 0',
          transform: `translate(${left}px, ${top}px) scale(${scale})`,
        }}
      />
    </AbsoluteFill>
  );
};

// The bubble video is d x 1.3d with its circle at the bottom: circle centre (cx, cy) => top = cy - 0.8d.
const HeadBubble: React.FC<{head: Head}> = ({head}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const a = headBox(head.prevPos ?? head.pos);
  const b = headBox(head.pos);
  const p = interpolate(frame, [0, 10], [0, 1], {...clamp, easing: Easing.inOut(Easing.cubic)});
  const cx = a.cx + (b.cx - a.cx) * p;
  const cy = a.cy + (b.cy - a.cy) * p;
  const d = a.d + (b.d - a.d) * p;
  return (
    <OffthreadVideo
      src={staticFile(head.src)}
      trimBefore={Math.round(head.from * fps)}
      transparent
      muted
      style={{
        position: 'absolute',
        left: cx - d / 2,
        top: cy - 0.8 * d,
        width: d,
        height: 1.3 * d,
        filter: 'drop-shadow(0 14px 30px rgba(0,0,0,.45))',
      }}
    />
  );
};

// The speaker's voice for a demo shot, with the same 2-frame ramps ShotView puts on every cut.
const Voice: React.FC<{shot: Shot}> = ({shot}) => {
  const {fps} = useVideoConfig();
  const n = shot.len;
  const vol = shot.vol ?? 0;
  if (!shot.src || vol === 0) return null;
  return (
    <Audio
      src={staticFile(shot.src)}
      trimBefore={Math.round((shot.from ?? 0) * fps)}
      playbackRate={shot.speed ?? 1}
      volume={(f) => interpolate(f, [0, 2, n - 2, n], [0, vol, vol, 0], clamp)}
    />
  );
};

// ---------------------------------------------------------------- annotations
// Everything "drawn" uses an SVG stroke whose dash offset animates, so it reads as being written
// on screen rather than popping in.
const draw = (frame: number, dur: number, len: number) => ({
  strokeDasharray: len,
  strokeDashoffset: interpolate(frame, [0, dur], [len, 0], clamp),
});

const Hand: React.FC<{children: React.ReactNode; size: number; color: string; style?: React.CSSProperties}> = ({
  children,
  size,
  color,
  style,
}) => (
  <div
    style={{
      fontFamily: HAND,
      fontWeight: 700,
      fontSize: size,
      lineHeight: 1.12,
      color,
      textShadow: '0 3px 18px rgba(0,0,0,0.45)',
      whiteSpace: 'pre-line',
      ...style,
    }}
  >
    {children}
  </div>
);

const AnnView: React.FC<{ann: Ann}> = ({ann}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const color = ann.color ?? C.accent;
  const n = ann.len;
  // noOutro: the next annotation continues this one (see noIntro), so don't fade the card out between them
  const out = ann.noOutro ? 1 : interpolate(frame, [n - 8, n], [1, 0], clamp);
  const k = ann.size ?? 1; // scales text and cards (ring/arrow: the stroke); big centred anns on card-only reels
  const pop = spring({frame, fps, config: {damping: 14, stiffness: 180}, durationInFrames: 12});
  const left = pct(ann.x, W);
  const top = pct(ann.y, H);
  const width = ann.w ? pct(ann.w, W) : undefined;
  const tilt = ann.rotate ?? 0;

  if (ann.kind === 'ring' || ann.kind === 'arrow') {
    // Both are free-floating strokes over the whole canvas.
    const dur = 14;
    if (ann.kind === 'ring') {
      const rx = pct(ann.w ?? 26, W) / 2;
      const ry = rx * 0.52;
      const circ = Math.PI * 2 * Math.sqrt((rx * rx + ry * ry) / 2);
      return (
        <AbsoluteFill style={{opacity: out}}>
          <svg width={W} height={H} style={{position: 'absolute'}}>
            <ellipse
              cx={left}
              cy={top}
              rx={rx}
              ry={ry}
              fill="none"
              stroke={color}
              strokeWidth={9 * k}
              strokeLinecap="round"
              transform={`rotate(${tilt || -4} ${left} ${top})`}
              style={draw(frame, dur, circ)}
            />
          </svg>
        </AbsoluteFill>
      );
    }
    const [tx, ty] = ann.to ?? [ann.x, ann.y + 10];
    const ex = pct(tx, W);
    const ey = pct(ty, H);
    const cx = (left + ex) / 2 + (ey - top) * 0.22;
    const cy = (top + ey) / 2 - (ex - left) * 0.22;
    const path = `M ${left} ${top} Q ${cx} ${cy} ${ex} ${ey}`;
    const seg = Math.hypot(ex - left, ey - top) * 1.25;
    const ang = Math.atan2(ey - cy, ex - cx);
    const head = 26 * k;
    return (
      <AbsoluteFill style={{opacity: out}}>
        <svg width={W} height={H} style={{position: 'absolute'}}>
          <path d={path} fill="none" stroke={color} strokeWidth={9 * k} strokeLinecap="round" style={draw(frame, dur, seg)} />
          <g opacity={interpolate(frame, [dur - 2, dur + 4], [0, 1], clamp)}>
            <path
              d={`M ${ex} ${ey} L ${ex - head * Math.cos(ang - 0.42)} ${ey - head * Math.sin(ang - 0.42)}
                  M ${ex} ${ey} L ${ex - head * Math.cos(ang + 0.42)} ${ey - head * Math.sin(ang + 0.42)}`}
              stroke={color}
              strokeWidth={9 * k}
              strokeLinecap="round"
              fill="none"
            />
          </g>
        </svg>
      </AbsoluteFill>
    );
  }

  const block: React.CSSProperties = {
    position: 'absolute',
    left,
    top,
    width,
    opacity: out,
    // size scales the block from its anchor (top-left); unscaled blocks keep the default centre pivot
    transform: k === 1 ? `rotate(${tilt}deg)` : `rotate(${tilt}deg) scale(${k})`,
    ...(k === 1 ? {} : {transformOrigin: 'left top'}),
  };
  // Annotations land on whatever is on screen — including white documentation pages, where cream
  // text on its own is invisible. Every block carries its own card so it reads anywhere.
  const card: React.CSSProperties = {
    background: 'rgba(18, 10, 5, 0.72)',
    borderRadius: 20,
    padding: '18px 26px 14px',
    boxShadow: '0 14px 44px rgba(0,0,0,0.42)',
  };

  if (ann.kind === 'label') {
    return (
      <AbsoluteFill>
        <div style={{...block, transform: `rotate(${tilt}deg) scale(${k * (0.7 + 0.3 * pop)})`, transformOrigin: 'left top'}}>
          <div
            style={{
              display: 'inline-block',
              fontFamily: BODY,
              fontWeight: 800,
              fontSize: 46,
              color: C.dark,
              background: color,
              padding: '14px 30px',
              borderRadius: 18,
              boxShadow: '0 10px 34px rgba(0,0,0,0.3)',
            }}
          >
            {ann.text}
          </div>
        </div>
      </AbsoluteFill>
    );
  }

  if (ann.kind === 'note') {
    // Handwritten line with a marker underline that wipes in beneath it.
    const uw = width ?? 380;
    return (
      <AbsoluteFill>
        <div style={{...block, ...card, width: 'fit-content', maxWidth: width}}>
          <Hand size={ann.text && ann.text.length > 26 ? 60 : 72} color={C.light}>
            {ann.text}
          </Hand>
          <svg width={uw} height={26} style={{display: 'block', marginTop: 2}}>
            <path
              d={`M 4 16 Q ${uw * 0.4} 4 ${uw - 6} 14`}
              fill="none"
              stroke={color}
              strokeWidth={8}
              strokeLinecap="round"
              style={draw(frame, 12, uw)}
            />
          </svg>
        </div>
      </AbsoluteFill>
    );
  }

  if (ann.kind === 'bar') {
    const rows = ann.bars ?? [];
    const bw = width ?? pct(40, W);
    return (
      <AbsoluteFill>
        <div style={{...block, ...card, width: 'fit-content'}}>
          {rows.map(([label, frac], i) => {
            const d = spring({frame: frame - i * 6, fps, config: {damping: 200}, durationInFrames: 16});
            return (
              <div key={i} style={{marginBottom: 20, opacity: Math.min(1, d * 1.6)}}>
                <Hand size={46} color={C.light} style={{marginBottom: 4}}>
                  {label}
                </Hand>
                <div style={{width: bw, height: 20, borderRadius: 999, background: 'rgba(255,255,255,0.22)'}}>
                  <div style={{width: bw * frac * d, height: 20, borderRadius: 999, background: color}} />
                </div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    );
  }

  // list: rows ticked off one at a time, each with a hand-drawn check. noIntro (set by build_edit when this
  // list continues the previous one with the same rows) = everything already drawn on the first frame.
  const items = ann.items ?? [];
  return (
    <AbsoluteFill>
      <div style={{...block, ...card, width: 'fit-content', maxWidth: width, paddingBottom: 4}}>
        {items.map((raw, i) => {
          const hot = raw.startsWith('*');
          const text = hot ? raw.slice(1) : raw;
          const d = ann.noIntro ? 1 : spring({frame: frame - i * 7, fps, config: {damping: 200}, durationInFrames: 14});
          const f2 = ann.noIntro ? 10 : frame - i * 7;
          return (
            <div
              key={i}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 16,
                marginBottom: 16,
                opacity: Math.min(1, d * 1.8),
                transform: `translateX(${(1 - d) * -22}px)`,
              }}
            >
              <svg width={42} height={42} style={{flexShrink: 0, marginTop: 10}}>
                <path
                  d="M 6 22 L 17 33 L 37 8"
                  fill="none"
                  stroke={hot ? color : 'rgba(255,255,255,0.75)'}
                  strokeWidth={7}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  style={draw(f2, 10, 60)}
                />
              </svg>
              <Hand size={54} color={hot ? color : C.light}>
                {text}
              </Hand>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- subtitles
const ReelSub: React.FC<{text: string; len: number}> = ({text, len}) => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [0, 3, len - 3, len], [0, 1, 1, 0], clamp);
  const rise = interpolate(frame, [0, 6], [12, 0], clamp);
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: SAFE_BOTTOM, opacity: o}}>
      <div
        style={{
          maxWidth: '86%',
          textAlign: 'center',
          fontFamily: BODY,
          fontWeight: 800,
          fontSize: 60,
          lineHeight: 1.22,
          color: '#fff',
          background: 'rgba(0,0,0,0.6)',
          padding: '16px 32px',
          borderRadius: 20,
          transform: `translateY(${rise}px)`,
          textShadow: '0 2px 10px rgba(0,0,0,0.5)',
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- cards
// `top`: text in the band above the big head bubble (top 150 px, two lines end by ≈520 px), so the
// hook never covers the face; otherwise centred as in v1.
const Card: React.FC<{big: string; small?: string; items?: string[]; len: number; solid?: boolean; top?: boolean}> = ({
  big,
  small,
  items,
  len,
  solid,
  top,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame, fps, config: {damping: 13, stiffness: 170}, durationInFrames: 16});
  const smallIn = spring({frame: frame - 5, fps, config: {damping: 200}, durationInFrames: 12});
  const out = interpolate(frame, [len - 7, len], [1, 0], clamp);
  return (
    <AbsoluteFill
      style={{
        alignItems: 'center',
        justifyContent: top ? 'flex-start' : 'center',
        ...(top ? {paddingTop: 150} : {paddingBottom: 180}),
        opacity: out,
        background: solid
          ? C.dark
          : top
            ? 'linear-gradient(to bottom, rgba(0,0,0,0.72) 0%, rgba(0,0,0,0.62) 25%, rgba(0,0,0,0) 37%)'
            : 'linear-gradient(to bottom, rgba(0,0,0,0.62) 0%, rgba(0,0,0,0.18) 55%, rgba(0,0,0,0.62) 100%)',
      }}
    >
      <div style={{textAlign: 'center', maxWidth: 940, padding: '0 50px'}}>
        <div
          style={{
            fontFamily: DISPLAY,
            fontWeight: 800,
            fontSize: top ? 100 : 118,
            lineHeight: 1.02,
            color: C.light,
            whiteSpace: 'pre-line',
            transform: `scale(${0.72 + 0.28 * pop})`,
            textShadow: '0 8px 36px rgba(0,0,0,0.6)',
          }}
        >
          {big}
        </div>
        {small && (
          <div
            style={{
              fontFamily: HAND,
              fontWeight: 700,
              fontSize: top ? 56 : 64,
              color: C.accent,
              marginTop: top ? 16 : 28,
              opacity: smallIn,
              transform: `translateY(${(1 - smallIn) * 18}px)`,
            }}
          >
            {small}
          </div>
        )}
        {items && (
          <div style={{marginTop: 44, textAlign: 'left', display: 'inline-block'}}>
            {items.map((it, i) => {
              const d = spring({frame: frame - 8 - i * 5, fps, config: {damping: 200}, durationInFrames: 12});
              return (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    gap: 18,
                    alignItems: 'baseline',
                    marginBottom: 14,
                    opacity: Math.min(1, d * 1.8),
                    transform: `translateX(${(1 - d) * -18}px)`,
                  }}
                >
                  <div style={{fontFamily: DISPLAY, fontWeight: 800, fontSize: 48, color: C.accent, minWidth: 54}}>{i + 1}</div>
                  <div style={{fontFamily: BODY, fontWeight: 800, fontSize: 52, color: C.light}}>{it}</div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};

// music level at an absolute frame: full volume, dipping to duckVolume under speech (10-frame ramps)
const duckLevel = (m: NonNullable<ReelData['music']>, t: number) => {
  let k = 0;
  for (const [a, b] of m.duck ?? []) {
    k = Math.max(k, interpolate(t, [a - 10, a, b, b + 10], [0, 1, 1, 0], clamp));
  }
  return m.volume + ((m.duckVolume ?? m.volume) - m.volume) * k;
};

// ---------------------------------------------------------------- the reel
export const ReelView: React.FC<{data: ReelData}> = ({data}) => {
  const D = data;
  const frame = useCurrentFrame();
  const hasMusic = D.music && getStaticFiles().some((s) => s.name === D.music!.file);
  const m = D.music;
  return (
    <AbsoluteFill style={{backgroundColor: C.dark}}>
      {D.shots.map((shot, i) => {
        const pic = shot.demo ? <DemoView demo={shot.demo} len={shot.len} /> : <ShotView shot={shot} index={i} />;
        return (
          <Sequence key={i} from={shot.start} durationInFrames={shot.len}>
            <Transition kind={shot.trans}>
              {shot.box ? (
                // 'board' layout: picture in a lower band, themed panel above for the annotations
                <AbsoluteFill style={{background: `linear-gradient(${C.dark} 0%, ${C.panel} 100%)`}}>
                  <div style={{position: 'absolute', top: `${shot.box}%`, left: 0, right: 0, bottom: 0, overflow: 'hidden'}}>
                    {pic}
                  </div>
                </AbsoluteFill>
              ) : (
                pic
              )}
            </Transition>
            {/* v2: the head floats outside the transition, so it stays put while the demo changes */}
            {shot.demo && shot.head && <HeadBubble head={shot.head} />}
            {shot.demo && <Voice shot={shot} />}
          </Sequence>
        );
      })}

      {/* annotations sit above the picture but below the subtitles */}
      {D.anns.map((ann, i) => (
        <Sequence key={`a${i}`} from={ann.start} durationInFrames={ann.len} layout="none">
          <AnnView ann={ann} />
        </Sequence>
      ))}

      {D.shots.flatMap((shot, si) =>
        (shot.subs ?? []).map((s: Sub, i) =>
          s.len > 3 ? (
            <Sequence key={`s${si}-${i}`} from={shot.start + s.from} durationInFrames={s.len} layout="none">
              <ReelSub text={s.text} len={s.len} />
            </Sequence>
          ) : null,
        ),
      )}

      {D.hook && (
        <Sequence from={D.hook.start} durationInFrames={D.hook.len} layout="none">
          <Card big={D.hook.big} small={D.hook.small} items={D.hook.items} len={D.hook.len} top={D.shots[0]?.head?.pos === 'big'} />
        </Sequence>
      )}
      {D.end && (
        <Sequence from={D.end.start} durationInFrames={D.end.len} layout="none">
          <Card big={D.end.big} small={D.end.small} items={D.end.items} len={D.end.len} solid />
        </Sequence>
      )}

      {/* thin progress bar: tells the viewer how much is left, which helps retention */}
      <AbsoluteFill style={{justifyContent: 'flex-start'}}>
        <div style={{height: 8, width: `${(frame / Math.max(1, D.total)) * 100}%`, background: C.accent, opacity: 0.9}} />
      </AbsoluteFill>

      {hasMusic &&
        m!.runs.map((run, i) => (
          <Sequence key={`m${i}`} from={run.start} durationInFrames={run.len}>
            <Audio
              src={staticFile(m!.file)}
              trimBefore={Math.round(run.songFrom * D.fps)}
              volume={(f) => {
                const fi = run.fadeIn ?? m!.fadeIn;
                const fo = run.fadeOut ?? m!.fadeOut;
                const env = interpolate(f, [0, fi, run.len - fo, run.len], [0, 1, 1, 0], clamp);
                return env * duckLevel(m!, run.start + f);
              }}
            />
          </Sequence>
        ))}
    </AbsoluteFill>
  );
};
