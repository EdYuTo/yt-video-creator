"""build_edit maps a reel line's demo + head bubble onto its silence-cut island shots."""
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
FPS = 30


def words(*spans):
    return [[s, e, f"w{i}"] for i, (s, e) in enumerate(spans)]


class Proj:
    """A fixture project with clips voice (8 s), demo (`demo_dur`) and bubble-r1 (8 s)."""

    def __init__(self, demo_dur=2.0):
        self.demo_dur = demo_dur

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = fixture.make_project(self.tmp.name, {"voice": 8.0, "demo": self.demo_dur, "bubble-r1": 8.0})
        return self

    def __exit__(self, *exc):
        self.tmp.cleanup()

    def build(self, items, ws):
        fixture.write_json(os.path.join(self.p, "transcripts", "words.json"),
                           {"voice:0-8": [{"s": 0, "e": 8, "t": "", "w": ws}]})
        plan = fixture.read_json(os.path.join(self.p, "plan.json"))
        plan["reels"] = [{"id": "Reel1", "slug": "r1", "title": "R1", "music": None, "items": items}]
        fixture.write_json(os.path.join(self.p, "plan.json"), plan)
        r = subprocess.run([sys.executable, BUILD, "--project", self.p], capture_output=True, text=True)
        if r.returncode:
            raise AssertionError(r.stdout + r.stderr)
        with open(os.path.join(self.p, "src", "edit-data.ts")) as f:
            m = re.search(r"export const REELS: ReelData\[\] = (.*?);\n*\Z", f.read(), re.S)
        if not m:
            raise AssertionError("REELS not found in edit-data.ts")
        return json.loads(m.group(1))[0]["shots"], r.stdout


def item(demo, pos="bl", talk=(0.0, 8.0)):
    return {"clip": "voice", "talk": list(talk), "demo": demo, "head": {"clip": "bubble-r1", "pos": pos}}


# Word gaps of 1.5 s leave ~1 s of cut silence between islands (pad 0.18/0.28, merge gap 0.6).
SHORT_LINE = words((0.5, 1.0), (1.0, 1.5), (3.0, 3.5))         # islands [0.32,1.78], [2.82,3.78]
LONG_LINE = words((0.5, 1.5), (1.6, 3.0), (4.5, 5.5), (5.6, 7.0))  # ~5 s spoken, island 1 ~3 s


