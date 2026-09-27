import React from 'react';
import {AbsoluteFill, Freeze, interpolate, OffthreadVideo, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {loadFont as loadAnton} from '@remotion/google-fonts/Anton';
import {loadFont as loadMont} from '@remotion/google-fonts/Montserrat';
import type {Cap, Fx, Layout, Rect, Seg, StreamShortData} from './types';

const ANTON = loadAnton('normal', {weights: ['400'], subsets: ['latin', 'latin-ext']}).fontFamily;
const MONT = loadMont('normal', {weights: ['900'], subsets: ['latin', 'latin-ext']}).fontFamily;

export const K = {
  accent: '#FFD21F', // key words, hook box
  hot: '#FF3B5C', // stickers
  ink: '#0B0B10',
  white: '#FFFFFF',
};

const W = 1080;
const H = 1920;
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// Height of the facecam panel per layout. 'game' has no panel; the cam becomes a bubble.
const CAM_H: Record<Layout, number> = {stack: 760, face: 1290, game: 0};
const EASE = 7; // frames for a layout change

const camHAt = (segs: Seg[], frame: number) => {
  let i = segs.findIndex((s) => frame >= s.start && frame < s.start + s.len);
  if (i < 0) i = frame < 0 ? 0 : segs.length - 1;
  const cur = CAM_H[segs[i].layout];
  if (i === 0) return cur;
  const prev = CAM_H[segs[i - 1].layout];
  const t = interpolate(frame - segs[i].start, [0, EASE], [0, 1], clamp);
  const e = 1 - Math.pow(1 - t, 3);
  return prev + (cur - prev) * e;
};

// Show source rect `r` (focus region) covering a W x h panel. Returns style for the <video>.
const coverStyle = (r: Rect, pw: number, ph: number, srcW: number, srcH: number): React.CSSProperties => {
  const [x, y, w, h] = r;
  const s = Math.max(pw / w, ph / h);
  const cx = x + w / 2;
  const cy = y + h / 2;
  const left = pw / 2 - cx * s;
  const top = ph / 2 - cy * s;
  return {position: 'absolute', width: srcW * s, height: srcH * s, left, top, maxWidth: 'none'};
};

// Game focus rect for a panel of aspect pw/ph: full height by default (tighter when the panel is wide),
// centred on gameX, clamped so it never slides into the facecam overlay (top-right of the source).
const gameRect = (d: StreamShortData, seg: Seg, pw: number, ph: number): Rect => {
  const aspect = pw / Math.max(1, ph);
  let h = d.srcH;
  let w = h * aspect;
  const maxW = d.cam[0] - 40; // keep left of the cam overlay
  if (w > maxW * 0.8) {
    // wide, short panel ('face' layout): zoom in instead of showing the whole width
    w = Math.min(w, maxW * 0.62);
    h = w / aspect;
  }
  // never slide right into the facecam overlay (top-right of the source)
  const cx = Math.min(Math.max((seg.gameX ?? 0.5) * d.srcW, w / 2), Math.min(d.srcW, d.cam[0] - 8) - w / 2);
  const cy = h >= d.srcH ? d.srcH / 2 : Math.min(d.srcH - h / 2, d.srcH * 0.56);
  return [cx - w / 2, cy - h / 2, w, h];
};

const camRect = (d: StreamShortData, pw: number, ph: number): Rect => {
  const [x, y, w, h] = d.cam;
  const aspect = pw / Math.max(1, ph);
  if (w / h > aspect) {
    const nw = h * aspect; // taller panel: trim the sides, keep the face centred
    return [x + (w - nw) / 2, y, nw, h];
  }
  const nh = w / aspect; // wider panel: trim top and bottom, biased to keep the face
  return [x, y + (h - nh) * 0.35, w, nh];
};

const Blurs: React.FC<{rects?: Rect[]; st: React.CSSProperties; srcW: number}> = ({rects, st, srcW}) => {
  if (!rects?.length) return null;
  const s = (st.width as number) / srcW;
  return (
    <>
      {rects.map(([x, y, w, h], i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: (st.left as number) + x * s,
            top: (st.top as number) + y * s,
            width: w * s,
            height: h * s,
            backdropFilter: 'blur(28px)',
            WebkitBackdropFilter: 'blur(28px)',
            background: 'rgba(20,20,24,0.35)',
          }}
        />
      ))}
    </>
  );
};

