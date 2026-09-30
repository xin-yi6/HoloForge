"""Scientific and numerical tests for the first HoloForge benchmark."""

import json
import unittest

import numpy as np

from holoforge.benchmarks.soft_wall_vector import (
    DEFAULT_TOLERANCE,
    SPECTRAL_REFINEMENT_RULE,
    SoftWallConfig,
    SpectralLevelDiagnostics,
    analytic_mass_squared,
    schrodinger_potential,
    solve_spectrum,
    spectral_refinement_verdict,
)


class SoftWallEquationTests(unittest.TestCase):
    def test_analytic_spectrum_and_scale(self) -> None:
        values = analytic_mass_squared(num_modes=4, kappa_gev=0.5)
        np.testing.assert_allclose(values, [1.0, 2.0, 3.0, 4.0])

    def test_potential_restores_kappa_dimensions(self) -> None:
        z = np.array([1.0, 2.0])
        values = schrodinger_potential(z, kappa_gev=0.5)
        expected = 0.5**4 * z**2 + 3.0 / (4.0 * z**2)
        np.testing.assert_allclose(values, expected)

    def test_invalid_physical_and_numerical_inputs_fail(self) -> None:
        with self.assertRaisesRegex(ValueError, "kappa"):
            SoftWallConfig(kappa_gev=0.0)
        with self.assertRaisesRegex(ValueError, "kappa"):
            SoftWallConfig(kappa_gev="not-a-number")  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "grid_points"):
            SoftWallConfig(grid_points=2)
        with self.assertRaisesRegex(ValueError, "z_max"):
            SoftWallConfig(z_max_gev_inverse=-1.0)
        with self.assertRaisesRegex(ValueError, "spectral_degree"):
            SoftWallConfig(spectral_degree=20)
        with self.assertRaisesRegex(ValueError, "num_modes"):
            analytic_mass_squared(num_modes=0, kappa_gev=1.0)
        with self.assertRaisesRegex(ValueError, "z_gev_inverse"):
            schrodinger_potential([0.0, 1.0], kappa_gev=1.0)


class SoftWallNumericalTests(unittest.TestCase):
    def test_default_solver_meets_declared_acceptance_tolerance(self) -> None:
        result = solve_spectrum(SoftWallConfig(), num_modes=4)
        np.testing.assert_allclose(
            result.analytic_mass_squared_gev2,
            [4.0, 8.0, 12.0, 16.0],
            rtol=0.0,
            atol=1.0e-14,
        )
        self.assertLessEqual(result.max_relative_error, DEFAULT_TOLERANCE)

    def test_grid_refinement_reduces_spectral_error(self) -> None:
        coarse = solve_spectrum(SoftWallConfig(grid_points=300), num_modes=4)
        fine = solve_spectrum(SoftWallConfig(grid_points=600), num_modes=4)

        observed_order = np.log(
            coarse.max_relative_error / fine.max_relative_error
        ) / np.log(
            coarse.grid_spacing_gev_inverse
            / fine.grid_spacing_gev_inverse
        )

        self.assertLess(fine.max_relative_error, coarse.max_relative_error)
        self.assertGreater(observed_order, 1.8)
        self.assertLess(observed_order, 2.2)

    def test_dimensionless_solution_is_scale_covariant(self) -> None:
        unit_scale = solve_spectrum(
            SoftWallConfig(kappa_gev=1.0, grid_points=600), num_modes=3
        )
        half_scale = solve_spectrum(
            SoftWallConfig(kappa_gev=0.5, grid_points=600), num_modes=3
        )
        np.testing.assert_allclose(
            half_scale.numerical_mass_squared_gev2,
            0.25 * unit_scale.numerical_mass_squared_gev2,
            rtol=1.0e-11,
            atol=1.0e-12,
        )

    def test_spectral_solver_reproduces_exact_modes_and_converges(self) -> None:
        result = solve_spectrum(
            SoftWallConfig(spectral_degree=40),
            num_modes=4,
            method="spectral",
        )
        record = result.to_dict(DEFAULT_TOLERANCE)

        self.assertLess(result.max_relative_error, 1.0e-10)
        self.assertEqual(result.spectral_refinement_degrees, (24, 32, 40))
        self.assertTrue(record["passed"])
        self.assertTrue(
            record["spectral_convergence"]["improves_at_every_level"]
        )
        self.assertEqual(record["numerical_method"]["route"], "spectral")

    def test_spectral_solution_is_scale_covariant(self) -> None:
        unit_scale = solve_spectrum(
            SoftWallConfig(kappa_gev=1.0, spectral_degree=40),
            num_modes=3,
            method="spectral",
        )
        half_scale = solve_spectrum(
            SoftWallConfig(kappa_gev=0.5, spectral_degree=40),
            num_modes=3,
            method="spectral",
        )
        np.testing.assert_allclose(
            half_scale.numerical_mass_squared_gev2,
            0.25 * unit_scale.numerical_mass_squared_gev2,
            rtol=1.0e-11,
            atol=1.0e-12,
        )


