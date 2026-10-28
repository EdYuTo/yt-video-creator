#!/usr/bin/env python3
"""Validate the reel scripts (P/scripts/reels.json) before they are read or recorded.

  python3 check_scripts.py <P>/scripts/reels.json      -> prints one problem per line, exit 1 if any

Always checked (the shape the teleprompter, assemble_reels.py and Reel.tsx rely on): unique reel ids that
are safe in file names, slug/title, hook and end cards, line text, a demo id per line, head position,
annotation kinds/fields/in-out timing/size, unique slugs, and annotations clear of the head bubble, the subtitle band,
the platform's right-hand buttons and each other. Annotation sizes are estimates of what Reel.tsx draws.

Content rules are per project, from the top-level "rules" object of reels.json (all optional):
  {"noPrices": false,          # flag currency amounts in any text
   "banned": [],               # regexes (case-insensitive) that must not appear in any text
   "maxWords": 22,             # words per line (one teleprompter screen)
   "durationRange": [20, 90]}  # estimated seconds per reel at the doc's wpm
"""
import json
import re
import sys

HEADS = {"bl": (5, 51, 32, 72), "tl": (5, 11, 32, 28), "big": (22, 29, 78, 72)}  # x0, y0, x1, y1 (% of frame)
SUB_TOP, RAIL = 76, 88
KINDS = {"label": ["text"], "note": ["text"], "list": ["items"], "bar": ["bars"], "ring": [], "arrow": ["to"]}
LINE_TAIL = 0.6  # seconds of pause per line in the duration estimate
DEFAULT_RULES = {"noPrices": False, "banned": [], "maxWords": 22, "durationRange": [20, 90]}
SIZE_RANGE = (0.5, 3)
PRICE = re.compile(r"[A-Z]{0,2}[$€£¥₹]\s*\d|\d[\d.,]*\s*[$€£¥₹]|\d[\d.,]*\s*(d[óo]lar(es)?|dollars?|reais|euros?|pounds?|usd|eur|gbp|brl)\b", re.I)
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")  # reel and demo ids end up in file and clip names
W, H = 1080, 1920


def words(text):
    return [t for t in text.split() if any(c.isalnum() for c in t)]


def duration(reel, wpm):
    return sum(len(words(str(l.get("text", "")) if isinstance(l, dict) else "")) * 60 / wpm + LINE_TAIL
               for l in reel.get("lines", []))


