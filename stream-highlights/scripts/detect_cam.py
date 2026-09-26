#!/usr/bin/env python3
"""Estimate the facecam overlay box of a stream VOD. Run with the venv python (OpenCV + YuNet).

usage: detect_cam.py <vod> --project <proj> [--samples 24] [--out check.jpg]
  prints the box as [x, y, w, h] in SOURCE pixels (paste into shorts.json "cam") and writes a check
  image with the box drawn on 4 frames. ALWAYS look at it: a guest on screen, a face in the game or a
  moving cam can fool it. If it's off, read the edges off a fine sheet and set "cam" by hand.

How: sample frames across the VOD (skipping the first/last 3%), detect faces, keep the location that
recurs most (the facecam doesn't move; faces in game/videos do), then grow the face box into a
typical 4:3 overlay around it and snap to the frame edge when close. It gives the overlay, not the
face: layouts crop inside it.
"""
import argparse
import os
import subprocess
from io import BytesIO

import cv2
import numpy as np
from PIL import Image, ImageDraw

from _base import duration, tools

MODEL = os.path.expanduser("~/.cache/yt-video-creator/yunet.onnx")
ap = argparse.ArgumentParser()
ap.add_argument("vod")
ap.add_argument("--project", required=True)
ap.add_argument("--samples", type=int, default=24)
ap.add_argument("--out", default="cam_check.jpg")
a = ap.parse_args()
ff, fp, env = tools(a.project)
dur = duration(a.vod, a.project)
W = 1280


def grab(t):
    p = subprocess.run([ff, "-v", "error", "-ss", f"{t:.1f}", "-i", a.vod, "-frames:v", "1", "-vf", f"scale={W}:-2",
                        "-f", "image2pipe", "-vcodec", "mjpeg", "-"], env=env, capture_output=True)
    return cv2.imdecode(np.frombuffer(p.stdout, np.uint8), cv2.IMREAD_COLOR)


times = [dur * (0.03 + 0.94 * i / (a.samples - 1)) for i in range(a.samples)]
frames = [(t, grab(t)) for t in times]
frames = [(t, f) for t, f in frames if f is not None]
H = frames[0][1].shape[0]
det = cv2.FaceDetectorYN.create(MODEL, "", (W, H), 0.6, 0.3, 20)
faces = []
for t, img in frames:
    _, fs = det.detect(img)
    for x, y, w, h, *rest in (fs.tolist() if fs is not None else []):
        faces.append((t, x, y, w, h))
if not faces:
    raise SystemExit("no faces found: no facecam, or too small; set cam by hand from a sheet")

# cluster by face centre (within 4% of width); the facecam is the most frequent, stable location
cl = []
for f in faces:
    cx, cy = f[1] + f[3] / 2, f[2] + f[4] / 2
    for c in cl:
        if abs(c["cx"] - cx) < 0.04 * W and abs(c["cy"] - cy) < 0.06 * H:
            c["m"].append(f)
            c["cx"], c["cy"] = np.mean([m[1] + m[3] / 2 for m in c["m"]]), np.mean([m[2] + m[4] / 2 for m in c["m"]])
            break
    else:
        cl.append({"cx": cx, "cy": cy, "m": [f]})
cl.sort(key=lambda c: -len({m[0] for m in c["m"]}))
best = cl[0]
seen = len({m[0] for m in best["m"]})
fw = float(np.median([m[3] for m in best["m"]]))
fh = float(np.median([m[4] for m in best["m"]]))
cx, cy = best["cx"], best["cy"]
bw = fw * 4.0
bh = bw * 0.75
x0, y0 = cx - bw / 2, cy - bh * 0.45
snap = 0.04 * W
if x0 < snap: x0 = 0
if y0 < snap: y0 = 0
if W - (x0 + bw) < snap: x0 = W - bw
if H - (y0 + bh) < snap: y0 = H - bh
x0, y0 = max(0, x0), max(0, y0)
bw, bh = min(bw, W - x0), min(bh, H - y0)
# Refine with the overlay's STATIC borders: the median gradient across frames keeps edges that never
# move (overlay frame) and washes out the game. Search each free side between the face and the
# heuristic edge (+50% margin) for the strongest straight edge.
grays = np.stack([cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32) for _, f in frames])
gx = np.median(np.abs(np.diff(grays, axis=2)), axis=0)  # vertical edges  (H, W-1)
gy = np.median(np.abs(np.diff(grays, axis=1)), axis=0)  # horizontal edges (H-1, W)
fx0, fx1 = cx - fw / 2, cx + fw / 2
fy0, fy1 = cy - fh / 2, cy + fh / 2
refined = []


