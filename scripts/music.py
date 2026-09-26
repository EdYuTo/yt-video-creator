#!/usr/bin/env python3
"""Analyze a music track so the edit can follow it.

usage: music.py <audio file> --project <proj> [--window START LEN]

Prints:
  - duration
  - loudness per second (0-9), so you can see intros, drops and breaks at a glance
  - silences/breaks (>= 0.3 s near-silent) with the exact onset of the next hit — a hit right
    after a break is the best place to start a Short, and a decay into silence is the best place
    to end one
  - tempo (BPM), beat period and phase, estimated over --window (default: whole track).
    Cut on multiples of the beat period starting from the phase offset.
"""
import argparse
import array
import math
import subprocess

from _ff import tools

ap = argparse.ArgumentParser()
ap.add_argument("audio")
ap.add_argument("--project")
ap.add_argument("--window", nargs=2, type=float)
a = ap.parse_args()
ff, _, env = tools(a.project)

SR = 8000
raw = subprocess.run(
    [ff, "-v", "error", "-i", a.audio, "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", "-f", "wav", "-"],
    env=env, capture_output=True,
).stdout[44:]
x = array.array("h", raw[: len(raw) // 2 * 2])
dur = len(x) / SR
print(f"duration {dur:.2f}s")


def rms(i, n):
    seg = x[i : i + n]
    return math.sqrt(sum(v * v for v in seg) / max(1, len(seg)))


sec = [rms(i, SR) for i in range(0, len(x) - SR, SR)]
m = max(sec) or 1
print("loudness/s:", " ".join(f"{i}:{int(9 * v / m)}" for i, v in enumerate(sec)))

# 20 ms envelope for silences + onsets
H = SR // 50
env20 = [rms(i, H) for i in range(0, len(x) - H, H)]
peak = max(env20) or 1
quiet = [v < 0.02 * peak for v in env20]
print("\nbreaks (silence start -> next onset):")
i = 0
while i < len(quiet):
    if quiet[i]:
        j = i
        while j < len(quiet) and quiet[j]:
            j += 1
        if (j - i) * 0.02 >= 0.3:
            nxt = f"{j * 0.02:.2f}s" if j < len(quiet) else "end"
            print(f"  {i * 0.02:.2f}s -> {nxt}   ({(j - i) * 0.02:.2f}s)")
        i = j
    else:
        i += 1

# Tempo: onset-strength autocorrelation at 100 Hz, then fine search of period + phase.
w0, wl = (a.window if a.window else (0, dur))
s0, s1 = int(w0 * SR), int(min(dur, w0 + wl) * SR)
h = SR // 100
env10 = [rms(i, h) for i in range(s0, s1 - h, h)]
flux = [0.0] + [max(0.0, env10[i] - env10[i - 1]) for i in range(1, len(env10))]
n = len(flux)
best = None
for ms in range(300, 1001, 2):  # 60-200 BPM
    per = ms / 1000
    for o in range(0, ms, 10):
        s, t = 0.0, o / 1000
        while t < n / 100 - 0.01:
            s += flux[int(round(t * 100))]
            t += per
        s /= max(1, (n / 100) / per)
        if best is None or s > best[0]:
            best = (s, per, o / 1000)
_, per, off = best
bpm = 60 / per
# Prefer the 80-160 BPM octave; double/halve if needed
while bpm < 80:
    bpm, per = bpm * 2, per / 2
while bpm > 160:
    bpm, per = bpm / 2, per * 2
print(f"\ntempo ~{bpm:.1f} BPM, beat {per:.3f}s, first beat at +{off:.2f}s from {w0:.2f}s")
