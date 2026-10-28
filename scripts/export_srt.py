#!/usr/bin/env python3
"""Export the long-form subtitles as caption tracks for YouTube (instead of / besides burning them in).

  python3 export_srt.py --project <proj> [--orig-lang pt]      (default: plan.json "language")
      -> <proj>/out/captions.en.srt   the plan's subtitles, on the final timeline
         <proj>/out/captions.<orig-lang>.srt   what was actually said, from transcripts/words.json

Reads src/edit-data.ts (run `npm run build` first). Subtitle cues use the same placement as the burned-in
ones; the original-language track groups the word timestamps of every talk shot into short cues.
"""
import argparse
import json
import os
import re

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True)
ap.add_argument("--orig-lang", help='language code of the speech (default: plan.json "language")')
a = ap.parse_args()
P = os.path.abspath(a.project)
if not a.orig_lang:
    plan_path = os.path.join(P, "plan.json")
    a.orig_lang = json.load(open(plan_path, encoding="utf8")).get("language") if os.path.exists(plan_path) else None
    if not a.orig_lang:
        ap.error('no original language: set "language" in plan.json or pass --orig-lang')

src = open(os.path.join(P, "src", "edit-data.ts"), encoding="utf8").read()
m = re.search(r"export const LONG: LongData \| null = (\{.*?\n\});\n", src, re.S)
LONG = json.loads(m.group(1))
FPS = LONG["fps"]
shots = [s for sec in LONG["sections"] for s in sec["shots"]] + (LONG.get("post") or {}).get("shots", [])


def ts(sec):
    ms = max(0, round(sec * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write(path, cues):
    with open(path, "w", encoding="utf8") as f:
        for i, (s, e, t) in enumerate(cues, 1):
            f.write(f"{i}\n{ts(s)} --> {ts(e)}\n{t}\n\n")
    print(f"{len(cues)} cues -> {os.path.relpath(path, P)}")


# translated subtitles, exactly as the template would have drawn them
en = []
for sh in shots:
    for s in sh.get("subs", []):
        if s["len"] <= 3:
            continue
        st, en_ = (sh["start"] + s["from"]) / FPS, (sh["start"] + s["from"] + s["len"]) / FPS
        if en and en[-1][2] == s["text"] and st - en[-1][1] <= 3 / FPS:  # same line split by a jump cut
            en[-1] = (en[-1][0], en_, s["text"])
        else:
            en.append((st, en_, s["text"]))
os.makedirs(os.path.join(P, "out"), exist_ok=True)
write(os.path.join(P, "out", "captions.en.srt"), en)

# original language: hand-cleaned lines aligned 1:1 with the English cues (captions.<lang>.json in the project),
# else a rough track straight from the word timestamps of the talk shots
lines_file = os.path.join(P, f"captions.{a.orig_lang}.json")
if os.path.exists(lines_file):
    lines = json.load(open(lines_file, encoding="utf8"))
    if len(lines) != len(en):
        raise SystemExit(f"{lines_file}: {len(lines)} lines but {len(en)} English cues; regenerate it")
    write(os.path.join(P, "out", f"captions.{a.orig_lang}.srt"), [(s, e, t) for (s, e, _), t in zip(en, lines)])
    raise SystemExit
words = json.load(open(os.path.join(P, "transcripts", "words.json"), encoding="utf8"))
bywin = {}
for key, segs in words.items():
    clip = key.split(":")[0]
    bywin.setdefault(clip, []).extend(w for seg in segs for w in seg["w"])
orig = []
for sh in shots:
    if sh.get("music") or "photo" in sh or sh.get("speed", 1) != 1 or "srcClip" not in sh:
        continue
    clip, a0 = sh["srcClip"].rsplit("@", 1)
    a0 = float(a0)
    b0 = a0 + sh["len"] / FPS
    t0, t1 = sh["start"] / FPS, (sh["start"] + sh["len"]) / FPS
    ws = sorted({(round(w[0], 2), round(w[1], 2), w[2].strip()) for w in bywin.get(clip, [])
                 if w[0] >= a0 - 0.05 and w[1] <= b0 + 0.15 and w[2].strip()})
    cues, cue = [], []
    for s, e, t in ws:
        text = " ".join(c[2] for c in cue)
        if cue and (s - cue[-1][1] > 0.6 or len(text + " " + t) > 64 or e - cue[0][0] > 4.5
                    or (len(text) >= 18 and text[-1] in ".,?!")):
            cues.append(cue)
            cue = []
        cue.append((s, e, t))
    if cue:
        cues.append(cue)
    for c in cues:  # source -> timeline, clamped to the shot
        orig.append((max(t0, t0 + c[0][0] - a0), min(t1, t0 + c[-1][1] - a0 + 0.25), " ".join(x[2] for x in c)))
orig = [c for c in orig if c[1] - c[0] > 0.2]
for i in range(len(orig) - 1):  # no overlaps
    if orig[i][1] > orig[i + 1][0]:
        orig[i] = (orig[i][0], orig[i + 1][0], orig[i][2])
write(os.path.join(P, "out", f"captions.{a.orig_lang}.srt"), orig)
