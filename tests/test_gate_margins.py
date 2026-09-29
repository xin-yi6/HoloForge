"""Checks for the gate-margin telemetry tool."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/gate_margins.py"
spec = importlib.util.spec_from_file_location("gate_margins", SCRIPT)
gate_margins = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate_margins)


RECORD = {
    "passed": False,
    "acceptance_checks": [
        {"id": "loose", "passed": True, "value": 1.0e-6, "criterion": "value <= 1e-3"},
        {
            "id": "tight",
            "passed": False,
            "value": 1.7e-9,
            "criterion": "value <= 1.0e-09",
        },
        {
            "id": "worded",
            "passed": True,
            "value": 4.0e-4,
            "criterion": "absolute difference <= 0.001",
        },
        {
            "id": "compound",
            "passed": True,
            "value": 8.4,
            "criterion": "8.2 <= value <= 8.7 and T/T_c <= 0.06",
        },
        {"id": "boolean", "passed": True, "criterion": "monotonic in T/T_c"},
    ],
}


class GateMarginTests(unittest.TestCase):
    def test_parses_only_single_positive_upper_bounds(self) -> None:
        self.assertEqual(gate_margins.parse_upper_bound("value <= 2e-4"), 2.0e-4)
        self.assertEqual(
            gate_margins.parse_upper_bound("maximum scaled difference <= 1.0e-12"),
            1.0e-12,
        )
        for criterion in (
            "8.2 <= value <= 8.7",
            "value <= 1 and other <= 2",
            "value >= 1",
            "value <= 0",
            "strictly decreasing across three degrees",
            None,
        ):
            self.assertIsNone(gate_margins.parse_upper_bound(criterion), criterion)

    def test_summary_orders_by_ratio_and_keeps_unparsed_gates(self) -> None:
        summary = gate_margins.summarize({"record.json": RECORD})
        self.assertEqual(
            [gate["id"] for gate in summary["gates"]], ["tight", "worded", "loose"]
        )
        self.assertAlmostEqual(summary["gates"][0]["ratio"], 1.7)
        self.assertEqual(
            {gate["id"] for gate in summary["not_parsed"]}, {"compound", "boolean"}
        )
        self.assertEqual(summary["records"], {"record.json": False})

    def test_command_emits_json_and_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            path.write_text(json.dumps(RECORD), encoding="utf-8")

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = gate_margins.main([str(path), "--json"])
            self.assertEqual(status, 0)
            self.assertEqual(len(json.loads(output.getvalue())["gates"]), 3)

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = gate_margins.main([str(path)])
            self.assertEqual(status, 0)
            self.assertIn("record.json: FAIL", output.getvalue())


if __name__ == "__main__":
    unittest.main()
