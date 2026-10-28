import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
sys.path.insert(0, HERE)
from fixture import FF, FP, ENV, make_project, needs_project, read_json, run_ff, write_json  # noqa: E402


def probe(path):
    out = subprocess.check_output(
        [FP, "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate:format=duration",
         "-of", "json", path], env=ENV)
    return json.loads(out)


def make_webm(raw, seconds=2):
    run_ff("-f", "lavfi", "-i", f"nullsrc=s=1920x1080:r=25:d={seconds}",
           "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
           "-vf", "format=yuv420p", "-c:v", "libvpx-vp9", "-deadline", "realtime", "-cpu-used", "8",
           "-b:v", "3M", "-c:a", "libopus", "-shortest", raw)


@needs_project
class ImportTakeTest(unittest.TestCase):
    def test_four_by_three_camera_is_pillarboxed_not_stretched(self):
        import numpy as np
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            proj = make_project(tmp, {})
            png = os.path.join(tmp, "white.png")
            Image.new("RGB", (1440, 1080), (255, 255, 255)).save(png)
            raw = os.path.join(tmp, "r1-take.webm")
            run_ff("-loop", "1", "-framerate", "25", "-i", png, "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                   "-t", "1", "-vf", "format=yuv420p", "-c:v", "libvpx-vp9", "-deadline", "realtime", "-cpu-used", "8",
                   "-b:v", "3M", "-c:a", "libopus", "-shortest", raw)
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "import_take.py"), proj, raw, "--id", "voice-r1"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            mp4 = os.path.join(proj, "recordings", "voice", "voice-r1.mp4")
            v = next(s for s in probe(mp4)["streams"] if s["codec_type"] == "video")
            self.assertEqual((v["width"], v["height"], v["r_frame_rate"]), (1920, 1080, "30/1"))
            frame = os.path.join(tmp, "f.png")
            run_ff("-i", mp4, "-frames:v", "1", frame)
            y = np.asarray(Image.open(frame).convert("L"), dtype=float)
            # 1440x1080 fits at full height: white 1440 px in the middle, 240 px black bars each side
            self.assertLess(y[:, :230].mean(), 30)
            self.assertLess(y[:, -230:].mean(), 30)
            self.assertGreater(y[:, 250:-250].mean(), 220)

    def test_imports_truncated_webm(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = make_project(tmp, {})
            raw_dir = os.path.join(proj, "recordings", "raw")
            os.makedirs(raw_dir)
            raw = os.path.join(raw_dir, "r1-2026-10-28T20-09-30-731Z.webm")
            make_webm(raw, 4)
            with open(raw, "rb") as f:
                data = f.read()
            with open(raw, "wb") as f:
                f.write(data[: int(len(data) * 0.7)])
            log = {"reel": "r1", "take": "2026-10-28T20-09-30-731Z", "events": [{"type": "line", "t": 0, "line": 0}]}
            with open(raw[:-len(".webm")] + ".log.json", "w") as f:
                json.dump(log, f)

            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "import_take.py"), proj, raw, "--id", "voice-r1"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)

            mp4 = os.path.join(proj, "recordings", "voice", "voice-r1.mp4")
            info = probe(mp4)
            v = next(s for s in info["streams"] if s["codec_type"] == "video")
            a = next(s for s in info["streams"] if s["codec_type"] == "audio")
            self.assertEqual((v["codec_name"], v["width"], v["height"], v["r_frame_rate"]), ("h264", 1920, 1080, "30/1"))
            self.assertEqual((a["codec_name"], a["sample_rate"]), ("aac", "48000"))
            dur = float(info["format"]["duration"])
            self.assertGreater(dur, 2)

            link = os.path.join(proj, "source", "voice-r1.mp4")
            self.assertTrue(os.path.islink(link))
            self.assertEqual(os.path.realpath(link), os.path.realpath(mp4))
            clip = read_json(os.path.join(proj, "plan.json"))["clips"]["voice-r1"]
            self.assertEqual((clip["file"], clip["media"], clip["audio"]), ("voice-r1.mp4", "link", True))
            self.assertAlmostEqual(clip["dur"], dur, delta=0.05)
            self.assertEqual(read_json(os.path.join(proj, "recordings", "voice", "voice-r1.log.json")), log)

    def test_reimport_drops_only_that_clips_stale_words(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = make_project(tmp, {})
            words_path = os.path.join(proj, "transcripts", "words.json")
            seg = [{"s": 0, "e": 1, "t": "x", "w": [[0, 1, "x"]]}]
            write_json(words_path, {"voice-r1:0.0-65.3": seg, "voice-r1:70.0-80.0": seg,
                                    "voice-r2:0.0-30.0": seg, "voice-r10:0.0-5.0": seg})
            raw = os.path.join(tmp, "r1-take.webm")
            make_webm(raw)

            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "import_take.py"), proj, raw, "--id", "voice-r1"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("dropped 2 stale transcript window(s) for voice-r1", r.stdout)
            self.assertEqual(sorted(read_json(words_path)), ["voice-r10:0.0-5.0", "voice-r2:0.0-30.0"])
            self.assertFalse(os.path.exists(words_path + ".tmp"))

            # nothing stale (and a project without words.json): silent, no file created
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "import_take.py"), proj, raw, "--id", "voice-r1"],
                               capture_output=True, text=True)
            self.assertNotIn("dropped", r.stdout)
            os.remove(words_path)
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "import_take.py"), proj, raw, "--id", "voice-r1"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse(os.path.exists(words_path))


if __name__ == "__main__":
    unittest.main()