def best_line(profile, lo, hi, outward):
    """First strong straight edge scanning AWAY from the face ('+' = increasing index)."""
    lo, hi = int(max(0, lo)), int(min(len(profile) - 1, hi))
    if hi - lo < 3:
        return None
    seg = profile[lo:hi]
    thr = max(3 * (np.median(profile) + 1e-3), 0.5 * seg.max())
    idx = range(len(seg)) if outward == "+" else range(len(seg) - 1, -1, -1)
    for i in idx:
        if seg[i] >= thr and seg[i] >= seg[max(0, i - 1)] and seg[i] >= seg[min(len(seg) - 1, i + 1)]:
            return lo + i
    return None


ys, ye = int(y0), int(min(H - 1, y0 + bh))
xs, xe = int(x0), int(min(W - 1, x0 + bw))
if x0 > 0:  # left border
    v = best_line(gx[ys:ye].mean(0), x0 - bw * 0.5, fx0 - fw * 0.3, "-")
    if v is not None:
        x1 = x0 + bw
        x0, bw = v + 1, x1 - (v + 1)
        refined.append("left")
if x0 + bw < W - 1:  # right border
    v = best_line(gx[ys:ye].mean(0), fx1 + fw * 0.3, x0 + bw * 1.5, "+")
    if v is not None:
        bw = v + 1 - x0
        refined.append("right")
xs, xe = int(x0), int(min(W - 1, x0 + bw))
if y0 + bh < H - 1:  # bottom border
    v = best_line(gy[:, xs:xe].mean(1), fy1 + fh * 0.3, y0 + bh * 1.5, "+")
    if v is not None:
        bh = v + 1 - y0
        refined.append("bottom")
if y0 > 0:  # top border
    v = best_line(gy[:, xs:xe].mean(1), y0 - bh * 0.5, fy0 - fh * 0.3, "-")
    if v is not None:
        y1 = y0 + bh
        y0, bh = v + 1, y1 - (v + 1)
        refined.append("top")
print("refined from static edges:", ", ".join(refined) or "none (heuristic box)")

src = subprocess.check_output([fp, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", a.vod], env=env).decode().strip().split(",")
S = int(src[0]) / W
box = [round(x0 * S), round(y0 * S), round(bw * S), round(bh * S)]
print(f"face seen in {seen}/{len(frames)} sampled frames at the same spot; {len(cl) - 1} other face location(s)")
print(f"cam: {box}   (source {src[0]}x{src[1]})")
if seen < len(frames) * 0.4:
    print("WARN: the face is absent in most samples (cam off for parts of the VOD, or not a facecam) — check the image")

tiles = []
for t, img in [frames[i] for i in np.linspace(0, len(frames) - 1, 4).astype(int)]:
    im = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    d = ImageDraw.Draw(im)
    d.rectangle([x0, y0, x0 + bw, y0 + bh], outline="yellow", width=4)
    d.text((8, 8), f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{int(t % 60):02d}", fill="yellow")
    tiles.append(im.resize((640, int(640 * H / W))))
g = Image.new("RGB", (1280, tiles[0].height * 2))
for i, t in enumerate(tiles):
    g.paste(t, ((i % 2) * 640, (i // 2) * tiles[0].height))
g.save(a.out, quality=85)
print("check image:", a.out)
