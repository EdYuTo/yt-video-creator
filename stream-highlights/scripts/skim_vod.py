#!/usr/bin/env python3
"""Language detection + chunked skim transcription of a whole VOD. Run with the venv python.

  skim_vod.py lang  --project <proj> [--at 600,3600,7200]
      auto-detects the language on 30-s windows (small model). All windows should agree; then
      FORCE that language below (auto-detect per chunk drifts on music, game audio, other voices).
  skim_vod.py skim  --project <proj> --language pt [--chunk 1200]
      splits analysis/vod16k.wav into chunks, runs yt-video-creator's transcribe.py skim on each
      (resumable: finished chunks are skipped), then merges into analysis/vod_skim.txt:
          [h:mm:ss] +12 text      (+12 = loudest second of the line vs the VOD median, dB)
      dropping Whisper repetition loops and zero-width-space junk.
  skim_vod.py ctx   --project <proj> 1:05:00-1:07:30 [...]
      print the skim lines inside time ranges (reading context around candidates).

Speed seen: ~25x realtime (3.5 h in 8.4 min) with mlx-whisper small on an M1 Pro.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import wave

import numpy as np

from _base import BASE_SCRIPTS, hms, secs

ap = argparse.ArgumentParser()
ap.add_argument("mode", choices=["lang", "skim", "ctx"])
ap.add_argument("ranges", nargs="*")
ap.add_argument("--project", required=True)
ap.add_argument("--language")
ap.add_argument("--chunk", type=int, default=1200)
ap.add_argument("--at")
a = ap.parse_intermixed_args()
P = os.path.abspath(a.project)
AN = os.path.join(P, "analysis")
WAV = os.path.join(AN, "vod16k.wav")
SK = os.path.join(AN, "skim")
TXT = os.path.join(AN, "vod_skim.txt")


def load(start=None, dur=None):
    w = wave.open(WAV)
    sr = w.getframerate()
    if start:
        w.setpos(int(start * sr))
    n = w.getnframes() if dur is None else int(dur * sr)
    return np.frombuffer(w.readframes(n), np.int16).astype(np.float32) / 32768, sr, w.getnframes() / sr


if a.mode == "lang":
    _, _, total = load(dur=0)
    if a.at:
        ats = [secs(t) for t in a.at.split(",")]
    else:
        # speech-heavy windows only: near-silent ones make Whisper hallucinate ("you" -> en)
        ap_ = os.path.join(AN, "audio.json")
        if os.path.exists(ap_):
            db = np.array(json.load(open(ap_))["db"])
            thirds = np.array_split(np.arange(len(db) - 30), 3)
            ats = [float(max(part[::30], key=lambda t: np.median(db[t:t + 30]))) for part in thirds]
        else:
            ats = [total * f for f in (0.15, 0.5, 0.85)]
    found = []
    try:
        import mlx_whisper
        for t in ats:
            x, _, _ = load(t, 30)
            r = mlx_whisper.transcribe(x, path_or_hf_repo="mlx-community/whisper-small-mlx", condition_on_previous_text=False, verbose=None)
            found.append(r["language"])
            print(f"{hms(t)}  {r['language']}  {r['text'][:120]}", flush=True)
    except ImportError:
        from faster_whisper import WhisperModel
        m = WhisperModel("small", compute_type="int8")
        for t in ats:
            x, _, _ = load(t, 30)
            segs, info = m.transcribe(x)
            found.append(info.language)
            print(f"{hms(t)}  {info.language}  {' '.join(s.text for s in segs)[:120]}", flush=True)
    if found:
        top = max(set(found), key=found.count)
        print(f"majority: {top} ({found.count(top)}/{len(found)})" + ("" if found.count(top) == len(found) else "  <- windows disagree: read them; pass --at with speech-heavy times"))

elif a.mode == "skim":
    if not a.language:
        sys.exit("--language is required (run `lang` first)")
    os.makedirs(SK, exist_ok=True)
    _, sr, total = load(dur=0)
    for i, off in enumerate(range(0, int(total), a.chunk)):
        done = os.path.join(SK, f"c{i:02d}_{off}.json")
        if os.path.exists(done):
            continue
        cw = os.path.join(SK, f"c{i:02d}_{off}.wav")
        x, _, _ = load(off, a.chunk)
        with wave.open(cw, "w") as o:
            o.setnchannels(1), o.setsampwidth(2), o.setframerate(sr)
            o.writeframes((x * 32767).astype(np.int16).tobytes())
        subprocess.run([sys.executable, os.path.join(BASE_SCRIPTS, "transcribe.py"), "skim", cw, "--project", P,
                        "--language", a.language, "--out", SK], check=True)
        os.remove(cw)
        print(f"chunk {i} ({hms(off)}) done", flush=True)
    audio = json.load(open(os.path.join(AN, "audio.json"))) if os.path.exists(os.path.join(AN, "audio.json")) else None
    rows = []
    for f in sorted(glob.glob(os.path.join(SK, "c*_*.json"))):
        off = int(re.search(r"_(\d+)\.json$", f).group(1))
        for s in json.load(open(f)):
            rows.append((off + s["start"], off + s["end"], s["text"]))
    prev, rep, kept = None, 0, 0
    with open(TXT, "w") as fh:
        for s, e, t in rows:
            rep = rep + 1 if t == prev else 0
            prev = t
            if rep >= 2 or not t or "​" in t:
                continue
            lv = ""
            if audio:
                seg = audio["db"][int(s):max(int(e), int(s) + 1)]
                lv = f"{(max(seg) - audio['global_median_db']) if seg else 0:+3.0f} "
            fh.write(f"[{hms(s)}] {lv}{t}\n")
            kept += 1
    print(f"{kept} lines -> {TXT}")

else:
    lines = open(TXT).read().splitlines()
    for r in a.ranges:
        lo, hi = (secs(v) for v in r.split("-"))
        print(f"===== {r}")
        for l in lines:
            m = re.match(r"\[(\d+):(\d+):(\d+)\]", l)
            t = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3])
            if lo <= t <= hi:
                print(l[:160])
