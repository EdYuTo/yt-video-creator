"""build_edit marks a reel list that only moves its highlight as a continuation (no entrance replay)."""
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


def line(t0, t1, *anns):
    return {"clip": "voice", "talk": [t0, t1], "cut": False, "anns": list(anns)}


def lst(items, at):
    return {"kind": "list", "x": 8, "y": 10, "items": items, "at": at}


def build(items):
    with tempfile.TemporaryDirectory() as tmp:
        p = fixture.make_project(tmp, {"voice": 10.0})
        plan = fixture.read_json(os.path.join(p, "plan.json"))
        plan["reels"] = [{"id": "Reel1", "slug": "r1", "title": "R1", "music": None, "items": items}]
        fixture.write_json(os.path.join(p, "plan.json"), plan)
        r = subprocess.run([sys.executable, BUILD, "--project", p], capture_output=True, text=True)
        if r.returncode:
            raise AssertionError(r.stdout + r.stderr)
        with open(os.path.join(p, "src", "edit-data.ts")) as f:
            m = re.search(r"export const REELS: ReelData\[\] = (.*?);\n*\Z", f.read(), re.S)
        return json.loads(m.group(1))[0]["anns"]


@fixture.needs_project
class BuildReelLists(unittest.TestCase):
    def test_same_rows_back_to_back_continue_without_intro(self):
        anns = build([
            line(0, 2, lst(["*Plan", "Build", "Ship"], [0, 2])),
            line(2, 4, lst(["Plan", "*Build", "Ship"], [2, 4])),           # same rows, highlight moved
            line(4, 6, lst(["Plan", "Build", "*Ship", "Repeat"], [4, 6])),  # different rows
            line(6, 8, {"kind": "note", "x": 8, "y": 10, "text": "pause", "at": [6, 6.5]},
                 lst(["Plan", "Build", "*Ship", "Repeat"], [6.5, 8])),     # same rows, but 15 frames later
        ])
        lists = [a for a in anns if a["kind"] == "list"]
        self.assertEqual([a["start"] for a in lists], [0, 60, 120, 195])
        self.assertEqual([bool(a.get("noIntro")) for a in lists], [False, True, False, False])
        self.assertEqual([bool(a.get("noOutro")) for a in lists], [True, False, False, False])
        self.assertNotIn("noIntro", next(a for a in anns if a["kind"] == "note"))

    def test_a_note_in_between_does_not_break_the_list_run(self):
        # "previous ann of kind list": other kinds on screen meanwhile don't matter
        anns = build([
            line(0, 2, lst(["*A", "B"], [0, 2])),
            line(2, 4, {"kind": "note", "x": 8, "y": 50, "text": "aside", "at": [2, 4]}, lst(["A", "*B"], [2, 4])),
        ])
        lists = [a for a in anns if a["kind"] == "list"]
        self.assertTrue(lists[1].get("noIntro"))


if __name__ == "__main__":
    unittest.main()
