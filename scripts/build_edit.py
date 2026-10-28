#!/usr/bin/env python3
"""plan.json (source time) -> media in public/footage + src/edit-data.ts + edit-map.json.

usage: build_edit.py --project <proj> [--no-media] [--rebuild]

plan.json is the single source of truth for the edit. Everything is in SOURCE time (the timestamps
you read off contact sheets and transcripts); this script turns it into frames.

{
  "fps": 30,
  "clips": {"<id>": {"file": "<name in source/>", "media": "link" | "proxy", ...}},   # from setup
  "language": "pt", "words": "transcripts/words.json",
  "silence": {"pad": [0.2, 0.3], "gap": 0.75},        # talk cutting from word timestamps
  "loudnorm": true,                                    # proxies only: even out talk levels (I=-18)
  "blur": [{"clip": "<id>", "from": 210.0, "to": 228.0, "rects": [[x, y, w, h]]}],   # % of frame
  "long": {
    "intro": {"kicker": "KOBE, JAPAN", "title": "Line one\\nLine two", "subtitle": "..."},
                                                       # drawn over the first section
    "listCard": {"sec": 6.5, "title": "You'll need", "rows": [["320 g", "flour"]], "photo": "footage/x.jpg"},
    "sections": [{"title": "...", "sub": "...", "step": 1,
                  "counter": {"from": 0, "to": 22, "max": 25, "format": "min", "label": "200 °C"},
                  "items": [
        {"clip": "<id>", "from": 124.0, "dur": 3.5, "speed": 4,          # b-roll (dur = timeline s)
         "x": 45, "y": 50, "fit": "cover"|"blur", "chip": {"big": "225 g", "small": "butter"},
         "ambient": 0.3, "music": true},
        {"clip": "<id>", "talk": [284.8, 300.0], "cut": true, "vol": 1,  # dialogue, silence-cut
         "subs": [[285.1, 286.2, "Is this a little bell?"]]},
        {"photo": "footage/photo1.jpg", "dur": 2.5}                      # still, slow zoom
    ]}],
    "outro": {"sec": 8, "photo": "...", "columns": [{"title": "Ingredients", "numbered": false, "items": ["..."]}]},
    "credits": {"sec": 9, "lines": [["Thanks for watching!", ""], ["Music", "..."]],
                "teaser": "Wait... bloopers", "photo": "..."},
    "post": [ ...items... ],                           # after credits, grayscale ("bloopers")
    "captions": "auto" | "bottom" | "top",             # auto: top-left if the video has subtitles
    "ambient": 0,                                      # default source volume under 1x b-roll
    "music": {"file": "music.mp3", "mode": "auto" | "bed" | "broll" | "duck", "volume": 0.7,
              "startSec": 0, "matchSong": false}       # bed + matchSong: outro stretches to song end
  },
  "short": {
    "music": {"file": "music.mp3", "startSec": 27.7, "beat": 0.566, "offset": 0.05, "tail": 0.4, "volume": 0.85},
    "sections": [{"big": "225 g", "small": "butter",
                  "items": [{"clip": "<id>", "from": 45, "beats": 2, "speed": 3, "x": 47, "fit": "cover"}]}],
    "end": {"beats": 4, "photo": "footage/x.jpg", "big": "Full recipe\\nin the caption", "small": "save it for later"}
  }
}

Music modes: "bed" = one continuous track under intro..credits (music-driven edits);
"broll" = plays only under b-roll/photos/cards, silent under talk, and the song position advances
only while audible (so it doesn't restart each time). "auto" = broll if any talk items, else bed.
"duck" = one continuous bed (looping loopFrom..loopTo) that dips to duckVolume under talk instead of going silent.
Reels: plan.json "reels" (see references/plan.md); each becomes a Reel<N> composition.
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ff import duration, tools  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True)
ap.add_argument("--no-media", action="store_true", help="skip linking/transcoding (layout only)")
ap.add_argument("--rebuild", action="store_true", help="re-transcode proxies even if present")
a = ap.parse_args()
P = os.path.abspath(a.project)
plan = json.load(open(os.path.join(P, "plan.json")))
FPS = plan.get("fps", 30)
CLIPS = plan["clips"]
fr = lambda s: int(round(s * FPS))
drop = lambda d, *ks: {k: v for k, v in d.items() if k not in ks}
warnings = []

# ---------------------------------------------------------------- talk -> silence-cut islands
WORDS = {}
wp = os.path.join(P, plan.get("words") or "transcripts/words.json")
if os.path.exists(wp):
    WORDS = json.load(open(wp))
PRE, POST = plan.get("silence", {}).get("pad", [0.2, 0.3])
GAP = plan.get("silence", {}).get("gap", 0.75)


def words_in(clip, s0, s1):
    out = set()
    for key, segs in WORDS.items():
        if key.rsplit(":", 1)[0] != clip:
            continue
        for seg in segs:
            for ws, we, w in seg["w"]:
                if w and s0 - 0.05 <= ws and we <= s1 + 0.3:
                    out.add((ws, we))
    return sorted(out)


def islands(clip, s0, s1):
    ws = words_in(clip, s0, s1)
    if not ws:
        warnings.append(f"talk {clip} {s0}-{s1}: no word timestamps -> kept whole (run transcribe.py words)")
        return [(s0, s1)]
    isl = []
    for s, e in ws:
        s, e = max(s0, s - PRE), min(s1, e + POST)
        if isl and s - isl[-1][1] < GAP:
            isl[-1][1] = max(isl[-1][1], e)
        else:
            isl.append([s, e])
    return [(s, e) for s, e in isl if e - s >= 0.3]


# ---------------------------------------------------------------- reel demos (picture under the voice)
def demo_span(d, off, n, line_n):
    """One island's slice of a line's demo. `off`/`n` = the island's start (frames from the line's first
    island, on the cut timeline) and length; `line_n` = the whole line. Crop rects are interpolated per
    island, so rect -> rectTo moves continuously across the cuts."""
    if d.get("card"):
        return {"card": True}
    if d.get("clip") not in CLIPS:
        raise SystemExit(f"demo: unknown clip id {d.get('clip')!r} (see plan.json clips)")
    sp = 1 if "rect" in d else d.get("speed", 1)
    o = dict(d, at=d["from"] + off / FPS * sp, span=n / FPS * sp, speed=sp)
    if "rectTo" in d and "rect" in d:
        lerp = lambda t: [round(p + (q - p) * t, 5) for p, q in zip(d["rect"], d["rectTo"])]
        o["rect"], o["rectTo"] = lerp(off / max(1, line_n)), lerp((off + n) / max(1, line_n))
    return o


def clip_dur(clip):
    info = CLIPS[clip]
    return info.get("dur") or duration(os.path.join(P, "source", info["file"]), P)


# ---------------------------------------------------------------- music
def duck_runs(mus, song, total, fade_first, fade_last, where):
    """Runs of one continuous bed that plays startSec..loopTo, then loops loopFrom..loopTo, for `total` frames."""
    lf, lt, start = mus.get("loopFrom", 0), mus.get("loopTo", song), mus.get("startSec", 0)
    if not all(isinstance(v, (int, float)) for v in (lf, lt, start)):
        raise SystemExit(f"{where} music: loopFrom/loopTo/startSec must be numbers of seconds")
    if not 0 <= lf < lt <= song + 0.05 or fr(lt - lf) < 1:
        raise SystemExit(f"{where} music: need 0 <= loopFrom < loopTo <= song length ({song:.2f} s); "
                         f"got loopFrom {lf}, loopTo {lt}")
    if not 0 <= start < lt or fr(lt - start) < 1:
        raise SystemExit(f"{where} music: startSec {start} must be at least a frame before loopTo {lt}")
    runs, pos, st = [], start, 0
    while st < total:
        n = min(total - st, fr(lt - pos))
        if n <= 0:  # unreachable after the checks above; never loop forever
            break
        runs.append({"start": st, "len": n, "songFrom": round(pos, 3), "fadeIn": 4 if st else fade_first,
                     "fadeOut": 4 if st + n < total else fade_last})
        st += n
        pos = lf
    return runs


# ---------------------------------------------------------------- expand items to shots (source time)
def expand(items, default_music=True):
    """-> list of shot dicts with source range [a, b], speed, dur (s), flags."""
    out = []
    for it in items:
        base = {k: it[k] for k in ("x", "y", "zoom", "fit", "chip", "trans", "box") if k in it}
        if "photo" in it:
            out.append(dict(base, photo=it["photo"], dur=it["dur"], music=it.get("music", default_music),
                            anns=it.get("anns", [])))
        elif "talk" in it:
            s0, s1 = it["talk"]
            rngs = islands(it["clip"], s0, s1) if it.get("cut", True) else [(s0, s1)]
            line_n, off = sum(fr(e - s) for s, e in rngs), 0
            for s, e in rngs:
                out.append(dict(base, clip=it["clip"], a=s, b=e, speed=1, dur=e - s, vol=it.get("vol", 1),
                                music=it.get("music", False), subs=it.get("subs", []), anns=it.get("anns", [])))
                if "demo" in it:  # reels v2: the line's demo runs on under its silence-cut islands
                    out[-1]["demo_in"] = dict(demo_span(it["demo"], off, fr(e - s), line_n), line=(s0, s1))
                if "head" in it:
                    out[-1]["head_in"] = it["head"]
                off += fr(e - s)
        else:
            sp = it.get("speed", 1)
            out.append(dict(base, clip=it["clip"], a=it["from"], b=it["from"] + it["dur"] * sp, speed=sp,
                            dur=it["dur"], vol=it.get("ambient"), music=it.get("music", default_music),
                            subs=it.get("subs", []), anns=it.get("anns", [])))
    return out


L = plan.get("long") or {}
S = plan.get("short") or {}
long_secs = [dict(sec, shots=expand(sec.get("items", []))) for sec in L.get("sections", [])]
post_shots = expand(L.get("post", []), default_music=False)
for sh in post_shots:  # bloopers keep their own sound
    if "clip" in sh and sh.get("vol") is None:
        sh["vol"] = 1

short_secs = []
for sec in S.get("sections", []):
    shots = []
    for it in sec.get("items", []):
        d = dict({k: it[k] for k in ("x", "y", "fit") if k in it}, beats=it["beats"])
        if "photo" in it:
            d["photo"] = it["photo"]
        else:
            sp = it.get("speed", 1)
            d.update(clip=it["clip"], a=it["from"], speed=sp)
            d["b"] = None  # filled once beat length is known
        shots.append(d)
    short_secs.append(dict(sec, shots=shots))

REELS_IN = plan.get("reels") or []
reel_shots = [expand(r.get("items", []), default_music=True) for r in REELS_IN]

SM = S.get("music", {})
BEAT, OFF = SM.get("beat", 0.566), SM.get("offset", 0.0)
beat_frame = lambda k: 0 if k == 0 else fr(OFF + k * BEAT)
k = 0
for sec in short_secs:
    for sh in sec["shots"]:
        sh["start"], sh["len"] = beat_frame(k), beat_frame(k + sh["beats"]) - beat_frame(k)
        k += sh["beats"]
        if "clip" in sh:
            sh["b"] = sh["a"] + sh["len"] / FPS * sh["speed"]
short_end_beat = k

# ---------------------------------------------------------------- media: link or proxy ranges
ff, fp, env = tools(P)
os.makedirs(os.path.join(P, "public/footage"), exist_ok=True)
MEDIA = {m["file"]: m for m in json.load(open(os.path.join(P, "media.json")))} if os.path.exists(os.path.join(P, "media.json")) else {}
all_shots = ([sh for s in long_secs for sh in s["shots"]] + post_shots
             + [sh for s in short_secs for sh in s["shots"]] + [sh for r in reel_shots for sh in r])
used = {}
for sh in all_shots:
    if "clip" in sh:
        if sh["clip"] not in CLIPS:
            raise SystemExit(f"unknown clip id {sh['clip']!r} (see plan.json clips)")
        used.setdefault(sh["clip"], []).append((sh["a"], sh["b"]))
    dm = sh.get("demo_in")
    if dm and "clip" in dm:
        end = clip_dur(dm["clip"])
        # A shot that starts past the demo's end gets a still of its last frame instead of nothing; one
        # that only runs over it stays a video (OffthreadVideo holds the last frame). Both are reported.
        dm["still"] = dm["at"] >= end - 1 / FPS
        if dm["still"] or dm["at"] + dm["span"] > end:
            msg = (f"demo {dm['clip']} shorter than line (talk {dm['line'][0]}-{dm['line'][1]}, "
                   f"demo ends {end:.2f}s) -> holding its last frame")
            if msg not in warnings:
                warnings.append(msg)
        if not dm["still"]:
            used.setdefault(dm["clip"], []).append((dm["at"], min(end, dm["at"] + dm["span"])))
    if sh.get("head_in"):
        if sh["head_in"]["clip"] not in CLIPS:
            raise SystemExit(f"head: unknown clip id {sh['head_in']['clip']!r} (see plan.json clips)")
        used.setdefault(sh["head_in"]["clip"], []).append((sh["a"], sh["b"]))

has_vt = b"h264_videotoolbox" in subprocess.run([ff, "-hide_banner", "-encoders"], env=env, capture_output=True).stdout
TABLE = {}  # clip -> [(src_start, src_end, public_path)]
for clip, rngs in used.items():
    info = CLIPS[clip]
    src = os.path.join(P, "source", info["file"])
    if info.get("media", "link") == "link":
        dest_rel = f"footage/{clip}{os.path.splitext(info['file'])[1].lower()}"
        dest = os.path.join(P, "public", dest_rel)
        if not a.no_media and not os.path.exists(dest):
            try:
                os.link(os.path.realpath(src), dest)
            except OSError:
                warnings.append(f"{clip}: hard link failed (different disk?) -> copied")
                shutil.copy2(os.path.realpath(src), dest)
        TABLE[clip] = [(0.0, 1e9, dest_rel)]
        continue
    m = MEDIA.get(info["file"], {})
    w, h = m.get("w", 1920), m.get("h", 1080)
    if m.get("rotation") in (90, -90, 270, -270):
        w, h = h, w
    # proxyBox lets a project keep more resolution than 1080p: reels zoom into screen recordings,
    # and a 1080p proxy upscaled 2x is visibly soft.
    pb = plan.get("proxyBox")
    box = tuple(pb) if pb else ((1920, 1080) if w >= h else (1080, 1920))
    scale = min(1, box[0] / w, box[1] / h)
    tw, th = int(w * scale) // 2 * 2, int(h * scale) // 2 * 2
    merged = []
    for s, e in sorted((max(0, s - 0.5), e + 0.5) for s, e in rngs):
        if merged and s - merged[-1][1] < 4:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    TABLE[clip] = []
    for s, e in merged:
        rel = f"footage/p_{clip}_{int(s * 10):06d}_{int(e * 10):06d}.mp4"
        TABLE[clip].append((s, e, rel))
        dest = os.path.join(P, "public", rel)
        if a.no_media or (os.path.exists(dest) and not a.rebuild):
            continue
        # proxyEncoder: "x264" forces software encoding. h264_videotoolbox produced corrupt
        # macroblocks on fast-scrolling screen recordings; libx264 is slower but clean.
        soft = plan.get("proxyEncoder") == "x264" or not has_vt
        venc = ["-c:v", "libx264", "-crf", "18", "-preset", "veryfast"] if soft else ["-c:v", "h264_videotoolbox", "-b:v", "18M"]
        # one keyframe a second: Remotion seeks per frame, and long GOPs made Chrome decode
        # macroblock garbage on some frames of a videotoolbox-encoded proxy.
        venc += ["-g", str(FPS), "-keyint_min", str(FPS), "-sc_threshold", "0"]
        aud = ["-map", "0:a:0?", "-ar", "48000", "-c:a", "aac", "-b:a", "192k"]
        if plan.get("loudnorm", True) and info.get("audio", True):
            aud[4:4] = ["-af", "loudnorm=I=-18:TP=-1.5:LRA=11"]
        cmd = [ff, "-v", "error"] + (["-hwaccel", "videotoolbox"] if has_vt and not soft else []) + [
            "-ss", f"{s:.3f}", "-i", src, "-t", f"{e - s:.3f}", "-map", "0:v:0", "-dn", "-map_metadata", "-1",
            "-vf", f"scale={tw}:{th},format=yuv420p", "-r", str(FPS)] + venc + aud + ["-movflags", "+faststart", "-y", dest]
        print(f"proxy {rel} ({e - s:.1f}s)", flush=True)
        subprocess.run(cmd, env=env, check=True)


def locate(clip, t):
    for s, e, rel in TABLE[clip]:
        if s - 1e-3 <= t <= e:
            return rel, t - s
    raise SystemExit(f"{clip}@{t}: not inside any proxy range")


def src_size(clip):
    """Display size of a clip's source (crop rects are fractions of it)."""
    info = CLIPS[clip]
    m = MEDIA.get(info["file"])
    if m and m.get("w"):
        w, h = m["w"], m["h"]
        return (h, w) if m.get("rotation") in (90, -90, 270, -270) else (w, h)
    out = subprocess.check_output([fp, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                   "-of", "csv=p=0", os.path.join(P, "source", info["file"])], env=env, text=True)
    w, h = (int(v) for v in out.strip().split(",")[:2])
    return w, h


