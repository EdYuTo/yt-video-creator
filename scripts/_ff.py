"""Locate a working ffmpeg/ffprobe.

Homebrew ffmpeg breaks often (e.g. missing libx265 dylib after an upgrade), so prefer the
binaries Remotion ships in node_modules/@remotion/compositor-*/ and fall back to the system ones.
Remotion's build is minimal: no drawtext/tile filters, no raw s16le muxer. Callers therefore
tile images with Pillow and decode audio to WAV.
"""
import glob
import os
import shutil
import subprocess


def _remotion_bin(project):
    if not project:
        return None
    hits = glob.glob(os.path.join(project, "node_modules/@remotion/compositor-*/ffmpeg"))
    return os.path.dirname(hits[0]) if hits else None


def tools(project=None):
    """Return (ffmpeg_path, ffprobe_path, env)."""
    d = _remotion_bin(project)
    if d:
        env = dict(os.environ, DYLD_LIBRARY_PATH=d, LD_LIBRARY_PATH=d)
        return f"{d}/ffmpeg", f"{d}/ffprobe", env
    ff, fp = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if ff and fp and subprocess.run([fp, "-version"], capture_output=True).returncode == 0:
        return ff, fp, dict(os.environ)
    raise SystemExit(
        "No working ffmpeg. Scaffold the Remotion project first (setup_project.sh installs one) "
        "and pass --project <project dir>."
    )


def duration(path, project=None):
    _, fp, env = tools(project)
    out = subprocess.check_output(
        [fp, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], env=env
    )
    return float(out)