def ann_texts(ann):
    """Every piece of text an annotation shows (tolerates malformed fields; check_ann reports those)."""
    if isinstance(ann.get("text"), str):
        yield ann["text"]
    if isinstance(ann.get("items"), list):
        for it in ann["items"]:
            yield str(it)
    if isinstance(ann.get("bars"), list):
        for row in ann["bars"]:
            if isinstance(row, list) and row:
                yield str(row[0])


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def ann_box(a):
    """Estimated (x0, y0, x1, y1) in % of the frame for what Reel.tsx draws (blocks scale by `size`)."""
    x, y = a["x"], a["y"]
    k = a["kind"]
    s = a.get("size", 1)
    if k == "ring":
        rx = (a.get("w") or 26) / 2
        ry = rx * W / H * 0.52
        return x - rx, y - ry, x + rx, y + ry
    if k == "arrow":
        tx, ty = a["to"]
        return min(x, tx), min(y, ty), max(x, tx), max(y, ty)
    if k == "label":
        wpx, hpx = len(a["text"]) * 0.55 * 46 + 60, 46 * 1.25 + 28
    elif k == "note":
        size = 60 if len(a["text"]) > 26 else 72
        rows = a["text"].split("\n")
        wpx = max(len(r) for r in rows) * 0.5 * size + 52
        hpx = len(rows) * size * 1.12 + 28 + 32
    elif k == "list":
        items = [str(i).lstrip("*") for i in a["items"]]
        wpx = max((len(i) for i in items), default=0) * 0.5 * 54 + 58 + 52
        hpx = len(items) * (54 * 1.12 + 16) + 22
    else:  # bar
        wpx = (a.get("w") or 40) / 100 * W + 52
        hpx = len(a["bars"]) * (46 * 1.12 + 44) + 32
    if a.get("w") and k in ("note", "list"):
        wpx = a["w"] / 100 * W + 52
    return x, y, x + wpx * s / W * 100, y + hpx * s / H * 100


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def check_ann(where, a, head):
    if not isinstance(a, dict):
        return [f"{where}: not an object"]
    k = a.get("kind")
    if k not in KINDS:
        return [f"{where}: unknown kind {k!r} (one of {', '.join(KINDS)})"]
    out = []
    for f in ["x", "y"]:
        if not is_num(a.get(f)):
            out.append(f"{where}: {k} needs a number {f}")
    for f in KINDS[k]:
        if not a.get(f):
            out.append(f"{where}: {k} needs {f}")
    if k in ("label", "note") and a.get("text") and not isinstance(a["text"], str):
        out.append(f"{where}: {k} text must be a string")
    if k in ("list", "bar") and a.get(KINDS[k][0]) and not isinstance(a[KINDS[k][0]], list):
        out.append(f"{where}: {k} {KINDS[k][0]} must be a list")
    if k == "arrow" and "to" in a and not (isinstance(a["to"], list) and len(a["to"]) == 2 and all(map(is_num, a["to"]))):
        out.append(f"{where}: arrow 'to' is its end point [x, y]; line timing is in/out")
    if "w" in a and not (is_num(a["w"]) and a["w"] > 0):
        out.append(f"{where}: {k} w must be a positive number (% of frame width), got {a['w']!r}")
    if "rotate" in a and not is_num(a["rotate"]):
        out.append(f"{where}: {k} rotate must be a number of degrees, got {a['rotate']!r}")
    if k == "list" and isinstance(a.get("items"), list) and not all(isinstance(i, str) for i in a["items"]):
        out.append(f"{where}: list items must be strings")
    if k == "bar" and isinstance(a.get("bars"), list):
        for n, row in enumerate(a["bars"], 1):
            if not (isinstance(row, list) and len(row) == 2 and isinstance(row[0], str) and is_num(row[1]) and 0 <= row[1] <= 1):
                out.append(f"{where}: bar row {n} must be [label, fraction 0-1], got {row!r}")
    if "from" in a:
        out.append(f"{where}: 'from' is not used; line timing is in/out")
    if "to" in a and k != "arrow":
        out.append(f"{where}: 'to' is only for arrows (end point); line timing is in/out")
    if "size" in a and not (isinstance(a["size"], (int, float)) and not isinstance(a["size"], bool)
                            and SIZE_RANGE[0] <= a["size"] <= SIZE_RANGE[1]):
        out.append(f"{where}: size must be a number from {SIZE_RANGE[0]} to {SIZE_RANGE[1]} (got {a['size']!r})")
    t_in, t_out = a.get("in", 0.1), a.get("out", 1.0)
    if not (isinstance(t_in, (int, float)) and isinstance(t_out, (int, float)) and 0 <= t_in < t_out <= 1):
        out.append(f"{where}: in/out must be fractions of the line with 0 <= in < out <= 1 (got {t_in!r}, {t_out!r})")
    if out:
        return out
    box = ann_box(a)
    if overlaps(box, HEADS[head]):
        out.append(f"{where}: {k} at ({a['x']}, {a['y']}) may sit under the head bubble ({head})")
    if k not in ("ring", "arrow"):
        if box[3] > SUB_TOP:
            out.append(f"{where}: {k} reaches y {box[3]:.0f} %, into the subtitle band (from {SUB_TOP} %)")
        if box[2] > RAIL:
            out.append(f"{where}: {k} reaches x {box[2]:.0f} %, under the platform's right-hand buttons (from {RAIL} %)")
        if box[0] < 0 or box[1] < 0:
            out.append(f"{where}: {k} starts off frame")
    return out


def check_text(where, text, rules):
    out = []
    if rules["noPrices"] and PRICE.search(text):
        out.append(f"{where}: price {PRICE.search(text).group(0)!r} (rules.noPrices)")
    for pat in rules["banned"]:
        m = re.search(pat, text, re.I)
        if m:
            out.append(f"{where}: {m.group(0)!r} matches banned pattern {pat!r}")
    return out


def load_rules(doc):
    """(rules with defaults filled in, problems with the rules object itself)."""
    raw = doc.get("rules", {})
    if not isinstance(raw, dict):
        return dict(DEFAULT_RULES), ["rules must be an object"]
    out, probs = dict(DEFAULT_RULES), []
    for k, v in raw.items():
        if k not in DEFAULT_RULES:
            probs.append(f"rules: unknown rule {k!r} (one of {', '.join(DEFAULT_RULES)})")
        elif k == "noPrices" and not isinstance(v, bool):
            probs.append("rules.noPrices must be true or false")
        elif k == "banned" and not (isinstance(v, list) and all(isinstance(p, str) for p in v)):
            probs.append("rules.banned must be a list of regex strings")
        elif k == "maxWords" and not (isinstance(v, int) and not isinstance(v, bool) and v > 0):
            probs.append("rules.maxWords must be a positive integer")
        elif k == "durationRange" and not (isinstance(v, list) and len(v) == 2
                                           and all(isinstance(x, (int, float)) for x in v) and 0 <= v[0] <= v[1]):
            probs.append("rules.durationRange must be [min, max] seconds")
        else:
            if k == "banned":
                ok = []
                for pat in v:
                    try:
                        re.compile(pat)
                        ok.append(pat)
                    except re.error as e:
                        probs.append(f"rules.banned: bad regex {pat!r} ({e})")
                v = ok
            out[k] = v
    return out, probs