def last_frame(clip):
    """public/footage still of a clip's last frame (for a demo that runs out before its line)."""
    t = max(0.0, clip_dur(clip) - 1 / FPS)
    rel = f"footage/still_{clip}_{int(round(t * 1000))}.png"
    dest = os.path.join(P, "public", rel)
    if not a.no_media and (not os.path.exists(dest) or a.rebuild):
        # Decode the last second and keep overwriting one png: the container duration can outlast the
        # last video frame (audio runs longer), and a seek to exactly dur - 1/30 then yields no frame.
        subprocess.run([ff, "-v", "error", "-ss", f"{max(0.0, t - 1):.3f}", "-i", os.path.join(P, "source", CLIPS[clip]["file"]),
                        "-map", "0:v:0", "-update", "1", "-y", dest], env=env, check=True)
        if not os.path.exists(dest):
            raise SystemExit(f"demo {clip}: could not grab its last frame")
    return rel


def demo_out(dm):
    """Shot.demo for Reel.tsx from a demo_span (+ the still decision made with the media ranges)."""
    if dm.get("card"):
        return {"kind": "card"}
    if dm["still"]:
        return {"kind": "still", "photo": last_frame(dm["clip"])}
    rel, off = locate(dm["clip"], dm["at"])
    if "rect" in dm:
        w, h = src_size(dm["clip"])
        o = {"kind": "crop", "src": rel, "from": round(off, 3), "srcW": w, "srcH": h, "rect": dm["rect"]}
        if "rectTo" in dm:
            o["rectTo"] = dm["rectTo"]
        return dict(o, cy=dm.get("cy", 0.42))
    return dict({"kind": "video", "src": rel, "from": round(off, 3), "speed": dm["speed"]},
                **{k: dm[k] for k in ("x", "y", "zoom") if k in dm})


