import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
sys.path.insert(0, HERE)
sys.path.insert(0, SCRIPTS)
from fixture import FOOTAGE, FOOTAGE_AT, needs_footage, needs_project, make_project, read_json, run_ff  # noqa: E402
import fixture  # noqa: E402
from bubble import bubble_frame, render_frame  # noqa: E402

TOP, BOTTOM = (0xC8, 0xA2, 0xE8), (0xEB, 0xDD, 0xF7)
BUBBLE = os.path.join(SCRIPTS, "bubble.py")


def clip(path, frames, w=320, h=240):
    run_ff("-f", "lavfi", "-i", f"nullsrc=s={w}x{h}:r=30", "-frames:v", str(frames),
           "-vf", "format=yuv420p", "-c:v", "libx264", "-preset", "ultrafast", path)


def video_info(path):
    return json.loads(subprocess.check_output(
        [fixture.FP, "-v", "error", "-count_frames", "-show_entries",
         "stream=codec_name,width,height,nb_read_frames:stream_tags=alpha_mode:format=duration",
         "-of", "json", path], env=fixture.ENV))


class BubbleFrameTest(unittest.TestCase):
    def test_zero_matte_gives_lavender_disk(self):
        d = 100
        cam = np.zeros((130, d, 3), np.uint8)
        cam[..., 0] = 255  # red
        out = bubble_frame(cam, np.zeros((130, d), np.float32), d)
        centre = out[80, 50]  # (H - d/2, d/2)
        self.assertEqual(centre[3], 255)
        mid = [(a + b) / 2 for a, b in zip(TOP, BOTTOM)]
        for got, want in zip(centre[:3], mid):
            self.assertAlmostEqual(int(got), want, delta=6)
        self.assertEqual(out[0, 0, 3], 0)

    def test_full_matte_breaks_out_above_and_clips_below(self):
        d = 100
        rng = np.random.default_rng(1)
        cam = rng.integers(0, 256, (130, d, 3), dtype=np.uint8)
        out = bubble_frame(cam, np.ones((130, d), np.float32), d)
        # Above the circle's top edge (row 30): the head breaks out, opaque and showing the camera.
        self.assertEqual(out[10, 50, 3], 255)
        np.testing.assert_array_equal(out[10, 50, :3], cam[10, 50])
        # Below the centre and outside the disk: the body is clipped by the circle.
        self.assertEqual(out[129, 0, 3], 0)

    def test_custom_gradient(self):
        import bubble
        top, bottom = bubble.hex_rgb("#102030"), bubble.hex_rgb("405060")
        self.assertEqual(list(top), [0x10, 0x20, 0x30])
        out = bubble_frame(np.zeros((130, 100, 3), np.uint8), np.zeros((130, 100), np.float32), 100, top, bottom)
        for got, want in zip(out[80, 50, :3], (top + bottom) / 2):
            self.assertAlmostEqual(int(got), want, delta=6)
        np.testing.assert_array_equal(bubble.TOP, np.array(TOP, np.float32))  # defaults unchanged
        np.testing.assert_array_equal(bubble.BOTTOM, np.array(BOTTOM, np.float32))
        with self.assertRaises(ValueError):
            bubble.hex_rgb("lavender")

    def test_bad_colour_flag_is_a_usage_error(self):
        r = subprocess.run([sys.executable, BUBBLE, "--cam", "x.mp4", "--matte", "m.mp4", "--crop", "0,0,10",
                            "--out", "o.webm", "--bg-top", "nope"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("not a #RRGGBB colour", r.stderr)

    def test_shape_and_dtype(self):
        out = bubble_frame(np.zeros((130, 100, 3), np.uint8), np.zeros((130, 100), np.float32), 100)
        self.assertEqual(out.shape, (130, 100, 4))
        self.assertEqual(out.dtype, np.uint8)


class OffFrameCropTest(unittest.TestCase):
    def test_off_frame_crop_is_transparent_without_dark_edges(self):
        # Real geometry: 1920x1080 voice, W = 900 -> crop height 1170, so Y = -50 overflows top (50) and bottom (40).
        skin = (120, 150, 200)  # BGR
        frame = np.zeros((1080, 1920, 3), np.uint8)
        frame[:] = skin
        matte = np.full((1080, 1920), 255, np.uint8)  # person everywhere in frame
        out = render_frame(frame, matte, 500, -50, 900, 640)
        self.assertEqual(out.shape, (832, 640, 4))
        top_pad, bottom_pad = 50 / 1170 * 832, 40 / 1170 * 832  # ~35.6 and ~28.4 rows
        self.assertTrue((out[: int(top_pad), :, 3] == 0).all())
        self.assertTrue((out[832 - int(bottom_pad):, :, 3] == 0).all())
        # In-frame person pixels keep their alpha: above the rim (breakout) and in the disk.
        self.assertTrue((out[int(top_pad) + 2: 150, :, 3] == 255).all())
        self.assertEqual(out[832 - 320, 320, 3], 255)
        # Pad pixels carry the edge colour, not black, so neither the resize nor yuva420p's 2x2 chroma can
        # darken the visible edge: every pixel, visible or not, is the camera colour.
        rgb = out[..., :3].astype(int)
        self.assertLessEqual(np.abs(rgb - np.array(skin[::-1])).max(), 1)


@needs_project
class MatteSyncTest(unittest.TestCase):
    def run_bubble(self, cam_frames, matte_frames):
        with tempfile.TemporaryDirectory() as tmp:
            proj = make_project(tmp, {})
            cam, matte = os.path.join(tmp, "cam.mp4"), os.path.join(tmp, "matte.mp4")
            clip(cam, cam_frames)
            clip(matte, matte_frames)  # written after cam, so it is not stale
            out = os.path.join(proj, "recordings", "voice", "bubble-r1.webm")
            r = subprocess.run([sys.executable, BUBBLE, "--cam", cam, "--matte", matte, "--crop", "0,0,100",
                                "--d", "100", "--out", out], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            return r.stderr, int(video_info(out)["streams"][0]["nb_read_frames"])

    def test_frame_count_mismatch_warns(self):
        err, n = self.run_bubble(90, 30)
        self.assertIn("WARN", err)
        self.assertIn("90", err)
        self.assertEqual(n, 30)

    def test_one_frame_difference_is_silent(self):
        err, n = self.run_bubble(31, 30)
        self.assertNotIn("WARN", err)
        self.assertEqual(n, 30)


@unittest.skipUnless(shutil.which("swiftc"), "swiftc missing")
@needs_project
@needs_footage
class BubbleCliTest(unittest.TestCase):
    """End to end on real footage: YVC_TEST_FOOTAGE (a person talking to the camera, landscape) from
    YVC_TEST_FOOTAGE_AT seconds; the crop is a fixed box, so only formats and registration are checked."""

    def test_cli_resegments_stale_matte_writes_alpha_webm_and_registers_clip(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = make_project(tmp, {})
            cam = os.path.join(tmp, "voice-r1.mp4")
            run_ff("-ss", str(FOOTAGE_AT), "-i", FOOTAGE, "-t", "3", "-an", "-vf", "scale=1920:-2", "-r", "30",
                   "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", cam)
            # A matte left over from an earlier take: older than the cam, and the wrong length.
            matte = os.path.join(tmp, "voice-r1.matte.mp4")
            clip(matte, 30, 1920, 1246)
            t = os.path.getmtime(cam) - 100
            os.utime(matte, (t, t))
            out = os.path.join(proj, "recordings", "voice", "bubble-r1.webm")
            r = subprocess.run([sys.executable, BUBBLE, "--cam", cam, "--matte", matte,
                                "--crop", "150,250,600", "--d", "320", "--out", out], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertGreater(os.path.getmtime(matte), os.path.getmtime(cam))  # re-segmented
            self.assertEqual(int(video_info(matte)["streams"][0]["nb_read_frames"]), 90)
            self.assertNotIn("WARN", r.stderr)

            info = video_info(out)
            v = info["streams"][0]
            self.assertEqual((v["codec_name"], v["width"], v["height"]), ("vp9", 320, 416))
            self.assertEqual(v["tags"]["alpha_mode"], "1")
            self.assertEqual(int(v["nb_read_frames"]), 90)

            link = os.path.join(proj, "source", "bubble-r1.webm")
            self.assertTrue(os.path.islink(link))
            self.assertEqual(os.path.realpath(link), os.path.realpath(out))
            clip_ = read_json(os.path.join(proj, "plan.json"))["clips"]["bubble-r1"]
            self.assertEqual((clip_["file"], clip_["media"], clip_["audio"]), ("bubble-r1.webm", "link", False))
            self.assertAlmostEqual(clip_["dur"], float(info["format"]["duration"]), delta=0.05)

if __name__ == "__main__":
    unittest.main()
