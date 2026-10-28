#!/usr/bin/env python3
"""Pick the clean take of each script line from the teleprompter log plus Whisper word timestamps.

  python3 takes.py <P> --reel r1 [--language pt] [--no-hint]   -> P/takes/r1.json  [{line, start, end, score, text, subs}]

Reads P/recordings/voice/voice-<reel>.log.json (copied there by import_take.py), the reel's lines from
P/scripts/reels.json and the words of clip voice-<reel> from P/transcripts/words.json. Prints
`WARN line N: ...` for a missing line or a weak match (score < 0.6) and still exits 0.

The karaoke pace is independent of how fast the speaker really talks, so their words for a line can spill
past the next `line` event: align() therefore searches the event window plus a pad and matches tokens.
start/end are the raw first/last matched word times; build_edit's silence cutter adds its own padding.

Plain Whisper mishears jargon and foreign terms (e.g. English words in Portuguese speech: "reel" -> "rio"),
which drops a good take below the score where subtitles use the script spelling. So by default each
picked take's window is transcribed again with the term list + the line's script text as Whisper's
initial_prompt, and those words replace the plain ones for the final score and the spoken-text subtitles.
A real misread (different words were said) still comes through. `--no-hint` skips this (and the model).
Terms: P/scripts/terms.txt, one per line (there is no built-in list; the line's own text is always in the prompt).
Language of that re-transcription: --language, else plan.json "language"; an error if neither is set.
"""
import argparse
import difflib
import json
import os
import re
import sys
import unicodedata

WARN_BELOW = 0.6     # weaker matches than this are flagged
SCRIPT_SUBS_FROM = 0.85  # at or above: subtitles use the script spelling; below: what was actually said
HINT_MODEL = "mlx-community/whisper-large-v3-turbo"
# Whisper is erratic about the window it is given: with the line's own text in the prompt, a window that
# holds bits of the neighbouring lines sometimes drops or garbles the whole sentence, while a window hugging the
# plain match cuts off the edge words the plain pass misheard. On real takes each kind won on
# different lines, so several windows are tried and the best-scoring result is kept. Each is
# (seconds before, seconds after) around the take's log segment or plain match, whichever reaches further;
# the last, "plain", hugs the plain match itself.
HINT_WINDOWS = [("wide", 1.0, 1.0), ("tight", 0.3, 0.4), ("plain", 0.3, 0.4), ("half", 0.5, 0.5)]
DEFAULT_TERMS = []   # project terms go in P/scripts/terms.txt
STRAY_GAP = 1.5      # a lone matched word this far (s) from the main block is a neighbour line's word


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def norm(word):
    s = unicodedata.normalize("NFD", word.lower())
    return re.sub(r"[^0-9a-z]", "", "".join(c for c in s if not unicodedata.combining(c)))


def triple(w):
    """(start, end, word) from a word tuple in either (start, end, word) or (word, start, end) order."""
    return tuple(w) if isinstance(w[2], str) else (w[1], w[2], w[0])


def segments(log):
    """One segment per `line` event, running to the next event; `abandoned` if that event is a tap."""
    out, open_seg = [], None
    for e in log.get("events", []):
        if open_seg is not None:
            open_seg["end"] = e["t"]
            open_seg["abandoned"] = e["type"] == "tap"
            out.append(open_seg)
            open_seg = None
        if e["type"] == "line":
            open_seg = {"line": e["line"], "start": e["t"], "end": None, "abandoned": False}
    if open_seg is not None:  # log cut short (crash): the take ran to the last thing we know about
        last = log["events"][-1]["t"]
        open_seg["end"] = max(last, open_seg["start"])
        out.append(open_seg)
    return out


def pick(segs):
    """The last non-abandoned segment of each line."""
    return {s["line"]: s for s in segs if not s["abandoned"]}


def _match(words, tokens):
    """Matched (token index, word index) pairs, dropping stray single words far from the main block."""
    wt = [norm(w[2]) for w in words]
    blocks = [b for b in difflib.SequenceMatcher(None, tokens, wt, autojunk=False).get_matching_blocks() if b.size]
    if not blocks:
        return []
    main = max(blocks, key=lambda b: b.size)
    lo, hi = words[main.b][0], words[main.b + main.size - 1][1]
    pairs = []
    for b in blocks:
        t0, t1 = words[b.b][0], words[b.b + b.size - 1][1]
        if b.size == 1 and b is not main and max(lo - t1, t0 - hi) > STRAY_GAP:
            continue
        pairs += [(b.a + k, b.b + k) for k in range(b.size)]
    return pairs


