"""Analytic tests for the shared Chebyshev collocation grid."""

import unittest

import numpy as np

from holoforge.numerics import CHEBYSHEV_CONSTRUCTION, chebyshev_lobatto_grid
from holoforge.numerics.interpolation import (
    deterministic_barycentric_interpolator,
)


class ChebyshevGridTests(unittest.TestCase):
    def test_nodes_are_ascending_and_include_mapped_endpoints(self) -> None:
        grid = chebyshev_lobatto_grid(12, 2.0, 5.0)

        self.assertEqual(grid.size, 13)
        self.assertEqual(grid.nodes[0], 2.0)
        self.assertEqual(grid.nodes[-1], 5.0)
        self.assertTrue(np.all(np.diff(grid.nodes) > 0.0))
        self.assertGreater(grid.maximum_spacing, grid.minimum_spacing)

    def test_first_and_second_derivatives_are_exact_for_polynomials(self) -> None:
        grid = chebyshev_lobatto_grid(12, -0.7, 2.3)
        z = grid.nodes
        values = z**7 - 2.0 * z**4 + 0.5 * z**2 - 3.0
        exact_first = 7.0 * z**6 - 8.0 * z**3 + z
        exact_second = 42.0 * z**5 - 24.0 * z**2 + 1.0

        np.testing.assert_allclose(
            grid.first_derivative @ values,
            exact_first,
            rtol=0.0,
            atol=2.0e-10,
        )
        np.testing.assert_allclose(
            grid.second_derivative @ values,
            exact_second,
            rtol=0.0,
            atol=2.0e-8,
        )

    def test_constant_derivative_and_matrix_immutability(self) -> None:
        grid = chebyshev_lobatto_grid(10, 0.0, 4.0)
        np.testing.assert_allclose(
            grid.first_derivative @ np.ones(grid.size),
            0.0,
            rtol=0.0,
            atol=2.0e-14,
        )
        self.assertFalse(grid.nodes.flags.writeable)
        self.assertFalse(grid.first_derivative.flags.writeable)
        self.assertFalse(grid.second_derivative.flags.writeable)

    def test_grid_contract_over_the_repair_node_set(self) -> None:
        # Section 4 of docs/numerics/chebyshev-construction-repair-plan.md.
        degrees = (2, 3, 16, 17, 40, 41, 64, 80, 96, 120, 128, 150, 160, 192, 256, 320, 384, 512, 640, 1024, 1280)
        intervals = ((-1.0, 1.0), (1.0e-5, 1.0), (0.0, 1.0), (2.0, 5.0))
        self.assertEqual(CHEBYSHEV_CONSTRUCTION, "c-s1-r1")
        for degree in degrees:
            for lower, upper in intervals:
                with self.subTest(degree=degree, interval=(lower, upper)):
                    grid = chebyshev_lobatto_grid(degree, lower, upper)
                    self.assertEqual(grid.nodes[0], lower)
                    self.assertEqual(grid.nodes[-1], upper)
                    self.assertTrue(np.all(np.diff(grid.nodes) > 0.0))
                    for matrix in (grid.first_derivative, grid.second_derivative):
                        self.assertEqual(matrix.shape, (degree + 1, degree + 1))
                        self.assertEqual(matrix.dtype, np.float64)
                        self.assertTrue(np.all(np.isfinite(matrix)))
                        self.assertFalse(matrix.flags.writeable)
                    self.assertFalse(grid.nodes.flags.writeable)
                    # Rows annihilate constants; D1 and D2 are exact on the
                    # affine coordinate. The tolerances allow for the rounding
                    # of the matrix-vector product itself (up to 1281 terms).
                    xi = (2.0 * grid.nodes - lower - upper) / (upper - lower)
                    scale = 2.0 / (upper - lower)
                    for matrix, expected in ((grid.first_derivative, scale), (grid.second_derivative, 0.0)):
                        row_scale = np.abs(matrix) @ np.ones(grid.size)
                        self.assertLessEqual(np.max(np.abs(matrix @ np.ones(grid.size)) / row_scale), 1.0e-14)
                        self.assertLessEqual(np.max(np.abs(matrix @ xi - expected) / row_scale), 1.0e-13)

    def test_nodes_are_symmetric_about_the_midpoint(self) -> None:
        for degree in (2, 3, 16, 17, 640):
            grid = chebyshev_lobatto_grid(degree, -1.0, 1.0)
            np.testing.assert_array_equal(grid.nodes, -grid.nodes[::-1])
            if degree % 2 == 0:
                self.assertEqual(grid.nodes[degree // 2], 0.0)

    def test_second_derivative_is_exact_for_a_quadratic(self) -> None:
        grid = chebyshev_lobatto_grid(64, 1.0e-5, 1.0)
        z = grid.nodes
        row_scale = np.abs(grid.second_derivative) @ (z * z)
        self.assertLessEqual(np.max(np.abs(grid.second_derivative @ (z * z) - 2.0) / row_scale), 1.0e-14)

    def test_invalid_inputs_fail_clearly(self) -> None:
        for invalid_degree in (True, 1, 3.5):
            with self.subTest(degree=invalid_degree):
                with self.assertRaisesRegex(ValueError, "degree"):
                    chebyshev_lobatto_grid(invalid_degree)  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "lower_bound"):
            chebyshev_lobatto_grid(8, float("nan"), 1.0)
        with self.assertRaisesRegex(ValueError, "upper_bound"):
            chebyshev_lobatto_grid(8, 0.0, float("inf"))
        with self.assertRaisesRegex(ValueError, "less than"):
            chebyshev_lobatto_grid(8, 1.0, 1.0)

    def test_shared_barycentric_interpolator_is_deterministic(self) -> None:
        nodes = np.linspace(-1.0, 1.0, 9)
        values = nodes**4 - 0.5 * nodes
        first = deterministic_barycentric_interpolator(nodes, values)
        second = deterministic_barycentric_interpolator(nodes, values)
        targets = np.linspace(-0.9, 0.9, 17)
        np.testing.assert_array_equal(first(targets), second(targets))


if __name__ == "__main__":
    unittest.main()