// One segment of source: cam panel + game panel (or full game + cam bubble).
const SegView: React.FC<{d: StreamShortData; seg: Seg; camH: number; zoom: number; shake: [number, number]}> = ({d, seg, camH, zoom, shake}) => {
  const {fps} = useVideoConfig();
  const n = seg.len;
  const trim = Math.round(seg.fromSec * fps);
  const vol = (fr: number) => interpolate(fr, [0, 2, n - 2, n], [0, 1, 1, 0], clamp);
  const gameH = H - camH;
  const gSt = coverStyle(gameRect(d, seg, W, gameH), W, gameH, d.srcW, d.srcH);
  const bubble = interpolate(camH, [0, 200], [1, 0], clamp);
  const panelCamH = Math.max(camH, 1);
  const cSt = coverStyle(camRect(d, W, panelCamH), W, panelCamH, d.srcW, d.srcH);
  const bw = 400;
  const bh = 300;
  const bSt = coverStyle(camRect(d, bw, bh), bw, bh, d.srcW, d.srcH);
  const video = (st: React.CSSProperties, audio: boolean) => (
    <OffthreadVideo src={staticFile(seg.src ?? d.src)} trimBefore={trim} playbackRate={seg.speed ?? 1} muted={!audio} volume={audio ? vol : 0} style={st} />
  );
  const tr = `translate(${shake[0]}px, ${shake[1]}px) scale(${zoom})`;
  return (
    <AbsoluteFill style={{backgroundColor: K.ink}}>
      {/* game panel */}
      <div style={{position: 'absolute', left: 0, top: camH, width: W, height: gameH, overflow: 'hidden'}}>
        <div style={{position: 'absolute', inset: 0, transform: tr, transformOrigin: '50% 45%'}}>
          <div style={{position: 'absolute', inset: 0, filter: seg.blurGame ? 'blur(26px) brightness(0.7)' : undefined, transform: seg.blurGame ? 'scale(1.08)' : undefined}}>
            {video(gSt, true)}
          </div>
          <Blurs rects={[...(d.gameBlur ?? []), ...(seg.blur ?? [])]} st={gSt} srcW={d.srcW} />
        </div>
      </div>
      {/* cam panel */}
      {camH > 2 && (
        <div style={{position: 'absolute', left: 0, top: 0, width: W, height: camH, overflow: 'hidden'}}>
          <div style={{position: 'absolute', inset: 0, transform: tr, transformOrigin: '50% 60%'}}>
            {video(cSt, false)}
            <Blurs rects={d.camBlur} st={cSt} srcW={d.srcW} />
          </div>
          <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: 8, background: K.accent}} />
        </div>
      )}
      {/* cam bubble in full-game layout */}
      {bubble > 0.01 && (
        <div
          style={{
            position: 'absolute',
            left: 48,
            top: 260,
            width: bw,
            height: bh,
            borderRadius: 36,
            overflow: 'hidden',
            border: `6px solid ${K.accent}`,
            boxShadow: '0 16px 50px rgba(0,0,0,0.55)',
            opacity: bubble,
            transform: `scale(${0.8 + 0.2 * bubble})`,
          }}
        >
          {video(bSt, false)}
        </div>
      )}
    </AbsoluteFill>
  );
};