def _level(degree, errors, scale=1.0e-12, *, mismatch=None):
    """Synthetic plateau-level data with a chosen first-order scale."""

    analytic = [4.0 * (n + 1) for n in range(len(errors))]
    eigenvalues = tuple(a * (1.0 + e) for a, e in zip(analytic, errors))
    norm = scale * min(eigenvalues) / np.finfo(float).eps
    matched = tuple(
        complex(value * (1.0 + (0.0 if mismatch is None else mismatch)))
        for value in eigenvalues
    )
    return analytic, SpectralLevelDiagnostics(
        degree=degree,
        eigenvalues=eigenvalues,
        matched_eigenvalues=matched,
        condition_numbers=tuple(1.0 for _ in errors),
        operator_two_norm=norm,
    )


class SpectralRefinementRuleTests(unittest.TestCase):
    """Rule version 2, evaluated on recorded data without an eigensolve."""

    def _verdict(self, maxima, errors_middle, errors_fine, **kwargs):
        analytic, middle = _level(56, errors_middle, **kwargs)
        _, fine = _level(64, errors_fine, **kwargs)
        return spectral_refinement_verdict(maxima, analytic, (middle, fine))

    def test_strict_convergence_is_the_unchanged_branch(self) -> None:
        verdict = self._verdict((1e-9, 1e-11, 1e-13), [1e-11] * 4, [1e-13] * 4)
        self.assertTrue(verdict["passed"])
        self.assertEqual(verdict["branch"], "convergence")

    def test_rounding_plateau_passes(self) -> None:
        verdict = self._verdict((2e-14, 4e-14, 1e-14), [4e-14] * 4, [1e-14] * 4)
        self.assertTrue(verdict["passed"])
        self.assertEqual(verdict["branch"], "plateau")
        self.assertEqual(len(verdict["plateau_levels"][1]["relative_errors"]), 4)

    def test_final_accuracy_requirement_is_unchanged(self) -> None:
        verdict = self._verdict((1e-5, 1e-6, 1e-7), [1e-6] * 4, [1e-7] * 4, scale=1.0)
        self.assertFalse(verdict["passed"])
        self.assertEqual(verdict["branch"], "none")

    def test_error_above_the_perturbation_scale_fails(self) -> None:
        verdict = self._verdict((4e-9, 4e-9, 4e-9), [4e-9] * 4, [4e-9] * 4)
        self.assertFalse(verdict["plateau"])
        self.assertFalse(verdict["passed"])

    def test_failed_eigenvalue_matching_fails_the_plateau(self) -> None:
        verdict = self._verdict(
            (2e-14, 4e-14, 1e-14), [4e-14] * 4, [1e-14] * 4, mismatch=1e-9
        )
        self.assertFalse(verdict["plateau_levels"][0]["matched"])
        self.assertFalse(verdict["passed"])

    def test_failed_cross_degree_stability_fails_the_plateau(self) -> None:
        # Codex's counterexample: each level lies within its own scale, on
        # opposite sides of the analytic value. Normalized by the computed
        # eigenvalue, the levels disagree by more than the sum of their
        # scales. A large synthetic scale makes the excess robust to
        # rounding; the plateau flag is tested directly, independently of
        # the accuracy requirement.
        scale = 1.0e-3
        error = 0.9999 * scale
        analytic, middle = _level(56, [error], scale=scale)
        _, fine = _level(64, [-error], scale=scale)
        verdict = spectral_refinement_verdict((1.0, error, error), analytic, (middle, fine))
        self.assertTrue(all(level["within_scale"] for level in verdict["plateau_levels"]))
        self.assertTrue(all(level["matched"] for level in verdict["plateau_levels"]))
        self.assertGreater(verdict["stability_ratios"][0], 1.0)
        self.assertFalse(verdict["plateau"])
        self.assertFalse(verdict["passed"])

    def test_non_finite_values_fail_without_raising(self) -> None:
        analytic, middle = _level(56, [4e-14] * 4)
        _, fine = _level(64, [1e-14] * 4)
        broken = SpectralLevelDiagnostics(
            degree=fine.degree,
            eigenvalues=(fine.eigenvalues[0], float("nan")) + fine.eigenvalues[2:],
            matched_eigenvalues=fine.matched_eigenvalues,
            condition_numbers=fine.condition_numbers,
            operator_two_norm=fine.operator_two_norm,
        )
        verdict = spectral_refinement_verdict((2e-14, 4e-14, 1e-14), analytic, (middle, broken))
        self.assertFalse(verdict["passed"])
        json.dumps(verdict, allow_nan=False)

    def test_diagnostics_must_cover_every_requested_mode(self) -> None:
        analytic, middle = _level(56, [4e-14] * 4)
        _, fine = _level(64, [1e-14] * 4)
        six_modes = [4.0 * (n + 1) for n in range(6)]
        verdict = spectral_refinement_verdict((2e-14, 4e-14, 1e-14), six_modes, (middle, fine))
        self.assertFalse(verdict["plateau"])
        self.assertFalse(verdict["passed"])

    def test_missing_diagnostics_fall_back_to_the_convergence_rule(self) -> None:
        analytic = [4.0, 8.0, 12.0, 16.0]
        self.assertFalse(spectral_refinement_verdict((2e-14, 4e-14, 1e-14), analytic, ())["passed"])
        self.assertTrue(spectral_refinement_verdict((1e-9, 1e-11, 1e-13), analytic, ())["passed"])


