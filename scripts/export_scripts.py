#!/usr/bin/env python3
"""Export the reel scripts as one readable document to review before recording.

  python3 export_scripts.py <P>      reads <P>/scripts/reels.json -> writes <P>/SCRIPTS.md

One section per reel: hook card, numbered lines (what is read on the teleprompter), and under each line the
demo beat, the head position and the annotations drawn on screen; then the end card. Lines marked
"confirm": true (claims that still need checking) are flagged for sign-off. The labels are English; the
script text stays in whatever language it is written in.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_scripts import duration  # noqa: E402

HEAD = {"bl": "small, bottom left", "tl": "small, top left", "big": "big, centre"}


def flat(s):
    return " / ".join(p.strip() for p in str(s).split("\n"))


def ann_md(a):
    k = a.get("kind")
    when = f" ({a.get('in', 0.1):.0%}–{a.get('out', 1.0):.0%} of the line)"
    if k in ("label", "note"):
        what = f"“{flat(a.get('text', ''))}”"
    elif k == "list":
        what = "; ".join(f"**{i[1:]}**" if str(i).startswith("*") else str(i) for i in a.get("items", []))
    elif k == "bar":
        what = "; ".join(f"{label}" for label, _ in a.get("bars", []))
    else:
        what = f"at ({a.get('x')}, {a.get('y')})"
    return f"{k} {what}{when}"


def card_md(c):
    s = flat(c.get("big", ""))
    if c.get("small"):
        s += f" — _{flat(c['small'])}_"
    return s


def export(doc):
    wpm = doc["wpm"]
    out = ["# Reel scripts", "",
           f"Durations estimated at {wpm} words per minute. Each numbered line is one teleprompter line;",
           "under it, what is on screen meanwhile.", ""]
    for r in doc["reels"]:
        out += [f"## {r['id']} · {r['title']} (~{duration(r, wpm):.0f} s)", "",
                f"**Hook card:** {card_md(r['hook'])}", ""]
        for n, l in enumerate(r["lines"], 1):
            out.append(f"{n}. {l['text']}" + (" **(claim to confirm)**" if l.get("confirm") else ""))
            note = f"demo `{l.get('demo')}` · head {HEAD.get(l.get('head', 'bl'), l.get('head'))}"
            anns = l.get("anns") or []
            if anns:
                note += " · " + " · ".join(ann_md(a) for a in anns)
            out += [f"   <br>_{note}_", ""]
        end = f"**End card:** {card_md(r['end'])}"
        if r["end"].get("items"):
            end += " · recap: " + "; ".join(r["end"]["items"])
        out += [end, ""]
        if r.get("caption"):
            out += [f"**Post caption:** {r['caption']}", ""]
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: export_scripts.py <project>")
    P = os.path.abspath(sys.argv[1])
    with open(os.path.join(P, "scripts", "reels.json"), encoding="utf8") as f:
        md = export(json.load(f))
    with open(os.path.join(P, "SCRIPTS.md"), "w", encoding="utf8") as f:
        f.write(md)
    print(f"-> {os.path.join(P, 'SCRIPTS.md')}")
