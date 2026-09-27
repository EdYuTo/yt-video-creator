#!/usr/bin/env python3
"""Verify rendered Shorts: specs (ffprobe), loudness (integrated LUFS + true peak via loudnorm
analysis), and a 1-frame-per-second contact sheet to look at.

usage: verify_short.py out/short-01.mp4 [...] --project <proj> --sheets <dir> [--width 144]
Targets: 1080x1920, 30 fps, H.264 + AAC; about -14 LUFS integrated, true peak <= -1 dBTP.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

from _base import BASE_SCRIPTS, tools

ap = argparse.ArgumentParser()
ap.add_argument("files", nargs="+")
ap.add_argument("--sheets", required=True)
ap.add_argument("--width", type=int, default=144)
ap.add_argument("--project", required=True)
a = ap.parse_args()
P = os.path.abspath(a.project)
FFMPEG, FFPROBE, ENV = tools(P)
SKILL_SHEETS = os.path.join(BASE_SCRIPTS, "sheets.py")

for f in a.files:
    pr = json.loads(subprocess.check_output([FFPROBE, "-v", "error", "-show_entries",
        "stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels:format=duration,size", "-of", "json", f], env=ENV))
    v = next(s for s in pr["streams"] if s["codec_type"] == "video")
    au = [s for s in pr["streams"] if s["codec_type"] == "audio"]
    dur = float(pr["format"]["duration"])
    err = subprocess.run([FFMPEG, "-hide_banner", "-i", f, "-vn", "-af", "loudnorm=I=-14:TP=-1:print_format=json", "-f", "null", "-"],
                         env=ENV, capture_output=True, text=True).stderr
    ln = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", err, re.S).group(0))
    print(f"{os.path.basename(f)}: {v['codec_name']} {v['width']}x{v['height']} {v['r_frame_rate']} fps, {dur:.2f}s, "
          f"audio {au[0]['codec_name'] + ' ' + au[0]['sample_rate'] + 'Hz x' + str(au[0]['channels']) if au else 'NONE'}, "
          f"{int(pr['format']['size']) / 1e6:.1f} MB | loudness {ln['input_i']} LUFS, true peak {ln['input_tp']} dBTP, LRA {ln['input_lra']}")
    name = os.path.splitext(os.path.basename(f))[0] + "_1fps"
    subprocess.run([sys.executable, SKILL_SHEETS, "fine", f, f"0-{int(dur)}:1", "--out", a.sheets, "--project", P,
                    "--width", str(a.width), "--cols", "10", "--name", name], check=True, capture_output=True)
    print("   sheet:", os.path.join(a.sheets, name + ".jpg"))
