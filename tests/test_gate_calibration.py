"""Fast fixture checks for the Batch 2a gate-calibration diagnostics.

These tests check that each diagnostic reconstructs its production quantity
exactly and that its supporting estimates are well formed. They do not assert
calibration findings; those are reported in
``docs/numerics/gate-calibration-2026-09-report.md``.
"""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from holoforge.benchmarks import gubser_nellore_ed as gn
from holoforge.benchmarks import holographic_superconductor_optical as optical


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/gate_calibration.py"
spec = importlib.util.spec_from_file_location("gate_calibration", SCRIPT)
calibration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calibration)


class GubserNelloreDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = gn.solve_coupled_profile(gn.QCD_LIKE, 1.04, 24)

    def test_high_precision_evaluator_matches_production_formula(self) -> None:
        fixture = calibration.gn_identity_fixture()
        self.assertTrue(fixture["passed"], fixture)

    def test_reconstruction_reproduces_production_residual_exactly(self) -> None:
        profile = self.profile
        double = calibration.gn_double_residual(
            profile.preset, profile.x_h, profile.degree,
            profile.blackening, profile.warp_factor, profile.scalar_factor,
        )
        reconstructed = max(float(np.max(np.abs(values))) for values in double.values())
        self.assertEqual(reconstructed, profile.nonlinear.final_scaled_residual)

    def test_evaluation_error_is_inside_the_rounding_bound(self) -> None:
        profile = self.profile
        arguments = (
            profile.preset, profile.x_h, profile.degree,
            profile.blackening, profile.warp_factor, profile.scalar_factor,
        )
        double = calibration.gn_double_residual(*arguments)
        high = calibration.gn_high_precision_residual(*arguments)
        bound = calibration.gn_rounding_bound(*arguments)
        for name in double:
            self.assertTrue(np.all(bound[name] > 0.0))
            self.assertTrue(np.all(np.abs(double[name] - high[name]) <= bound[name]))


class OpticalDiagnosticTests(unittest.TestCase):
    def test_reconstruction_reproduces_production_residual_exactly(self) -> None:
        with_capture = calibration.optical_solve_with_capture
        background = type(
            "NormalState", (), {
                "scalar_profile": staticmethod(optical.zero_scalar_profile),
                "scalar_response": 0.0,
                "horizon_scalar": 0.0,
            },
        )
        response, captured = with_capture(40.0, 64, background)
        profile = calibration.optical_residual_profiles(*captured["args"])
        self.assertEqual(profile["maximum"], float(response.equation_residual))
        self.assertGreaterEqual(profile["regular_maximum"], 0.0)


class SoftWallDiagnosticTests(unittest.TestCase):
    def test_condition_numbers_and_floors_are_well_formed(self) -> None:
        record = calibration.soft_wall_degree_record(48)
        self.assertTrue(all(value >= 1.0 - 1.0e-12 for value in record["eigenvalue_condition_numbers"]))
        self.assertTrue(all(value > 0.0 for value in record["relative_floor_estimates"]))
        self.assertGreater(record["operator_two_norm"], 0.0)

    def test_command_prints_json(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = calibration.main(["soft-wall"])
        self.assertEqual(status, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["gate"], "soft-wall")
        self.assertEqual(payload["case_set"], "calibration")
        self.assertIn("numpy_blas", payload["runtime"])


class DiagnosticStatusTests(unittest.TestCase):
    """A failed prerequisite must fail the command; scientific values must not."""

    def _run(self, gate, fake_result):
        output, errors = io.StringIO(), io.StringIO()
        with patch.dict(calibration.RUNNERS, {gate: lambda case_set, adverse: fake_result}):
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                status = calibration.main([gate])
        return status, json.loads(output.getvalue()), errors.getvalue()

    def test_failed_identity_fixture_exits_with_error(self) -> None:
        status, payload, errors = self._run(
            "gn", {"identity_fixture": {"passed": False}, "stopped": "identity fixture failed"}
        )
        self.assertEqual(status, 2)
        self.assertEqual(payload["status"], "diagnostic-error")
        self.assertTrue(payload["diagnostic_errors"])
        self.assertIn("identity", errors)

    def test_identity_mismatch_exits_with_error(self) -> None:
        status, payload, _ = self._run(
            "optical", {"records": [{"identity_check": {"exact_match": False}}]}
        )
        self.assertEqual(status, 2)
        self.assertEqual(payload["status"], "diagnostic-error")

    def test_non_finite_diagnostic_value_exits_with_error(self) -> None:
        status, payload, _ = self._run(
            "soft-wall", {"records": [{"max_relative_error": float("nan")}]}
        )
        self.assertEqual(status, 2)
        self.assertEqual(payload["status"], "diagnostic-error")

    def test_large_scientific_values_are_not_errors(self) -> None:
        status, payload, _ = self._run(
            "gn",
            {
                "identity_fixture": {"passed": True},
                "records": [{"identity_check": {"exact_match": True}, "max_double_residual": 5.0}],
            },
        )
        self.assertEqual(status, 0)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["diagnostic_errors"], [])

    def test_execution_metadata_is_recorded(self) -> None:
        _, payload, _ = self._run("soft-wall", {"records": []})
        execution = payload["execution"]
        self.assertRegex(execution["tool_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(execution["plan_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(set(execution["installed_wheel_tags"]), {"numpy", "scipy"})
        self.assertIsInstance(execution["thread_environment"], dict)
        self.assertIn("maximum value", payload["identity_scope"])


class RoundingConstantTests(unittest.TestCase):
    def test_gamma_is_close_to_count_times_epsilon(self) -> None:
        epsilon = np.finfo(float).eps
        self.assertAlmostEqual(calibration.rounding_gamma(10) / (10 * epsilon), 1.0, places=12)


if __name__ == "__main__":
    unittest.main()
