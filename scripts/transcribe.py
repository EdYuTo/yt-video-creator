#!/usr/bin/env python3
"""Local speech-to-text for talk footage. Run with the venv python from setup_speech.sh.

Two passes (cheap skim, then accurate words only where needed):

  1) Skim whole clips (small model) -> transcripts/<id>.txt / .json, one line per segment:
     transcribe.py skim <clip...> --project <proj> --language pt [--model small]

  2) Word timestamps for chosen windows (large-v3-turbo) -> merged into transcripts/words.json,
     which build_edit.py uses to cut silences:
     transcribe.py words <id>:<start>-<end> [...] --project <proj> --language pt

Clips are given as ids (source/<id>.*) or paths. The .LRF proxy is used automatically when present
(same audio, faster decode).

Lessons baked in:
  - ALWAYS force --language. Auto-detect listens to the first 30 s; one Japanese waiter turned
    40 min of Portuguese into garbage Japanese. Speech in other languages then comes out
    translated-ish into the forced language, which is often fine for subtitles.
  - condition_on_previous_text=False: stops the small model's repetition loops ("RICARDO" x12).
  - Audio is decoded with Remotion's ffmpeg and passed as an array: mlx-whisper otherwise shells out
    to the system ffmpeg, which may be broken.
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ff import pcm  # noqa: E402

import numpy as np  # noqa: E402

SR = 16000
MODELS = {
    "small": ("mlx-community/whisper-small-mlx", "small"),
    "turbo": ("mlx-community/whisper-large-v3-turbo", "large-v3-turbo"),
}

ap = argparse.ArgumentParser()
ap.add_argument("mode", choices=["skim", "words"])
ap.add_argument("items", nargs="+")
ap.add_argument("--project", required=True)
ap.add_argument("--language", required=True)
ap.add_argument("--model")
ap.add_argument("--out")
a = ap.parse_args()
proj = os.path.abspath(a.project)
out_dir = a.out or os.path.join(proj, "transcripts")
os.makedirs(out_dir, exist_ok=True)

try:
    import mlx_whisper

    def run(x, model, words):
        r = mlx_whisper.transcribe(x, path_or_hf_repo=MODELS[model][0], language=a.language,
                                   condition_on_previous_text=False, word_timestamps=words, verbose=None)
        return r["segments"]
except ImportError:
    from faster_whisper import WhisperModel

    _cache = {}

    def run(x, model, words):
        m = _cache.setdefault(model, WhisperModel(MODELS[model][1], compute_type="int8"))
        segs, _ = m.transcribe(x, language=a.language, condition_on_previous_text=False, word_timestamps=words)
        return [dict(start=s.start, end=s.end, text=s.text, no_speech_prob=s.no_speech_prob,
                     words=[dict(start=w.start, end=w.end, word=w.word) for w in (s.words or [])]) for s in segs]


def resolve(item):
    if os.path.exists(item):
        return os.path.splitext(os.path.basename(item))[0], item
    hits = sorted(glob.glob(os.path.join(proj, "source", item + ".*")))
    lrf = [h for h in hits if h.endswith(".lrf.mp4")]
    full = [h for h in hits if not h.endswith(".lrf.mp4")]
    if not (lrf or full):
        raise SystemExit(f"no source file for {item}")
    return item, (lrf or full)[0]


def audio(path, start=None, dur=None):
    return np.frombuffer(pcm(path, proj, SR, start, dur), np.int16).astype(np.float32) / 32768


fmt = lambda t: f"{int(t // 60)}:{t % 60:04.1f}"

if a.mode == "skim":
    for item in a.items:
        cid, path = resolve(item)
        segs = run(audio(path), a.model or "small", False)
        segs = [dict(start=round(s["start"], 2), end=round(s["end"], 2), text=s["text"].strip(),
                     nsp=round(s.get("no_speech_prob", 0), 2)) for s in segs]
        json.dump(segs, open(f"{out_dir}/{cid}.json", "w"), ensure_ascii=False, indent=0)
        with open(f"{out_dir}/{cid}.txt", "w") as fh:
            for s in segs:
                fh.write(f"[{fmt(s['start'])}-{fmt(s['end'])}] {s['text']}\n")
        print(f"{cid}: {len(segs)} segments -> {out_dir}/{cid}.txt", flush=True)
else:
    wpath = os.path.join(out_dir, "words.json")
    words = json.load(open(wpath)) if os.path.exists(wpath) else {}
    for item in a.items:
        cid, se = item.rsplit(":", 1)
        s0, s1 = map(float, se.split("-"))
        _, path = resolve(cid)
        segs = run(audio(path, s0, s1 - s0), a.model or "turbo", True)
        words[f"{cid}:{s0}-{s1}"] = [
            dict(s=round(s0 + s["start"], 2), e=round(s0 + s["end"], 2), t=s["text"].strip(),
                 w=[[round(s0 + w["start"], 2), round(s0 + w["end"], 2), w["word"].strip()] for w in s.get("words", [])])
            for s in segs
        ]
        print(f"== {item}")
        for s in words[f"{cid}:{s0}-{s1}"]:
            print(f"  {s['s']:8.2f}-{s['e']:8.2f} {s['t']}", flush=True)
        json.dump(words, open(wpath, "w"), ensure_ascii=False)
    print(f"-> {wpath}")
