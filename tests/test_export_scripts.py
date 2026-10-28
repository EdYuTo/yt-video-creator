import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
sys.path.insert(0, HERE)
from fixture import write_json  # noqa: E402

DOC = {"wpm": 140, "reels": [{
    "id": "r0", "slug": "s", "title": "Título", "caption": "Legenda",
    "hook": {"big": "Gancho\nduas linhas", "small": "sub"}, "end": {"big": "Fim", "items": ["um", "dois"]},
    "lines": [{"text": "Primeira frase.", "demo": "card", "head": "big", "confirm": True},
              {"text": "Segunda frase.", "demo": "r0-page",
               "anns": [{"kind": "list", "x": 6, "y": 8, "items": ["a", "*b"], "in": 0, "out": 0.5}]}]}]}


class ExportScripts(unittest.TestCase):
    def test_writes_scripts_md_with_english_labels_and_original_text(self):
        with tempfile.TemporaryDirectory() as p:
            os.makedirs(os.path.join(p, "scripts"))
            write_json(os.path.join(p, "scripts", "reels.json"), DOC)
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "export_scripts.py"), p], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse(os.path.exists(os.path.join(p, "ROTEIROS.md")))
            with open(os.path.join(p, "SCRIPTS.md"), encoding="utf8") as f:
                md = f.read()
        for part in ["# Reel scripts", "## r0 · Título", "**Hook card:** Gancho / duas linhas — _sub_",
                     "1. Primeira frase. **(claim to confirm)**", "head big, centre", "head small, bottom left",
                     "list a; **b** (0%–50% of the line)", "**End card:** Fim · recap: um; dois", "**Post caption:** Legenda"]:
            self.assertIn(part, md)


if __name__ == "__main__":
    unittest.main()