def blur_for(clip, s0, s1):
    return [r for b in plan.get("blur", []) if b["clip"] == clip and s0 < b["to"] and s1 > b["from"] for r in b["rects"]]


# ---------------------------------------------------------------- long timeline (frames)
has_talk = any("talk" in it for s in L.get("sections", []) for it in s.get("items", []))
captions = L.get("captions", "auto")
if captions == "auto":
    captions = "top" if any(sh.get("subs") for s in long_secs for sh in s["shots"]) else "bottom"
ambient = L.get("ambient", 0)


def to_shot(sh, start):
    n = fr(sh["dur"])
    o = {"start": start, "len": n}
    for k2 in ("x", "y", "zoom", "fit", "chip", "trans", "box"):
        if k2 in sh:
            o[k2] = sh[k2]
    if "photo" in sh:
        o["photo"] = sh["photo"]
    else:
        rel, off = locate(sh["clip"], sh["a"])
        o.update(src=rel, from_=round(off, 3), speed=sh["speed"], srcClip=f"{sh['clip']}@{sh['a']:.2f}")
        vol = sh.get("vol")
        if vol is None:
            vol = ambient if sh["speed"] == 1 else 0
        if vol:
            o["vol"] = vol
        subs, srt = [], sorted(sh.get("subs", []))
        for i, (s, e, t) in enumerate(srt):
            nxt = srt[i + 1][0] if i + 1 < len(srt) else 1e9
            s2, e2 = max(s, sh["a"]), min(e + 0.25, nxt, sh["b"])
            if e2 - s2 > 0.15:
                a_ = fr((s2 - sh["a"]) / sh["speed"])
                subs.append({"from": a_, "len": max(1, min(n, fr((e2 - sh["a"]) / sh["speed"])) - a_), "text": t})
        if subs:
            o["subs"] = subs
        blur = blur_for(sh["clip"], sh["a"], sh["b"])
        if blur:
            o["blur"] = blur
    # annotations ride along with the shot they were anchored to, so silence cuts can't desync them
    anns = []
    for an in sh.get("anns", []):
        s_, e_ = an["at"]
        s2, e2 = (max(s_, sh["a"]), min(e_, sh["b"])) if "clip" in sh else (s_, e_)
        if e2 - s2 > 0.1:
            a_ = fr((s2 - (sh["a"] if "clip" in sh else s_)) / sh.get("speed", 1))
            b_ = fr((e2 - (sh["a"] if "clip" in sh else s_)) / sh.get("speed", 1))
            anns.append(dict(drop(an, "at"), start=a_, len=max(1, min(n, b_) - a_)))
    if anns:
        o["anns"] = anns
    if sh.get("music"):
        o["music"] = True
    return o


