#!/usr/bin/env python3
"""Contact sheets so clips can be *seen* without watching them.

Overview (one sheet per clip, N evenly spaced frames, 4 columns):
  sheets.py overview <clip or folder> --out <dir> --project <proj> [-n 12]

Fine (one sheet for a time range of one clip, every STEP seconds, 6 columns). Also works on a
rendered output to check it frame by frame:
  sheets.py fine <clip> <start> <end> <step> --out <dir> --project <proj> [--width 256]

Each thumbnail is stamped with its source timestamp (m:ss.s) — those numbers are the in/out
points you write into the edit file.
"""
import argparse
import glob
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

from PIL import Image, ImageDraw

from _ff import duration, tools

VIDEO = (".mov", ".mp4", ".m4v", ".mkv", ".avi", ".mts", ".webm")

ap = argparse.ArgumentParser()
ap.add_argument("mode", choices=["overview", "fine"])
ap.add_argument("src")
ap.add_argument("range", nargs="*", type=float)
ap.add_argument("--out", required=True)
ap.add_argument("--project")
ap.add_argument("-n", type=int, default=12)
ap.add_argument("--width", type=int)
a = ap.parse_args()
ff, _, env = tools(a.project)
os.makedirs(a.out, exist_ok=True)


def grab(path, t, width):
    p = subprocess.run(
        [ff, "-v", "error", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1", "-vf", f"scale={width}:-2",
         "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
        env=env, capture_output=True,
    )
    im = Image.open(BytesIO(p.stdout)).convert("RGB")
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 64, 15], fill="black")
    d.text((3, 2), f"{int(t // 60)}:{t % 60:04.1f}", fill="yellow")
    return im


def tile(ims, cols, dest):
    w, h = ims[0].size
    rows = (len(ims) + cols - 1) // cols
    cols = min(cols, len(ims))
    s = Image.new("RGB", (w * cols, h * rows))
    for i, im in enumerate(ims):
        s.paste(im, ((i % cols) * w, (i // cols) * h))
    s.save(dest, quality=80)
    print(dest)


def stem(path):
    return os.path.splitext(os.path.basename(path))[0].replace(" ", "_")


if a.mode == "overview":
    files = [a.src] if os.path.isfile(a.src) else sorted(
        f for f in glob.glob(os.path.join(a.src, "*")) if f.lower().endswith(VIDEO)
    )

    def one(path):
        d = duration(path, a.project)
        ims = [grab(path, d * (i + 0.5) / a.n, a.width or 384) for i in range(a.n)]
        tile(ims, 4, os.path.join(a.out, f"sheet_{stem(path)}.jpg"))
        return f"{os.path.basename(path)} {d:.1f}s"

    with ThreadPoolExecutor(6) as ex:
        for line in ex.map(one, files):
            print(line)
else:
    start, end, step = a.range
    ts, t = [], start
    while t <= end + 1e-6:
        ts.append(t)
        t += step
    with ThreadPoolExecutor(8) as ex:
        ims = list(ex.map(lambda t: grab(a.src, t, a.width or 256), ts))
    tile(ims, 6, os.path.join(a.out, f"fine_{stem(a.src)}_{int(start)}.jpg"))
