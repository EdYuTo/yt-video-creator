#!/usr/bin/env python3
"""Rank 30-s windows of a VOD into a reading list of candidate moments. Run with the venv python.

usage: find_moments.py --project <proj> [--top 45] [--lang pt|en|es|all] [--win 30 --hop 15]
  reads analysis/skim/*.json (skim_vod.py) + analysis/audio.json (vod_audio.py)
  -> analysis/moments.md: rank, time, score, tags (laugh/swear/wow/chat/game/hype/story), words,
     loudness, transcript excerpt

This is a READING LIST, not the answer. In the first run the best Shorts (a storytime with a
punchline, friends roasting the streamer, "I'm top of the scoreboard so we're doomed") scored
mid-table; they were found by reading the transcript around these windows (skim_vod.py ctx).
"""
import argparse
import glob
import json
import os
import re

import numpy as np

from _base import hms

PATTERNS = {
    "pt": {
        "laugh": r"k{3,}|(ha){2,}|(ah){3,}|hahah|risos",
        "swear": r"\b(caralho|porra|puta|merda|foda|cacete|pqp|vsf|fdp|desgra[cç])",
        "wow": r"\b(nossa|meu deus|n[aã]o acredito|que isso|como assim|mentira|absurdo|inacredit|olha isso|olha s[oó])",
        "chat": r"\b(chat|galera|voc[eê]s|live|sub|follow|seguid|twitch|stream|mods?)\b",
        "game": r"\b(ace|clutch|um contra|virada|cheat|chit|hack|wall|headshot|hs\b|faca|awp|campe[aã]o|ganhamos|perdemos|rank)",
        "hype": r"\b(vamo+|bora|vai vai|toma+|pega+|lindo|monstro|insano)",
        "story": r"\b(a[ií] eu|ent[aã]o eu|tipo assim|ser[aá] que|sabe o que|um dia|aconteceu)",
    },
    "en": {
        "laugh": r"(ha){2,}|lmao|lol\b|hahah",
        "swear": r"\b(fuck|shit|damn|bitch|wtf|holy)",
        "wow": r"\b(oh my god|omg|no way|what the|are you kidding|insane|unbelievable|look at this)",
        "chat": r"\b(chat|guys|stream|sub|follow|mods?|viewers?)\b",
        "game": r"\b(ace|clutch|1v\d|cheat|hack|wall|headshot|knife|awp|ranked|won|lost)\b",
        "hype": r"\b(let'?s go+|come on|ez|easy|clean|sick|cracked)",
        "story": r"\b(so i|one time|guess what|you know what|this one time|story)",
    },
    "es": {
        "laugh": r"j{3,}|(ja){2,}|jaja",
        "swear": r"\b(joder|mierda|puta|cabr[oó]n|carajo|hostia|verga)",
        "wow": r"\b(dios m[ií]o|no puede ser|qu[eé] es eso|mira esto|incre[ií]ble|en serio)",
        "chat": r"\b(chat|gente|stream|sub|follow|mods?)\b",
        "game": r"\b(ace|clutch|cheat|hack|headshot|cuchillo|awp|ganamos|perdimos)\b",
        "hype": r"\b(vamos+|dale|ez|f[aá]cil|brutal)",
        "story": r"\b(entonces yo|una vez|sabes qu[eé]|resulta que)",
    },
}
WEIGHT = {"laugh": 3, "swear": 1.5, "wow": 2, "chat": 1.2, "game": 1.5, "hype": 1.2, "story": 1.5}

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True)
ap.add_argument("--top", type=int, default=45)
ap.add_argument("--lang", default="all")
ap.add_argument("--win", type=int, default=30)
ap.add_argument("--hop", type=int, default=15)
a = ap.parse_args()
AN = os.path.join(os.path.abspath(a.project), "analysis")
pats = {}
for lang, ps in PATTERNS.items():
    if a.lang in ("all", lang):
        for k, p in ps.items():
            pats[k] = f"{pats[k]}|{p}" if k in pats else p

segs = []
for f in sorted(glob.glob(os.path.join(AN, "skim", "c*_*.json"))):
    off = int(re.search(r"_(\d+)\.json$", f).group(1))
    prev = None
    for s in json.load(open(f)):
        if s["text"] == prev or "​" in s["text"]:
            continue
        prev = s["text"]
        segs.append((off + s["start"], s["text"]))
audio = json.load(open(os.path.join(AN, "audio.json")))
db, med = np.array(audio["db"]), audio["global_median_db"]
rows = []
for t0 in range(0, len(db) - a.win, a.hop):
    text = " ".join(t for s, t in segs if t0 <= s < t0 + a.win).lower()
    tags = {k: len(re.findall(p, text)) * WEIGHT[k] for k, p in pats.items()}
    words = len(text.split())
    loud = float(np.clip(np.percentile(db[t0:t0 + a.win], 90) - med, 0, 30))
    spread = float(np.percentile(db[t0:t0 + a.win], 95) - np.percentile(db[t0:t0 + a.win], 30))
    rows.append((sum(tags.values()) + 0.04 * words + 0.25 * loud + 0.08 * spread, t0, tags, words, loud, text))
rows.sort(key=lambda r: -r[0])
picked = []
for r in rows:
    if all(abs(r[1] - p[1]) >= 45 for p in picked):
        picked.append(r)
    if len(picked) >= a.top:
        break
out = os.path.join(AN, "moments.md")
with open(out, "w") as fh:
    fh.write("# Candidate moments (reading list: open each with `skim_vod.py ctx`)\n\n| # | time | score | tags | words | loud | excerpt |\n|---|---|---|---|---|---|---|\n")
    for i, (s, t0, tags, words, loud, text) in enumerate(picked, 1):
        tg = " ".join(f"{k}{v:g}" for k, v in tags.items() if v)
        fh.write(f"| {i} | {hms(t0)} | {s:.1f} | {tg} | {words} | {loud:.0f} | {text[:200].replace('|', '/')} |\n")
print(f"{len(picked)} windows -> {out}")
for i, (s, t0, tags, words, loud, text) in enumerate(picked[:15], 1):
    print(f"{i:2d} {hms(t0)} {s:5.1f} {text[:110]}")