t = 0
# burnSubs: false = subtitles go to .srt caption tracks (export_srt.py) instead of the picture
LONG = {"fps": FPS, "captions": captions, "burnSubs": L.get("burnSubs", True), "intro": L.get("intro"), "sections": []}
for i, sec in enumerate(long_secs):
    shots = []
    for sh in sec["shots"]:
        shots.append(to_shot(sh, t))
        t += shots[-1]["len"]
    LONG["sections"].append({k2: sec[k2] for k2 in ("title", "sub", "step", "counter") if sec.get(k2) is not None}
                            | {"start": shots[0]["start"] if shots else t, "len": sum(s["len"] for s in shots), "shots": shots})
    if i == 0 and L.get("listCard"):
        lc = L["listCard"]
        LONG["listCard"] = dict(drop(lc, "sec"), start=t, len=fr(lc["sec"]))
        t += fr(lc["sec"])
if long_secs and not L.get("listCard"):
    LONG["listCard"] = None

# music
mus = L.get("music") or {}
mfile = os.path.join(P, "public", mus.get("file", "music.mp3"))
song = duration(mfile, P) if os.path.exists(mfile) else None
mode = mus.get("mode", "auto")
if mode == "auto":
    mode = "broll" if has_talk else "bed"

if L.get("outro"):
    osec = L["outro"]["sec"]
    if mode == "bed" and mus.get("matchSong") and song:
        cred = fr(L["credits"]["sec"]) if L.get("credits") else 0
        osec = max(osec, (fr(song - mus.get("startSec", 0)) - t - cred) / FPS)
    LONG["outro"] = dict(drop(L["outro"], "sec"), start=t, len=fr(osec))
    t += fr(osec)
