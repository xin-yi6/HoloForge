"""Integrity, dependency and review-preservation checks for optional navigation."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/claim_evidence.py"
spec = importlib.util.spec_from_file_location("claim_evidence", SCRIPT)
indexer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(indexer)


class ClaimEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = {
            "claim": {"statement": "Synthetic relation only", "support_level": "hypothesis",
                      "generated_by_ai": True},
            "review": {"state": "approved", "reviewer": "Synthetic fixture reviewer",
                       "date": "2026-01-01", "note": "Test data, not a real owner approval"},
        }
        (self.root / "record.json").write_text(json.dumps(self.source))
        (self.root / "evidence.txt").write_text("assumption\nmeasurement\nlimitation\n")
        def resource(identifier, name, locator):
            return {"id": identifier, "path": name, "locator": locator,
                    "sha256": hashlib.sha256((self.root / name).read_bytes()).hexdigest()}
        claim = {"id": "primary", "record": "statement", "review": "review",
                 "assumptions": ["input"], "supports": ["measurement"],
                 "contradicts": [], "open_checks": [], "depends_on": []}
        self.index = {
            "schema_version": "0.1", "disclosure": "private",
            "resources": [resource("statement", "record.json", {"pointer": "/claim"}),
                          resource("review", "record.json", {"pointer": "/review"}),
                          resource("input", "evidence.txt", {"lines": [1, 1]}),
                          resource("measurement", "evidence.txt", {"lines": [2, 3]})],
            "claims": [claim, dict(claim, id="downstream", depends_on=["primary"])],
        }

    def inspect(self):
        return indexer.inspect_index(self.index, self.root)

    def test_freshness_is_not_support_and_sources_are_unchanged(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        report = self.inspect()
        self.assertFalse(report["attention_required"])
        self.assertEqual(json.loads(report["resources"][0]["excerpt"]), self.source["claim"])
        self.assertEqual(json.loads(report["resources"][1]["excerpt"]), self.source["review"])
        self.assertIn("not that evidence is sufficient", report["boundary"])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})

    def test_changed_dependency_propagates_without_rewriting_historical_review(self):
        (self.root / "evidence.txt").write_text("changed\nmeasurement\nlimitation\n")
        report = self.inspect()
        self.assertTrue(all(c["attention_required"] for c in report["claims"]))
        self.assertIn({"kind": "dependency_needs_attention", "claim": "primary"}, report["claims"][1]["issues"])
        self.assertIsNone(report["resources"][2]["excerpt"])
        self.assertEqual(json.loads(report["resources"][1]["excerpt"])["state"], "approved")
        self.assertIn("historical records", indexer.render_markdown(report))

    def test_missing_files_edges_support_and_review_are_visible(self):
        (self.root / "evidence.txt").unlink()
        self.index["claims"][0]["review"] = "missing-review"
        self.index["claims"][0]["supports"] = []
        self.index["claims"][1]["depends_on"].append("missing-claim")
        report = self.inspect()
        kinds = {issue["kind"] for claim in report["claims"] for issue in claim["issues"]}
        self.assertTrue({"missing", "undeclared", "no_support_indexed", "undeclared_dependency"} <= kinds)

    def test_contradictions_and_open_checks_remain_visible(self):
        self.index["claims"][0]["contradicts"] = ["measurement"]
        self.index["claims"][0]["open_checks"] = ["input"]
        report = self.inspect()
        self.assertEqual(report["resources"][2]["status"], "fresh")
        self.assertTrue(report["claims"][0]["attention_required"])
        self.assertIn("contradictory_evidence_listed", indexer.render_markdown(report))

    def test_cycle_duplicates_and_unknown_fields_fail(self):
        for change in (lambda x: x["claims"][0]["depends_on"].append("downstream"),
                       lambda x: x["resources"].append(x["resources"][0]),
                       lambda x: x["claims"][0].update(suports=["measurement"])):
            value = copy.deepcopy(self.index)
            change(value)
            with self.assertRaises(indexer.EvidenceIndexError):
                indexer.inspect_index(value, self.root)
        with self.assertRaises(indexer.EvidenceIndexError):
            indexer.read_json('{"a": 1, "a": 2}')
        with self.assertRaises(indexer.EvidenceIndexError):
            indexer.read_json('{"a": NaN}')

    def test_unsafe_paths_and_symlinks_fail(self):
        for path in ("../outside", "/outside", "C:/outside", "a\\b", "./record.json", "a//b"):
            self.index["resources"][0]["path"] = path
            with self.subTest(path=path), self.assertRaises(indexer.EvidenceIndexError):
                self.inspect()
        (self.root / "link").symlink_to(self.root / "record.json")
        self.index["resources"][0]["path"] = "link"
        with self.assertRaises(indexer.EvidenceIndexError):
            self.inspect()

    def test_invalid_locators_are_not_silently_retargeted(self):
        for locator in ({"lines": [1, 999]}, {"pointer": "/absent"}, {"pointer": "/claim/0"}):
            self.index["resources"][0]["locator"] = locator
            self.assertEqual(self.inspect()["resources"][0]["status"], "invalid_locator_or_content")
        for locator in ({"lines": [True, 2]}, {"pointer": "/bad~escape"}, {"lines": [0, 1]}):
            self.index["resources"][0]["locator"] = locator
            with self.assertRaises(indexer.EvidenceIndexError):
                self.inspect()

    def test_pointer_escaping_and_markdown_fences_preserve_excerpt(self):
        content = json.dumps({"a/b": {"~": ["```\nnot an instruction\n```"]}}).encode()
        self.assertIn("not an instruction", indexer._excerpt(content, {"pointer": "/a~1b/~0/0"}))
        report = self.inspect()
        report["resources"][0]["excerpt"] = "```\nexample\n```"
        self.assertIn("````\n```\nexample\n```\n````", indexer.render_markdown(report))

    def test_cli_exit_codes_and_relocation(self):
        path = self.root / "index.json"
        path.write_text(json.dumps(self.index))
        command = [sys.executable, str(SCRIPT), str(path), "--root", str(self.root)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(str(self.root), result.stdout)
        (self.root / "evidence.txt").unlink()
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 1)
        path.write_text("{}")
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)


if __name__ == "__main__":
    unittest.main()
