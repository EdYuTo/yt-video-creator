#!/usr/bin/env python3
"""Contact sheets so clips can be *seen* without watching them.

Overview (one sheet per clip, N evenly spaced frames, 4 columns):
  sheets.py overview <clip or folder> --out <dir> --project <proj> [-n 12] [--width 320]

Fine (one sheet for one clip, one row group per range; each range is START-END:STEP in seconds).
Also works on a rendered output to check it frame by frame:
  sheets.py fine <clip> 30-40:2 95-110:3 --out <dir> --project <proj> [--width 256] [--cols 6] [--name x]

Each thumbnail is stamped with its source timestamp (m:ss.s) — those numbers are the in/out
points you write into the edit plan. Tip: for DJI footage, point overview at the .LRF proxies
(same timeline, 10x faster to decode).
"""
import argparse
import glob
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

from PIL import Image, ImageDraw

from _ff import duration, tools

VIDEO = (".mov", ".mp4", ".m4v", ".mkv", ".avi", ".mts", ".webm", ".lrf")

ap = argparse.ArgumentParser()
ap.add_argument("mode", choices=["overview", "fine"])
ap.add_argument("src")
ap.add_argument("ranges", nargs="*")
ap.add_argument("--out", required=True)
ap.add_argument("--project")
ap.add_argument("-n", type=int, default=12)
ap.add_argument("--width", type=int)
ap.add_argument("--cols", type=int, default=6)
ap.add_argument("--name")
a = ap.parse_args()
ff, _, env = tools(a.project)
os.makedirs(a.out, exist_ok=True)


def grab(path, t, width):
    p = subprocess.run(
        [ff, "-v", "error", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1", "-vf", f"scale={width}:-2",
         "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
        env=env, capture_output=True,
    )
    try:
        im = Image.open(BytesIO(p.stdout)).convert("RGB")
    except Exception:
        im = Image.new("RGB", (width, width * 9 // 16), "gray")
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 64, 15], fill="black")
    d.text((3, 2), f"{int(t // 60)}:{t % 60:04.1f}", fill="yellow")
    return im


def tile(rows, cols, dest):
    w, h = rows[0][0].size
    s = Image.new("RGB", (w * cols, h * len(rows)), "gray")
    for y, row in enumerate(rows):
        for x, im in enumerate(row):
            s.paste(im, (x * w, y * h))
    s.save(dest, quality=80)
    print(dest, s.size)


def stem(path):
    return os.path.splitext(os.path.basename(path))[0].replace(" ", "_")


if a.mode == "overview":
    files = [a.src] if os.path.isfile(a.src) else sorted(
        f for f in glob.glob(os.path.join(a.src, "*")) if f.lower().endswith(VIDEO)
    )

    def one(path):
        d = duration(path, a.project)
        ims = [grab(path, d * (i + 0.5) / a.n, a.width or 320) for i in range(a.n)]
        tile([ims[i:i + 4] for i in range(0, len(ims), 4)], 4, os.path.join(a.out, f"sheet_{stem(path)}.jpg"))
        return f"{os.path.basename(path)} {d:.1f}s"

    with ThreadPoolExecutor(6) as ex:
        for line in ex.map(one, files):
            print(line)
else:
    if not a.ranges:
        raise SystemExit("fine needs at least one START-END:STEP range")
    rows_t = []
    for r in a.ranges:
        se, step = r.split(":")
        s, e = map(float, se.split("-"))
        ts, t = [], s
        while t <= e + 1e-6:
            ts.append(t)
            t += float(step)
        rows_t += [ts[i:i + a.cols] for i in range(0, len(ts), a.cols)]
    with ThreadPoolExecutor(8) as ex:
        rows = [list(ex.map(lambda t: grab(a.src, t, a.width or 256), row)) for row in rows_t]
    first = a.ranges[0].split("-")[0]
    name = a.name or f"fine_{stem(a.src)}_{first}{'_x' + str(len(a.ranges)) if len(a.ranges) > 1 else ''}"
    tile(rows, a.cols, os.path.join(a.out, f"{name}.jpg"))
