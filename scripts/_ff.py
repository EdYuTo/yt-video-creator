"""Locate a working ffmpeg/ffprobe, plus small shared helpers.

Homebrew ffmpeg breaks often (e.g. missing libx265 dylib after an upgrade), so prefer the
binaries Remotion ships in node_modules/@remotion/compositor-*/ and fall back to the system ones.

Remotion's build is minimal. It HAS: scale, crop, format, trim/atrim, concat, loudnorm,
silencedetect, volume, aresample, zscale/tonemap; encoders libx264, h264_videotoolbox, libx265,
aac; hwaccel videotoolbox. It LACKS: fps (use `-r 30`), drawtext, tile, the raw s16le muxer.
So: tile images with Pillow and decode audio to WAV (see pcm()).
"""
import glob
import os
import shutil
import subprocess
import sys


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


def pcm(path, project=None, sr=16000, start=None, dur=None):
    """Decode audio to mono s16 PCM bytes at `sr` Hz (via WAV, since s16le muxer is missing)."""
    ff, _, env = tools(project)
    cmd = [ff, "-v", "error"]
    if start is not None:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += ["-i", path]
    if dur is not None:
        cmd += ["-t", f"{dur:.3f}"]
    cmd += ["-vn", "-ac", "1", "-ar", str(sr), "-c:a", "pcm_s16le", "-f", "wav", "-"]
    raw = subprocess.run(cmd, env=env, capture_output=True, check=True).stdout
    return raw[44:][: (len(raw) - 44) // 2 * 2]


def project_arg(argv=None):
    """Tiny helper for scripts that just need --project from argv."""
    argv = argv or sys.argv
    return argv[argv.index("--project") + 1] if "--project" in argv else None