if L.get("credits"):
    LONG["credits"] = dict(drop(L["credits"], "sec"), start=t, len=fr(L["credits"]["sec"]))
    t += fr(L["credits"]["sec"])
main_end = t
if post_shots:
    shots = []
    for sh in post_shots:
        shots.append(to_shot(sh, t))
        t += shots[-1]["len"]
    LONG["post"] = {"start": main_end, "len": t - main_end, "shots": shots}
LONG["total"] = max(t, 1)

runs = []
if song and long_secs:
    vol = mus.get("volume", 0.7 if mode == "bed" else 0.15)
    if mode == "bed":
        runs = [{"start": 0, "len": main_end, "songFrom": mus.get("startSec", 0)}]
    elif mode == "duck":
        # one continuous bed, looped [loopFrom, loopTo) of the song, ducked under talk shots
        runs = duck_runs(mus, song, main_end, 15, 60, "long")
    else:
        spans = [(s["start"], s["len"]) for sec in LONG["sections"] for s in sec["shots"] if s.get("music")]
        for key in ("listCard", "outro", "credits"):
            if LONG.get(key):
                spans.append((LONG[key]["start"], LONG[key]["len"]))
        pos = mus.get("startSec", 0)
        for st, n in sorted(spans):
            if runs and runs[-1]["start"] + runs[-1]["len"] == st:
                runs[-1]["len"] += n
            else:
                if pos + n / FPS > song - 1:
                    pos = mus.get("startSec", 0)  # wrap at a run boundary; the fades hide it
                runs.append({"start": st, "len": n, "songFrom": round(pos, 3)})
            pos += n / FPS
    LONG["music"] = {"file": mus.get("file", "music.mp3"), "volume": vol, "mode": mode, "runs": runs,
                     "fadeIn": 15 if mode == "bed" else 10, "fadeOut": 60 if mode == "bed" else 15}
    if mode == "duck":
        duck = []
        for sec in LONG["sections"]:
            for s in sec["shots"]:
                if not s.get("music") and "photo" not in s:
                    if duck and duck[-1][1] >= s["start"] - 6:
                        duck[-1][1] = s["start"] + s["len"]
                    else:
                        duck.append([s["start"], s["start"] + s["len"]])
        LONG["music"]["duck"] = duck
        LONG["music"]["duckVolume"] = mus.get("duckVolume", 0.04)
