import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
sys.path.insert(0, HERE)
sys.path.insert(0, SCRIPTS)
import takes  # noqa: E402
from fixture import read_json, write_json  # noqa: E402

VPY = sys.executable


def ev(kind, t, line=0, **kw):
    return dict(type=kind, t=t, line=line, **kw)


class SegmentsTest(unittest.TestCase):
    LOG = {"reel": "r1", "take": "x", "events": [
        ev("line", 0, 0), ev("line", 4, 1), ev("tap", 6, 1), ev("line", 7, 1),
        ev("line", 11, 2), ev("stop", 15, 2)]}

    def test_segments_mark_tapped_away_takes_abandoned(self):
        segs = takes.segments(self.LOG)
        line1 = [s for s in segs if s["line"] == 1]
        self.assertEqual([(s["start"], s["end"], s["abandoned"]) for s in line1],
                         [(4, 6, True), (7, 11, False)])
        self.assertEqual([(s["line"], s["start"], s["end"]) for s in segs if s["line"] != 1],
                         [(0, 0, 4), (2, 11, 15)])

    def test_pick_keeps_last_good_take(self):
        picked = takes.pick(takes.segments(self.LOG))
        self.assertEqual(sorted(picked), [0, 1, 2])
        self.assertEqual((picked[1]["start"], picked[1]["end"]), (7, 11))

    def test_double_tap_before_line_and_stray_tap(self):
        log = {"events": [ev("tap", 0.5, 0), ev("line", 1, 0), ev("line", 3, 1), ev("tap", 4, 1),
                          ev("tap", 4.5, 0), ev("line", 5.5, 0), ev("stop", 9, 0)]}
        segs = takes.segments(log)
        self.assertEqual([(s["line"], s["start"], s["end"], s["abandoned"]) for s in segs],
                         [(0, 1, 3, False), (1, 3, 4, True), (0, 5.5, 9, False)])

    def test_log_cut_short_without_stop(self):
        # tab closed after line 2 started: no `stop`. The open segment ends at the last event (zero length)
        # and is kept, not dropped and not abandoned; earlier segments are unaffected.
        log = {"events": [ev("line", 0, 0), ev("line", 4, 1), ev("tap", 6, 1), ev("line", 7, 1), ev("line", 11, 2)]}
        segs = takes.segments(log)
        self.assertEqual([(s["line"], s["start"], s["end"], s["abandoned"]) for s in segs],
                         [(0, 0, 4, False), (1, 4, 6, True), (1, 7, 11, False), (2, 11, 11, False)])
        self.assertEqual(sorted(takes.pick(segs)), [0, 1, 2])

    def test_empty_log(self):
        self.assertEqual(takes.segments({"events": []}), [])
        self.assertEqual(takes.segments({}), [])