class SpectralRefinementSolveTests(unittest.TestCase):
    """End-to-end behaviour on the confirmed regression controls."""

    def _record(self, degree, *, modes=4, z_max_factor=None):
        z_max = None if z_max_factor is None else z_max_factor / 1.0
        result = solve_spectrum(
            SoftWallConfig(spectral_degree=degree, z_max_gev_inverse=z_max),
            num_modes=modes,
            method="spectral",
        )
        record = result.to_dict(DEFAULT_TOLERANCE)
        checks = {check["id"]: check for check in record["acceptance_checks"]}
        return result, record, checks

    def test_high_degree_plateau_now_passes(self) -> None:
        for degree in (56, 64, 100):
            with self.subTest(degree=degree):
                result, record, checks = self._record(degree)
                self.assertTrue(checks["spectral-degree-refinement"]["passed"])
                self.assertTrue(record["passed"])
                self.assertEqual(record["numerical_method"]["refinement_rule"], SPECTRAL_REFINEMENT_RULE)
                self.assertLess(result.max_relative_error, 1.0e-12)

    def test_under_resolution_still_fails(self) -> None:
        _, record, checks = self._record(24)
        self.assertFalse(checks["spectral-degree-refinement"]["passed"])
        self.assertEqual(record["spectral_convergence"]["branch"], "none")

    def test_truncated_domains_still_fail(self) -> None:
        for factor in (4.0, 6.0):
            with self.subTest(z_max_factor=factor):
                _, record, checks = self._record(56, z_max_factor=factor)
                self.assertFalse(checks["spectral-degree-refinement"]["passed"])
                self.assertFalse(record["passed"])

    def test_other_mode_counts_check_every_requested_mode(self) -> None:
        for modes in (2, 6):
            with self.subTest(modes=modes):
                _, record, checks = self._record(64, modes=modes)
                levels = record["spectral_convergence"]["plateau_levels"]
                self.assertTrue(all(len(level["relative_errors"]) == modes for level in levels))
                self.assertEqual(len(record["spectral_convergence"]["stability_ratios"]), modes)
                self.assertTrue(checks["spectral-degree-refinement"]["passed"])

    def test_record_is_strict_json(self) -> None:
        _, record, _ = self._record(64)
        json.dumps(record, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