else:
    LONG["music"] = None

# ---------------------------------------------------------------- reels (1080x1920)
# Each reel is a flat, silence-cut shot list with its own music bed. Annotations are lifted from
# shot-local frames to the reel timeline so Reel.tsx can draw them without knowing about cutting.
LIST_JOIN = 3  # frames: a list this close after the previous list, with the same rows, continues it


def list_rows(an):
    return [str(i).lstrip("*") for i in an.get("items") or []]


def join_lists(anns):
    """Mark a list that continues the previous list on screen (same rows, only the highlight moved; also the
    pieces one list is split into by silence cuts): noIntro = drawn fully from its first frame, and the one
    before it gets noOutro = no fade-out. Otherwise each would replay its entrance and flash an empty card."""
    prev = None
    for an in sorted(anns, key=lambda x: x["start"]):
        if an.get("kind") != "list":
            continue
        if prev is not None and 0 <= an["start"] - (prev["start"] + prev["len"]) <= LIST_JOIN \
                and list_rows(an) == list_rows(prev):
            an["noIntro"] = True
            prev["noOutro"] = True
        prev = an
    return anns


def build_reel(spec, shots_src, idx):
    rid = spec.get("id") or f"Reel{idx + 1}"
    tt = 0
    shots, anns = [], []
    for sh in shots_src:
        o = to_shot(sh, tt)
        if "demo_in" in sh:
            o["demo"] = demo_out(sh["demo_in"])
        if "head_in" in sh:
            rel, off = locate(sh["head_in"]["clip"], sh["a"])
            o["head"] = {"src": rel, "from": round(off, 3), "pos": sh["head_in"].get("pos", "bl")}
            if shots and shots[-1].get("head"):
                o["head"]["prevPos"] = shots[-1]["head"]["pos"]
        for an in o.pop("anns", []):
            anns.append(dict(an, start=an["start"] + tt))
        shots.append(o)
        tt += o["len"]
    body_end = tt
    R = {"id": rid, "slug": spec.get("slug", rid.lower()), "title": spec.get("title", rid),
         "fps": FPS, "shots": shots, "anns": join_lists(anns), "hook": None, "end": None}
    if spec.get("hook"):
        hk = spec["hook"]
        R["hook"] = dict(drop(hk, "sec"), start=0, len=min(fr(hk.get("sec", 2.2)), body_end or 1))
    if spec.get("end"):
        en = spec["end"]
        R["end"] = dict(drop(en, "sec"), start=tt, len=fr(en.get("sec", 2.5)))
        # the end card plays over a freeze of nothing, so give it its own slot on the timeline
        tt += R["end"]["len"]
    R["total"] = max(tt, 1)

    # "music": null in the spec = no music track, even if public/music.mp3 exists
    no_music = "music" in spec and spec["music"] is None
    rmus = spec.get("music") or {}
    rfile = os.path.join(P, "public", rmus.get("file", "music.mp3"))
    rsong = duration(rfile, P) if not no_music and os.path.exists(rfile) else None
    if rsong and shots:
        rmode = rmus.get("mode", "duck")
        rvol = rmus.get("volume", 0.14)
        rruns = []
        if rmode == "duck":
            rruns = duck_runs(rmus, rsong, R["total"], 12, 24, rid)
        else:
            rruns = [{"start": 0, "len": R["total"], "songFrom": rmus.get("startSec", 0)}]
        R["music"] = {"file": rmus.get("file", "music.mp3"), "volume": rvol, "mode": rmode, "runs": rruns,
                      "fadeIn": 12, "fadeOut": 24}
        duck = []
        for sh2 in shots:
            if not sh2.get("music") and "photo" not in sh2:
                if duck and duck[-1][1] >= sh2["start"] - 6:
                    duck[-1][1] = sh2["start"] + sh2["len"]
                else:
                    duck.append([sh2["start"], sh2["start"] + sh2["len"]])
        R["music"]["duck"] = duck
        R["music"]["duckVolume"] = rmus.get("duckVolume", 0.035)
    else:
        R["music"] = None
    return R