// Karaoke caption: 1-3 words, the spoken word pops, key words in accent colour.
const Caption: React.FC<{cap: Cap; y: number}> = ({cap, y}) => {
  const frame = useCurrentFrame(); // local to the caption sequence
  const {fps} = useVideoConfig();
  const pop = spring({frame, fps, config: {damping: 14, stiffness: 220}, durationInFrames: 8});
  const out = interpolate(frame, [cap.len - 2, cap.len], [1, 0], clamp);
  const long = cap.words.map((w) => w.text).join(' ').length > 16;
  const size = long ? 78 : 96;
  return (
    <div
      style={{
        position: 'absolute',
        left: 60,
        right: 150, // clear of the right-side action buttons
        top: y - size * 0.7,
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: 'center',
        gap: '0 22px',
        opacity: out,
        transform: `scale(${0.85 + 0.15 * pop})`,
      }}
    >
      {cap.words.map((w, i) => {
        const active = frame >= w.start - cap.start && frame < w.start - cap.start + w.len;
        const said = frame >= w.start - cap.start;
        return (
          <span
            key={i}
            style={{
              fontFamily: MONT,
              fontWeight: 900,
              fontSize: w.hl ? size * 1.12 : size,
              lineHeight: 1.12,
              textTransform: 'uppercase',
              color: w.hl ? K.accent : K.white,
              opacity: said ? 1 : 0.55,
              WebkitTextStroke: `${Math.round(size / 7)}px ${K.ink}`,
              paintOrder: 'stroke fill',
              textShadow: '0 8px 22px rgba(0,0,0,0.55)',
              display: 'inline-block',
              transform: `scale(${active ? 1.1 : 1}) rotate(${w.hl && active ? -3 : 0}deg)`,
            }}
          >
            {w.text}
          </span>
        );
      })}
    </div>
  );
};

