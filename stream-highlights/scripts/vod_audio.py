#!/usr/bin/env python3
"""Decode a VOD's audio once and compute cheap loudness signals. Run with the venv python
(numpy) from yt-video-creator's setup_speech.sh.

usage: vod_audio.py <vod> --project <proj> [--out <proj>/analysis]
  -> analysis/vod16k.wav        16 kHz mono (every later step reads this, never the huge video)
  -> analysis/audio.json        per-second dBFS, global median, ranked peaks
  prints: loudness per 10 min (to see the energy arc: games, breaks, muted stretches) + top peaks

Audio alone is a weak detector for talkative streamers (it found none of the best moments in the
first run); treat peaks as a tiebreaker and a pointer to screams/laughter. The baseline is clamped
to the global median so a quiet or muted hour doesn't produce all the "spikes".
"""
import argparse
import json
import os
import subprocess
import wave

import numpy as np

from _base import hms, tools

ap = argparse.ArgumentParser()
ap.add_argument("vod")
ap.add_argument("--project", required=True)
ap.add_argument("--out")
a = ap.parse_args()
out = a.out or os.path.join(a.project, "analysis")
os.makedirs(out, exist_ok=True)
wav = os.path.join(out, "vod16k.wav")
ff, _, env = tools(a.project)
if not os.path.exists(wav):
    subprocess.run([ff, "-v", "error", "-i", a.vod, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", "-y", wav], env=env, check=True)
    print("decoded", wav)

w = wave.open(wav)
sr, n = w.getframerate(), w.getnframes()
x = np.frombuffer(w.readframes(n), np.int16).astype(np.float32) / 32768
N = n // sr
x = x[: N * sr].reshape(N, sr)
db = 20 * np.log10(np.sqrt((x ** 2).mean(1)) + 1e-9)
pk = 20 * np.log10(np.sqrt((x.reshape(N, 10, sr // 10) ** 2).mean(2)).max(1) + 1e-9)
hf = np.sqrt((np.diff(x, axis=1) ** 2).mean(1)) / (np.sqrt((x ** 2).mean(1)) + 1e-9)  # brightness: screams, laughs


def rolling_median(v, k):
    from numpy.lib.stride_tricks import sliding_window_view
    return np.median(sliding_window_view(np.pad(v, (k // 2, k // 2), mode="edge"), k), axis=1)[: len(v)]


glob = float(np.median(db))
rel = db - np.maximum(rolling_median(db, 61), glob)
k5 = np.ones(5) / 5
exc = np.convolve(np.maximum(rel, 0), k5, "same") + 0.5 * np.convolve(np.maximum(pk - db - 6, 0), k5, "same")
drop = np.zeros(N)
for t in range(5, N - 3):
    before = db[t - 5:t].mean()
    drop[t] = max(0, before - db[t:t + 3].mean() - 10) * (before > glob + 8)
score = exc + 0.3 * drop + 0.4 * np.maximum(hf - np.median(hf), 0) * (rel > 3)
picked = []
for t in np.argsort(-score):
    if len(picked) >= 80:
        break
    if all(abs(t - p) > 20 for p in picked):
        picked.append(int(t))
json.dump(dict(global_median_db=glob, db=[round(float(v), 1) for v in db],
               peaks=[dict(t=p, hms=hms(p), score=round(float(score[p]), 2), db=round(float(db[p]), 1), rel=round(float(rel[p]), 1)) for p in picked]),
          open(os.path.join(out, "audio.json"), "w"))
print(f"{N / 3600:.2f} h, median {glob:.1f} dBFS, p95 {np.percentile(db, 95):.1f}")
print("loudness per 10 min (median / p95):")
for i in range(0, N, 600):
    print(f"  {hms(i)}  {np.median(db[i:i + 600]):6.1f} {np.percentile(db[i:i + 600], 95):6.1f}")
print("top peaks (t, score, dB, rel):")
for p in picked[:30]:
    print(f"  {hms(p)}  {score[p]:5.1f} {db[p]:6.1f} {rel[p]:+5.1f}")