REELS = [build_reel(spec, reel_shots[i], i) for i, spec in enumerate(REELS_IN)]

# ---------------------------------------------------------------- short timeline
SHORT = None
if short_secs:
    secs = []
    for sec in short_secs:
        shots = []
        for sh in sec["shots"]:
            o = {"start": sh["start"], "len": sh["len"]}
            for k2 in ("x", "y", "fit"):
                if k2 in sh:
                    o[k2] = sh[k2]
            if "photo" in sh:
                o["photo"] = sh["photo"]
            else:
                rel, off = locate(sh["clip"], sh["a"])
                o.update(src=rel, from_=round(off, 3), speed=sh["speed"], srcClip=f"{sh['clip']}@{sh['a']:.2f}")
                blur = blur_for(sh["clip"], sh["a"], sh["b"])
                if blur:
                    o["blur"] = blur
            shots.append(o)
        secs.append({k2: sec[k2] for k2 in ("big", "small") if sec.get(k2)} |
                    {"start": shots[0]["start"], "len": sum(s["len"] for s in shots), "shots": shots})
    end = S.get("end") or {"beats": 4}
    es = beat_frame(short_end_beat)
    total = beat_frame(short_end_beat + end["beats"]) + fr(SM.get("tail", 0.4))
    sfile = os.path.join(P, "public", SM.get("file", "music.mp3"))
    SHORT = {"fps": FPS, "sections": secs, "end": dict(drop(end, "beats"), start=es, len=total - es), "total": total,
             "music": {"file": SM.get("file", "music.mp3"), "startSec": SM.get("startSec", 0),
                       "volume": SM.get("volume", 0.85)} if os.path.exists(sfile) else None}