def check_reel(i, r, wpm, rules, seen):
    rid = r.get("id") if isinstance(r, dict) else None
    if not isinstance(r, dict):
        return [f"reel {i + 1}: not an object"]
    out = []
    if not isinstance(rid, str) or not ID.match(rid):
        out.append(f"reel {i + 1}: id {rid!r} must be letters, digits, '-' or '_' (it names files: takes/<id>.json, voice-<id>)")
    elif rid in seen:
        out.append(f"{rid}: duplicate reel id (also reel {seen[rid] + 1})")
    else:
        seen[rid] = i
    rid = rid if isinstance(rid, str) else f"reel {i + 1}"
    for f in ["slug", "title"]:
        if not isinstance(r.get(f), str) or not r[f].strip():
            out.append(f"{rid}: missing {f}")
        else:
            out += check_text(f"{rid} {f}", r[f], rules)
    slug = r.get("slug")
    if isinstance(slug, str) and slug.strip():
        key = ("slug", slug)  # assemble_reels matches plan.json entries by slug, so slugs must be unique too
        if key in seen:
            out.append(f"{rid}: duplicate slug {slug!r} (also reel {seen[key] + 1})")
        else:
            seen[key] = i
    if isinstance(r.get("caption"), str):
        out += check_text(f"{rid} caption", r["caption"], rules)
    for card in ["hook", "end"]:
        c = r.get(card)
        if not isinstance(c, dict) or not isinstance(c.get("big"), str) or not c["big"].strip():
            out.append(f"{rid}: missing {card} card (needs {{big, small}})")
            continue
        for f in ["big", "small"]:
            if isinstance(c.get(f), str):
                out += check_text(f"{rid} {card}", c[f], rules)
        for it in c.get("items") or []:
            out += check_text(f"{rid} {card}", str(it), rules)
    lines = r.get("lines")
    if not isinstance(lines, list) or not lines:
        return out + [f"{rid}: no lines"]
    for n, l in enumerate(lines, 1):
        where = f"{rid} line {n}"
        if not isinstance(l, dict) or not isinstance(l.get("text"), str) or not l["text"].strip():
            out.append(f"{where}: missing text")
            continue
        out += check_text(where, l["text"], rules)
        nw = len(words(l["text"]))
        if nw > rules["maxWords"]:
            out.append(f"{where}: {nw} words (max {rules['maxWords']}); split it")
        if not isinstance(l.get("demo"), str) or not ID.match(l["demo"]):
            out.append(f"{where}: demo {l.get('demo')!r} must be 'card' or a beat id from demos/manifest.json "
                       "(letters, digits, '-' or '_')")
        head = l.get("head", "bl")
        if head not in HEADS:
            out.append(f"{where}: head {head!r} not one of big, bl, tl")
            head = "bl"
        anns = l.get("anns") or []
        placed = []  # (index, box, in, out) of valid block annotations, for overlap checks
        for j, a in enumerate(anns, 1):
            probs = check_ann(f"{where} ann {j}", a, head)
            out += probs
            if isinstance(a, dict):
                for t in ann_texts(a):
                    out += check_text(f"{where} ann {j}", t, rules)
            if not probs and a["kind"] not in ("ring", "arrow"):
                box, t_in, t_out = ann_box(a), a.get("in", 0.1), a.get("out", 1.0)
                for k, kbox, k_in, k_out in placed:
                    if overlaps(box, kbox) and t_in < k_out and k_in < t_out:
                        out.append(f"{where} ann {j}: overlaps ann {k} on screen at the same time")
                placed.append((j, box, t_in, t_out))
    lo, hi = rules["durationRange"]
    sec = duration(r, wpm)
    if not lo <= sec <= hi:
        out.append(f"{rid}: estimated duration {sec:.1f} s outside {lo}-{hi} s at {wpm} wpm (rules.durationRange)")
    return out


def check(doc):
    """Return the list of problems in a reels.json document (empty = valid)."""
    if not isinstance(doc, dict):
        return ["document is not an object"]
    wpm = doc.get("wpm")
    if not isinstance(wpm, (int, float)) or wpm <= 0:
        return [f"wpm must be a positive number (got {wpm!r})"]
    reels = doc.get("reels")
    if not isinstance(reels, list) or not reels:
        return ["no reels"]
    rules, out = load_rules(doc)
    seen = {}
    for i, r in enumerate(reels):
        out += check_reel(i, r, wpm, rules, seen)
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: check_scripts.py <reels.json>")
    with open(sys.argv[1], encoding="utf8") as f:
        problems = check(json.load(f))
    for p in problems:
        print(p)
    sys.exit(1 if problems else 0)
