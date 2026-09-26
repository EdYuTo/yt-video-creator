#!/usr/bin/env python3
"""List every video/photo/audio file in a footage folder with duration, resolution, fps, codec,
bit depth, and whether it has audio — plus a media recommendation per clip:
  link  = H.264/8-bit/<=1080p: hard-link the whole clip, render from it directly
  proxy = HEVC, 10-bit, >1080p or >30 fps: transcode only the used ranges to 1080p30 H.264

DJI .LRF files (low-res H.264 proxies with the same audio) are listed as `lrf` — use them for fast
analysis (sheets, transcription), never for the final render.

usage: probe.py <footage_dir> --project <remotion project dir> [--json out.json]
"""
import argparse
import json
import os
import subprocess

from _ff import tools

VIDEO = {".mov", ".mp4", ".m4v", ".mkv", ".avi", ".mts", ".webm"}
PHOTO = {".jpg", ".jpeg", ".png", ".heic", ".webp"}
AUDIO = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}

ap = argparse.ArgumentParser()
ap.add_argument("folder")
ap.add_argument("--project")
ap.add_argument("--json")
a = ap.parse_args()
_, fp, env = tools(a.project)

rows, total = [], 0.0
for name in sorted(os.listdir(a.folder)):
    path = os.path.join(a.folder, name)
    ext = os.path.splitext(name)[1].lower()
    if not os.path.isfile(path):
        continue
    kind = ("lrf" if ext == ".lrf" or name.lower().endswith(".lrf.mp4") else "video" if ext in VIDEO
            else "photo" if ext in PHOTO else "audio" if ext in AUDIO else None)
    if not kind:
        continue
    info = json.loads(subprocess.run(
        [fp, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
        env=env, capture_output=True, text=True).stdout or "{}")
    streams = info.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video" and s.get("disposition", {}).get("attached_pic") != 1), None)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    dur = float(info.get("format", {}).get("duration", 0) or 0)
    row = dict(file=name, kind=kind, mb=round(os.path.getsize(path) / 1e6), dur=round(dur, 2), audio=has_audio)
    if v:
        num, den = (v.get("r_frame_rate", "0/1").split("/") + ["1"])[:2]
        fps = round(float(num) / float(den or 1), 2) if float(den or 1) else 0
        pix = v.get("pix_fmt", "")
        bits = 10 if "10" in pix else 12 if "12" in pix else 8
        w, h = v.get("width", 0), v.get("height", 0)
        rot = next((sd.get("rotation") for sd in v.get("side_data_list", []) if "rotation" in sd), 0)
        row.update(codec=v.get("codec_name"), profile=v.get("profile"), pix_fmt=pix, bits=bits, w=w, h=h, fps=fps, rotation=rot)
        if kind == "video":
            heavy = v.get("codec_name") != "h264" or bits > 8 or max(w, h) > 1920 or fps > 31
            row["media"] = "proxy" if heavy else "link"
            total += dur
    rows.append(row)
    desc = f"[{kind}] {name}  {row['mb']} MB"
    if v:
        desc += f"  {row['codec']} {row['profile'] if isinstance(row['profile'], str) and not row['profile'].isdigit() else ''} {row['bits']}-bit {row['w']}x{row['h']} {row['fps']}fps"
        if row.get("rotation"):
            desc += f" rot={row['rotation']}"
    if dur and kind != "photo":
        desc += f"  {dur/60:.1f} min" if dur >= 120 else f"  {dur:.1f} s"
    desc += "  audio" if has_audio else ("  NO AUDIO" if kind == "video" else "")
    if row.get("media"):
        desc += f"  -> {row['media']}"
    print(desc)

print(f"\nTotal video: {total/60:.1f} min")
if a.json:
    json.dump(rows, open(a.json, "w"), indent=1)
    print(f"wrote {a.json}")
