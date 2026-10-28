import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
sys.path.insert(0, SCRIPTS)
import assemble_reels  # noqa: E402

MANIFEST = {
    "r1-page": {"type": "web"},
    "r1-shot": {"type": "crop", "clip": "screen-rec", "from": 12.5, "rect": [0.1, 0.2, 0.5, 0.3]},
    "r1-pan": {"type": "crop", "clip": "screen-rec", "from": 3, "rect": [0, 0, 1, 0.5],
               "rectTo": [0.2, 0.2, 0.6, 0.3], "cy": 0.4},
    "r1-screen": {"type": "video", "clip": "screen-rec", "from": 40, "x": 0.3, "zoom": 1.4},
}


def doc():
    return {"wpm": 140, "reels": [
        {"id": "r0", "slug": "massa-fresca", "title": "Massa fresca", "caption": "ignorado",
         "hook": {"big": "Massa fresca", "small": "etapas"},
         "end": {"big": "Salve", "small": "mapa", "items": ["a", "b"]},
         "lines": [{"text": "um", "demo": "card", "head": "big"}]},
        {"id": "r1", "slug": "molho", "title": "Molho",
         "hook": {"big": "Molho", "small": "x"}, "end": {"big": "Salve", "small": "y"},
         "lines": [
             {"text": "zero", "demo": "r1-page", "confirm": True,
              "anns": [{"kind": "label", "x": 6, "y": 5, "text": "A", "in": 0.5, "out": 1.0},
                       {"kind": "arrow", "x": 50, "y": 8, "to": [62, 22]}]},
             {"text": "um", "demo": "r1-shot", "head": "tl"},
             {"text": "dois", "demo": "r1-page"},
             {"text": "três", "demo": "r1-pan"},
             {"text": "quatro", "demo": "r1-screen", "head": "big"},
             {"text": "cinco", "demo": "card"},
             {"text": "seis", "demo": "r1-shot"},
         ]}]}


