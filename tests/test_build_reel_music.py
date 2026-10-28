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
CLIP = "clip1"


def build_reels(reel_extra):
    """Make a fixture project with one talk reel (plus `reel_extra`), run build_edit, return REELS."""
    with tempfile.TemporaryDirectory() as tmp:
        p = fixture.make_project(tmp, {CLIP: 3.0})
        fixture.make_music(os.path.join(p, "public", "music.mp3"))
        plan = fixture.read_json(os.path.join(p, "plan.json"))
        reel = {"id": "Reel1", "slug": "r1", "title": "R1",
                "items": [{"clip": CLIP, "talk": [0.0, 3.0]}]}
        plan["reels"] = [dict(reel, **reel_extra)]
        fixture.write_json(os.path.join(p, "plan.json"), plan)
        r = subprocess.run([sys.executable, BUILD, "--project", p], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        with open(os.path.join(p, "src", "edit-data.ts")) as f:
            ts = f.read()
        m = re.search(r"export const REELS: ReelData\[\] = (.*?);\n*\Z", ts, re.S)
        return json.loads(m.group(1))


@fixture.needs_project
class BuildReelMusic(unittest.TestCase):
    def test_music_null_disables_track(self):
        reels = build_reels({"music": None})
        self.assertIsNone(reels[0]["music"])

    def test_music_omitted_still_defaults(self):
        reels = build_reels({})
        self.assertIsNotNone(reels[0]["music"])
        self.assertEqual(reels[0]["music"]["file"], "music.mp3")


if __name__ == "__main__":
    unittest.main()
