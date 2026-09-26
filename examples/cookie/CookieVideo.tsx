import React from 'react';
import {
  AbsoluteFill,
  Audio,
  getStaticFiles,
  interpolate,
  Sequence,
  Series,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {
  DOG,
  FPS,
  INGREDIENTS,
  INGREDIENTS_SEC,
  INTRO_SEC,
  MIN_OUTRO_SEC,
  TARGET_SEC,
  PHOTO_SEC,
  PHOTOS,
  Section,
  SECTIONS,
  STEPS,
} from './edit';
import {AmountChip, BakeTimer, BottomShade, C, Caption, KenBurns, SANS, SERIF, ShotView, useInOut} from './ui';

const fr = (s: number) => Math.round(s * FPS);
const sectionSec = (s: Section) => s.shots.reduce((a, x) => a + x.dur, 0);

const bodyFrames =
  fr(INTRO_SEC) +
  fr(INGREDIENTS_SEC) +
  SECTIONS.reduce((a, s) => a + s.shots.reduce((b, x) => b + fr(x.dur), 0), 0) +
  PHOTOS.length * fr(PHOTO_SEC) +
  fr(DOG.dur);
const outroFrames = Math.max(fr(MIN_OUTRO_SEC), fr(TARGET_SEC) - bodyFrames);
const OUTRO_SEC = outroFrames / FPS;

export const totalFrames = () => bodyFrames + outroFrames;

const MUSIC = 'music.mp3';

const Music: React.FC = () => {
  const {durationInFrames} = useVideoConfig();
  if (!getStaticFiles().some((f) => f.name === MUSIC)) {
    return null;
  }
  return (
    <Audio
      src={staticFile(MUSIC)}
      volume={(f) =>
        interpolate(f, [0, 15, durationInFrames - 60, durationInFrames], [0, 0.8, 0.8, 0], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        })
      }
    />
  );
};

