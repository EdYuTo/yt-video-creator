#!/usr/bin/env python3
"""Check a render's audio mix per segment kind, using edit-map.json from build_edit.py.

usage: audio_levels.py <render.mp4> --project <proj> [--comp long] [-v]

Prints RMS dBFS averaged by kind (talk, broll, photo, listCard, outro, credits, post) plus the peak.
Targets that worked: talk around -20 dBFS, music-only b-roll 6-8 dB below talk, peak under -1 dBFS.
If the music is too loud or quiet, change long.music.volume in plan.json (0.14 gave -27 against
-20 talk in a noisy restaurant).
"""
import argparse
import array
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ff import pcm  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("--project", required=True)
ap.add_argument("--comp", default="long")
ap.add_argument("-v", action="store_true")
a = ap.parse_args()
P = os.path.abspath(a.project)
SR = 16000
x = array.array("h", pcm(a.video, P, SR))


def db(s, e):
    seg = x[int(s * SR): int(e * SR)]
    if not seg:
        return None
    return 20 * math.log10(math.sqrt(sum(v * v for v in seg) / len(seg)) / 32768 + 1e-9)


rows = [r for r in json.load(open(os.path.join(P, "edit-map.json"))) if r["comp"] == a.comp]
agg = {}
for r in rows:
    if r["end"] - r["start"] < 0.4:
        continue
    v = db(r["start"] + 0.1, r["end"] - 0.1)
    if v is None:
        continue
    agg.setdefault(r["kind"], []).append(v)
    if a.v:
        print(f"{r['kind']:9s} {r['start']:7.1f}-{r['end']:7.1f} {str(r['clip']):28s} {v:6.1f}")
for k, vs in agg.items():
    print(f"{k:9s} n={len(vs):3d}  mean {sum(vs) / len(vs):6.1f} dBFS  min {min(vs):6.1f}  max {max(vs):6.1f}")
peak = max(abs(v) for v in x) if x else 0
print(f"peak {20 * math.log10(peak / 32768 + 1e-9):.1f} dBFS, length {len(x) / SR:.1f}s")
