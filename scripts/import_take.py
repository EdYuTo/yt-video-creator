#!/usr/bin/env python3
"""Import a teleprompter recording as a project clip.

  python3 import_take.py <P> <raw.webm> --id voice-r1

Re-encodes P/recordings/raw/<reel>-<take>.webm (VP9+Opus, variable frame rate, possibly cut short by a
crash or a closed tab) to P/recordings/voice/<id>.mp4: 1920x1080 (other aspect ratios, e.g. a 4:3 webcam, are
fitted inside and padded with black, never stretched), constant 30 fps, H.264 CRF 14, AAC 48 kHz, loudness-normalised. Then symlinks P/source/<id>.mp4 to it, registers the clip in plan.json
as a "link" clip, drops the clip's old words.json windows (a re-import is a new recording), and copies the take's log next to it as <id>.log.json for takes.py.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ff  # noqa: E402

# Fit inside 1920x1080 keeping the aspect ratio, then centre on a black 1920x1080 canvas. Remotion's ffmpeg has no
# `pad` filter; `rotate` by 0 with a larger output size and black fill does the same thing.
FIT = ("scale=1920:1080:force_original_aspect_ratio=decrease:force_divisible_by=2,"
       "rotate=0:ow=1920:oh=1080:c=black,format=yuv420p")
VIDEO = ["-vf", FIT, "-r", "30", "-c:v", "libx264", "-crf", "14", "-preset", "medium", "-pix_fmt", "yuv420p"]
AUDIO = ["-af", "loudnorm=I=-18:TP=-1.5:LRA=11,aresample=48000", "-ar", "48000", "-c:a", "aac", "-b:a", "192k"]


def drop_stale_words(project, clip_id):
    """Remove every words.json window of `clip_id`: a re-import is a different recording, and mixing the old
    take's word timings with the new would corrupt the cuts (build_edit and takes.py merge all keys of a clip)."""
    path = os.path.join(project, "transcripts", "words.json")
    if not os.path.exists(path):
        return 0
    with open(path, encoding="utf-8") as f:
        words = json.load(f)
    keep = {k: v for k, v in words.items() if k.rsplit(":", 1)[0] != clip_id}
    dropped = len(words) - len(keep)
    if dropped:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(keep, f, ensure_ascii=False)
        os.replace(tmp, path)
        print(f"dropped {dropped} stale transcript window(s) for {clip_id}")
    return dropped


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project")
    ap.add_argument("raw")
    ap.add_argument("--id", required=True)
    a = ap.parse_args(argv)
    P, raw = os.path.abspath(a.project), os.path.abspath(a.raw)
    ff, _, env = _ff.tools(P)

    voice = os.path.join(P, "recordings", "voice")
    os.makedirs(voice, exist_ok=True)
    out = os.path.join(voice, f"{a.id}.mp4")
    # Live MediaRecorder output has no duration/cues and may end mid-cluster: tolerate damage, rebuild timestamps.
    cmd = [ff, "-v", "error", "-y", "-fflags", "+genpts+discardcorrupt", "-err_detect", "ignore_err",
           "-i", raw, *VIDEO, *AUDIO, "-movflags", "+faststart", out]
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(out) or os.path.getsize(out) == 0:
        sys.exit(f"ffmpeg failed on {raw}:\n{r.stderr[-2000:]}")
    dur = round(_ff.duration(out, P), 2)
    drop_stale_words(P, a.id)  # only after the new file exists, so a failed import loses nothing

    src = os.path.join(P, "source")
    os.makedirs(src, exist_ok=True)
    link = os.path.join(src, f"{a.id}.mp4")
    if os.path.lexists(link):
        os.remove(link)
    os.symlink(out, link)

    plan_path = os.path.join(P, "plan.json")
    plan = json.load(open(plan_path))
    plan.setdefault("clips", {})[a.id] = {"file": f"{a.id}.mp4", "media": "link", "dur": dur, "audio": True}
    json.dump(plan, open(plan_path, "w"), indent=1)

    log = raw[: -len(".webm")] + ".log.json" if raw.endswith(".webm") else raw + ".log.json"
    if os.path.exists(log):
        shutil.copyfile(log, os.path.join(voice, f"{a.id}.log.json"))
    else:
        print(f"WARN no log next to {raw} (expected {log}); takes.py needs it")
    print(f"{a.id}: {dur:.1f} s -> {out}")


if __name__ == "__main__":
    main()
