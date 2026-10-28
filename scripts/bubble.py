#!/usr/bin/env python3
"""Render the "head bubble" (macOS Presenter Overlay look) as a transparent VP9 webm.

  python3 bubble.py --cam <voice.mp4> --matte <matte.mp4> --crop X,Y,W --d 640 \
      [--bg-top '#C8A2E8' --bg-bottom '#EBDDF7'] --out <P>/recordings/voice/bubble-<reel>.webm

Crops X,Y,W x round(1.3W) camera pixels from every frame of --cam (head and shoulders), scales it to
d x round(1.3d), and draws it as a disk at the bottom (vertical gradient --bg-top -> --bg-bottom,
lavender by default) with the person cut out by the matte: the head breaks out above the rim, the
body below the centre is clipped by the circle. If --matte doesn't exist (or is older than --cam) it
is made first with segment_person (Apple Vision, macOS only, local; compiled with swiftc on first use).
Then symlinks <P>/source/bubble-<reel>.webm to the output and registers it in <P>/plan.json as a
"link" clip without audio, where <P> is three levels above --out.
"""
import argparse
import json
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ff  # noqa: E402

SWIFT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "segment_person.swift")
SEGMENTER = os.path.expanduser("~/.cache/yt-video-creator/bin/segment_person")
BG_TOP, BG_BOTTOM = "#C8A2E8", "#EBDDF7"


def hex_rgb(s):
    """'#RRGGBB' (or 'RRGGBB') -> float32 RGB array."""
    h = s.strip().lstrip("#")
    if len(h) != 6 or any(c not in "0123456789abcdefABCDEF" for c in h):
        raise ValueError(f"not a #RRGGBB colour: {s!r}")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32)


TOP, BOTTOM = hex_rgb(BG_TOP), hex_rgb(BG_BOTTOM)


def bubble_frame(cam, matte, d, top=TOP, bottom=BOTTOM):
    """cam: HxWx3 uint8 RGB, matte: HxW float32 0..1, both already cropped to H = round(1.3d), W = d.
    top/bottom: RGB of the disk's gradient. Returns HxWx4 uint8 RGBA (straight alpha)."""
    H, W = cam.shape[:2]
    cy, cx, r = H - d / 2, d / 2, d / 2
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    dist = np.hypot(xs + 0.5 - cx, ys + 0.5 - cy)
    disk = np.clip((r - dist) / 1.5 + 0.5, 0, 1)  # antialiased over 1.5 px
    t = np.clip((np.arange(H, dtype=np.float32) - (H - d)) / max(d - 1, 1), 0, 1)[:, None, None]
    bg = top * (1 - t) + bottom * t  # gradient over the disk's rows
    m = cv2.GaussianBlur(matte.astype(np.float32), (0, 0), 1.5)
    above = (ys < cy).astype(np.float32)
    alpha = np.clip(disk + m * above, 0, 1)
    camf = cam.astype(np.float32)
    inside = m[..., None] * camf + (1 - m[..., None]) * bg
    rgb = disk[..., None] * inside + (1 - disk[..., None]) * camf
    out = np.empty((H, W, 4), np.uint8)
    out[..., :3] = np.clip(np.rint(rgb), 0, 255)
    out[..., 3] = np.clip(np.rint(alpha * 255), 0, 255)
    return out


def segmenter():
    """Path to the compiled segment_person, (re)building it if missing or older than its source."""
    if not os.path.exists(SEGMENTER) or os.path.getmtime(SEGMENTER) < os.path.getmtime(SWIFT):
        os.makedirs(os.path.dirname(SEGMENTER), exist_ok=True)
        print(f"compiling {SEGMENTER}", file=sys.stderr)
        r = subprocess.run(["swiftc", "-O", "-suppress-warnings", SWIFT, "-o", SEGMENTER], capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"swiftc failed:\n{r.stderr[-3000:]}")
    return SEGMENTER


def crop(img, x, y, w, h):
    """img[y:y+h, x:x+w]; where the box runs off the frame, the edge pixels are repeated outwards.
    Returns (crop, inside-mask). Repeating (not black) keeps the resize and yuva420p's 2x2 chroma from
    darkening the visible edge next to the transparent pad."""
    fh, fw = img.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, fw), min(y + h, fh)
    if x1 <= x0 or y1 <= y0:  # entirely off-frame
        return np.zeros((h, w) + img.shape[2:], img.dtype), np.zeros((h, w), np.float32)
    pads = (y0 - y, y + h - y1, x0 - x, x + w - x1)  # top, bottom, left, right
    out = cv2.copyMakeBorder(img[y0:y1, x0:x1], *pads, cv2.BORDER_REPLICATE)
    valid = cv2.copyMakeBorder(np.ones((y1 - y0, x1 - x0), np.float32), *pads, cv2.BORDER_CONSTANT, value=0)
    return out, valid


