"""Qualify the optional native integrator against finite-cutoff and independent solutions."""
import importlib.util
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

import numpy as np
from scipy.optimize import brentq
from scipy.special import j0, j1, jn_zeros, y0, y1

from holoforge.benchmarks.hard_wall_vector import (
    HardWallConfig,
    hard_wall_cutoff_refinement,
    solve_hard_wall_spectrum,
)


class OptionalInstallationTests(unittest.TestCase):
    def test_explicit_request_reports_missing_extension(self):
        with patch.dict(sys.modules, {"holoforge_native": None}):
            with self.assertRaisesRegex(RuntimeError, "pip install ./native"):
                solve_hard_wall_spectrum(method="shooting-rust")
            self.assertEqual(solve_hard_wall_spectrum(num_modes=1).method, "shooting")


@unittest.skipUnless(
    importlib.util.find_spec("holoforge_native"), "optional Rust wheel not installed"
)
class RustShootingTests(unittest.TestCase):
    def test_finite_cutoff_masses_and_wall_scaling(self):
        zeros = jn_zeros(0, 7)
        bounds = 0.5 * (np.r_[0.0, zeros[:-1]] + zeros)
        for cutoff, modes in ((1e-4, 1), (3e-3, 4), (1e-2, 6)):
            with self.subTest(cutoff=cutoff, modes=modes):
                config = HardWallConfig(
                    epsilon_fraction=cutoff,
                    z_m_gev_inverse=2.5,
                    integration_rtol=2e-10,
                    integration_atol=2e-12,
                    root_rtol=3e-11,
                )
                result = solve_hard_wall_spectrum(config, modes, method="shooting-rust")

                def determinant(m):
                    return j1(m * cutoff) * y0(m) - y1(m * cutoff) * j0(m)

                expected = np.array(
                    [
                        brentq(determinant, a, b)
                        for a, b in zip(bounds[:modes], bounds[1 : modes + 1])
                    ]
                )
                np.testing.assert_allclose(
                    result.dimensionless_masses, expected, rtol=2e-9
                )
                np.testing.assert_allclose(result.masses_gev, expected / 2.5, rtol=2e-9)
                payload = result.to_dict()
                for name in ("integration_rtol", "integration_atol", "root_rtol"):
                    self.assertEqual(payload["configuration"][name], getattr(config, name))

    def test_independent_routes_and_cutoff_convergence(self):
        native = solve_hard_wall_spectrum(method="shooting-rust")
        for method in ("shooting", "collocation", "spectral"):
            other = solve_hard_wall_spectrum(method=method)
            np.testing.assert_allclose(
                native.dimensionless_masses, other.dimensionless_masses, rtol=2e-9
            )
        self.assertTrue(
            hard_wall_cutoff_refinement(method="shooting-rust").improves_at_every_level
        )

    def test_off_root_derivative_and_invalid_native_inputs(self):
        from holoforge_native import hard_wall_residual

        m, eps = 7.0, 0.003
        exact = np.pi * m / 2 * (j1(m * eps) * y0(m) - y1(m * eps) * j0(m))
        self.assertAlmostEqual(
            hard_wall_residual(m, eps, 1e-10, 1e-12) / exact, 1.0, places=8
        )
        for args in (
            (m, 0.0, 1e-9, 1e-11),
            (np.nan, eps, 1e-9, 1e-11),
            (m, eps, 0.0, 1e-11),
        ):
            with self.assertRaises(ValueError):
                hard_wall_residual(*args)

    def test_cli_reports_selected_integrator_and_version(self):
        import holoforge_native

        raw = subprocess.check_output(
            [
                sys.executable,
                "-m",
                "holoforge",
                "verify",
                "hard-wall-vector",
                "--method",
                "shooting-rust",
                "--json",
            ],
            text=True,
        )
        record = json.loads(raw)
        self.assertTrue(record["passed"])
        self.assertEqual(record["numerical_method"]["route"], "shooting-rust")
        self.assertEqual(record["numerical_method"]["integrator"], "ivp::methods::DOP853")
        self.assertEqual(
            record["software_versions"]["holoforge-native"], holoforge_native.__version__
        )
