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


class OpticalOBTests(unittest.TestCase):
    """The O-B 50-digit evaluator and its guards (not the O-B findings)."""

    def test_identity_fixture_passes(self) -> None:
        fixture = calibration.optical_ob_identity_fixture()
        self.assertTrue(fixture["passed"], fixture)

    def test_evaluator_reproduces_a_quadratic_off_node_and_at_nodes(self) -> None:
        from decimal import Decimal, localcontext

        with localcontext() as context:
            context.prec = calibration.HIGH_PRECISION_DIGITS
            nodes = [Decimal(float(x)) for x in np.linspace(0.0, 1.0, 9)]
            weights = calibration.decimal_barycentric_weights(nodes)
            values = [(1 + 2 * x + 3 * x * x, -x * x) for x in nodes]
            for point in (Decimal("0.3"), nodes[0], nodes[4]):
                value, first, second = calibration.decimal_interpolant_derivatives(
                    nodes, weights, values, point
                )
                expected = (
                    (1 + 2 * point + 3 * point * point, -point * point),
                    (2 + 6 * point, -2 * point),
                    (Decimal(6), Decimal(-2)),
                )
                for got, want in zip((value, first, second), expected):
                    self.assertLess(abs(got[0] - want[0]) + abs(got[1] - want[1]), Decimal("1e-40"))

    def test_regular_residual_matches_the_double_formula(self) -> None:
        with_capture = calibration.optical_solve_with_capture
        background = type(
            "NormalState", (), {
                "scalar_profile": staticmethod(optical.zero_scalar_profile),
                "scalar_response": 0.0,
                "horizon_scalar": 0.0,
            },
        )
        record = calibration.optical_ob_case_record(40.0, 64, background, {})
        self.assertTrue(record["identity_check"]["exact_match"])
        spike = next(
            node for node in record["measurement_2"]
            if node["check_index"] == record["spike_check_index"]
        )
        # Same polynomial and inputs: only double evaluation error separates them.
        self.assertLess(
            spike["residual_difference_abs"], 0.5 * spike["double_regular_residual_abs"]
        )
        self.assertLess(record["precision_cross_check"]["max_relative_difference_at_spike"], 1.0e-30)
        self.assertLess(record["measurement_1"]["maximum_identity_defect_common_denominator"], 1.0e-12)
        self.assertEqual(len(record["measurement_4"]), calibration.OPTICAL_OB_LOCAL_NODES)

    def test_interpretation_rules(self) -> None:
        rule = calibration.optical_ob_interpretation
        self.assertEqual(rule(1.0e-4, 1.0e-6, 1.0e-4, 1.0e-4), "evaluation-artifact")
        self.assertEqual(rule(1.0e-4, 1.0e-6, 1.0e-4, 1.0e-6), "unresolved")
        self.assertEqual(rule(1.0e-4, 1.05e-4, 5.0e-6, 5.0e-6), "polynomial-defect")
        self.assertEqual(rule(1.0e-4, 1.9e-4, 9.0e-5, 9.0e-5), "polynomial-defect")
        self.assertEqual(rule(1.0e-4, 3.0e-5, 7.0e-5, 7.0e-5), "unresolved")

    def test_reserved_cases_and_adverse_controls_are_refused(self) -> None:
        for arguments in (["optical-ob", "--case-set", "confirmation"], ["optical-ob", "--adverse"]):
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                status = calibration.main(arguments)
            payload = json.loads(output.getvalue())
            self.assertEqual(status, 2)
            self.assertEqual(payload["plan"], "docs/numerics/optical-ob-diagnosis-plan.md")
            self.assertIn("stopped", payload["result"])


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


class SoftWallSATests(unittest.TestCase):
    """The candidate rule's verdict logic, on synthetic level data."""

    @staticmethod
    def _level(degree, errors, scale=1.0e-12):
        analytic = [4.0, 8.0, 12.0, 16.0]
        eigenvalues = [a * (1.0 + e) for a, e in zip(analytic, errors)]
        norm = scale / np.finfo(float).eps * min(eigenvalues)
        return {
            "degree": degree,
            "eigenvalues": eigenvalues,
            "analytic": analytic,
            "matched_with_vectors": [[value, 0.0] for value in eigenvalues],
            "condition_numbers": [1.0] * 4,
            "operator_two_norm": norm,
        }

    def test_strict_convergence_passes_both_rules(self) -> None:
        levels = [self._level(d, [e] * 4) for d, e in ((40, 1e-9), (48, 1e-11), (56, 1e-13))]
        verdict = calibration.sa_verdict(levels)
        self.assertTrue(verdict["current_rule_pass"])
        self.assertTrue(verdict["sa_pass"])

    def test_rounding_plateau_passes_only_the_candidate(self) -> None:
        levels = [self._level(d, [e] * 4) for d, e in ((48, 2e-14), (56, 4e-14), (64, 1e-14))]
        verdict = calibration.sa_verdict(levels)
        self.assertFalse(verdict["current_rule_pass"])
        self.assertTrue(verdict["branch_p_plateau"])
        self.assertTrue(verdict["sa_pass"])

    def test_plateau_above_the_perturbation_scale_fails(self) -> None:
        levels = [self._level(d, [4e-9] * 4) for d in (48, 56, 64)]
        verdict = calibration.sa_verdict(levels)
        self.assertFalse(verdict["branch_p_plateau"])
        self.assertFalse(verdict["sa_pass"])

    def test_accuracy_requirement_is_unchanged(self) -> None:
        levels = [self._level(d, [e] * 4, scale=1.0) for d, e in ((40, 1e-5), (48, 1e-6), (56, 1e-7))]
        verdict = calibration.sa_verdict(levels)
        self.assertFalse(verdict["current_rule_pass"])
        self.assertFalse(verdict["sa_pass"])

    def test_non_finite_eigenvalue_fails_without_raising(self) -> None:
        levels = [self._level(d, [e] * 4) for d, e in ((48, 2e-14), (56, 4e-14), (64, 1e-14))]
        levels[2]["eigenvalues"][1] = float("nan")
        verdict = calibration.sa_verdict(levels)
        self.assertFalse(verdict["sa_pass"])
        self.assertFalse(verdict["current_rule_pass"])

    def test_reconstruction_matches_the_production_rule(self) -> None:
        record = calibration.soft_wall_sa_case(40, 1.0, None)
        self.assertTrue(record["identity_check"]["exact_match"], record["identity_check"])


class RoundingConstantTests(unittest.TestCase):
    def test_gamma_is_close_to_count_times_epsilon(self) -> None:
        epsilon = np.finfo(float).eps
        self.assertAlmostEqual(calibration.rounding_gamma(10) / (10 * epsilon), 1.0, places=12)


if __name__ == "__main__":
    unittest.main()