def align(words, text, around, pad=2.0):
    """(start, end, score): first/last matched word times and the share of the line's tokens matched."""
    words = [triple(w) for w in words]
    tokens = [t for t in map(norm, text.split()) if t]
    lo, hi = around[0] - pad, around[1] + pad
    win = sorted((w for w in words if lo <= w[0] <= hi and norm(w[2])), key=lambda w: w[0])
    pairs = _match(win, tokens) if tokens and win else []
    if not pairs:
        return around[0], around[1], 0.0
    return win[pairs[0][1]][0], win[pairs[-1][1]][1], round(len(pairs) / len(tokens), 3)


def split_subs(text, start, end, words, max_chars=42):
    """Chunks of <= max_chars as [start, end, text], broken at punctuation or word boundaries.

    Each chunk is timed to its first and last matched word; tokens that match no word get times
    interpolated between their neighbours."""
    toks = text.split()
    if not toks:
        return []
    words = [triple(w) for w in words]
    keys = [norm(t) for t in toks]
    times = [None] * len(toks)
    for a, b in _match_tokens(keys, words):
        times[a] = (words[b][0], words[b][1])
    # interpolate unmatched runs between anchors (start before the first token, end after the last)
    i = 0
    while i < len(toks):
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < len(toks) and times[j] is None:
            j += 1
        t0 = times[i - 1][1] if i else start
        t1 = times[j][0] if j < len(toks) else end
        t1 = max(t1, t0)
        for k in range(i, j):
            a = t0 + (t1 - t0) * (k - i) / (j - i)
            b = t0 + (t1 - t0) * (k - i + 1) / (j - i)
            times[k] = (a, b)
        i = j
    out, i = [], 0
    while i < len(toks):
        j, n = i, 0
        while j < len(toks) and (j == i or n + 1 + len(toks[j]) <= max_chars):
            n += (1 if j > i else 0) + len(toks[j])
            j += 1
        if j < len(toks):  # prefer to break after punctuation if that sits in the second half of the chunk
            for k in range(j - 1, i, -1):
                if toks[k - 1][-1] in ",;:.!?…" and len(" ".join(toks[i:k])) * 2 >= n:
                    j = k
                    break
        out.append([round(times[i][0], 2), round(times[j - 1][1], 2), " ".join(toks[i:j])])
        i = j
    return out


def _match_tokens(keys, words):
    """Like _match, for display tokens that may include ones that normalise to nothing."""
    idx = [i for i, k in enumerate(keys) if k]
    pairs = _match(words, [keys[i] for i in idx]) if idx and words else []
    return [(idx[a], b) for a, b in pairs]


def load_words(project, clip):
    path = os.path.join(project, "transcripts", "words.json")
    data = read_json(path) if os.path.exists(path) else {}
    seen, out = set(), []
    for key, segs in data.items():
        if key.rsplit(":", 1)[0] != clip:
            continue
        for seg in segs:
            for s, e, w in seg.get("w", []):
                if (s, w) not in seen:
                    seen.add((s, w))
                    out.append((s, e, w.strip()))
    return sorted(out)


def load_terms(project):
    path = os.path.join(project, "scripts", "terms.txt")
    extra = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            extra = [l.strip() for l in f]
    out = []
    for t in DEFAULT_TERMS + [t for t in extra if t]:
        if t.lower() not in (o.lower() for o in out):
            out.append(t)
    return out


def plan_language(project, override=None):
    """The transcription language: the --language flag, else plan.json "language"; None if neither."""
    if override:
        return override
    path = os.path.join(project, "plan.json")
    return (read_json(path).get("language") if os.path.exists(path) else None) or None


