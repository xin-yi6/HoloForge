"""Fast checks for the Chebyshev construction repair diagnostics.

These tests cover the tool's machinery (static preflight, reference
operators, candidate API and comparison rules). They do not assert the
repair's findings; those are in
``docs/numerics/chebyshev-construction-repair-report.md``.
"""

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/chebyshev_repair.py"
spec = importlib.util.spec_from_file_location("chebyshev_repair", SCRIPT)
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


class StructuralPreflightTests(unittest.TestCase):
    def test_regression_table_matches_source_and_committed_records(self) -> None:
        result = repair.p0_check()
        failing = [item for item in result["consumers"] if not item["passed"]]
        self.assertEqual(failing, [])
        self.assertEqual(len(result["consumers"]), 8)

    def test_pointer_resolution_handles_lists_mappings_and_indices(self) -> None:
        record = {"a": [{"b": 1}, {"b": 2}], "m": {"x": {"b": 3}, "y": {"b": 4}}}
        self.assertEqual(repair.resolve_pointer(record, "/a/*/b"), [1, 2])
        self.assertEqual(sorted(repair.resolve_pointer(record, "/m/*/b")), [3, 4])
        self.assertEqual(repair.resolve_pointer(record, "/a/-1/b"), [2])
        self.assertEqual(repair.resolve_pointer(record, "/a/*/missing"), [])

    def test_call_graph_detects_transitive_reach(self) -> None:
        graph = {"control": {"helper"}, "helper": {"leaf"}, "solver": {repair.ROUTINE}, "bad": {"solver"}}
        self.assertNotIn(repair.ROUTINE, repair.reachable(graph, "control"))
        self.assertIn(repair.ROUTINE, repair.reachable(graph, "bad"))


if __name__ == "__main__":
    unittest.main()
