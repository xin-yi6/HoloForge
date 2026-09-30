"""Checks for the read-only environment diagnostics tool."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/environment_report.py"
spec = importlib.util.spec_from_file_location("environment_report", SCRIPT)
environment_report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(environment_report)

ABSOLUTE_PATH = re.compile(r"(?:^|\s)(?:/|~|[A-Za-z]:[\\/])")


def _strings(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, str):
        yield value


class EnvironmentReportTests(unittest.TestCase):
    def test_report_is_serializable_and_path_free(self) -> None:
        report = environment_report.build_report(environment={})
        json.dumps(report)
        self.assertEqual(report["report"], "holoforge-environment")
        self.assertEqual(
            set(report["test_extras_available"]),
            set(environment_report.TEST_EXTRAS),
        )
        for field in ("numpy_blas", "holoforge_source_sha256", "longdouble_epsilon"):
            self.assertIn(field, report["runtime"])
        self.assertFalse(
            [text for text in _strings(report) if ABSOLUTE_PATH.search(text)]
        )

    def test_stale_metadata_and_missing_extras_are_reported(self) -> None:
        with patch.object(
            environment_report, "_installed_distribution_version", return_value="0.2.0"
        ), patch.object(
            environment_report,
            "_module_available",
            side_effect=lambda name: name != "rfc3339_validator",
        ):
            report = environment_report.build_report(environment={})

        self.assertFalse(report["installed_metadata_matches_source"])
        warnings = " ".join(report["warnings"])
        self.assertIn("0.2.0", warnings)
        self.assertIn("rfc3339_validator", warnings)

    def test_uninstalled_source_has_no_metadata_verdict(self) -> None:
        with patch.object(
            environment_report, "_installed_distribution_version", return_value=None
        ):
            report = environment_report.build_report(environment={})
        self.assertEqual(report["installed_distribution_version"], "not-installed")
        self.assertIsNone(report["installed_metadata_matches_source"])

    def test_thread_variables_mask_non_numeric_values(self) -> None:
        report = environment_report.build_report(
            environment={"VECLIB_MAXIMUM_THREADS": "1", "OMP_NUM_THREADS": "/tmp/x"}
        )
        self.assertEqual(
            report["thread_environment"],
            {"VECLIB_MAXIMUM_THREADS": "1", "OMP_NUM_THREADS": "set"},
        )

    def test_command_prints_json(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = environment_report.main([])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue())["report_version"], "1")


if __name__ == "__main__":
    unittest.main()