@fixture.needs_project
class BuildReelDemo(unittest.TestCase):
    def test_two_islands_carry_demo_offset(self):
        with Proj() as pj:
            shots, _ = pj.build([item({"clip": "demo", "from": 0})], SHORT_LINE)
        self.assertEqual(len(shots), 2)
        self.assertEqual(shots[0]["demo"]["kind"], "video")
        self.assertAlmostEqual(shots[0]["demo"]["from"], 0, places=3)
        self.assertEqual(shots[1]["demo"]["kind"], "video")
        self.assertAlmostEqual(shots[1]["demo"]["from"], shots[0]["len"] / FPS, places=3)
        self.assertEqual(shots[1]["demo"]["speed"], 1)
        self.assertTrue(shots[1]["demo"]["src"].startswith("footage/demo"))

    def test_speed_scales_offset(self):
        with Proj(demo_dur=8.0) as pj:
            shots, _ = pj.build([item({"clip": "demo", "from": 1.0, "speed": 2, "x": 30})], SHORT_LINE)
        self.assertAlmostEqual(shots[1]["demo"]["from"], 1.0 + 2 * shots[0]["len"] / FPS, places=3)
        self.assertEqual(shots[1]["demo"]["x"], 30)

    def test_demo_shorter_than_line_freezes(self):
        with Proj() as pj:
            shots, out = pj.build([item({"clip": "demo", "from": 0})], LONG_LINE)
            self.assertEqual(len(shots), 2)
            self.assertGreater(shots[0]["len"] / FPS, 2.0)  # the 2 s demo runs out during island 1
            last = shots[-1]["demo"]
            self.assertEqual(last["kind"], "still")
            self.assertRegex(last["photo"], r"^footage/still_demo_\d+\.png$")
            self.assertTrue(os.path.getsize(os.path.join(pj.p, "public", last["photo"])) > 0)
        self.assertIn("WARN demo demo shorter than line", out)

    def test_demo_running_out_mid_shot_warns_and_keeps_video(self):
        # one island of ~1.46 s over a 1 s demo: the shot starts inside the demo, so it stays a video
        # (OffthreadVideo holds the last frame past the end), but the overrun is still reported
        with Proj(demo_dur=1.0) as pj:
            shots, out = pj.build([item({"clip": "demo", "from": 0}, talk=(0.0, 2.0))], SHORT_LINE)
        self.assertEqual(len(shots), 1)
        self.assertGreater(shots[0]["len"] / FPS, 1.0)
        self.assertEqual(shots[0]["demo"]["kind"], "video")
        self.assertIn("WARN demo demo shorter than line", out)

    def test_demo_long_enough_does_not_warn(self):
        with Proj(demo_dur=8.0) as pj:
            _, out = pj.build([item({"clip": "demo", "from": 0})], LONG_LINE)
        self.assertNotIn("shorter than line", out)

    def test_head_follows_source_time_and_previous_pos(self):
        with Proj() as pj:
            shots, _ = pj.build([item({"clip": "demo", "from": 0})], SHORT_LINE)
        for sh in shots:
            a = float(sh["srcClip"].split("@")[1])
            self.assertAlmostEqual(sh["head"]["from"], a, places=2)
            self.assertEqual(sh["head"]["pos"], "bl")
            self.assertTrue(sh["head"]["src"].startswith("footage/bubble-r1"))
        self.assertNotIn("prevPos", shots[0]["head"])
        self.assertEqual(shots[1]["head"]["prevPos"], shots[0]["head"]["pos"])

    def test_prev_pos_crosses_lines(self):
        with Proj() as pj:
            shots, _ = pj.build([item({"card": True}, pos="big", talk=(0.0, 2.0)),
                                 item({"clip": "demo", "from": 0}, pos="bl", talk=(2.5, 8.0))], SHORT_LINE)
        self.assertEqual([s["head"]["pos"] for s in shots], ["big", "bl"])
        self.assertEqual(shots[0]["demo"], {"kind": "card"})
        self.assertEqual(shots[1]["head"]["prevPos"], "big")

    def test_crop_rect_moves_continuously_over_the_line(self):
        r0, r1 = [0.1, 0.1, 0.5, 0.3], [0.3, 0.5, 0.7, 0.7]
        with Proj(demo_dur=8.0) as pj:
            shots, _ = pj.build([item({"clip": "demo", "from": 0, "rect": r0, "rectTo": r1})], SHORT_LINE)
        d0, d1 = shots[0]["demo"], shots[1]["demo"]
        self.assertEqual(d0["kind"], "crop")
        self.assertEqual((d0["srcW"], d0["srcH"], d0["cy"]), (1920, 1080, 0.42))
        for v, w in zip(d0["rect"], r0):
            self.assertAlmostEqual(v, w, places=4)
        for v, w in zip(d1["rectTo"], r1):
            self.assertAlmostEqual(v, w, places=4)
        for v, w in zip(d0["rectTo"], d1["rect"]):  # no jump at the cut between islands
            self.assertAlmostEqual(v, w, places=4)
        self.assertAlmostEqual(d1["from"], shots[0]["len"] / FPS, places=3)

    def test_shot_without_demo_is_unchanged(self):
        with Proj() as pj:
            shots, _ = pj.build([{"clip": "voice", "talk": [0.0, 8.0]}], SHORT_LINE)
        self.assertEqual(len(shots), 2)
        for sh in shots:
            self.assertNotIn("demo", sh)
            self.assertNotIn("head", sh)


if __name__ == "__main__":
    unittest.main()