def write(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


def take(n, start, end):
    return {"line": n, "start": start, "end": end, "score": 1.0, "text": "t", "subs": [[start, end, "t"]]}


TAKES = {"r1": [take(0, 10.0, 14.0), take(2, 20.0, 22.0), take(3, 30.0, 33.0), take(4, 40.0, 41.0),
                take(5, 50.0, 52.0), take(6, 60.0, 62.0)],
         "r0": [take(0, 1.0, 3.0)]}


class AssembleTest(unittest.TestCase):
    def reels(self, **kw):
        return assemble_reels.assemble(kw.get("doc") or doc(), kw.get("takes", TAKES), kw.get("manifest", MANIFEST))

    def test_ids_slugs_titles(self):
        r = self.reels()
        self.assertEqual([x["id"] for x in r], ["Reel1", "Reel2"])
        self.assertEqual((r[1]["slug"], r[1]["title"]), ("molho", "Molho"))
        self.assertNotIn("caption", r[0])

    def test_hook_end_music(self):
        r = self.reels()[0]
        self.assertEqual(r["hook"], {"sec": 2.6, "big": "Massa fresca", "small": "etapas"})
        self.assertEqual(r["end"], {"sec": 3.4, "big": "Salve", "small": "mapa", "items": ["a", "b"]})
        self.assertIsNone(r["music"])

    def test_line_without_take_is_skipped(self):
        items = self.reels()[1]["items"]
        self.assertEqual(len(items), 6)  # line 1 has no take
        self.assertEqual([i["talk"] for i in items], [[10.0, 14.0], [20.0, 22.0], [30.0, 33.0], [40.0, 41.0], [50.0, 52.0], [60.0, 62.0]])

    def test_item_shape(self):
        it = self.reels()[1]["items"][0]
        self.assertEqual(it["clip"], "voice-r1")
        self.assertEqual(it["subs"], [[10.0, 14.0, "t"]])
        self.assertEqual(it["head"], {"clip": "bubble-r1", "pos": "bl"})
        self.assertNotIn("confirm", it)
        self.assertEqual(self.reels()[1]["items"][1]["head"]["pos"], "bl")  # line 2 has no head
        self.assertEqual(self.reels()[1]["items"][3]["head"]["pos"], "big")
        self.assertEqual(self.reels()[0]["items"][0]["head"]["pos"], "big")

    def test_ann_fractions_map_onto_take_window(self):
        label, arrow = self.reels()[1]["items"][0]["anns"]
        self.assertEqual(label["at"], [12.0, 14.0])  # in 0.5, out 1.0 of 10..14
        self.assertNotIn("in", label)
        self.assertNotIn("out", label)
        self.assertEqual(label["kind"], "label")
        self.assertAlmostEqual(arrow["at"][0], 10.4)  # default in 0.1
        self.assertAlmostEqual(arrow["at"][1], 14.0)
        self.assertEqual(arrow["to"], [62, 22])

    def test_input_not_mutated(self):
        d = doc()
        self.reels(doc=d)
        self.assertEqual(d, doc())

    def test_trans(self):
        items = self.reels()[1]["items"]
        self.assertEqual([i.get("trans") for i in items], ["zoom", None, "whip", "whip", "whip", "whip"])

    def test_demo_resolution(self):
        items = self.reels()[1]["items"]
        self.assertEqual(items[0]["demo"], {"clip": "demo-r1-page", "from": 0})
        # same beat as item 0 (the skipped line 2 in between neither breaks nor advances): continues after 4 s
        self.assertEqual(items[1]["demo"], {"clip": "demo-r1-page", "from": 4.0})
        self.assertEqual(items[5]["demo"], {"clip": "screen-rec", "from": 12.5, "rect": [0.1, 0.2, 0.5, 0.3]})
        self.assertEqual(items[2]["demo"], {"clip": "screen-rec", "from": 3, "rect": [0, 0, 1, 0.5],
                                            "rectTo": [0.2, 0.2, 0.6, 0.3], "cy": 0.4})
        self.assertEqual(items[3]["demo"], {"clip": "screen-rec", "from": 40, "x": 0.3, "zoom": 1.4})
        self.assertEqual(items[4]["demo"], {"card": True})

    def test_unknown_beat_names_reel_line_and_id(self):
        d = doc()
        d["reels"][1]["lines"][2]["demo"] = "r1-nope"
        with self.assertRaises(ValueError) as cm:
            self.reels(doc=d)
        msg = str(cm.exception)
        for part in ("r1", "line 3", "r1-nope"):
            self.assertIn(part, msg)

    def test_skipped_line_with_unknown_beat_is_not_an_error(self):
        d = doc()
        d["reels"][1]["lines"][1]["demo"] = "r1-nope"  # line 1 has no take
        self.assertEqual(len(self.reels(doc=d)[1]["items"]), 6)

    def test_hook_items_kept_and_reel_without_takes(self):
        r = self.reels(takes={})
        self.assertEqual(r[0]["items"], [])


class RunTest(unittest.TestCase):
    def run_doc(self, demos, takes_for=None, manifest=MANIFEST):
        d = {"reels": [{"id": "r1", "slug": "s", "title": "T", "lines": [{"text": "x", "demo": b} for b in demos]}]}
        windows = takes_for or [(10 * n, 10 * n + 2 + n) for n in range(len(demos))]  # durations 2, 3, 4...
        tk = {"r1": [take(n, a, b) for n, (a, b) in enumerate(windows) if a is not None]}
        return d, tk, assemble_reels.assemble(d, tk, manifest)[0]["items"]

    def test_same_web_beat_continues(self):
        d, tk, items = self.run_doc(["r1-page"] * 3)
        self.assertEqual([i["demo"]["from"] for i in items], [0, 2, 5])
        self.assertEqual(assemble_reels.demo_runs(d, tk), {("r1", "r1-page", 0): 9})

    def test_card_breaks_run(self):
        d, tk, items = self.run_doc(["r1-page", "r1-page", "card", "r1-page"])
        self.assertEqual([i["demo"].get("from") for i in items], [0, 2, None, 0])
        self.assertEqual(assemble_reels.demo_runs(d, tk),
                         {("r1", "r1-page", 0): 5, ("r1", "r1-page", 1): 5})

    def test_other_beat_breaks_run(self):
        _, _, items = self.run_doc(["r1-page", "r1-shot", "r1-page"])
        self.assertEqual(items[2]["demo"]["from"], 0)

    def test_skipped_line_between_same_beat_continues(self):
        windows = [(0, 2), (None, None), (20, 24)]
        _, _, items = self.run_doc(["r1-page"] * 3, windows)
        self.assertEqual([i["demo"]["from"] for i in items], [0, 2])

    def test_crop_and_video_base_from_honoured(self):
        _, _, items = self.run_doc(["r1-shot", "r1-shot"])
        self.assertEqual([i["demo"]["from"] for i in items], [12.5, 14.5])
        self.assertEqual(items[1]["demo"]["rect"], [0.1, 0.2, 0.5, 0.3])  # rect given per line, unchanged
        m = dict(MANIFEST, **{"r1-fast": {"type": "video", "clip": "c", "from": 40, "speed": 2}})
        _, _, items = self.run_doc(["r1-fast", "r1-fast"], manifest=m)
        self.assertEqual([i["demo"]["from"] for i in items], [40, 44])  # 2 s of talk at speed 2

    def test_cli_prints_record_length_for_web_beats(self):
        with tempfile.TemporaryDirectory() as p:
            d, tk, _ = self.run_doc(["r1-page"] * 3)
            for sub in ("scripts", "takes", "demos"):
                os.makedirs(os.path.join(p, sub))
            write(os.path.join(p, "scripts", "reels.json"), d)
            write(os.path.join(p, "takes", "r1.json"), tk["r1"])
            write(os.path.join(p, "demos", "manifest.json"), MANIFEST)
            write(os.path.join(p, "plan.json"), {})
            out = subprocess.run([sys.executable, os.path.join(SCRIPTS, "assemble_reels.py"), p],
                                 capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertIn("record r1-page (run 1): at least 9.0 s", out.stdout)


class CliTest(unittest.TestCase):
    def test_writes_reels_and_keeps_other_keys(self):
        with tempfile.TemporaryDirectory() as p:
            for sub in ("scripts", "takes", "demos"):
                os.makedirs(os.path.join(p, sub))
            write(os.path.join(p, "scripts", "reels.json"), doc())
            write(os.path.join(p, "takes", "r1.json"), TAKES["r1"])  # r0 has no takes file
            write(os.path.join(p, "demos", "manifest.json"), MANIFEST)
            write(os.path.join(p, "plan.json"), {"fps": 30, "clips": {"a": 1}, "reels": [{"old": 1}]})
            out = subprocess.run([sys.executable, os.path.join(SCRIPTS, "assemble_reels.py"), p],
                                 capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            with open(os.path.join(p, "plan.json")) as f:
                plan = json.load(f)
            self.assertEqual((plan["fps"], plan["clips"]), (30, {"a": 1}))
            # r0 has no takes yet: skipped with a WARN, and the old plan.json reels had no Reel1 to keep
            self.assertEqual([r["id"] for r in plan["reels"]], ["Reel2"])
            self.assertEqual(len(plan["reels"][0]["items"]), 6)
            self.assertIn("WARN r0: no takes yet", out.stdout)
            self.assertEqual([f for f in os.listdir(p) if f.startswith("plan.json.")], [])

    def project(self, p, reels_doc, takes, plan_reels):
        for sub in ("scripts", "takes", "demos"):
            os.makedirs(os.path.join(p, sub))
        write(os.path.join(p, "scripts", "reels.json"), reels_doc)
        for rid, tk in takes.items():
            write(os.path.join(p, "takes", f"{rid}.json"), tk)
        write(os.path.join(p, "demos", "manifest.json"), MANIFEST)
        write(os.path.join(p, "plan.json"), {"fps": 30, "reels": plan_reels})

    def cli(self, p, *args):
        return subprocess.run([sys.executable, os.path.join(SCRIPTS, "assemble_reels.py"), p, *args],
                              capture_output=True, text=True)

    def test_reels_flag_assembles_only_those_and_keeps_the_rest(self):
        d = doc()
        d["reels"].append({"id": "r2", "slug": "later", "title": "Later", "lines": [{"text": "x", "demo": "r2-not-yet"}]})
        with tempfile.TemporaryDirectory() as p:
            # r2 has a take but its beat is not in the manifest: assembling everything is an error...
            self.project(p, d, dict(TAKES, r2=[take(0, 1.0, 2.0)]),
                         [{"id": "Reel1", "slug": "massa-fresca", "old": 1}, {"id": "Reel2", "slug": "molho", "old": 2},
                          {"id": "Reel3", "slug": "later", "old": 3}])
            out = self.cli(p)
            self.assertNotEqual(out.returncode, 0)
            self.assertIn("r2-not-yet", out.stderr)
            self.assertIn("--reels", out.stderr)
            # ...but --reels r1 leaves r0 and r2 as they are in plan.json
            out = self.cli(p, "--reels", "r1")
            self.assertEqual(out.returncode, 0, out.stderr)
            with open(os.path.join(p, "plan.json")) as f:
                reels = json.load(f)["reels"]
            self.assertEqual([r["id"] for r in reels], ["Reel1", "Reel2", "Reel3"])
            self.assertEqual((reels[0]["old"], reels[2]["old"]), (1, 3))
            self.assertEqual([r["script"] for r in reels], ["r0", "r1", "r2"])
            self.assertEqual(len(reels[1]["items"]), 6)
            self.assertEqual(reels[1]["slug"], "molho")
            # an id that is not in reels.json is an error
            out = self.cli(p, "--reels", "r1,r9")
            self.assertNotEqual(out.returncode, 0)
            self.assertIn("r9", out.stderr)

    def test_kept_reels_follow_their_script_not_their_position(self):
        d = doc()
        d["reels"].insert(0, {"id": "r9", "slug": "new-first", "title": "New", "lines": [{"text": "x", "demo": "card"}]})
        with tempfile.TemporaryDirectory() as p:
            # plan.json from before r9 was added at the top: by position, Reel1 would now be paired with r9
            self.project(p, d, TAKES, [{"id": "Reel1", "slug": "massa-fresca", "old": "r0"},
                                       {"id": "Reel2", "script": "r1", "slug": "renamed", "old": "r1"}])
            out = self.cli(p, "--reels", "r9")
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertIn("WARN r9: no takes yet", out.stdout)
            self.assertIn("not in plan.json yet", out.stdout)
            with open(os.path.join(p, "plan.json")) as f:
                reels = json.load(f)["reels"]
            # r0 matched by slug, r1 by its recorded script id (despite the slug change); both renumbered
            self.assertEqual([(r["id"], r["script"], r["old"]) for r in reels], [("Reel2", "r0", "r0"), ("Reel3", "r1", "r1")])
            with open(os.path.join(p, "takes", "r9.json"), "w") as f:
                json.dump([take(0, 1.0, 2.0)], f)
            out = self.cli(p, "--reels", "r9")
            self.assertEqual(out.returncode, 0, out.stderr)
            with open(os.path.join(p, "plan.json")) as f:
                reels = json.load(f)["reels"]
            self.assertEqual([(r["id"], r["script"]) for r in reels], [("Reel1", "r9"), ("Reel2", "r0"), ("Reel3", "r1")])
            self.assertEqual(reels[0]["slug"], "new-first")
            self.assertNotIn("old", reels[0])

    def test_reel_without_takes_and_beats_is_skipped_with_warn(self):
        d = doc()
        d["reels"].append({"id": "r2", "slug": "later", "title": "Later", "lines": [{"text": "x", "demo": "r2-not-yet"}]})
        with tempfile.TemporaryDirectory() as p:
            self.project(p, d, TAKES, [{"id": "Reel3", "slug": "later", "old": 3}])  # no takes/r2.json, no r2-not-yet beat
            out = self.cli(p, "--reels", "r1,r2")
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertIn("WARN r2: no takes yet", out.stdout)
            self.assertIn("plan.json entry kept", out.stdout)
            with open(os.path.join(p, "plan.json")) as f:
                reels = json.load(f)["reels"]
            self.assertEqual([r["id"] for r in reels], ["Reel2", "Reel3"])
            self.assertEqual(reels[1], {"id": "Reel3", "slug": "later", "old": 3, "script": "r2"})
            out = self.cli(p)  # without --reels too
            self.assertEqual(out.returncode, 0, out.stderr)


if __name__ == "__main__":
    unittest.main()