class AlignTest(unittest.TestCase):
    WORDS = [("o", 7.1, 7.2), ("molho", 7.2, 7.6), ("começa", 7.7, 8.1)]

    def test_perfect_match(self):
        self.assertEqual(takes.align(self.WORDS, "O molho começa.", (7.0, 8.5)), (7.1, 8.1, 1.0))

    def test_accents_and_punctuation_ignored(self):
        words = [("Começa,", 1.0, 1.4), ("AÇÃO!", 1.5, 2.0)]
        self.assertEqual(takes.align(words, "comeca acao", (1.0, 2.0)), (1.0, 2.0, 1.0))

    def test_one_wrong_word(self):
        words = [("o", 7.1, 7.2), ("circuito", 7.2, 7.6), ("começa", 7.7, 8.1)]
        s, e, score = takes.align(words, "O molho começa.", (7.0, 8.5))
        self.assertEqual((s, e), (7.1, 8.1))
        self.assertTrue(0.6 < score < 1)

    def test_window_excludes_other_lines(self):
        words = [("o", 1, 1.2), ("molho", 1.2, 1.6), ("começa", 1.7, 2.1), ("o", 30, 30.2), ("molho", 30.2, 30.6)]
        s, e, score = takes.align(words, "O molho começa.", (29.5, 31), pad=2.0)
        self.assertEqual((s, e), (30, 30.6))
        self.assertAlmostEqual(score, 2 / 3, places=2)  # 2 of the 3 script tokens

    def test_lone_word_far_before_main_block_is_ignored(self):
        # "mostro" at 1.0 s is a stray from the previous line, 2.9 s before the real block "o molho completo"
        # ("cada" was skipped, so they are separate matching blocks): the start must not stretch back to it
        words = [("mostro", 1.0, 1.1), ("o", 4.0, 4.1), ("molho", 4.2, 4.5), ("completo", 4.6, 5.0)]
        self.assertEqual(takes.align(words, "Mostro cada o molho completo", (0, 6)), (4.0, 5.0, 0.6))

    def test_lone_word_within_gap_is_kept(self):
        # documented behaviour: a lone matching word less than STRAY_GAP (1.5 s) from the block counts
        words = [("mostro", 3.0, 3.1), ("o", 4.0, 4.1), ("molho", 4.2, 4.5), ("completo", 4.6, 5.0)]
        self.assertEqual(takes.align(words, "Mostro cada o molho completo", (0, 6)), (3.0, 5.0, 0.8))

    def test_speech_spilling_past_next_line_event(self):
        # karaoke ran ahead: line 0's window is 0-2 s, but the speaker is still saying it until 3.6 s,
        # and the next line's first words already sit inside the pad
        words = [("o", 0.2, 0.4), ("molho", 1.0, 1.4), ("começa", 2.0, 2.6), ("agora", 3.2, 3.6),
                 ("segunda", 3.8, 4.0), ("linha", 4.1, 4.4)]
        self.assertEqual(takes.align(words, "O molho começa agora.", (0, 2)), (0.2, 3.6, 1.0))

    def test_nothing_in_window(self):
        self.assertEqual(takes.align(self.WORDS, "O molho começa.", (50, 52)), (50, 52, 0.0))


class SplitSubsTest(unittest.TestCase):
    def test_long_sentence_splits_in_two(self):
        text = "Eu mostro cada etapa da receita, do começo até a sobremesa final."
        toks = text.split()
        words = [(toks[i], i * 0.4, i * 0.4 + 0.3) for i in range(len(toks))]
        subs = takes.split_subs(text, 0, words[-1][1] + 0.3, words)
        self.assertEqual(len(subs), 2)
        for s, e, t in subs:
            self.assertLessEqual(len(t), 42)
            self.assertLess(s, e)
        self.assertLess(subs[0][1], subs[1][0] + 1e-9)
        self.assertEqual(" ".join(t for _, _, t in subs), text)
        self.assertEqual(subs[0][2], "Eu mostro cada etapa da receita,")  # breaks at the comma

    def test_short_sentence_is_one_chunk(self):
        words = [("o", 1, 1.1), ("molho", 1.1, 1.5)]
        self.assertEqual(takes.split_subs("O molho", 1, 1.5, words), [[1, 1.5, "O molho"]])