const Intro: React.FC = () => {
  const {enter, opacity} = useInOut(INTRO_SEC, 8);
  return (
    <AbsoluteFill>
      <KenBurns src={PHOTOS[0]} dur={INTRO_SEC} />
      <AbsoluteFill style={{background: 'linear-gradient(90deg, rgba(46,27,16,0.85) 0%, rgba(46,27,16,0) 60%)'}} />
      <AbsoluteFill style={{justifyContent: 'center', paddingLeft: 120, opacity}}>
        <div style={{transform: `translateX(${(1 - enter) * -60}px)`, color: C.cream}}>
          <div style={{fontFamily: SANS, fontWeight: 800, fontSize: 32, letterSpacing: 8, color: C.caramel}}>
            MAKE-AHEAD
          </div>
          <div style={{fontFamily: SERIF, fontWeight: 800, fontSize: 140, lineHeight: 0.95, marginTop: 12}}>
            Chocolate
            <br />
            Chunk Cookies
          </div>
          <div style={{fontFamily: SANS, fontWeight: 600, fontSize: 40, marginTop: 24, opacity: 0.9}}>
            Freeze the dough, bake whenever you want
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const Ingredients: React.FC = () => {
  const frame = useCurrentFrame();
  const {opacity} = useInOut(INGREDIENTS_SEC);
  return (
    <AbsoluteFill style={{backgroundColor: C.choc}}>
      <AbsoluteFill style={{opacity: 0.35}}>
        <KenBurns src={PHOTOS[1]} dur={INGREDIENTS_SEC} zoomIn={false} />
      </AbsoluteFill>
      <AbsoluteFill style={{padding: '90px 140px', opacity, color: C.cream}}>
        <div style={{fontFamily: SERIF, fontWeight: 800, fontSize: 96}}>You'll need</div>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            columnGap: 100,
            rowGap: 26,
            marginTop: 48,
          }}
        >
          {INGREDIENTS.map(([amount, name], i) => {
            const t = interpolate(frame, [10 + i * 5, 22 + i * 5], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            });
            return (
              <div
                key={name}
                style={{
                  display: 'flex',
                  alignItems: 'baseline',
                  gap: 24,
                  opacity: t,
                  transform: `translateY(${(1 - t) * 20}px)`,
                  borderBottom: '2px solid rgba(255,244,230,0.18)',
                  paddingBottom: 14,
                }}
              >
                <span style={{fontFamily: SERIF, fontWeight: 800, fontSize: 52, color: C.caramel, minWidth: 250}}>
                  {amount}
                </span>
                <span style={{fontFamily: SANS, fontWeight: 600, fontSize: 44}}>{name}</span>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const SectionView: React.FC<{section: Section}> = ({section}) => {
  const dur = sectionSec(section);
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
      {section.title && <BottomShade />}
      {section.shots.map((shot, i) => {
        const start = offset;
        offset += fr(shot.dur);
        return shot.amount ? (
          <Sequence key={i} from={start} durationInFrames={fr(shot.dur)} layout="none">
            <AmountChip amount={shot.amount} item={shot.item ?? ''} dur={shot.dur} />
          </Sequence>
        ) : null;
      })}
      {section.overlay === 'bake-timer' && <BakeTimer dur={dur} />}
      {section.title && <Caption step={section.step} title={section.title} sub={section.sub} dur={dur} />}
    </AbsoluteFill>
  );
};

const Outro: React.FC = () => {
  const frame = useCurrentFrame();
  const {opacity} = useInOut(OUTRO_SEC);
  return (
    <AbsoluteFill style={{backgroundColor: C.choc, color: C.cream}}>
      <AbsoluteFill style={{opacity: 0.25}}>
        <KenBurns src={PHOTOS[3]} dur={OUTRO_SEC} />
      </AbsoluteFill>
      <AbsoluteFill style={{padding: '70px 110px', opacity, flexDirection: 'row', gap: 90}}>
        <div style={{width: 560}}>
          <div style={{fontFamily: SERIF, fontWeight: 800, fontSize: 64, color: C.caramel}}>Ingredients</div>
          {INGREDIENTS.map(([a, n]) => (
            <div key={n} style={{fontFamily: SANS, fontWeight: 600, fontSize: 32, marginTop: 14}}>
              <b style={{fontWeight: 800}}>{a}</b> {n}
            </div>
          ))}
        </div>
        <div style={{flex: 1}}>
          <div style={{fontFamily: SERIF, fontWeight: 800, fontSize: 64, color: C.caramel}}>Method</div>
          {STEPS.map((s, i) => {
            const t = interpolate(frame, [8 + i * 4, 18 + i * 4], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            });
            return (
              <div key={i} style={{display: 'flex', gap: 18, fontFamily: SANS, fontWeight: 600, fontSize: 29, marginTop: 13, opacity: t}}>
                <span style={{fontWeight: 800, color: C.caramel, minWidth: 36}}>{i + 1}.</span>
                <span>{s}</span>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const CookieVideo: React.FC = () => {
  return (
    <AbsoluteFill style={{backgroundColor: C.choc}}>
      <Series>
        <Series.Sequence durationInFrames={fr(INTRO_SEC)}>
          <Intro />
        </Series.Sequence>
        <Series.Sequence durationInFrames={fr(INGREDIENTS_SEC)}>
          <Ingredients />
        </Series.Sequence>
        {SECTIONS.map((s, i) => (
          <Series.Sequence key={i} durationInFrames={s.shots.reduce((a, x) => a + fr(x.dur), 0)}>
            <SectionView section={s} />
          </Series.Sequence>
        ))}
        {PHOTOS.map((p, i) => (
          <Series.Sequence key={p} durationInFrames={fr(PHOTO_SEC)}>
            <KenBurns src={p} dur={PHOTO_SEC} zoomIn={i % 2 === 0} />
          </Series.Sequence>
        ))}
        <Series.Sequence durationInFrames={fr(DOG.dur)}>
          <SectionView section={{title: 'Official taste tester', sub: 'Waiting for crumbs', shots: [DOG]}} />
        </Series.Sequence>
        <Series.Sequence durationInFrames={outroFrames}>
          <Outro />
        </Series.Sequence>
      </Series>
      <Music />
    </AbsoluteFill>
  );
};
