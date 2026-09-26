import React from 'react';
import {AbsoluteFill, Audio, getStaticFiles, interpolate, Sequence, Series, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Caption, Chip, Counter, PhotoView, Shade, ShotView, useInOut} from './components';
import {LIST_CARD, LongSection, MONTAGE, MUSIC, INTRO, OUTRO, SECTIONS, TARGET_SEC} from './long-edit';
import {BODY, C, DISPLAY, FPS} from './theme';

const fr = (s: number) => Math.round(s * FPS);
const sectionFrames = (s: LongSection) => s.shots.reduce((a, x) => a + fr(x.dur), 0);

const bodyFrames =
  fr(INTRO.sec) +
  (LIST_CARD ? fr(LIST_CARD.sec) : 0) +
  SECTIONS.reduce((a, s) => a + sectionFrames(s), 0) +
  MONTAGE.photos.length * fr(MONTAGE.secEach);
const outroFrames = Math.max(fr(OUTRO.minSec), TARGET_SEC ? fr(TARGET_SEC) - bodyFrames : 0);
export const longFormFrames = () => bodyFrames + outroFrames;

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

const Music: React.FC = () => {
  const {durationInFrames} = useVideoConfig();
  if (!getStaticFiles().some((s) => s.name === MUSIC.file)) return null;
  return (
    <Audio
      src={staticFile(MUSIC.file)}
      trimBefore={fr(MUSIC.startSec)}
      volume={(f) => interpolate(f, [0, 15, durationInFrames - 60, durationInFrames], [0, MUSIC.volume, MUSIC.volume, 0], clamp)}
    />
  );
};

const Intro: React.FC = () => {
  const {enter, opacity} = useInOut(INTRO.sec, 8);
  return (
    <AbsoluteFill>
      <PhotoView src={INTRO.photo} sec={INTRO.sec} />
      <AbsoluteFill style={{background: `linear-gradient(90deg, ${C.dark}dd 0%, ${C.dark}00 60%)`}} />
      <AbsoluteFill style={{justifyContent: 'center', paddingLeft: 120, opacity}}>
        <div style={{transform: `translateX(${(1 - enter) * -60}px)`, color: C.light}}>
          <div style={{fontFamily: BODY, fontWeight: 800, fontSize: 32, letterSpacing: 8, color: C.accent}}>{INTRO.kicker}</div>
          <div style={{fontFamily: DISPLAY, fontWeight: 800, fontSize: 140, lineHeight: 0.95, marginTop: 12, whiteSpace: 'pre-line'}}>
            {INTRO.title}
          </div>
          <div style={{fontFamily: BODY, fontWeight: 600, fontSize: 40, marginTop: 24, opacity: 0.9}}>{INTRO.subtitle}</div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const ListCard: React.FC<{card: NonNullable<typeof LIST_CARD>}> = ({card}) => {
  const frame = useCurrentFrame();
  const {opacity} = useInOut(card.sec);
  return (
    <AbsoluteFill style={{backgroundColor: C.dark}}>
      {card.photo && (
        <AbsoluteFill style={{opacity: 0.35}}>
          <PhotoView src={card.photo} sec={card.sec} zoomIn={false} />
        </AbsoluteFill>
      )}
      <AbsoluteFill style={{padding: '90px 140px', opacity, color: C.light}}>
        <div style={{fontFamily: DISPLAY, fontWeight: 800, fontSize: 96}}>{card.title}</div>
        <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', columnGap: 100, rowGap: 26, marginTop: 48}}>
          {card.rows.map(([a, b], i) => {
            const t = interpolate(frame, [10 + i * 5, 22 + i * 5], [0, 1], clamp);
            return (
              <div
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'baseline',
                  gap: 24,
                  opacity: t,
                  transform: `translateY(${(1 - t) * 20}px)`,
                  borderBottom: `2px solid ${C.light}2e`,
                  paddingBottom: 14,
                }}
              >
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

const SectionView: React.FC<{section: LongSection}> = ({section}) => {
  const sec = sectionFrames(section) / FPS;
  let offset = 0;
  return (
    <AbsoluteFill>
      <Series>
        {section.shots.map((shot, i) => (
          <Series.Sequence key={i} durationInFrames={fr(shot.dur)}>
            <ShotView shot={shot} />
          </Series.Sequence>
        ))}
      </Series>
      {section.title && <Shade from="bottom" />}
      {section.shots.map((shot, i) => {
        const start = offset;
        offset += fr(shot.dur);
        return shot.chip ? (
          <Sequence key={i} from={start} durationInFrames={fr(shot.dur)} layout="none">
            <Chip big={shot.chip.big} small={shot.chip.small} sec={shot.dur} />
          </Sequence>
        ) : null;
      })}
      {section.counter && <Counter spec={section.counter} sec={sec} />}
      {section.title && <Caption step={section.step} title={section.title} sub={section.sub} sec={sec} />}
    </AbsoluteFill>
  );
};

const Outro: React.FC<{sec: number}> = ({sec}) => {
  const frame = useCurrentFrame();
  const {opacity} = useInOut(sec);
  let n = 0;
  return (
    <AbsoluteFill style={{backgroundColor: C.dark, color: C.light}}>
      {OUTRO.photo && (
        <AbsoluteFill style={{opacity: 0.25}}>
          <PhotoView src={OUTRO.photo} sec={sec} />
        </AbsoluteFill>
      )}
      <AbsoluteFill style={{padding: '70px 110px', opacity, flexDirection: 'row', gap: 90}}>
        {OUTRO.columns.map((col, ci) => (
          <div key={ci} style={{flex: ci === 0 && OUTRO.columns.length > 1 ? '0 0 560px' : 1}}>
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

export const LongForm: React.FC = () => (
  <AbsoluteFill style={{backgroundColor: C.dark}}>
    <Series>
      <Series.Sequence durationInFrames={fr(INTRO.sec)}>
        <Intro />
      </Series.Sequence>
      {LIST_CARD && (
        <Series.Sequence durationInFrames={fr(LIST_CARD.sec)}>
          <ListCard card={LIST_CARD} />
        </Series.Sequence>
      )}
      {SECTIONS.map((s, i) => (
        <Series.Sequence key={i} durationInFrames={sectionFrames(s)}>
          <SectionView section={s} />
        </Series.Sequence>
      ))}
      {MONTAGE.photos.map((p, i) => (
        <Series.Sequence key={p} durationInFrames={fr(MONTAGE.secEach)}>
          <PhotoView src={p} sec={MONTAGE.secEach} zoomIn={i % 2 === 0} />
        </Series.Sequence>
      ))}
      <Series.Sequence durationInFrames={outroFrames}>
        <Outro sec={outroFrames / FPS} />
      </Series.Sequence>
    </Series>
    <Music />
  </AbsoluteFill>
);
