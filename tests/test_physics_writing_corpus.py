"""Editorial record integrity; these tests do not assess prose or physics."""

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PhysicsWritingCorpusTests(unittest.TestCase):
    def test_reading_counts_and_provenance_are_consistent(self):
        corpus = json.loads((ROOT / "docs/physics-writing-corpus.json").read_text())
        entries = corpus["entries"]
        self.assertEqual(len(entries), corpus["total_distinct_papers"])
        self.assertEqual(len({entry["id"] for entry in entries}), len(entries))
        self.assertEqual(len({entry["title"] for entry in entries}), len(entries))
        full = [e for e in entries if e["reading_status"] == "complete_main_text"]
        self.assertEqual(len(full), corpus["complete_main_text_count"])
        self.assertEqual(len(full), 50)  # The recorded study, not a future quota.
        legacy = [e for e in entries if not e["id"].startswith("E")]
        new = [e for e in entries if e["id"].startswith("E")]
        self.assertEqual(len(legacy), corpus["historical_record_count"])
        self.assertEqual(len(new), corpus["new_reading_count"])
        self.assertEqual(sum(e["reading_status"] == "selected_sections" for e in legacy), 14)
        for entry in entries:
            with self.subTest(entry=entry["id"]):
                self.assertIn(entry["reading_status"], {"complete_main_text", "selected_sections"})
                self.assertTrue(entry["read_scope"])
                self.assertTrue(entry["field"])
                self.assertTrue(entry["provenance"])
                self.assertTrue(entry["source_urls"])
                self.assertTrue(all(url.startswith("https://") for url in entry["source_urls"]))
        for entry in new:
            with self.subTest(entry=entry["id"]):
                self.assertRegex(entry["pdf_sha256"], r"^[0-9a-f]{64}$")
                self.assertRegex(entry["source_urls"][0], r"^https://arxiv.org/abs/.+v\d+$")
                self.assertEqual(entry["reading_status"], "complete_main_text")
                self.assertTrue(entry["genre"])
                self.assertTrue(entry["lesson"])

    def test_study_navigation_and_counterexamples(self):
        target = "physics-writing-expanded-study.md"
        for source in ("physics-manuscript-writing.md", "physics-writing-reading-study.md",
                       "physics-writing-cross-field-study.md"):
            self.assertIn(target, (ROOT / "docs" / source).read_text())
        study = (ROOT / "docs" / target).read_text()
        self.assertEqual(len(re.findall(r"^### \d+\.", study, re.M)), 12)
        for boundary in ("not representative", "not a recurring quota",
                         "not writing quality", "Exceptions", "physics-writing-corpus.json"):
            if boundary == "Exceptions":
                self.assertIn("Exception:", study)
            else:
                self.assertIn(boundary, " ".join(study.split()))
        corpus = json.loads((ROOT / "docs/physics-writing-corpus.json").read_text())
        ids = {e["id"] for e in corpus["entries"]}
        self.assertLessEqual(set(re.findall(r"\bE\d{2}\b", study)), ids)


if __name__ == "__main__":
    unittest.main()
