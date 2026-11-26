"""Check the optional neutral Einstein–scalar collocation residual against NumPy."""
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from holoforge.benchmarks.dewolfe_gubser_rosen_emd import DGR_POTENTIAL
from holoforge.benchmarks.gubser_nellore_ed import (
    COSH_CALIBRATION, QCD_LIKE, CoupledSolverConfig,
    _rust_collocation_equations, _scaled_coupled_equations, solve_coupled_profile,
)
from holoforge.numerics import chebyshev_lobatto_grid

try:
    from holoforge_native import gubser_nellore_equations
except ImportError:
    gubser_nellore_equations = None


class ResidualSelectionTests(unittest.TestCase):
    def test_optional_installation_and_supported_backends(self):
        for extension in (None, SimpleNamespace(__version__="0.1.0")):
            with patch.dict(sys.modules, {"holoforge_native": extension}):
                self.assertNotIn("holoforge-native", CoupledSolverConfig().software_versions())
                with self.assertRaisesRegex(RuntimeError, "pip install ./native"):
                    solve_coupled_profile(
                        QCD_LIKE, 0.2, 24, config=CoupledSolverConfig(residual_backend="rust")
                    )
        with self.assertRaisesRegex(ValueError, "residual_backend"):
            CoupledSolverConfig(residual_backend="unknown")


@unittest.skipUnless(gubser_nellore_equations, "requires the optional native collocation kernel")
class RustCollocationTests(unittest.TestCase):
    def test_pointwise_residual_including_endpoints_and_off_solution_fields(self):
        rng = np.random.default_rng(19)
        for preset, horizon, degree in (
            (COSH_CALIBRATION, 35.5, 40), (QCD_LIKE, 1.25, 150), (DGR_POTENTIAL, 0.82, 80)
        ):
            with self.subTest(preset=preset.identifier):
                u = chebyshev_lobatto_grid(degree, 0.0, 1.0).nodes
                fields = rng.normal(0.0, 0.02, size=(9, len(u)))
                fields[6] += 1.0
                expected = _scaled_coupled_equations(preset, horizon, u, *fields)
                evaluate = _rust_collocation_equations(preset, horizon, u)
                np.testing.assert_allclose(evaluate(*fields), expected, atol=0.0, rtol=2e-15)

    def test_invalid_array_length(self):
        u = np.ones(5)
        field = (u, u, u)
        with self.assertRaisesRegex(ValueError, "radial grid"):
            gubser_nellore_equations(1.0, 1.0, u, field, field, field, u[:-1])

    def test_public_profile_solver_agrees_for_all_three_potentials(self):
        for preset in (COSH_CALIBRATION, QCD_LIKE, DGR_POTENTIAL):
            with self.subTest(preset=preset.identifier):
                reference = solve_coupled_profile(preset, 0.2, 40)
                rust_config = CoupledSolverConfig(residual_backend="rust")
                actual = solve_coupled_profile(preset, 0.2, 40, config=rust_config)
                self.assertTrue(actual.nonlinear.success)
                for field in ("blackening", "warp_factor", "scalar_factor"):
                    np.testing.assert_allclose(
                        getattr(actual, field), getattr(reference, field), atol=1e-10, rtol=1e-10
                    )
                self.assertIn("holoforge-native", rust_config.software_versions())
