#!/usr/bin/env python3
"""Speech/silence map of a clip's audio from loudness (needs numpy: use the setup_speech.sh venv).
Good for QUIET footage (vlog to camera, voice-over). In noisy places (restaurant, street, grill)
energy can't separate speech from room noise; cut from word timestamps instead (transcribe.py words
+ build_edit.py).

usage: speech_map.py <clip or wav> --project <proj> [--from S --to E] [--thresh-db -38] [--min-gap 0.6] [--pad 0.15] [--strip]
Prints: per-second loudness strip (dBFS, one char per second: ' '=<-50 .=-50 :=-42 -=-36 ==-30 #=louder),
and speech islands (start-end) separated by >= min-gap of audio below thresh — i.e. the keep ranges
when "cutting silences". Speech band (200-3800 Hz) energy is used so grill sizzle/hum weighs less.
"""
import argparse, os, sys, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ff import pcm
ap = argparse.ArgumentParser()
ap.add_argument("wav"); ap.add_argument("--project"); ap.add_argument("--from", dest="t0", type=float, default=0); ap.add_argument("--to", dest="t1", type=float)
ap.add_argument("--thresh-db", type=float, default=-38); ap.add_argument("--min-gap", type=float, default=0.6)
ap.add_argument("--pad", type=float, default=0.15); ap.add_argument("--strip", action="store_true")
a = ap.parse_args()
if a.wav.lower().endswith(".wav"):
    with wave.open(a.wav) as f:
        sr = f.getframerate(); x = np.frombuffer(f.readframes(f.getnframes()), np.int16).astype(np.float32) / 32768
else:
    sr = 16000; x = np.frombuffer(pcm(a.wav, a.project, sr), np.int16).astype(np.float32) / 32768
t1 = a.t1 or len(x) / sr
x = x[int(a.t0 * sr): int(t1 * sr)]
H = sr // 50  # 20 ms frames
n = len(x) // H
fr = x[: n * H].reshape(n, H)
spec = np.abs(np.fft.rfft(fr * np.hanning(H), axis=1))
freqs = np.fft.rfftfreq(H, 1 / sr)
band = (freqs > 200) & (freqs < 3800)
e = np.sqrt((spec[:, band] ** 2).sum(1) / H) * 2 / H * np.sqrt(H)
db = 20 * np.log10(e + 1e-9)
db = np.convolve(db, np.ones(5) / 5, mode="same")
fmt = lambda t: f"{int(t//60)}:{t%60:04.1f}"
if a.strip:
    persec = [db[i:i + 50].max() for i in range(0, n, 50)]
    ch = lambda d: " " if d < -50 else "." if d < -42 else ":" if d < -36 else "-" if d < -30 else "=" if d < -24 else "#"
    for m in range(0, len(persec), 60):
        print(f"{fmt(a.t0 + m)} |" + "".join(ch(d) for d in persec[m:m + 60]) + "|")
on = db > a.thresh_db
isl, i = [], 0
while i < n:
    if on[i]:
        j = i
        while j < n and on[j]: j += 1
        isl.append([i * 0.02, j * 0.02]); i = j
    else: i += 1
merged = []
for s, e_ in isl:
    if merged and s - merged[-1][1] < a.min_gap: merged[-1][1] = e_
    else: merged.append([s, e_])
merged = [(max(0, s - a.pad) + a.t0, e_ + a.pad + a.t0) for s, e_ in merged if e_ - s >= 0.25]
tot = sum(e_ - s for s, e_ in merged)
print(f"{len(merged)} islands, {tot:.1f}s of {t1 - a.t0:.1f}s kept (thresh {a.thresh_db} dB, gap {a.min_gap}s)")
for s, e_ in merged: print(f"  {s:8.2f} {e_:8.2f}  ({fmt(s)}-{fmt(e_)}) {e_ - s:.1f}s")
