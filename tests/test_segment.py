import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
sys.path.insert(0, HERE)
sys.path.insert(0, SCRIPTS)
from fixture import FOOTAGE, FOOTAGE_AT, needs_footage, needs_project, run_ff  # noqa: E402



def frames(path):
    cap = cv2.VideoCapture(path)
    out = []
    while True:
        ok, f = cap.read()
        if not ok:
            return np.array(out)
        out.append(f)


@unittest.skipUnless(shutil.which("swiftc"), "swiftc missing")
@needs_project
@needs_footage
class SegmentPersonTest(unittest.TestCase):
    """Apple Vision person segmentation on real footage. YVC_TEST_FOOTAGE: a video of one person talking to the
    camera (head and shoulders, face visible); YVC_TEST_FOOTAGE_AT: a second where they are on screen (3 s are
    used). Skipped unless both a project (YVC_TEST_PROJECT, for ffmpeg) and the footage are given."""

    @classmethod
    def setUpClass(cls):
        import bubble
        cls.seg = bubble.segmenter()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.cam = os.path.join(cls.tmp.name, "cam.mp4")
        # Uniform scale to 1920 wide at 30 fps, like the voice recordings; the fractional boxes still hold.
        run_ff("-ss", str(FOOTAGE_AT), "-i", FOOTAGE, "-t", "3", "-an", "-vf", "scale=1920:-2", "-r", "30",
               "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", cls.cam)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_matte_covers_face_not_background(self):
        matte = os.path.join(self.tmp.name, "matte.mp4")
        r = subprocess.run([self.seg, self.cam, matte], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

        c, m = frames(self.cam), frames(matte)
        self.assertEqual(len(m), len(c))
        self.assertEqual(m.shape[1:3], c.shape[1:3])
        m = m[..., 0].astype(np.float32) / 255
        # Footage-agnostic: a person is found in every frame, covering part (not all) of it, with a confident
        # (mostly 0 or 1) matte and a stable outline from frame to frame.
        person = (m > 0.5).mean(axis=(1, 2))
        hint = f"; is the person on screen at YVC_TEST_FOOTAGE_AT={FOOTAGE_AT} s of {FOOTAGE}?"
        self.assertGreater(person.min(), 0.03, "no person in some frames" + hint)
        self.assertLess(person.max(), 0.85, "matte covers nearly the whole frame" + hint)
        unsure = ((m > 0.1) & (m < 0.9)).mean()
        self.assertLess(unsure, 0.1, f"{unsure:.0%} of matte pixels are neither person nor background")
        self.assertLess(np.abs(np.diff(m > 0.5, axis=0)).mean(), 0.02, "matte flickers between frames")

    def test_interrupted_run_leaves_old_matte_and_no_partial(self):
        d = os.path.join(self.tmp.name, "interrupted")
        os.makedirs(d)
        matte = os.path.join(d, "matte.mp4")
        with open(matte, "wb") as f:
            f.write(b"old matte")
        partial = os.path.join(d, ".matte.partial.mp4")
        p = subprocess.Popen([self.seg, self.cam, matte], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        t0 = time.time()  # interrupt as soon as it is mid-run (writing its partial file), not after a fixed sleep
        while not os.path.exists(partial) and p.poll() is None and time.time() - t0 < 30:
            time.sleep(0.02)
        time.sleep(0.2)
        self.assertIsNone(p.poll(), "segment_person finished before it could be interrupted")
        p.send_signal(signal.SIGTERM)
        self.assertNotEqual(p.wait(), 0)
        with open(matte, "rb") as f:
            self.assertEqual(f.read(), b"old matte")
        self.assertEqual(os.listdir(d), ["matte.mp4"])

    def test_failed_run_leaves_no_matte(self):
        bogus = os.path.join(self.tmp.name, "not-a-video.mp4")
        with open(bogus, "w") as f:
            f.write("nope")
        matte = os.path.join(self.tmp.name, "failed", "matte.mp4")
        os.makedirs(os.path.dirname(matte))
        r = subprocess.run([self.seg, bogus, matte], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(os.listdir(os.path.dirname(matte)), [])

if __name__ == "__main__":
    unittest.main()
