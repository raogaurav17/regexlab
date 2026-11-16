"""Rendering, tables, API payloads, CLI and server tests."""
import json
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from http.server import ThreadingHTTPServer
from pathlib import Path

from regexlab.api import build_payload, run_payload
from regexlab.pipeline import build
from regexlab.render import draw_svg, to_dot
from regexlab.report import build_report
from regexlab.server import Handler
from regexlab.tables import LABELS, automaton_tables, text_table

ROOT = Path(__file__).resolve().parent.parent


class RenderTests(unittest.TestCase):
    def test_svg_is_well_formed_and_has_every_node(self):
        m = build("(ab|a)(c|bc)*d?")
        for key in ("nfa", "dfa", "min"):
            g = getattr(m, key)
            root = ET.fromstring(draw_svg(g, key, LABELS[key]))
            ids = {e.get("id") for e in root.iter() if e.get("id", "").startswith(f"{key}-n")}
            self.assertEqual(ids, {f"{key}-n{i}" for i in range(g.n)})

    def test_accepting_states_are_double_circled(self):
        m = build("ab")
        root = ET.fromstring(draw_svg(m.min, "min", LABELS["min"]))
        acc = [e for e in root.iter() if (e.get("class") or "").startswith("nd acc")]
        self.assertEqual(len(acc), 1)

    def test_special_characters_are_escaped(self):
        m = build(r"<\&>")
        ET.fromstring(draw_svg(m.nfa, "nfa", LABELS["nfa"]))          # must still parse
        self.assertNotIn("<&>", build_report(m, ["<&>"]))             # report escapes user text

    def test_dot_export(self):
        dot = to_dot(build("(a|b)*abb").min, "MIN", LABELS["min"])
        self.assertTrue(dot.startswith("digraph MIN {"))
        self.assertEqual(dot.count("doublecircle"), 1)
        self.assertIn('"M0" -> "M1"', dot)


class TableTests(unittest.TestCase):
    def test_tables_shape(self):
        m = build("(a|b)*abb")
        titles = [t for t, _, _ in automaton_tables(m)]
        self.assertEqual(len(titles), 3)
        _, head, rows = automaton_tables(m)[2]
        self.assertEqual(len(rows), m.min.n)
        self.assertEqual(head, ["State", "Merged DFA states", "a", "b"])
        self.assertIn("→", rows[0][0])
        self.assertIn("text", text_table(["x"], [["text"]]))


class ApiTests(unittest.TestCase):
    def test_build_payload(self):
        p = build_payload("(a|b)*abb")
        self.assertTrue(p["ok"])
        self.assertEqual(p["counts"], {"ast": 8, "nfa": 14, "dfa": 5, "min": 4})
        self.assertEqual(set(p["svg"]), {"nfa", "dfa", "min"})

    def test_errors_are_reported_not_raised(self):
        for bad in ["(a|", "*a", "a)", "", "a" * 500]:
            with self.subTest(bad=bad[:10]):
                self.assertFalse(build_payload(bad)["ok"])
                self.assertFalse(run_payload(bad, "a")["ok"])

    def test_run_payload(self):
        r = run_payload("(a|b)*abb", "babb")
        self.assertTrue(r["accepted"] and r["agree"] and r["oracle"])
        self.assertEqual(len(r["steps"]["dfa"]), 5)
        self.assertFalse(run_payload("(a|b)*abb", "bab")["accepted"])

    def test_dead_state_trace(self):
        r = run_payload("ab", "ba")
        self.assertEqual(r["steps"]["min"][1], [])          # fell into the dead state
        self.assertFalse(r["accepted"])


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-m", "regexlab", *args], cwd=ROOT,
                              capture_output=True, text=True, timeout=60)

    def test_output_files(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.run_cli("(a|b)*abb", "-t", "babb", "-t", "ab", "-o", d, "-q")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("ACCEPT", r.stdout)
            self.assertIn("REJECT", r.stdout)
            for name in ["nfa.svg", "dfa.svg", "min.svg", "nfa.dot", "dfa.dot", "min.dot", "report.html"]:
                self.assertTrue((Path(d) / name).is_file(), name)
            ET.parse(Path(d) / "min.svg")

    def test_bad_regex_exit_code(self):
        r = self.run_cli("(a|")
        self.assertEqual(r.returncode, 2)
        self.assertIn("Missing", r.stderr)


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def get(self, path):
        return urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=10)

    def test_static_files(self):
        for path, ctype in [("/", "text/html"), ("/app.js", "javascript"), ("/style.css", "text/css")]:
            r = self.get(path)
            self.assertEqual(r.status, 200)
            self.assertIn(ctype, r.headers["Content-Type"])

    def test_api(self):
        data = json.load(self.get("/api/build?re=%28a%7Cb%29%2Aabb"))
        self.assertEqual(data["counts"]["min"], 4)
        run = json.load(self.get("/api/run?re=%28a%7Cb%29%2Aabb&s=abb"))
        self.assertTrue(run["accepted"])

    def test_path_traversal_blocked(self):
        for path in ["/../cli.py", "/%2e%2e/cli.py", "/..%2fcli.py"]:
            with self.assertRaises(urllib.error.HTTPError) as cm:
                self.get(path)
            self.assertEqual(cm.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