def render_frame(frame, mframe, x, y, w, d, top=TOP, bottom=BOTTOM):
    """One bubble frame from a camera frame (BGR) and its matte (uint8, cam-sized): crop x,y,w x round(1.3w),
    scale to d x round(1.3d), draw. Off-frame parts of the crop come out transparent. Returns RGBA uint8."""
    hc, h = round(1.3 * w), round(1.3 * d)
    c, valid = crop(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), x, y, w, hc)
    m, _ = crop(mframe, x, y, w, hc)
    interp = cv2.INTER_AREA if d < w else cv2.INTER_CUBIC
    c = cv2.resize(c, (d, h), interpolation=interp)
    m = cv2.resize(m, (d, h), interpolation=interp).astype(np.float32) / 255
    rgba = bubble_frame(c, m, d, top, bottom)
    if valid.min() < 1:
        v = cv2.resize(valid, (d, h), interpolation=cv2.INTER_AREA)
        rgba[..., 3] = np.rint(rgba[..., 3] * v).astype(np.uint8)
    return rgba


def drain(cap):
    n = 0
    while cap.grab():
        n += 1
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cam", required=True)
    ap.add_argument("--matte", required=True)
    ap.add_argument("--crop", required=True, help="X,Y,W in camera pixels; height = round(1.3*W)")
    ap.add_argument("--d", type=int, default=640)
    ap.add_argument("--bg-top", default=BG_TOP, help=f"disk gradient colour at its top (default {BG_TOP})")
    ap.add_argument("--bg-bottom", default=BG_BOTTOM, help=f"disk gradient colour at its bottom (default {BG_BOTTOM})")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    try:
        top, bottom = hex_rgb(a.bg_top), hex_rgb(a.bg_bottom)
    except ValueError as e:
        ap.error(str(e))
    out = os.path.abspath(a.out)
    P = os.path.dirname(os.path.dirname(os.path.dirname(out)))
    cid = os.path.splitext(os.path.basename(out))[0]
    ff, fp, env = _ff.tools(P)

    # Missing, or older than the cam (a re-imported take): segment again rather than reuse a stale matte.
    if not os.path.exists(a.matte) or os.path.getmtime(a.matte) < os.path.getmtime(a.cam):
        print(f"segmenting {a.cam} -> {a.matte}", file=sys.stderr)
        r = subprocess.run([segmenter(), a.cam, a.matte])
        if r.returncode != 0:
            sys.exit(f"segment_person failed on {a.cam}")

    X, Y, W = (int(v) for v in a.crop.split(","))
    Hc, d = round(1.3 * W), a.d
    rate = subprocess.check_output([fp, "-v", "error", "-select_streams", "v:0", "-show_entries",
                                    "stream=r_frame_rate", "-of", "csv=p=0", a.cam], env=env, text=True).strip()
    cam, mat = cv2.VideoCapture(a.cam), cv2.VideoCapture(a.matte)
    fw, fh = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if X < 0 or Y < 0 or X + W > fw or Y + Hc > fh:
        print(f"WARN crop {X},{Y},{W}x{Hc} runs off the {fw}x{fh} frame; padding with transparent pixels", file=sys.stderr)

    os.makedirs(os.path.dirname(out), exist_ok=True)
    # Remotion's ffmpeg has no rawvideo demuxer, so frames go in as lossless RGBA PNGs (fast, low compression).
    enc = subprocess.Popen([ff, "-v", "error", "-y", "-f", "image2pipe", "-c:v", "png", "-framerate", rate,
                            "-i", "-", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", "-b:v", "6M",
                            "-row-mt", "1", out], stdin=subprocess.PIPE, env=env)
    n = 0
    while True:
        ok1, frame = cam.read()
        ok2, mframe = mat.read()
        if not (ok1 and ok2):
            break
        if mframe.shape[:2] != frame.shape[:2]:
            mframe = cv2.resize(mframe, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_LINEAR)
        rgba = render_frame(frame, mframe[..., 0], X, Y, W, d, top, bottom)
        ok, png = cv2.imencode(".png", cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA), [cv2.IMWRITE_PNG_COMPRESSION, 1])
        enc.stdin.write(png.tobytes())
        n += 1
    # Stop at the shorter stream; a one-frame difference is normal, more means the matte isn't this cam's.
    extra = (1 + drain(cam)) if ok1 else (1 + drain(mat)) if ok2 else 0
    if extra > 1:
        cn, mn = (n + extra, n) if ok1 else (n, n + extra)
        print(f"WARN cam has {cn} frames but matte has {mn}; bubble stops at {n}. Delete {a.matte} to re-segment.",
              file=sys.stderr)
    enc.stdin.close()
    if enc.wait() != 0 or n == 0:
        sys.exit(f"ffmpeg failed writing {out} ({n} frames)")
    dur = round(_ff.duration(out, P), 2)

    src = os.path.join(P, "source")
    os.makedirs(src, exist_ok=True)
    link = os.path.join(src, os.path.basename(out))
    if os.path.lexists(link):
        os.remove(link)
    os.symlink(out, link)
    plan_path = os.path.join(P, "plan.json")
    plan = json.load(open(plan_path))
    plan.setdefault("clips", {})[cid] = {"file": os.path.basename(out), "media": "link", "dur": dur, "audio": False}
    json.dump(plan, open(plan_path, "w"), indent=1)
    print(f"{cid}: {n} frames, {dur:.1f} s -> {out}")


if __name__ == "__main__":
    main()
