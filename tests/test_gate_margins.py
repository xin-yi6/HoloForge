"""Checks for the gate-margin telemetry tool."""

import contextlib
import copy
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


def _passing(record):
    result = copy.deepcopy(record)
    for check in result["acceptance_checks"]:
        check["passed"] = True
    result["passed"] = True
    return result


class GateMarginTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def _write(self, relative: str, payload) -> str:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        text = payload if isinstance(payload, str) else json.dumps(payload)
        path.write_text(text, encoding="utf-8")
        return str(path)

    def _run(self, *arguments: str):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            status = gate_margins.main(list(arguments))
        return status, output.getvalue(), errors.getvalue()

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

    def test_scientific_fail_is_reported_not_treated_as_error(self) -> None:
        path = self._write("record.json", RECORD)
        status, output, _ = self._run(path, "--json")
        self.assertEqual(status, 0)
        self.assertEqual(len(json.loads(output)["gates"]), 3)

        status, output, _ = self._run(path)
        self.assertEqual(status, 0)
        self.assertIn("record.json: FAIL", output)

    def test_same_file_name_from_two_platforms_keeps_both_records(self) -> None:
        linux = self._write("linux/gubser-nellore-ed.json", _passing(RECORD))
        macos = self._write("macos/gubser-nellore-ed.json", RECORD)
        verdicts = []
        for order in ((linux, macos), (macos, linux)):
            status, output, _ = self._run(*order, "--json")
            self.assertEqual(status, 0)
            verdicts.append(json.loads(output)["records"])
        self.assertEqual(verdicts[0], verdicts[1])
        self.assertEqual(sorted(verdicts[0].values()), [False, True])

    def test_same_path_twice_is_rejected(self) -> None:
        path = self._write("record.json", RECORD)
        status, _, errors = self._run(path, path)
        self.assertEqual(status, 2)
        self.assertIn("more than once", errors)

    def test_malformed_or_inconsistent_records_exit_with_error(self) -> None:
        inconsistent = copy.deepcopy(RECORD)
        inconsistent["passed"] = True
        boolean_value = _passing(RECORD)
        boolean_value["acceptance_checks"][0]["value"] = True
        cases = {
            "error-object": {"error": "execution failed"},
            "string-verdict": {"passed": "false", "acceptance_checks": []},
            "no-checks": {"passed": True, "acceptance_checks": []},
            "verdict-disagrees-with-checks": inconsistent,
            "boolean-value": boolean_value,
            "not-an-object": [RECORD],
            "non-finite-value": json.dumps(_passing(RECORD)).replace("1e-06", "NaN"),
            "empty-file": "",
        }
        for name, payload in cases.items():
            with self.subTest(name):
                path = self._write(f"{name}.json", payload)
                status, output, errors = self._run(path)
                self.assertEqual(status, 2)
                self.assertEqual(output, "")
                self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
