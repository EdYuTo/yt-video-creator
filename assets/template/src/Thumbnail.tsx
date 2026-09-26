import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';
import {THUMB} from './edit-data';
import {BODY, C, DISPLAY} from './theme';
import type {ThumbData, ThumbPanel} from './types';

// 1280x720 YouTube thumbnail. Rules of thumb it follows: one big face or subject per panel,
// <= 4 words of huge outlined text, strong contrast, and nothing important in the bottom-right
// corner (YouTube draws the duration there).
const D = THUMB as ThumbData;

const Panel: React.FC<{p: ThumbPanel; clip?: string}> = ({p, clip}) => {
  const cx = (p.cx ?? 0.5) * 100;
  const cy = (p.cy ?? 0.5) * 100;
  return (
    <AbsoluteFill style={{clipPath: clip, overflow: 'hidden'}}>
      <Img
        src={staticFile(p.src)}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          objectPosition: `${cx}% ${cy}%`,
          transform: `translate(${p.dx ?? 0}%, ${p.dy ?? 0}%) scale(${p.zoom ?? 1})`,
          transformOrigin: `${cx}% ${cy}%`,
          filter: 'saturate(1.25) contrast(1.08) brightness(1.05)',
        }}
      />
    </AbsoluteFill>
  );
};

// Diagonal split: left panel ends between 58% (top) and 46% (bottom).
const LEFT = 'polygon(0 0, 58% 0, 46% 100%, 0 100%)';
const RIGHT = 'polygon(58% 0, 100% 0, 100% 100%, 46% 100%)';

export const Thumbnail: React.FC = () => {
  const [a, b] = D.panels;
  return (
    <AbsoluteFill style={{backgroundColor: C.dark}}>
      {b ? (
        <>
          <Panel p={a} clip={LEFT} />
          <Panel p={b} clip={RIGHT} />
          {/* divider stripe */}
          <AbsoluteFill style={{clipPath: 'polygon(57.4% 0, 58.6% 0, 46.6% 100%, 45.4% 100%)', backgroundColor: C.light}} />
        </>
      ) : (
        <Panel p={a} />
      )}
      <AbsoluteFill style={{background: 'linear-gradient(to top, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0) 45%)'}} />
      <AbsoluteFill style={{justifyContent: 'flex-end', padding: '0 0 34px 44px'}}>
        {D.kicker && (
          <div style={{fontFamily: BODY, fontWeight: 800, fontSize: 34, letterSpacing: 6, color: C.accent, textShadow: '0 3px 12px rgba(0,0,0,0.8)'}}>
            {D.kicker}
          </div>
        )}
        <div
          style={{
            fontFamily: DISPLAY,
            fontWeight: 800,
            fontSize: 148,
            lineHeight: 0.92,
            color: C.light,
            whiteSpace: 'pre-line',
            WebkitTextStroke: `14px ${C.dark}`,
            paintOrder: 'stroke fill',
            textShadow: '0 8px 30px rgba(0,0,0,0.6)',
          }}
        >
          {D.title}
        </div>
      </AbsoluteFill>
      {D.badge && (
        <AbsoluteFill style={{alignItems: 'flex-end', padding: '30px 34px 0 0'}}>
          <div
            style={{
              transform: 'rotate(4deg)',
              fontFamily: BODY,
              fontWeight: 800,
              fontSize: 50,
              color: '#fff',
              background: '#E0301E',
              padding: '10px 26px',
              borderRadius: 18,
              border: '5px solid #fff',
              boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
            }}
          >
            {D.badge}
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};
