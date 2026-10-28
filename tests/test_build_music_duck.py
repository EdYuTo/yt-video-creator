"""build_edit's "duck" music bed (long form and reels): looping, and bad loop bounds as clear errors, never a hang."""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixture  # noqa: E402

BUILD = os.path.join(fixture.TOOLKIT, "scripts", "build_edit.py")


def build(music, reel=False, song=5):
    """Fixture project with 8 s of talk under a `song`-second music.mp3; returns (returncode, output, music data)."""
    with tempfile.TemporaryDirectory() as tmp:
        p = fixture.make_project(tmp, {"clip1": 8.0})
        fixture.make_music(os.path.join(p, "public", "music.mp3"), song)
        plan = fixture.read_json(os.path.join(p, "plan.json"))
        item = {"clip": "clip1", "talk": [0.0, 8.0], "cut": False}
        if reel:
            plan["reels"] = [{"id": "Reel1", "slug": "r1", "title": "R1", "music": music, "items": [item]}]
        else:
            plan["long"] = {"sections": [{"items": [item]}], "music": music}
        fixture.write_json(os.path.join(p, "plan.json"), plan)
        r = subprocess.run([sys.executable, BUILD, "--project", p], capture_output=True, text=True, timeout=120)
        data = None
        if r.returncode == 0:
            with open(os.path.join(p, "src", "edit-data.ts")) as f:
                ts = f.read()
            if reel:
                data = json.loads(re.search(r"export const REELS: ReelData\[\] = (.*?);\n*\Z", ts, re.S).group(1))[0]["music"]
            else:
                data = json.loads(re.search(r"export const LONG: LongData \| null = (\{.*?\n\});\n", ts, re.S).group(1))["music"]
        return r.returncode, r.stdout + r.stderr, data


@fixture.needs_project
class DuckMusic(unittest.TestCase):
    def test_long_bed_loops_between_loop_points(self):
        rc, out, m = build({"mode": "duck", "volume": 0.14, "duckVolume": 0.03, "startSec": 0.5, "loopFrom": 1.0, "loopTo": 4.0})
        self.assertEqual(rc, 0, out)
        runs = m["runs"]
        self.assertEqual([r["songFrom"] for r in runs], [0.5, 1.0, 1.0])  # 3.5 s, then 3 s loops
        self.assertEqual([r["len"] for r in runs[:2]], [105, 90])
        self.assertEqual(sum(r["len"] for r in runs), runs[-1]["start"] + runs[-1]["len"])
        self.assertTrue(all(r["len"] > 0 for r in runs))
        self.assertEqual(m["duckVolume"], 0.03)
        self.assertEqual(m["duck"], [[0, 240]])  # all talk

    def test_bad_loop_bounds_are_clear_errors_not_hangs(self):
        for music, needle in [
            ({"loopFrom": 3.0, "loopTo": 3.0}, "loopFrom < loopTo"),
            ({"loopFrom": 3.0, "loopTo": 2.0}, "loopFrom < loopTo"),
            ({"loopFrom": 1.0, "loopTo": 9.0}, "song length"),
            ({"loopFrom": 1.0, "loopTo": 3.0, "startSec": 4.0}, "startSec 4.0 must be at least a frame before loopTo"),
        ]:
            for reel in (False, True):
                with self.subTest(music=music, reel=reel):
                    rc, out, _ = build(dict(music, mode="duck"), reel=reel)
                    self.assertNotEqual(rc, 0)
                    self.assertIn(needle, out)
                    self.assertIn("Reel1 music" if reel else "long music", out)

    def test_reel_bed_loops_too(self):
        rc, out, m = build({"mode": "duck", "loopFrom": 1.0, "loopTo": 4.0}, reel=True)
        self.assertEqual(rc, 0, out)
        self.assertEqual([r["songFrom"] for r in m["runs"]], [0, 1.0, 1.0])


if __name__ == "__main__":
    unittest.main()
