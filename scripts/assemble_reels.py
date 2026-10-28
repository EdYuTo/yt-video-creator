#!/usr/bin/env python3
"""Turn the reel scripts + picked takes + demo manifest into plan.json's `reels` list.

  python3 assemble_reels.py <P> [--reels r0,r1]   -> rewrites P/plan.json["reels"] (every other key kept)

Reads P/scripts/reels.json, P/takes/<reel>.json (takes.py) and P/demos/manifest.json. One talk item per
script line that has a take; lines without a take are skipped (takes.py already warned). Then `npm run build`.
The plan.json reel for reels.json entry i (by position, whatever its id) is "Reel<i+1>"; each also records its
script id as "script". `--reels` assembles only those script ids; every other reel keeps whatever plan.json already
has for it, found by "script" (else by slug) — not by position, so reordering reels.json can't mix them up — and
renumbered to its new position. A reel with no takes yet is skipped with a WARN the same way (its plan.json entry,
if any, is kept), so its beats don't need manifest entries yet. A line with a take whose
beat is missing from the manifest is an error: record/describe the beat, or leave that reel out with --reels.

manifest.json: {"<beatId>": {"type": "web"}
                          | {"type": "crop", "clip", "from", "rect", "rectTo"?, "cy"?}
                          | {"type": "video", "clip", "from", "speed"?, "x"?, "y"?, "zoom"?}
                          | {"type": "card"}}
A `web` beat is the recorded page clip `demo-<beatId>`; the line demo id `card` needs no entry.

A run of consecutive emitted items with the same beat id continues one demo: item k's `from` is the beat's
base `from` (0 for web) plus the talk durations (take end - start) of the earlier items in the run, times
the beat's `speed` for video beats. A different beat id or a `card` ends the run. A line without a take
is not in the video, so it neither breaks nor advances a run (A, skipped A, A is one run): the run
continues over the gap only when the beat ids on both sides match. The talk durations are pre-silence-cut,
so the demo over-advances slightly by the silences removed from earlier lines. `demo_runs` / the CLI report
how many seconds of each run the demo recording must cover.
"""
import json
import os
import sys
import tempfile

HOOK_SEC, END_SEC = 2.6, 3.4
CARRY = {"crop": ("clip", "from", "rect", "rectTo", "cy"), "video": ("clip", "from", "speed", "x", "y", "zoom")}


def resolve_demo(beat, manifest, where, offset=0.0):
    """`offset` = seconds of talk already spent on this beat in the current run."""
    if beat == "card":
        return {"card": True}
    entry = manifest.get(beat)
    if entry is None:
        raise ValueError(f"{where}: unknown demo {beat!r} (not 'card' and not in demos/manifest.json)")
    kind = entry.get("type")
    if kind == "web":
        return {"clip": f"demo-{beat}", "from": round(offset, 3)}
    if kind == "card":
        return {"card": True}
    if kind in CARRY:
        d = {k: entry[k] for k in CARRY[kind] if k in entry}
        if offset:  # crop demos play at speed 1; video demos advance `speed` source seconds per second
            d["from"] = round(d["from"] + offset * (d.get("speed", 1) if kind == "video" else 1), 3)
        return d
    raise ValueError(f"{where}: demo {beat!r} has unknown manifest type {kind!r}")


def map_ann(ann, start, end):
    """Line-relative in/out fractions -> absolute source seconds in `at`."""
    t_in, t_out = ann.get("in", 0.1), ann.get("out", 1.0)
    out = {k: v for k, v in ann.items() if k not in ("in", "out")}
    out["at"] = [start + t_in * (end - start), start + t_out * (end - start)]
    return out


def emitted(r, rid, takes):
    """Yield (n, line, take, run, offset) for each line with a take: `run` counts the beat's runs in this
    reel from 0 (None for card lines), `offset` = seconds of talk earlier in the same run."""
    by_line = {t["line"]: t for t in takes.get(rid, [])}
    prev, run, offset, seen = None, -1, 0.0, {}
    for n, line in enumerate(r["lines"]):
        t = by_line.get(n)
        if t is None:
            continue
        beat = line["demo"]
        if beat != prev:
            run, offset = seen.get(beat, -1) + 1, 0.0
            seen[beat] = run
        yield n, line, t, (None if beat == "card" else run), offset
        offset += t["end"] - t["start"]
        prev = beat


def demo_runs(doc, takes):
    """{(reel id, beat id, run index): seconds the demo must cover} for every non-card run."""
    out = {}
    for i, r in enumerate(doc["reels"]):
        rid = r.get("id", f"r{i}")
        for n, line, t, run, offset in emitted(r, rid, takes):
            if run is not None:
                out[(rid, line["demo"], run)] = offset + t["end"] - t["start"]
    return out


