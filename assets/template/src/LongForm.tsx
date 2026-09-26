import React from 'react';
import {AbsoluteFill, Audio, getStaticFiles, interpolate, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {Caption, Chip, Counter, FadeBlack, PhotoView, Pill, Shade, ShotSubs, ShotView, useInOut} from './components';
import {LONG} from './edit-data';
import {BODY, C, DISPLAY} from './theme';
import type {LongData} from './types';

// Layout is precomputed by build_edit.py (frames); this file only draws it.
const D = LONG as LongData;
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

const Intro: React.FC<{len: number}> = ({len}) => {
  const {enter, opacity} = useInOut(len, 8);
  const intro = D.intro!;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{background: `linear-gradient(90deg, ${C.dark}ee 0%, ${C.dark}00 65%)`}} />
      <AbsoluteFill style={{justifyContent: 'center', paddingLeft: 120, opacity}}>
        <div style={{transform: `translateX(${(1 - enter) * -60}px)`, color: C.light}}>
          {intro.kicker && <div style={{fontFamily: BODY, fontWeight: 800, fontSize: 32, letterSpacing: 8, color: C.accent}}>{intro.kicker}</div>}
          <div style={{fontFamily: DISPLAY, fontWeight: 800, fontSize: 132, lineHeight: 0.98, marginTop: 12, whiteSpace: 'pre-line'}}>{intro.title}</div>
          {intro.subtitle && <div style={{fontFamily: BODY, fontWeight: 600, fontSize: 40, marginTop: 24, opacity: 0.9}}>{intro.subtitle}</div>}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const ListCard: React.FC<{card: NonNullable<LongData['listCard']>}> = ({card}) => {
  const frame = useCurrentFrame();
  const {opacity} = useInOut(card.len);
  return (
    <AbsoluteFill style={{backgroundColor: C.dark}}>
      {card.photo && (
        <AbsoluteFill style={{opacity: 0.35}}>
          <PhotoView src={card.photo} len={card.len} zoomIn={false} />
        </AbsoluteFill>
      )}
      <AbsoluteFill style={{padding: '90px 140px', opacity, color: C.light}}>
        <div style={{fontFamily: DISPLAY, fontWeight: 800, fontSize: 96}}>{card.title}</div>
        <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', columnGap: 100, rowGap: 26, marginTop: 48}}>
          {card.rows.map(([a, b], i) => {
            const t = interpolate(frame, [10 + i * 5, 22 + i * 5], [0, 1], clamp);
            return (
              <div key={i} style={{display: 'flex', alignItems: 'baseline', gap: 24, opacity: t, transform: `translateY(${(1 - t) * 20}px)`, borderBottom: `2px solid ${C.light}2e`, paddingBottom: 14}}>
                <span style={{fontFamily: DISPLAY, fontWeight: 800, fontSize: 52, color: C.accent, minWidth: 250}}>{a}</span>
                <span style={{fontFamily: BODY, fontWeight: 600, fontSize: 44}}>{b}</span>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const Outro: React.FC<{o: NonNullable<LongData['outro']>}> = ({o}) => {
  const frame = useCurrentFrame();
  const {opacity} = useInOut(o.len);
  let n = 0;
  return (
    <AbsoluteFill style={{backgroundColor: C.dark, color: C.light}}>
      {o.photo && (
        <AbsoluteFill style={{opacity: 0.25}}>
          <PhotoView src={o.photo} len={o.len} />
        </AbsoluteFill>
      )}
      <AbsoluteFill style={{padding: '70px 110px', opacity, flexDirection: 'row', gap: 90}}>
        {o.columns.map((col, ci) => (
          <div key={ci} style={{flex: ci === 0 && o.columns.length > 1 ? '0 0 560px' : 1}}>
            <div style={{fontFamily: DISPLAY, fontWeight: 800, fontSize: 64, color: C.accent}}>{col.title}</div>
            {col.items.map((item, i) => {
              const t = interpolate(frame, [8 + n * 3, 18 + n++ * 3], [0, 1], clamp);
              return (
                <div key={i} style={{display: 'flex', gap: 18, fontFamily: BODY, fontWeight: 600, fontSize: 30, marginTop: 13, opacity: t}}>
                  {col.numbered && <span style={{fontWeight: 800, color: C.accent, minWidth: 36}}>{i + 1}.</span>}
                  <span>{item}</span>
                </div>
              );
            })}
          </div>
        ))}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// Lines: [heading, ""] = big line; [label, value] = small caps label + value.
const Credits: React.FC<{c: NonNullable<LongData['credits']>}> = ({c}) => {
  const frame = useCurrentFrame();
  const {opacity} = useInOut(c.len);
  const teaser = interpolate(frame, [c.len - 70, c.len - 55], [0, 1], clamp);
  return (
    <AbsoluteFill style={{backgroundColor: C.dark, color: C.light, justifyContent: 'center', alignItems: 'center', opacity}}>
      {c.photo && (
        <AbsoluteFill style={{opacity: 0.22}}>
          <PhotoView src={c.photo} len={c.len} zoomIn={false} fill />
        </AbsoluteFill>
      )}
      {c.lines.map(([a, b], i) => {
        const t = interpolate(frame, [8 + i * 10, 22 + i * 10], [0, 1], clamp);
        return (
          <div key={i} style={{opacity: t, transform: `translateY(${(1 - t) * 20}px)`, textAlign: 'center', marginBottom: b ? 28 : 56}}>
            {b ? (
              <>
                <div style={{fontFamily: BODY, fontWeight: 800, fontSize: 26, letterSpacing: 6, color: C.accent, textTransform: 'uppercase'}}>{a}</div>
                <div style={{fontFamily: BODY, fontWeight: 600, fontSize: 38, marginTop: 6}}>{b}</div>
              </>
            ) : (
              <div style={{fontFamily: DISPLAY, fontWeight: 800, fontSize: 96}}>{a}</div>
            )}
          </div>
        );
      })}
      {c.teaser && <div style={{position: 'absolute', bottom: 90, fontFamily: DISPLAY, fontWeight: 800, fontSize: 48, color: C.accent, opacity: teaser}}>{c.teaser}</div>}
    </AbsoluteFill>
  );
};

export const LongForm: React.FC = () => {
  const hasMusic = D.music && getStaticFiles().some((s) => s.name === D.music!.file);
  const shots = D.sections.flatMap((s) => s.shots);
  const first = D.sections[0];
  return (
    <AbsoluteFill style={{backgroundColor: 'black'}}>
      {shots.map((shot, i) => (
        <Sequence key={`v${i}`} from={shot.start} durationInFrames={shot.len}>
          <ShotView shot={shot} index={i} />
        </Sequence>
      ))}
      {D.sections.map((s, i) => {
        const titleLen = D.captions === 'top' ? Math.min(s.len, 135) : s.len;
        return (
          <React.Fragment key={`sec${i}`}>
            {i === 0 && D.intro ? (
              <Sequence from={s.start} durationInFrames={s.len}>
                <Intro len={s.len} />
              </Sequence>
            ) : s.title ? (
              <Sequence from={s.start} durationInFrames={titleLen}>
                <Shade from={D.captions} />
                <Caption step={s.step} title={s.title} sub={s.sub} len={titleLen} pos={D.captions} />
              </Sequence>
            ) : null}
            {s.counter && (
              <Sequence from={s.start} durationInFrames={s.len}>
                <Counter spec={s.counter} len={s.len} />
              </Sequence>
            )}
          </React.Fragment>
        );
      })}
      {shots.map((shot, i) =>
        shot.chip ? (
          <Sequence key={`c${i}`} from={shot.start} durationInFrames={shot.len}>
            <Chip big={shot.chip.big} small={shot.chip.small} len={shot.len} />
          </Sequence>
        ) : null,
      )}
      {shots.map((shot, i) => (
        <ShotSubs key={`s${i}`} shot={shot} />
      ))}
      {first && (
        <Sequence from={0} durationInFrames={20}>
          <FadeBlack len={20} />
        </Sequence>
      )}
      {D.listCard && (
        <Sequence from={D.listCard.start} durationInFrames={D.listCard.len}>
          <ListCard card={D.listCard} />
        </Sequence>
      )}
      {D.outro && (
        <Sequence from={D.outro.start} durationInFrames={D.outro.len}>
          <Outro o={D.outro} />
        </Sequence>
      )}
      {D.credits && (
        <Sequence from={D.credits.start} durationInFrames={D.credits.len}>
          <Credits c={D.credits} />
        </Sequence>
      )}
      {D.post && (
        <>
          {D.post.shots.map((shot, i) => (
            <Sequence key={`p${i}`} from={shot.start} durationInFrames={shot.len}>
              <ShotView shot={shot} gray index={i} />
            </Sequence>
          ))}
          {D.post.shots.map((shot, i) => (
            <ShotSubs key={`ps${i}`} shot={shot} />
          ))}
          <Sequence from={D.post.start} durationInFrames={D.post.len}>
            <AbsoluteFill style={{padding: '56px 0 0 72px', alignItems: 'flex-start'}}>
              <Pill size={30} style={{letterSpacing: 6, background: '#fff', color: '#111'}}>
                BLOOPERS
              </Pill>
            </AbsoluteFill>
          </Sequence>
          <Sequence from={D.post.start} durationInFrames={12}>
            <FadeBlack len={12} />
          </Sequence>
        </>
      )}
      <Sequence from={D.total - 20} durationInFrames={20}>
        <FadeBlack len={20} out />
      </Sequence>
      {hasMusic &&
        D.music!.runs.map((r, i) => (
          <Sequence key={`m${i}`} from={r.start} durationInFrames={r.len}>
            <Audio
              src={staticFile(D.music!.file)}
              trimBefore={Math.round(r.songFrom * D.fps)}
              volume={(f) => interpolate(f, [0, D.music!.fadeIn, r.len - D.music!.fadeOut, r.len], [0, D.music!.volume, D.music!.volume, 0], clamp)}
            />
          </Sequence>
        ))}
    </AbsoluteFill>
  );
};
