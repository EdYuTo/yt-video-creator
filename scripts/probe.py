#!/usr/bin/env python3
"""List every video/photo/audio file in a footage folder with duration, resolution, fps, codecs.

usage: probe.py <footage_dir> --project <remotion project dir>
"""
import argparse
import os
import subprocess

from _ff import tools

VIDEO = {".mov", ".mp4", ".m4v", ".mkv", ".avi", ".mts", ".webm"}
PHOTO = {".jpg", ".jpeg", ".png", ".heic", ".webp"}
AUDIO = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}

ap = argparse.ArgumentParser()
ap.add_argument("folder")
ap.add_argument("--project")
a = ap.parse_args()
_, fp, env = tools(a.project)

total = 0.0
for name in sorted(os.listdir(a.folder)):
    path = os.path.join(a.folder, name)
    ext = os.path.splitext(name)[1].lower()
    if not os.path.isfile(path) or ext not in VIDEO | PHOTO | AUDIO:
        continue
    out = subprocess.run(
        [fp, "-v", "error", "-show_entries",
         "stream=codec_type,codec_name,width,height,r_frame_rate:stream_side_data=rotation:format=duration",
         "-of", "compact=p=0:nk=1", path],
        env=env, capture_output=True, text=True,
    ).stdout.split("\n")
    kind = "video" if ext in VIDEO else "photo" if ext in PHOTO else "audio"
    info = " | ".join(l for l in out if l.strip())
    size = os.path.getsize(path) / 1e6
    print(f"[{kind}] {name}  {size:.0f} MB  {info}")
    if kind == "video":
        try:
            total += float(out[-2] if out[-1] == "" else out[-1])
        except (ValueError, IndexError):
            pass
print(f"\nTotal video: {total/60:.1f} min")