def assemble(doc, takes, manifest):
    """doc = reels.json; takes = {"r0": [take, ...]}; -> the plan.json `reels` list."""
    reels = []
    for i, r in enumerate(doc["reels"]):
        rid = r.get("id", f"r{i}")
        items, prev = [], None
        for n, line, t, run, offset in emitted(r, rid, takes):
            beat = line["demo"]
            item = {
                "clip": f"voice-{rid}",
                "talk": [t["start"], t["end"]],
                "subs": t["subs"],
                "anns": [map_ann(a, t["start"], t["end"]) for a in line.get("anns") or []],
                "demo": resolve_demo(beat, manifest, f"{rid} line {n + 1}", offset),
                "head": {"clip": f"bubble-{rid}", "pos": line.get("head", "bl")},
            }
            if prev is None:
                item["trans"] = "zoom"
            elif beat != prev:
                item["trans"] = "whip"
            prev = beat
            items.append(item)
        # talking-head reels have no music unless the script asks for it (same object as plan.json reel music)
        reel = {"id": f"Reel{i + 1}", "slug": r["slug"], "title": r["title"], "music": r.get("music"), "items": items}
        reel["hook"] = dict(r["hook"], sec=HOOK_SEC) if r.get("hook") else None
        reel["end"] = dict(r["end"], sec=END_SEC) if r.get("end") else None
        reels.append(reel)
    return reels


def load(path, default=None):
    if not os.path.exists(path) and default is not None:
        return default
    with open(path, encoding="utf8") as f:
        return json.load(f)


def main(P, only=None):
    """`only`: script reel ids to assemble (None = all); the rest keep their current plan.json entry."""
    doc = load(os.path.join(P, "scripts", "reels.json"))
    manifest = load(os.path.join(P, "demos", "manifest.json"), {})
    ids = [r.get("id", f"r{i}") for i, r in enumerate(doc["reels"])]
    if only is not None:
        unknown = [x for x in only if x not in ids]
        if unknown:
            raise ValueError(f"--reels: {', '.join(unknown)} not in scripts/reels.json (have: {', '.join(ids)})")
    plan_path = os.path.join(P, "plan.json")
    plan = load(plan_path)
    old_entries = [r for r in plan.get("reels") or [] if isinstance(r, dict)]

    def previous(i):
        """This reel's current plan.json entry: matched by the script id it records, else by slug."""
        r = doc["reels"][i]
        hit = next((e for e in old_entries if e.get("script") == ids[i]), None)
        if hit is None and r.get("slug"):
            hit = next((e for e in old_entries if "script" not in e and e.get("slug") == r["slug"]), None)
        return hit

    takes, chosen = {}, []
    for i, rid in enumerate(ids):
        if only is not None and rid not in only:
            continue
        takes[rid] = load(os.path.join(P, "takes", f"{rid}.json"), [])
        if not takes[rid]:
            kept = "plan.json entry kept" if previous(i) else "not in plan.json yet"
            print(f"WARN {rid}: no takes yet (takes/{rid}.json missing or empty); skipped ({kept})")
            continue
        chosen.append(i)
    sub = dict(doc, reels=[dict(doc["reels"][i], id=ids[i]) for i in chosen])
    built = dict(zip(chosen, assemble(sub, takes, manifest)))
    reels = []
    for i in range(len(ids)):
        if i in built:
            # assemble() numbered the subset; keep the full-doc numbering
            reels.append(dict(built[i], id=f"Reel{i + 1}", script=ids[i]))
        elif previous(i) is not None:
            reels.append(dict(previous(i), id=f"Reel{i + 1}", script=ids[i]))
    plan["reels"] = reels
    fd, tmp = tempfile.mkstemp(prefix="plan.json.", dir=P)
    try:
        with os.fdopen(fd, "w", encoding="utf8") as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, plan_path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    for i, r in built.items():
        print(f"Reel{i + 1} {r['slug']}: {len(r['items'])} items")
    for (rid, beat, run), sec in demo_runs(sub, takes).items():
        if manifest.get(beat, {}).get("type", "web") == "web":
            print(f"  record {beat} (run {run + 1}): at least {sec:.1f} s")
    print(f"-> {plan_path} ({len(built)} assembled, {len(reels)} reels in plan.json)")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project")
    ap.add_argument("--reels", help="comma-separated script reel ids to assemble (default: all)")
    a = ap.parse_args()
    try:
        main(a.project, [x.strip() for x in a.reels.split(",") if x.strip()] if a.reels else None)
    except ValueError as e:
        sys.exit(f"ERROR {e}" + ("" if a.reels else "\n(use --reels <id,...> to assemble only the reels that are ready)"))
