#!/usr/bin/env python3
"""Privacy check: find faces in a render and map them to shots, for blur decisions.
Run with the venv python from setup_speech.sh (needs opencv-python-headless + the YuNet model).

  faces.py scan   <render.mp4> --project <proj> [--comp long] [--every 10] [--score 0.55]
      -> <proj>/faces.json and a per-shot summary: sample count, max faces per frame, face centers.
  faces.py review <render.mp4> --project <proj> --out review.jpg [--times 12.3,45.6] [--xmin 0.55]
      -> tiles of flagged frames with red boxes. Default flags: >1 face in frame, or a face with
         center x >= xmin or < 0.08 (edges, where bystanders usually are). LOOK at it: about half of
         YuNet hits on food/vlog footage are hands, glasses, yolks, bottle caps.

Then put blur boxes in plan.json ("blur": [{clip, from, to, rects: [[x,y,w,h] %]}], source time,
from the shot's srcClip) or replace the shot, rebuild, re-render, and scan again.
Limits to tell the user: misses profiles and faces at the frame edge; boxes are static per shot.
"""
import argparse
import json
import os

import cv2
from PIL import Image, ImageDraw

MODEL = os.path.expanduser("~/.cache/yt-video-creator/yunet.onnx")
ap = argparse.ArgumentParser()
ap.add_argument("mode", choices=["scan", "review"])
ap.add_argument("video")
ap.add_argument("--project", required=True)
ap.add_argument("--comp", default="long")
ap.add_argument("--every", type=int, default=10)
ap.add_argument("--score", type=float, default=0.55)
ap.add_argument("--out", default="review.jpg")
ap.add_argument("--times")
ap.add_argument("--xmin", type=float, default=0.55)
a = ap.parse_args()
P = os.path.abspath(a.project)
fj = os.path.join(P, "faces.json")

emap = [r for r in json.load(open(os.path.join(P, "edit-map.json"))) if r["comp"] == a.comp]


def shot_at(t):
    for r in emap:
        if r["start"] <= t < r["end"]:
            return r
    return {"clip": None, "kind": "card", "start": t}


if a.mode == "scan":
    cap = cv2.VideoCapture(a.video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    W = 960
    H = int(W * cap.get(cv2.CAP_PROP_FRAME_HEIGHT) / cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    det = cv2.FaceDetectorYN.create(MODEL, "", (W, H), a.score, 0.3, 5000)
    hits, f = [], 0
    while cap.grab():
        if f % a.every == 0:
            _, img = cap.retrieve()
            _, faces = det.detect(cv2.resize(img, (W, H)))
            if faces is not None:
                t = f / fps
                r = shot_at(t)
                hits.append(dict(t=round(t, 2), frame=f, clip=r["clip"], kind=r["kind"], local=round(t - r["start"], 2),
                                 boxes=[[round(x / W, 3), round(y / H, 3), round(w / W, 3), round(h / H, 3), round(float(fc[-1]), 2)]
                                        for x, y, w, h, *fc in faces.tolist()]))
        f += 1
    json.dump(hits, open(fj, "w"))
    print(f"{f} frames, {len(hits)} sampled frames with faces -> {fj}")
    by = {}
    for h in hits:
        by.setdefault(h["clip"], []).append(h)
    for clip, hs in by.items():
        xs = sorted({round(b[0] + b[2] / 2, 1) for h in hs for b in h["boxes"]})
        print(f"{clip!s:28s} t={hs[0]['t']:7.1f}-{hs[-1]['t']:7.1f} n={len(hs):3d} "
              f"max_faces={max(len(h['boxes']) for h in hs)} centers_x={xs}")
else:
    hits = json.load(open(fj))
    if a.times:
        want = [float(x) for x in a.times.split(",")]
        sel = [min(hits, key=lambda h: abs(h["t"] - t)) for t in want]
    else:
        sel = [h for h in hits if len(h["boxes"]) > 1 or any(b[0] + b[2] / 2 >= a.xmin or b[0] + b[2] / 2 < 0.08 for b in h["boxes"])]
    cap = cv2.VideoCapture(a.video)
    W, cols = 320, 6
    tiles = []
    for h in sel[:96]:
        cap.set(cv2.CAP_PROP_POS_FRAMES, h["frame"])
        ok, img = cap.read()
        if not ok:
            continue
        Hh = int(W * img.shape[0] / img.shape[1])
        im = Image.fromarray(cv2.cvtColor(cv2.resize(img, (W, Hh)), cv2.COLOR_BGR2RGB))
        d = ImageDraw.Draw(im)
        for x, y, w, hh, s in h["boxes"]:
            d.rectangle([x * W, y * Hh, (x + w) * W, (y + hh) * Hh], outline="red", width=2)
        d.rectangle([0, 0, 170, 13], fill="black")
        d.text((2, 1), f"{h['t']:.1f}s {h['clip']}", fill="yellow")
        tiles.append(im)
    if not tiles:
        raise SystemExit("nothing flagged")
    w, hh = tiles[0].size
    g = Image.new("RGB", (w * cols, hh * ((len(tiles) + cols - 1) // cols)), "gray")
    for i, t in enumerate(tiles):
        g.paste(t, ((i % cols) * w, (i // cols) * hh))
    g.save(a.out, quality=85)
    print(f"{len(tiles)} frames -> {a.out}" + (" (first 96 only)" if len(sel) > 96 else ""))
