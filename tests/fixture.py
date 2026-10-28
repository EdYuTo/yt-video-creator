"""Shared test helper: a minimal, real project on disk that build_edit.py can run against.

Environment:
  YVC_TEST_PROJECT     a Remotion video project dir with node_modules (e.g. one made by setup_project.sh).
                       Its bundled ffmpeg encodes the test clips (system ffmpeg builds vary too much), and its
                       node_modules is symlinked into the temp projects. Tests that need it are skipped when unset.
  YVC_TEST_FOOTAGE     a real video of one person talking to the camera (head and shoulders, face clearly
                       visible, plain room behind) for the segmentation/bubble integration tests; skipped when unset.
  YVC_TEST_FOOTAGE_AT  second in that video where the person is on screen (default 0); 3 s from there are used.
"""
import json
import os
import subprocess
import sys
import unittest

TOOLKIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(TOOLKIT, "scripts"))
from _ff import tools  # noqa: E402

# A project with node_modules, so tools() finds Remotion's bundled ffmpeg (Homebrew's is unreliable).
FFMPEG_PROJECT = os.environ.get("YVC_TEST_PROJECT") or None
NO_PROJECT = None
if not FFMPEG_PROJECT:
    NO_PROJECT = "set YVC_TEST_PROJECT to a Remotion project dir with node_modules (bundled ffmpeg) to run this test"
elif not os.path.isdir(os.path.join(FFMPEG_PROJECT, "node_modules", "@remotion")):
    NO_PROJECT = f"YVC_TEST_PROJECT={FFMPEG_PROJECT} has no node_modules/@remotion (run npm install there)"
FF = FP = ENV = None
if not NO_PROJECT:
    FF, FP, ENV = tools(FFMPEG_PROJECT)
# Class/method decorator for tests that encode media or build a project.
needs_project = unittest.skipIf(NO_PROJECT, NO_PROJECT or "")

FOOTAGE = os.environ.get("YVC_TEST_FOOTAGE") or None
FOOTAGE_AT = float(os.environ.get("YVC_TEST_FOOTAGE_AT") or 0)
NO_FOOTAGE = None
if not FOOTAGE:
    NO_FOOTAGE = "set YVC_TEST_FOOTAGE to a video of a person talking to the camera to run this test"
elif not os.path.exists(FOOTAGE):
    NO_FOOTAGE = f"YVC_TEST_FOOTAGE={FOOTAGE} does not exist"
needs_footage = unittest.skipIf(NO_FOOTAGE, NO_FOOTAGE or "")


def _require_project():
    if NO_PROJECT:
        raise unittest.SkipTest(NO_PROJECT)


def run_ff(*args):
    _require_project()
    subprocess.run([FF, "-v", "error", "-y", *args], env=ENV, check=True)


def make_clip(path, dur, w=1920, h=1080, fps=30):
    # Remotion's ffmpeg has no testsrc/color, only nullsrc: a flat frame is enough for layout tests.
    run_ff("-f", "lavfi", "-i", f"nullsrc=s={w}x{h}:r={fps}:d={dur}",
           "-f", "lavfi", "-i", f"sine=frequency=440:duration={dur}",
           "-vf", "format=yuv420p", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
           "-shortest", path)


def make_music(path, dur=5):
    run_ff("-f", "lavfi", "-i", f"sine=frequency=220:duration={dur}", "-c:a", "libmp3lame", path)


def read_json(path):
    with open(path) as f:
        return json.load(f)


def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=1)


def make_project(tmp: str, clips: dict[str, float]) -> str:
    """Write a minimal project under `tmp` and return its path.

    `clips` maps clip id -> duration in seconds. Each becomes source/<id>.mp4 (1920x1080, 30 fps,
    with a sine track). plan.json lists them as hard-linked ("link") clips with empty words,
    silence, and reels; tests edit plan.json to add what they need. node_modules is a symlink to
    the real project's, so build_edit can find ffmpeg.
    """
    _require_project()
    p = os.path.join(tmp, "project")
    for d in ("src", "public", "source", "transcripts"):
        os.makedirs(os.path.join(p, d), exist_ok=True)
    # build_edit finds ffmpeg through <project>/node_modules, so borrow the real project's.
    os.symlink(os.path.join(FFMPEG_PROJECT, "node_modules"), os.path.join(p, "node_modules"))
    plan_clips, media = {}, []
    for cid, dur in clips.items():
        fname = f"{cid}.mp4"
        make_clip(os.path.join(p, "source", fname), dur)
        plan_clips[cid] = {"file": fname, "media": "link", "dur": dur, "audio": True}
        media.append({"file": fname, "kind": "video", "dur": dur, "audio": True, "w": 1920, "h": 1080,
                      "fps": 30.0, "rotation": 0, "media": "link"})
    plan = {"fps": 30, "clips": plan_clips, "language": "pt", "words": "transcripts/words.json",
            "silence": {"pad": [0.18, 0.28], "gap": 0.6}, "reels": []}
    write_json(os.path.join(p, "plan.json"), plan)
    write_json(os.path.join(p, "media.json"), media)
    write_json(os.path.join(p, "transcripts", "words.json"), {})
    return p