// Opening hook: tilted accent box that slams in, then shrinks into a small title for the rest.
const Hook: React.FC<{text: string; sub?: string; len: number; tag?: string}> = ({text, sub, len, tag}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const slam = spring({frame, fps, config: {damping: 11, stiffness: 200}, durationInFrames: 12});
  const shrink = spring({frame: frame - len, fps, config: {damping: 200}, durationInFrames: 14});
  // full size on frame 0 (platform thumbnails), then a small settle; shrinks into a title after `len`
  const scale = interpolate(shrink, [0, 1], [1, 0.46]) * (1 + 0.12 * (1 - slam));
  const top = interpolate(shrink, [0, 1], [300, 170]);
  const subO = interpolate(frame, [6, 12, len - 4, len], [0, 1, 1, 0], clamp);
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div style={{position: 'absolute', left: 0, right: 0, top, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
        <div style={{transform: `scale(${scale}) rotate(-2.5deg)`, transformOrigin: '50% 0%'}}>
          <div
            style={{
              fontFamily: ANTON,
              fontSize: 112,
              lineHeight: 1.02,
              color: K.ink,
              background: K.accent,
              padding: '14px 34px 8px',
              borderRadius: 18,
              textTransform: 'uppercase',
              textAlign: 'center',
              maxWidth: 900,
              whiteSpace: 'pre-line',
              boxShadow: `10px 12px 0 ${K.ink}`,
            }}
          >
            {text}
          </div>
        </div>
        {sub && (
          <div
            style={{
              marginTop: 34,
              opacity: subO,
              fontFamily: MONT,
              fontWeight: 900,
              fontSize: 50,
              color: K.white,
              background: 'rgba(11,11,16,0.8)',
              padding: '10px 26px',
              borderRadius: 999,
              transform: 'rotate(1.5deg)',
            }}
          >
            {sub}
          </div>
        )}
      </div>
      {tag && (
        <div
          style={{
            position: 'absolute',
            left: 48,
            top: 172,
            opacity: shrink,
            fontFamily: MONT,
            fontWeight: 900,
            fontSize: 30,
            letterSpacing: 3,
            color: K.white,
            background: K.hot,
            padding: '6px 16px',
            borderRadius: 10,
          }}
        >
          {tag}
        </div>
      )}
    </AbsoluteFill>
  );
};

// Sticker text for an emphasis beat ("CLUTCH!", "KKKK").
const Sticker: React.FC<{text: string; len: number; i: number; y: number}> = ({text, len, i, y}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = spring({frame, fps, config: {damping: 9, stiffness: 240}, durationInFrames: 10});
  const o = interpolate(frame, [len - 5, len], [1, 0], clamp);
  const rot = i % 2 ? 7 : -7;
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'flex-start', paddingTop: y, opacity: o}}>
      <div
        style={{
          fontFamily: ANTON,
          fontSize: 150,
          color: K.white,
          WebkitTextStroke: `14px ${K.hot}`,
          paintOrder: 'stroke fill',
          transform: `scale(${p * 1.0}) rotate(${rot}deg)`,
          textShadow: '0 12px 40px rgba(0,0,0,0.6)',
          textTransform: 'uppercase',
          whiteSpace: 'pre-line',
          textAlign: 'center',
          lineHeight: 1,
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};

const fxZoom = (fx: Fx[], frame: number, fps: number) => {
  let z = 1;
  for (const e of fx) {
    if (e.kind !== 'punch' || frame < e.at || frame > e.at + e.len) continue;
    const t = frame - e.at;
    const inn = spring({frame: t, fps, config: {damping: 12, stiffness: 260}, durationInFrames: 6});
    const out = interpolate(t, [e.len - 8, e.len], [1, 0], clamp);
    z = Math.max(z, 1 + (e.strength ?? 0.22) * inn * out);
  }
  return z;
};

const fxShake = (fx: Fx[], frame: number): [number, number] => {
  for (const e of fx) {
    if (e.kind !== 'shake' || frame < e.at || frame > e.at + e.len) continue;
    const t = frame - e.at;
    const a = (e.strength ?? 26) * (1 - t / e.len);
    return [Math.sin(t * 2.7) * a, Math.cos(t * 3.9) * a * 0.7];
  }
  return [0, 0];
};

export const StreamShort: React.FC<{d: StreamShortData}> = ({d}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const camH = camHAt(d.segs, frame);
  const zoom = fxZoom(d.fx, frame, fps);
  const shake = fxShake(d.fx, frame);
  const capY = camH > 100 ? Math.min(camH + 150, 1330) : 1180;
  return (
    <AbsoluteFill style={{backgroundColor: K.ink}}>
      {d.segs.map((s, i) => (
        <Sequence key={i} from={s.start} durationInFrames={s.len}>
          {s.speed === 0 ? (
            <Freeze frame={0}>
              <AbsoluteFill style={{filter: 'saturate(0.35) contrast(1.1)'}}>
                <SegView d={d} seg={{...s, speed: 1}} camH={camH} zoom={zoom} shake={shake} />
              </AbsoluteFill>
            </Freeze>
          ) : (
            <SegView d={d} seg={s} camH={camH} zoom={zoom} shake={shake} />
          )}
        </Sequence>
      ))}
      {d.fx
        .filter((e) => e.kind === 'flash')
        .map((e, i) => (
          <Sequence key={`fl${i}`} from={e.at} durationInFrames={e.len}>
            <Flash len={e.len} />
          </Sequence>
        ))}
      {d.caps.map((c, i) => (
        <Sequence key={`c${i}`} from={c.start} durationInFrames={c.len}>
          <Caption cap={c} y={capY} />
        </Sequence>
      ))}
      {d.fx
        .filter((e) => e.text)
        .map((e, i) => (
          <Sequence key={`st${i}`} from={e.at} durationInFrames={Math.max(e.len, 20)}>
            <Sticker text={e.text!} len={Math.max(e.len, 20)} i={i} y={camHAt(d.segs, e.at) > 1000 ? 1110 : camHAt(d.segs, e.at) > 100 ? 1120 : 700} />
          </Sequence>
        ))}
      <Sequence from={0} durationInFrames={d.outro ? d.total - d.outro.len : d.total}>
        <Hook text={d.hook.text} sub={d.hook.sub} len={d.hook.len} tag={d.tag} />
      </Sequence>
      {d.outro && (
        <Sequence from={d.total - d.outro.len} durationInFrames={d.outro.len}>
          <Outro text={d.outro.text} len={d.outro.len} />
        </Sequence>
      )}
    </AbsoluteFill>
  );
};

const Flash: React.FC<{len: number}> = ({len}) => {
  const f = useCurrentFrame();
  return <AbsoluteFill style={{backgroundColor: 'white', opacity: interpolate(f, [0, len], [0.75, 0], clamp)}} />;
};

const Outro: React.FC<{text: string; len: number}> = ({text, len}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = spring({frame, fps, config: {damping: 12, stiffness: 180}, durationInFrames: 12});
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', background: `rgba(11,11,16,${0.45 * p})`}}>
      <div
        style={{
          fontFamily: ANTON,
          fontSize: 104,
          lineHeight: 1.05,
          color: K.ink,
          background: K.accent,
          padding: '18px 40px 10px',
          borderRadius: 20,
          textTransform: 'uppercase',
          textAlign: 'center',
          whiteSpace: 'pre-line',
          transform: `scale(${p}) rotate(-2deg)`,
          marginBottom: 380,
          boxShadow: `10px 12px 0 ${K.ink}`,
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};
