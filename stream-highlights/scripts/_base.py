"""Shared helpers: reuse yt-video-creator's ffmpeg locator, find the base skill's scripts."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# The stream skill lives inside the yt-video-creator repo (stream-highlights/), and may also be
# symlinked to ~/.claude/skills/stream-highlights — resolve the real path so ../../scripts works.
BASE_SCRIPTS = os.path.normpath(os.path.join(os.path.realpath(HERE), "..", "..", "scripts"))
if not os.path.exists(os.path.join(BASE_SCRIPTS, "_ff.py")):
    BASE_SCRIPTS = os.path.expanduser("~/.claude/skills/yt-video-creator/scripts")
sys.path.insert(0, BASE_SCRIPTS)

from _ff import duration, pcm, tools  # noqa: E402,F401


def hms(t):
    t = int(t)
    return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}"


def secs(x):
    """'1:02:03', '62:03', '3723' or 3723.5 -> seconds."""
    if isinstance(x, (int, float)):
        return float(x)
    parts = [float(p) for p in str(x).split(":")]
    s = 0.0
    for p in parts:
        s = s * 60 + p
    return s
