#!/usr/bin/env python3
"""shorts.json (VOD source time) -> per-short proxies + src/shorts-data.ts.

usage: build_shorts.py --project <proj> [--only short-01] [--no-media] [--rebuild]
       (the project's `npm run build:shorts` calls this)

shorts.json:
{
  "src": "vod.mp4",                      # under source/ (symlink to the VOD)
  "fps": 30,
  "cam": [2014, 0, 546, 410],            # facecam box in source px
  "camBlur": [], "gameBlur": [],         # optional privacy boxes (source px)
  "loudnorm": "I=-14:TP=-1.5:LRA=11",    # per-short proxy normalisation (Shorts platforms ~ -14 LUFS)
  "words": "transcripts/words.json",     # from transcribe.py words vod:<s>-<e>
  "shorts": [{
    "id": "short-01", "tag": "CS2",
    "hook": {"text": "...", "sub": "...", "sec": 2.2},
    "cuts": [{"s": 1560.2, "e": 1575.0, "layout": "stack|face|game", "gameX": 0.5}],
    "fx": [{"t": 1566.3, "kind": "punch|shake|flash", "len": 0.5, "text": "KKKK", "strength": 0.2}],
    "hl": ["words", "to", "highlight"],   # matched case/accent-insensitively
    "fix": {"wrong": "right", "5328.70": "tomei"},  # caption word fixes by word or by start time ("" drops)
    "caps": [[s, e, "TEXT"]],             # optional manual captions (source time) instead of words
    "outro": {"text": "...", "sec": 1.2}  # freeze-frame end card
  }]
}
Every source time inside a cut maps to the timeline; fx/captions outside all cuts are dropped (WARN).
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import unicodedata

from _base import tools

ap = argparse.ArgumentParser()
ap.add_argument("--project", default=".")
ap.add_argument("--only")
ap.add_argument("--no-media", action="store_true")
ap.add_argument("--rebuild", action="store_true")
a = ap.parse_args()
P = os.path.abspath(a.project)
plan = json.load(open(os.path.join(P, "shorts.json")))
FPS = plan.get("fps", 30)
fr = lambda s: int(round(s * FPS))

FF, FP, ENV = tools(P)
SRC = os.path.join(P, "source", plan["src"])
HAS_VT = b"h264_videotoolbox" in subprocess.run([FF, "-hide_banner", "-encoders"], env=ENV, capture_output=True).stdout
VENC = ["-c:v", "h264_videotoolbox", "-b:v", "24M"] if HAS_VT else ["-c:v", "libx264", "-crf", "17", "-preset", "veryfast"]
info = json.loads(subprocess.check_output([FP, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", SRC], env=ENV))["streams"][0]
SW, SH = info["width"], info["height"]
WORDS = {}
wp = os.path.join(P, plan.get("words", "transcripts/words.json"))
if os.path.exists(wp):
    WORDS = json.load(open(wp))
warn = []


def norm(w):
    w = unicodedata.normalize("NFKD", w.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in w if not unicodedata.combining(c)))


def all_words():
    seen, out = set(), []
    for key, segs in WORDS.items():
        for s in segs:
            for ws, we, t in s["w"]:
                k = (round(ws, 1), t)
                if k not in seen:
                    seen.add(k)
                    out.append((ws, we, t))
    return sorted(out)


ALLW = all_words()


def build(sh):
    cuts = sh["cuts"]
    # one proxy per group of nearby cuts (a montage may span hours of VOD)
    groups = []
    for c in sorted(cuts, key=lambda c: c["s"]):
        if groups and c["s"] - groups[-1][1] < 20:
            groups[-1][1] = max(groups[-1][1], c["e"])
        else:
            groups.append([c["s"], c["e"]])
    ranges = []
    for k, (g0, g1) in enumerate(groups):
        lo, hi = g0 - 1.0, g1 + 1.0
        rel = f"footage/{sh['id']}.mp4" if len(groups) == 1 else f"footage/{sh['id']}_{k}.mp4"
        ranges.append((lo, hi, rel))
        dest = os.path.join(P, "public", rel)
        stamp = f"{lo:.2f}-{hi:.2f}"
        stamp_file = dest + ".range"
        fresh = os.path.exists(dest) and os.path.exists(stamp_file) and open(stamp_file).read() == stamp
        if a.no_media or (fresh and not a.rebuild):
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        cmd = [FF, "-v", "error"] + (["-hwaccel", "videotoolbox"] if HAS_VT else []) + ["-ss", f"{lo:.3f}", "-i", SRC, "-t", f"{hi - lo:.3f}",
               "-map", "0:v:0", "-map", "0:a:0", "-dn", "-map_metadata", "-1", "-vf", "format=yuv420p", "-r", str(FPS)] + VENC + [
               "-af", f"loudnorm={plan.get('loudnorm', 'I=-14:TP=-1.5:LRA=11')}",
               "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-y", dest]
        print(f"proxy {rel} ({hi - lo:.1f}s)", flush=True)
        subprocess.run(cmd, env=ENV, check=True)
        open(stamp_file, "w").write(stamp)

    def where(c):
        return next(r for r in ranges if r[0] <= c["s"] and c["e"] <= r[1])

    # timeline segments
    segs, t = [], 0
    for c in cuts:
        n = fr(c["e"] - c["s"])
        lo, _, rel = where(c)
        segs.append(dict(start=t, len=n, src=rel, fromSec=round(c["s"] - lo, 3), layout=c.get("layout", "stack"),
                         **{k: c[k] for k in ("gameX", "blur", "blurGame") if k in c}, _s=c["s"], _e=c["e"]))
        t += n
    lo, hi = groups[0][0], groups[-1][1]
    rel = ranges[0][2]

    def tl(x):
        for s in segs:
            if s["_s"] - 1e-3 <= x <= s["_e"] + 1e-3:
                return s["start"] + fr(x - s["_s"])
        return None

    # captions
    hl = {norm(w) for w in sh.get("hl", [])}
    # fix keys: a word ("Nubis") replaces it everywhere; a source time ("5328.70") replaces the word starting there
    fixt = {float(k): v for k, v in sh.get("fix", {}).items() if re.fullmatch(r"[0-9.]+", k)}
    fix = {norm(k): v for k, v in sh.get("fix", {}).items() if not re.fullmatch(r"[0-9.]+", k)}
    caps = []
    if sh.get("caps"):
        for s0, s1, text in sh["caps"]:
            a0, a1 = tl(s0), tl(s1)
            if a0 is None or a1 is None:
                warn.append(f"{sh['id']}: caption {text!r} outside cuts")
                continue
            ws = text.split()
            step = max(1, (a1 - a0) // max(1, len(ws)))
            caps.append(dict(start=a0, len=max(6, a1 - a0), words=[dict(start=a0 + i * step, len=step, text=w, hl=norm(w) in hl) for i, w in enumerate(ws)]))
    else:
        words = []
        for ws, we, text in ALLW:
            s0 = next((s for s in segs if s["_s"] <= ws and we <= s["_e"] + 0.15), None)
            if not s0:
                continue
            k = norm(text)
            tk = next((v for t0, v in fixt.items() if abs(t0 - ws) < 0.03), None)
            if tk is not None or k in fix:
                text = tk if tk is not None else fix[k]
                if not text:
                    continue
            start = s0["start"] + fr(ws - s0["_s"])
            end = min(s0["start"] + s0["len"], s0["start"] + fr(we - s0["_s"]))
            words.append(dict(start=start, len=max(2, end - start), text=text.strip(), hl=norm(text) in hl, seg=id(s0)))
        group = []

        def flush():
            if group:
                caps.append(dict(start=group[0]["start"], len=0, words=[{k: v for k, v in w.items() if k != "seg"} for w in group]))
                group.clear()

        for w in words:
            chars = sum(len(g["text"]) + 1 for g in group) + len(w["text"])
            gap = w["start"] - (group[-1]["start"] + group[-1]["len"]) if group else 0
            if group and (len(group) >= 3 or chars > 17 or gap > fr(0.35) or w["seg"] != group[-1]["seg"]
                          or re.search(r"[.!?,]$", group[-1]["text"])):
                flush()
            group.append(w)
        flush()
        for i, c in enumerate(caps):
            last = c["words"][-1]
            end = last["start"] + last["len"] + fr(0.25)
            if i + 1 < len(caps):
                end = min(end, caps[i + 1]["start"])
            c["len"] = max(6, end - c["start"])
            for w in c["words"]:
                w["text"] = w["text"].strip(" ,.")
    fx = []
    for e in sh.get("fx", []):
        at = tl(e["t"])
        if at is None:
            warn.append(f"{sh['id']}: fx at {e['t']} outside cuts")
            continue
        fx.append(dict(at=at, kind=e.get("kind", "punch"), len=fr(e.get("len", 0.5)), **{k: e[k] for k in ("text", "strength") if k in e}))
    total = t
    outro = None
    if sh.get("outro"):
        n = fr(sh["outro"].get("sec", 1.2))
        last = segs[-1]
        segs.append(dict(start=total, len=n, src=last["src"], fromSec=round(last["fromSec"] + (last["len"] - 1) / FPS, 3), layout=last["layout"], speed=0,
                         **{k: last[k] for k in ("gameX", "blur", "blurGame") if k in last}, _s=0, _e=0))
        total += n
        outro = dict(text=sh["outro"]["text"], len=n)
    for s in segs:
        s.pop("_s"), s.pop("_e")
    out = dict(id=sh["id"], fps=FPS, total=total, src=rel, srcW=SW, srcH=SH, cam=plan["cam"],
               camBlur=plan.get("camBlur", []) + sh.get("camBlur", []), gameBlur=plan.get("gameBlur", []) + sh.get("gameBlur", []),
               segs=segs, caps=caps, fx=fx, hook=dict(text=sh["hook"]["text"], sub=sh["hook"].get("sub"), len=fr(sh["hook"].get("sec", 2.2))),
               tag=sh.get("tag"), outro=outro)
    words_src = sum(c["e"] - c["s"] for c in cuts)
    print(f"{sh['id']}: {total / FPS:.1f}s  ({len(cuts)} cuts, {len(ranges)} proxies, {lo:.0f}-{hi:.0f}s, {len(caps)} captions, {len(fx)} fx)")
    if not caps:
        warn.append(f"{sh['id']}: no captions (run transcribe.py words for {lo:.1f}-{hi:.1f})")
    if not 15 <= total / FPS <= 60:
        warn.append(f"{sh['id']}: length {total / FPS:.1f}s outside 15-60 s")
    return out


data_path = os.path.join(P, "src", "shorts-data.ts")
existing = {}
if a.only and os.path.exists(os.path.join(P, "shorts-data.json")):
    existing = {s["id"]: s for s in json.load(open(os.path.join(P, "shorts-data.json")))}
for sh in plan["shorts"]:
    if a.only and sh["id"] != a.only:
        continue
    existing[sh["id"]] = build(sh)
ordered = [existing[s["id"]] for s in plan["shorts"] if s["id"] in existing]
json.dump(ordered, open(os.path.join(P, "shorts-data.json"), "w"))
with open(data_path, "w") as fh:
    fh.write("// GENERATED by build_shorts.py (stream-highlights skill) from shorts.json. Do not edit.\n")
    fh.write("import type {StreamShortData} from './stream/types';\n")
    fh.write(f"export const SHORTS: StreamShortData[] = {json.dumps(ordered, ensure_ascii=False)};\n")
for w in warn:
    print("WARN", w)