def whisper_transcriber(project, clip, language):
    """transcriber(start, end, prompt) -> [(start, end, word)] in clip time, via mlx-whisper (local)."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import numpy as np
    import mlx_whisper
    from _ff import pcm
    path = os.path.join(project, "recordings", "voice", f"{clip}.mp4")

    def transcribe(start, end, prompt):
        audio = np.frombuffer(pcm(path, project, 16000, start, end - start), np.int16).astype(np.float32) / 32768
        r = mlx_whisper.transcribe(audio, path_or_hf_repo=HINT_MODEL, language=language, word_timestamps=True,
                                   condition_on_previous_text=False, initial_prompt=prompt, verbose=None)
        return [(round(start + w["start"], 2), round(start + w["end"], 2), w["word"].strip())
                for seg in r["segments"] for w in seg.get("words", []) if w["word"].strip()]
    return transcribe


def main(argv=None, transcriber=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project")
    ap.add_argument("--reel", required=True)
    ap.add_argument("--no-hint", action="store_true",
                    help="skip re-transcribing each take with the term list as Whisper's prompt")
    ap.add_argument("--language", help="Whisper language code for the hinted pass (default: plan.json \"language\")")
    a = ap.parse_args(argv)
    P, clip = a.project, f"voice-{a.reel}"

    reels = read_json(os.path.join(P, "scripts", "reels.json"))["reels"]
    reel = next((r for r in reels if r.get("id") == a.reel), None)
    if reel is None:
        sys.exit(f"reel {a.reel} not in scripts/reels.json")
    lines = [l["text"] for l in reel["lines"]]
    log = read_json(os.path.join(P, "recordings", "voice", f"{clip}.log.json"))
    words = load_words(P, clip)
    if not words:
        print(f"WARN no words for {clip} in transcripts/words.json (run transcribe.py words first)")

    hint, language = None, None
    if not a.no_hint and transcriber is None:
        language = plan_language(P, a.language)
        if not language:
            sys.exit('no transcription language: set "language" in plan.json or pass --language (or use --no-hint)')
    if not a.no_hint:
        try:
            hint = transcriber or whisper_transcriber(P, clip, language)
        except ImportError as e:
            print(f"WARN hinted re-transcription unavailable ({e}); using the plain words")
    terms = load_terms(P)

    segs = segments(log)
    picked = pick(segs)
    result = []
    for n, text in enumerate(lines):
        seg = picked.get(n)
        if seg is None:
            print(f"WARN line {n}: no clean take in the log (never read, or every take was tapped away)")
            continue
        usable = words
        i = segs.index(seg)
        if i and segs[i - 1]["abandoned"]:  # don't match the words of the take just thrown away
            usable = [w for w in words if w[0] >= segs[i - 1]["end"]]
        start, end, score = plain = align(usable, text, (seg["start"], seg["end"]))
        if hint:
            floor = segs[i - 1]["end"] if i and segs[i - 1]["abandoned"] else 0.0  # not the thrown-away take
            t0, t1 = min(start, seg["start"]), max(end, seg["end"])
            best, tried = None, set()
            for kind, before, after in HINT_WINDOWS:
                a0, a1 = (start, end) if kind == "plain" else (t0, t1)
                lo, hi = round(max(a0 - before, floor, 0.0), 3), round(a1 + after, 3)
                if (lo, hi) in tried:
                    continue
                tried.add((lo, hi))
                try:
                    hinted = sorted(triple(w) for w in hint(lo, hi, ", ".join(terms + [text])))
                except Exception as e:  # one bad line (decode error, model failure) must not abort the run
                    print(f"WARN line {n}: hinted re-transcription failed ({type(e).__name__}: {e})")
                    continue
                if not hinted:
                    continue
                cand = align(hinted, text, (lo, hi), pad=0)  # the second align picks the final start/end
                if best is None or cand[2] > best[0][2]:  # ties keep the earlier (wider) window
                    best = (cand, hinted)
                if cand[2] >= 1.0:
                    break
            if best and best[0][2] >= plain[2]:
                (start, end, score), usable = best
                note = ""
            else:  # nothing beat the plain pass (or nothing came back): keep the plain words
                note = " (plain words)"
            print(f"line {n}: score {plain[2]:.2f} -> {score:.2f}{note}")
        else:
            print(f"line {n}: score {score:.2f}")
        spoken = [w for w in usable if start <= w[0] and w[1] <= end]
        if score >= SCRIPT_SUBS_FROM or not spoken:
            subs = split_subs(text, start, end, spoken)
        else:
            subs = split_subs(" ".join(w[2] for w in spoken), start, end, spoken)
        if score < WARN_BELOW:
            print(f"WARN line {n}: weak match (score {score:.2f}); check the take by ear")
        result.append({"line": n, "start": start, "end": end, "score": score, "text": text, "subs": subs})
    for n in sorted(set(picked) - set(range(len(lines)))):
        print(f"WARN line {n}: in the log but not in scripts/reels.json")

    os.makedirs(os.path.join(P, "takes"), exist_ok=True)
    out = os.path.join(P, "takes", f"{a.reel}.json")
    with open(out, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"-> {out} ({len(result)}/{len(lines)} lines)")


if __name__ == "__main__":
    main()
