import copy
import os
import subprocess
import sys
import json
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
sys.path.insert(0, SCRIPTS)
import check_scripts  # noqa: E402

# 15 words per line at 40 wpm = 22.5 s + 0.6 s tail; two lines = 46.2 s, inside the default 20-90 s.
FIFTEEN = "um dois três quatro cinco seis sete oito nove dez onze doze treze quatorze quinze."


def valid_doc():
    return {
        "wpm": 40,
        "reels": [{
            "id": "r0", "slug": "massa-fresca", "title": "Massa fresca",
            "hook": {"big": "Massa fresca", "small": "todas as etapas"},
            "end": {"big": "Salva", "small": "reel zero", "items": ["Step one"]},
            "lines": [
                {"text": FIFTEEN, "demo": "card", "head": "bl",
                 "anns": [{"kind": "label", "x": 6, "y": 5, "text": "1 · STEP ONE", "in": 0.1, "out": 1.0}]},
                {"text": FIFTEEN, "demo": "r0-page", "head": "big"},
            ],
        }],
    }


def with_line(text=None, **fields):
    d = valid_doc()
    line = d["reels"][0]["lines"][1]
    if text is not None:
        line["text"] = text
    line.update(fields)
    return d


class CheckScripts(unittest.TestCase):
    def assertProblem(self, doc, *needles):
        probs = check_scripts.check(doc)
        self.assertTrue(any(all(n in p for n in needles) for p in probs),
                        f"no problem containing {needles!r} in {probs!r}")

    def test_valid_two_line_reel(self):
        self.assertEqual(check_scripts.check(valid_doc()), [])

    def test_prices_allowed_by_default(self):
        self.assertEqual(check_scripts.check(with_line("Custa R$ 47 por mês e mais nada aqui hoje.")), [])

    def test_prices_flagged_with_reel_and_line_when_rule_on(self):
        for price in ["R$ 47", "$89", "US$ 12", "47 dólares", "10 €", "5 dollars"]:
            with self.subTest(price=price):
                d = with_line(f"Custa {price} por mês e mais nada aqui hoje.")
                d["rules"] = {"noPrices": True}
                self.assertProblem(d, "r0", "line 2", "price")

    def test_price_in_annotation_flagged(self):
        d = valid_doc()
        d["rules"] = {"noPrices": True}
        d["reels"][0]["lines"][0]["anns"][0]["text"] = "Pro · US$ 99"
        self.assertProblem(d, "r0", "line 1", "price")

    def test_price_in_end_card_flagged(self):
        d = valid_doc()
        d["rules"] = {"noPrices": True}
        d["reels"][0]["end"]["items"] = ["R$ 30 por mês"]
        self.assertProblem(d, "r0", "end", "price")

    def test_banned_patterns(self):
        d = with_line("As respostas VAZADAS do exame estão aqui, todas elas, hoje mesmo.")
        self.assertEqual(check_scripts.check(d), [])  # nothing banned by default
        d["rules"] = {"banned": [r"vazad\w*", "leaked"]}
        self.assertProblem(d, "r0", "line 2", "'VAZADAS'", "banned")

    def test_bad_rules_reported(self):
        for rules, needle in [({"maxWords": 0}, "maxWords"), ({"banned": ["("]}, "bad regex"),
                              ({"durationRange": [90, 20]}, "durationRange"), ({"noPrice": True}, "unknown rule"),
                              ({"noPrices": "yes"}, "noPrices")]:
            with self.subTest(rules=rules):
                d = valid_doc()
                d["rules"] = rules
                self.assertProblem(d, "rules")

    def test_line_over_22_words(self):
        self.assertProblem(with_line(" ".join(["palavra"] * 23)), "r0", "line 2", "23 words")

    def test_max_words_rule(self):
        d = with_line(" ".join(["palavra"] * 23))
        d["rules"] = {"maxWords": 30}
        self.assertEqual(check_scripts.check(d), [])
        d["rules"] = {"maxWords": 10}
        self.assertProblem(d, "r0", "line 1", "15 words (max 10)")

    def test_duration_too_short(self):
        d = valid_doc()
        d["wpm"] = 140
        self.assertProblem(d, "r0", "duration")

    def test_duration_too_long(self):
        d = valid_doc()
        d["wpm"] = 20
        self.assertProblem(d, "r0", "duration")

    def test_duration_range_rule(self):
        d = valid_doc()  # 46.2 s
        d["rules"] = {"durationRange": [50, 60]}
        self.assertProblem(d, "r0", "duration", "50-60")
        d["rules"] = {"durationRange": [40, 50]}
        self.assertEqual(check_scripts.check(d), [])

    def test_duration_formula(self):
        # 15 words x 60/40 + 0.6 per line, two lines
        self.assertAlmostEqual(check_scripts.duration(valid_doc()["reels"][0], 40), 2 * (22.5 + 0.6))

    def test_missing_hook_or_end(self):
        for key in ["hook", "end"]:
            with self.subTest(key=key):
                d = valid_doc()
                del d["reels"][0][key]
                self.assertProblem(d, "r0", key)

    def test_bad_head(self):
        self.assertProblem(with_line(head="br"), "r0", "line 2", "head 'br' not one of")

    def test_unknown_ann_kind(self):
        self.assertProblem(with_line(anns=[{"kind": "sparkle", "x": 6, "y": 5}]),
                           "r0", "line 2", "sparkle")

    def test_ann_missing_required_field(self):
        self.assertProblem(with_line(anns=[{"kind": "list", "x": 6, "y": 5}]), "r0", "line 2", "items")

    def test_ann_timing_out_of_range(self):
        self.assertProblem(with_line(anns=[{"kind": "label", "x": 6, "y": 5, "text": "x",
                                            "in": 0.8, "out": 0.3}]), "r0", "line 2", "in/out must be")

    def test_stale_from_to_timing_rejected(self):
        self.assertProblem(with_line(anns=[{"kind": "label", "x": 6, "y": 5, "text": "x", "from": 0.2}]),
                           "r0", "line 2", "'from' is not used")
        self.assertProblem(with_line(anns=[{"kind": "label", "x": 6, "y": 5, "text": "x", "to": 0.9}]),
                           "r0", "line 2", "'to' is only for arrows")
        self.assertProblem(with_line(anns=[{"kind": "arrow", "x": 50, "y": 8, "to": [62, 22], "from": 0.2}]),
                           "r0", "line 2", "'from' is not used")

    def test_arrow_to_is_a_point(self):
        ok = with_line(head="big", anns=[{"kind": "arrow", "x": 50, "y": 8, "to": [62, 22], "in": 0.3, "out": 0.9}])
        self.assertEqual(check_scripts.check(ok), [])
        self.assertProblem(with_line(anns=[{"kind": "arrow", "x": 50, "y": 10, "to": 0.5}]),
                           "r0", "line 2", "arrow 'to' is its end point")

    def test_ann_under_head_bubble(self):
        # head "bl" covers x 5-32 %, y 51-72 % (bubble centre y 1230, circle bottom 1380)
        self.assertProblem(with_line(head="bl", anns=[{"kind": "label", "x": 8, "y": 60, "text": "aqui"}]),
                           "r0", "line 2", "head bubble (bl)")
        # a label spanning y 47-51.5 % touches the head poking above the rim (the old 54 % top missed it)
        self.assertProblem(with_line(head="bl", anns=[{"kind": "label", "x": 8, "y": 47, "text": "aqui"}]),
                           "r0", "line 2", "head bubble (bl)")
        # head "big" covers the middle: a note there is under it
        self.assertProblem(with_line(head="big", anns=[{"kind": "note", "x": 30, "y": 40, "text": "meio"}]),
                           "r0", "line 2", "head bubble (big)")

    def test_ann_in_subtitle_band_or_right_buttons(self):
        self.assertProblem(with_line(head="tl", anns=[{"kind": "label", "x": 40, "y": 78, "text": "baixo"}]),
                           "r0", "line 2", "subtitle")
        self.assertProblem(with_line(head="bl", anns=[{"kind": "note", "x": 40, "y": 10, "w": 56, "text": "x"}]),
                           "r0", "line 2", "right-hand buttons")

    def test_anns_overlapping_each_other(self):
        two = [{"kind": "label", "x": 30, "y": 5, "text": "um"}, {"kind": "note", "x": 30, "y": 6, "text": "dois"}]
        self.assertProblem(with_line(head="big", anns=two), "r0", "line 2", "ann 2", "overlaps ann 1")
        # same place, but one after the other in time: fine
        two[0].update({"in": 0.0, "out": 0.5})
        two[1].update({"in": 0.5, "out": 1.0})
        self.assertEqual(check_scripts.check(with_line(head="big", anns=two)), [])

    def test_last_line_may_use_any_head(self):
        self.assertEqual(check_scripts.check(with_line(head="bl")), [])

    def test_reel_ids_unique_and_file_safe_not_numbered(self):
        d = valid_doc()
        d["reels"].append(copy.deepcopy(d["reels"][0]))
        d["reels"][1]["id"] = "launch_day-2"
        d["reels"][1]["slug"] = "launch-day"
        self.assertEqual(check_scripts.check(d), [])
        d["reels"][1]["id"] = "r0"
        self.assertProblem(d, "r0", "duplicate reel id")
        for bad in ["my reel", "../x", "", None]:
            with self.subTest(id=bad):
                d["reels"][1]["id"] = bad
                self.assertProblem(d, "reel 2", "id")

    def test_demo_id_format(self):
        self.assertProblem(with_line(demo="Web page"), "r0", "line 2", "demo")
        self.assertProblem(with_line(demo=None), "r0", "line 2", "demo")
        self.assertEqual(check_scripts.check(with_line(demo="intro_screen-1")), [])

    def test_duplicate_slug(self):
        d = valid_doc()
        d["reels"].append(dict(copy.deepcopy(d["reels"][0]), id="r1"))
        self.assertProblem(d, "r1", "duplicate slug")

    def test_malformed_fields_are_problems_not_crashes(self):
        cases = [
            ({"kind": "ring", "x": 50, "y": 50, "w": "big"}, "w must be a positive number"),
            ({"kind": "note", "x": 40, "y": 10, "text": "x", "w": [3]}, "w must be a positive number"),
            ({"kind": "bar", "x": 40, "y": 10, "bars": [3]}, "bar row 1 must be [label, fraction 0-1]"),
            ({"kind": "bar", "x": 40, "y": 10, "bars": [["ok", 0.5], ["x"]]}, "bar row 2"),
            ({"kind": "bar", "x": 40, "y": 10, "bars": [["ok", 2]]}, "bar row 1"),
            ({"kind": "bar", "x": 40, "y": 10, "bars": "nope"}, "bars must be a list"),
            ({"kind": "list", "x": 40, "y": 10, "items": [1, None]}, "items must be strings"),
            ({"kind": "arrow", "x": 40, "y": 10, "to": ["a", 3]}, "arrow 'to' is its end point"),
            ({"kind": "label", "x": True, "y": 10, "text": "x"}, "needs a number x"),
            ({"kind": "note", "x": 40, "y": 10, "text": "x", "rotate": "left"}, "rotate must be a number"),
        ]
        for ann, needle in cases:
            with self.subTest(ann=ann):
                d = with_line(anns=[ann])
                d["rules"] = {"noPrices": True, "banned": ["zzz"]}  # text rules walk the malformed fields too
                self.assertProblem(d, "r0", "line 2", needle)

    def test_ann_size(self):
        ok = with_line(head="bl", anns=[{"kind": "label", "x": 40, "y": 10, "text": "x", "size": 2}])
        self.assertEqual(check_scripts.check(ok), [])
        for bad in [0.4, 3.5, "2", True]:
            with self.subTest(size=bad):
                self.assertProblem(with_line(anns=[{"kind": "label", "x": 40, "y": 10, "text": "x", "size": bad}]),
                                   "r0", "line 2", "size must be a number from 0.5 to 3")

    def test_ann_size_scales_its_box(self):
        # a label that fits at size 1 runs under the right-hand buttons at size 3
        ann = {"kind": "label", "x": 40, "y": 10, "text": "ABCDEFGH"}
        self.assertEqual(check_scripts.check(with_line(head="bl", anns=[ann])), [])
        self.assertProblem(with_line(head="bl", anns=[dict(ann, size=3)]), "r0", "line 2", "right-hand buttons")

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            good, bad = os.path.join(tmp, "good.json"), os.path.join(tmp, "bad.json")
            for path, doc in [(good, valid_doc()), (bad, with_line(head="xx"))]:
                with open(path, "w") as f:
                    json.dump(doc, f)
            cli = os.path.join(SCRIPTS, "check_scripts.py")
            r = subprocess.run([sys.executable, cli, good], capture_output=True, text=True)
            self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))
            r = subprocess.run([sys.executable, cli, bad], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("head 'xx' not one of", r.stdout)


if __name__ == "__main__":
    unittest.main()