# ---------------------------------------------------------------- thumbnail
THUMB = None
if plan.get("thumbnail"):
    th = plan["thumbnail"]
    panels = []
    for pn in th["panels"]:
        o = {k2: pn[k2] for k2 in ("cx", "cy", "zoom", "dx", "dy") if k2 in pn}
        if "photo" in pn:
            o["src"] = pn["photo"]
        else:  # a frame grabbed from the ORIGINAL at full quality (not the proxy)
            rel = f"footage/thumb_{pn['clip']}_{int(pn['at'] * 100)}.jpg"
            dest = os.path.join(P, "public", rel)
            if not os.path.exists(dest) or a.rebuild:
                subprocess.run([ff, "-v", "error", "-ss", f"{pn['at']:.3f}", "-i", os.path.join(P, "source", CLIPS[pn["clip"]]["file"]),
                                "-frames:v", "1", "-vf", "scale='min(2560,iw)':-2,format=yuv420p", "-q:v", "2", "-y", dest],
                               env=env, check=True)
            o["src"] = rel
        panels.append(o)
    THUMB = {"panels": panels, **{k2: th[k2] for k2 in ("title", "badge", "kicker") if th.get(k2)}}

# ---------------------------------------------------------------- write outputs
ts = ("// GENERATED by build_edit.py from plan.json. Edit plan.json and re-run; don't edit this file.\n"
      "import type {LongData, ReelData, ShortData, ThumbData} from './types';\n\n"
      f"export const LONG: LongData | null = {json.dumps(LONG if long_secs else None, indent=1, ensure_ascii=False)};\n\n"
      f"export const SHORT: ShortData | null = {json.dumps(SHORT, indent=1, ensure_ascii=False)};\n\n"
      f"export const THUMB: ThumbData | null = {json.dumps(THUMB, indent=1, ensure_ascii=False)};\n\n"
      f"export const REELS: ReelData[] = {json.dumps(REELS, indent=1, ensure_ascii=False)};\n").replace('"from_"', '"from"')
open(os.path.join(P, "src/edit-data.ts"), "w").write(ts)

emap = []
if long_secs:
    for sec in LONG["sections"]:
        for s in sec["shots"]:
            kind = "photo" if "photo" in s else ("broll" if s.get("music") else "talk")
            emap.append(dict(comp="long", start=s["start"] / FPS, end=(s["start"] + s["len"]) / FPS, kind=kind,
                             clip=s.get("srcClip") or s.get("photo"), section=sec.get("title")))
    for key in ("listCard", "outro", "credits"):
        if LONG.get(key):
            emap.append(dict(comp="long", start=LONG[key]["start"] / FPS, end=(LONG[key]["start"] + LONG[key]["len"]) / FPS,
                             kind=key, clip=None, section=key))
    if LONG.get("post"):
        for s in LONG["post"]["shots"]:
            emap.append(dict(comp="long", start=s["start"] / FPS, end=(s["start"] + s["len"]) / FPS, kind="post",
                             clip=s.get("srcClip") or s.get("photo"), section="post"))
if SHORT:
    for sec in SHORT["sections"]:
        for s in sec["shots"]:
            emap.append(dict(comp="short", start=s["start"] / FPS, end=(s["start"] + s["len"]) / FPS,
                             kind="photo" if "photo" in s else "shot", clip=s.get("srcClip") or s.get("photo"), section=sec.get("big")))
for R in REELS:
    for sh2 in R["shots"]:
        emap.append(dict(comp=R["id"], start=sh2["start"] / FPS, end=(sh2["start"] + sh2["len"]) / FPS,
                         kind="photo" if "photo" in sh2 else ("broll" if sh2.get("music") else "talk"),
                         clip=sh2.get("srcClip") or sh2.get("photo"), section=R["title"]))
json.dump(sorted(emap, key=lambda r: (r["comp"], r["start"])), open(os.path.join(P, "edit-map.json"), "w"), indent=0)

if long_secs:
    talk = sum(s["len"] for sec in LONG["sections"] for s in sec["shots"] if "vol" in s and not s.get("music")) / FPS
    print(f"long: {LONG['total'] / FPS:.1f}s total ({main_end / FPS:.1f}s main, talk {talk:.1f}s), "
          f"{sum(len(s['shots']) for s in LONG['sections'])} shots, captions={captions}, music={mode if song else 'none'}"
          + (f" ({len(runs)} runs, song {song:.1f}s)" if song else ""))
if THUMB:
    print(f"thumbnail: {len(THUMB['panels'])} panel(s), title {THUMB['title']!r}")
if SHORT:
    print(f"short: {SHORT['total'] / FPS:.2f}s, {short_end_beat + (S.get('end') or {'beats': 4})['beats']} beats")
for R in REELS:
    talk_s = sum(x["len"] for x in R["shots"] if "vol" in x and not x.get("music")) / FPS
    print(f"{R['id']}: {R['total'] / FPS:.1f}s, {len(R['shots'])} shots (talk {talk_s:.1f}s), "
          f"{len(R['anns'])} annotations, music={'duck' if R['music'] else 'none'}  -> {R['title']}")
for w in warnings:
    print("WARN", w)