def make_words_json(proj, cid, words):
    ws = [[round(s, 2), round(e, 2), w] for w, s, e in words]
    seg = dict(s=ws[0][0], e=ws[-1][1], t=" ".join(w for _, _, w in ws), w=ws)
    path = os.path.join(proj, "transcripts", "words.json")
    data = read_json(path)
    data[f"{cid}:0.0-60.0"] = [seg]
    write_json(path, data)


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p = os.path.join(self.tmp.name, "proj")
        os.makedirs(os.path.join(self.p, "scripts"))
        os.makedirs(os.path.join(self.p, "transcripts"))
        os.makedirs(os.path.join(self.p, "recordings", "voice"))
        write_json(os.path.join(self.p, "scripts", "reels.json"), {"reels": [
            {"id": "r1", "title": "t", "confirm": "x", "lines": [
                {"text": "O molho começa agora.", "anns": []},
                {"text": "Eu mostro cada etapa da receita, do começo até a sobremesa final."},
                {"text": "Terceira linha nunca lida."}]}]})
        write_json(os.path.join(self.p, "transcripts", "words.json"), {})

    def run_cli(self, events, words):
        write_json(os.path.join(self.p, "recordings", "voice", "voice-r1.log.json"),
                   {"reel": "r1", "take": "x", "events": events})
        make_words_json(self.p, "voice-r1", words)
        # a decoy for another clip must be ignored
        data = read_json(os.path.join(self.p, "transcripts", "words.json"))
        data["voice-r2:0.0-9.0"] = [dict(s=0, e=1, t="x", w=[[0, 1, "zzz"]])]
        write_json(os.path.join(self.p, "transcripts", "words.json"), data)
        r = subprocess.run([VPY, os.path.join(SCRIPTS, "takes.py"), self.p, "--reel", "r1", "--no-hint"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = read_json(os.path.join(self.p, "takes", "r1.json"))
        return r.stdout, {t["line"]: t for t in out}

    def test_missing_line_warns(self):
        events = [ev("line", 0, 0), ev("line", 3, 1), ev("line", 9, 2), ev("tap", 10, 2), ev("stop", 11, 2)]
        words = [("o", 0.2, 0.3), ("molho", 0.3, 0.6), ("começa", 0.7, 1.0), ("agora", 1.1, 1.5)]
        out, by_line = self.run_cli(events, words)
        self.assertIn("WARN line 2", out)
        self.assertNotIn(2, by_line)

    def test_score_one_uses_script_text_and_low_score_uses_spoken(self):
        text1 = "Eu mostro cada etapa da receita, do começo até a sobremesa final."
        spoken = text1.replace("etapa", "fase").replace(",", "").split()
        events = [ev("line", 0, 0), ev("line", 3, 1), ev("line", 9, 2), ev("stop", 12, 2)]
        words = [("o", 0.2, 0.3), ("molho", 0.3, 0.6), ("começa", 0.7, 1.0), ("agora", 1.1, 1.5)]
        words += [(w, 3.2 + 0.4 * i, 3.5 + 0.4 * i) for i, w in enumerate(spoken)]
        out, by_line = self.run_cli(events, words)
        self.assertEqual(by_line[0]["score"], 1.0)
        self.assertEqual(" ".join(t for _, _, t in by_line[0]["subs"]), "O molho começa agora.")
        self.assertEqual(by_line[0]["text"], "O molho começa agora.")
        self.assertEqual(by_line[0]["start"], 0.2)
        self.assertEqual(by_line[0]["end"], 1.5)

    def test_low_score_subs_follow_spoken_words(self):
        # 4 of 5 tokens match: score 0.8 < 0.85, so subs show "fase", not "etapa"
        write_json(os.path.join(self.p, "scripts", "reels.json"), {"reels": [
            {"id": "r1", "lines": [{"text": "Eu mostro cada etapa agora."}]}]})
        events = [ev("line", 0, 0), ev("stop", 5, 0)]
        words = [("Eu", 0.2, 0.3), ("mostro", 0.3, 0.6), ("cada", 0.7, 1.0), ("fase", 1.1, 1.5), ("agora", 1.6, 2.0)]
        out, by_line = self.run_cli(events, words)
        t = by_line[0]
        self.assertTrue(0.6 < t["score"] < 0.85, t["score"])
        joined = " ".join(x for _, _, x in t["subs"])
        self.assertIn("fase", joined)
        self.assertNotIn("etapa", joined)
        self.assertNotIn("WARN", out)

    def test_flubbed_attempt_inside_pad_is_not_matched(self):
        # first attempt (0-3 s) is tapped away; the retake starts at 4 s, so the flub's words (2.1-2.7 s)
        # sit inside the retake's 2 s pad. Both attempts say the whole line, so only the exclusion of the
        # abandoned take's words keeps the start at the retake.
        events = [ev("line", 0, 0), ev("tap", 3, 0), ev("line", 4, 0), ev("line", 9, 1), ev("stop", 12, 1)]
        flub = [("o", 2.1, 2.2), ("molho", 2.3, 2.4), ("começa", 2.5, 2.6), ("agora", 2.7, 2.8)]
        retake = [("o", 4.3, 4.4), ("molho", 4.5, 4.7), ("começa", 4.8, 5.2), ("agora", 5.3, 5.7)]
        out, by_line = self.run_cli(events, flub + retake)
        self.assertEqual((by_line[0]["start"], by_line[0]["end"], by_line[0]["score"]), (4.3, 5.7, 1.0))

    def run_hinted(self, plain, hinted, text, events=None, transcriber=None):
        """In-process CLI run with a fake transcriber; returns (stdout, takes by line, calls)."""
        write_json(os.path.join(self.p, "scripts", "reels.json"), {"reels": [{"id": "r1", "lines": [{"text": text}]}]})
        with open(os.path.join(self.p, "scripts", "terms.txt"), "w") as f:
            f.write("Meu Termo\n\nreel\nMEU TERMO\n")
        write_json(os.path.join(self.p, "recordings", "voice", "voice-r1.log.json"),
                   {"events": events or [ev("line", 0, 0), ev("stop", 5, 0)]})
        make_words_json(self.p, "voice-r1", plain)
        calls = []

        def fake(start, end, prompt):
            calls.append((start, end, prompt))
            return [w for w in hinted if w[0] >= start and w[1] <= end]  # like the real thing: only that audio

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            takes.main([self.p, "--reel", "r1"], transcriber=transcriber or fake)
        return out.getvalue(), {t["line"]: t for t in read_json(os.path.join(self.p, "takes", "r1.json"))}, calls

    def test_language_comes_from_flag_then_plan_json(self):
        self.assertIsNone(takes.plan_language(self.p))
        write_json(os.path.join(self.p, "plan.json"), {"language": "es"})
        self.assertEqual(takes.plan_language(self.p), "es")
        self.assertEqual(takes.plan_language(self.p, "pt"), "pt")

    def test_hinted_run_without_language_is_an_error(self):
        write_json(os.path.join(self.p, "recordings", "voice", "voice-r1.log.json"), {"events": [ev("line", 0, 0), ev("stop", 5, 0)]})
        r = subprocess.run([VPY, os.path.join(SCRIPTS, "takes.py"), self.p, "--reel", "r1"], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('set "language" in plan.json or pass --language', r.stderr)

    def test_hinted_words_replace_plain_words_in_score_and_subs(self):
        text = "Cada etapa tem um reel do Code Quest."
        plain = [(w, round(0.5 + 0.4 * i, 2), round(0.8 + 0.4 * i, 2)) for i, w in enumerate("Cada etapa tem um rio do CoQuest".split())]
        hinted = [(round(0.45 + 0.4 * i, 2), round(0.8 + 0.4 * i, 2), w) for i, w in enumerate("Cada etapa tem um reel do Code Quest".split())]
        out, by_line, calls = self.run_hinted(plain, hinted, text)
        t = by_line[0]
        self.assertEqual(t["score"], 1.0)
        self.assertEqual(" ".join(x for _, _, x in t["subs"]), text)  # script spelling, since score >= 0.85
        self.assertEqual((t["start"], t["end"]), (0.45, 3.6))
        self.assertIn("score 0.62 -> 1.00", out)  # before -> after, plain 5/8 tokens
        self.assertNotIn("WARN", out)
        # window = plain start - 0.3 .. plain end + 0.4; prompt = terms.txt (deduped, no built-in terms) + the line
        (lo, hi, prompt), = calls
        self.assertAlmostEqual(lo, 0.0)  # min(plain start 0.5, segment start 0) - 1.0, floored at 0
        self.assertAlmostEqual(hi, 6.0)  # max(plain end 2.8, segment end 5) + 1.0
        self.assertEqual(prompt, "Meu Termo, reel, " + text)  # "MEU TERMO" is a case-insensitive repeat

    def test_hinted_window_recovers_misheard_final_words(self):
        # plain heard "CoQuest" for "Code Quest": its match stops at "o" (4.0 s), but the speaker finished at 5.4 s,
        # beyond plain end + 0.4. The wide window lets the hinted pass transcribe it and `end` moves there.
        text = "Rodadas próprias como o Code Quest."
        plain = [("Rodadas", 1.0, 1.4), ("próprias", 1.6, 2.2), ("como", 2.8, 3.2), ("o", 3.6, 4.0), ("CoQuest", 4.4, 5.0)]
        hinted = [(1.0, 1.4, "Rodadas"), (1.6, 2.2, "próprias"), (2.8, 3.2, "como"), (3.6, 4.0, "o"),
                  (4.4, 4.9, "Code"), (4.95, 5.4, "Quest")]
        events = [ev("line", 1, 0), ev("line", 7, 1), ev("stop", 9, 1)]
        out, by_line, calls = self.run_hinted(plain, hinted, text, events=events)
        (lo, hi, _), = calls
        self.assertAlmostEqual(lo, 0.0)   # min(plain 1.0, segment 1) - 1.0
        self.assertAlmostEqual(hi, 8.0)   # segment end 7 + 1.0
        t = by_line[0]
        self.assertEqual((t["start"], t["end"], t["score"]), (1.0, 5.4, 1.0))
        self.assertIn("score 0.67 -> 1.00", out)  # plain: 4 of 6 tokens

    def test_garbled_wide_window_is_retried_tight_and_never_worse_than_plain(self):
        text = "Cada etapa tem um reel próprio."
        plain = [("Cada", 1.0, 1.3), ("etapa", 1.4, 1.8), ("tem", 1.9, 2.1), ("um", 2.2, 2.4), ("rio", 2.5, 2.8), ("próprio", 2.9, 3.4)]
        good = [(1.0, 1.3, "Cada"), (1.4, 1.8, "etapa"), (1.9, 2.1, "tem"), (2.2, 2.4, "um"), (2.5, 2.8, "reel"), (2.9, 3.4, "próprio")]
        events = [ev("line", 1, 0), ev("line", 4, 1), ev("stop", 6, 1)]
        calls = []

        def whisper_drops_sentence_in_wide_window(start, end, prompt):
            calls.append((round(start, 2), round(end, 2)))
            return [(5.0, 5.4, "Salve")] if end - start > 4 else [w for w in good if w[0] >= start and w[1] <= end]

        out, by_line, _ = self.run_hinted(plain, good, text, events=events, transcriber=whisper_drops_sentence_in_wide_window)
        self.assertEqual(calls, [(0.0, 5.0), (0.7, 4.4)])  # wide (+-1 s) first, then tight (-0.3 / +0.4)
        self.assertEqual((by_line[0]["score"], by_line[0]["start"], by_line[0]["end"]), (1.0, 1.0, 3.4))
        self.assertIn("score 0.83 -> 1.00", out)

        # a hinted pass that is worse than the plain one on both windows is ignored
        def useless(start, end, prompt):
            return [(5.0, 5.4, "Salve")]
        out, by_line, _ = self.run_hinted(plain, good, text, events=events, transcriber=useless)
        self.assertIn("score 0.83 -> 0.83 (plain words)", out)
        self.assertIn("rio", " ".join(x for _, _, x in by_line[0]["subs"]))

    def test_hinted_transcriber_error_falls_back_to_plain_words(self):
        def boom(start, end, prompt):
            raise RuntimeError("decode failed")
        plain = [("O", 0.5, 0.7), ("molho", 0.8, 1.2), ("começa", 1.3, 1.8), ("agora", 1.9, 2.4)]
        out, by_line, _ = self.run_hinted(plain, [], "O molho começa agora.", transcriber=boom)
        self.assertIn("WARN line 0: hinted re-transcription failed (RuntimeError: decode failed)", out)
        self.assertIn("line 0: score 1.00 -> 1.00 (plain words)", out)
        self.assertEqual((by_line[0]["start"], by_line[0]["end"], by_line[0]["score"]), (0.5, 2.4, 1.0))

    def test_real_misread_survives_hinting_and_shows_spoken_words(self):
        text = "São um ou dois problemas de código."
        spoken = "São dois ou três problemas de código".split()
        plain = [(w, round(0.5 + 0.4 * i, 2), round(0.8 + 0.4 * i, 2)) for i, w in enumerate(spoken)]
        hinted = [(round(0.5 + 0.4 * i, 2), round(0.8 + 0.4 * i, 2), w) for i, w in enumerate(spoken)]
        out, by_line, _ = self.run_hinted(plain, hinted, text)
        t = by_line[0]
        self.assertTrue(0.6 < t["score"] < 0.85, t["score"])
        joined = " ".join(x for _, _, x in t["subs"])
        self.assertIn("três", joined)
        self.assertNotIn("um ou", joined)

    def test_low_score_warns(self):
        events = [ev("line", 0, 0), ev("line", 3, 1), ev("line", 6, 2), ev("stop", 9, 2)]
        words = [("blá", 0.2, 0.3), ("bla", 0.3, 0.6), ("agora", 1.1, 1.5)]
        out, _ = self.run_cli(events, words)
        self.assertIn("WARN line 0", out)


if __name__ == "__main__":
    unittest.main()
