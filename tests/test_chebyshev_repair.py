"""Fast checks for the Chebyshev construction repair diagnostics.

These tests cover the tool's machinery (static preflight, reference
operators, candidate API and comparison rules). They do not assert the
repair's findings; those are in
``docs/numerics/chebyshev-construction-repair-report.md``.
"""

import importlib.util
from pathlib import Path
import unittest

import numpy as np

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


class ReferenceAndCandidateTests(unittest.TestCase):
    def test_row_sets_are_defined_for_the_smallest_degrees(self) -> None:
        self.assertEqual(repair.row_sets(2), {"all": [0, 1, 2], "uv": [1], "ir": [1]})
        self.assertEqual(repair.row_sets(3)["uv"], [1, 2])
        self.assertEqual(repair.row_sets(3)["ir"], [1, 2])
        self.assertEqual(repair.row_sets(640)["uv"], [1, 2, 3])
        self.assertEqual(repair.row_sets(640)["ir"], [637, 638, 639])
        with self.assertRaises(ValueError):
            repair.row_sets(1)

    def test_compensated_sum_and_product_are_accurate(self) -> None:
        import math
        from fractions import Fraction

        rng = np.random.default_rng(7)
        values = rng.standard_normal((4, 257)) * 10.0 ** rng.integers(-6, 6, (4, 257))
        for got, row in zip(repair.compensated_row_sum(values), values):
            self.assertEqual(got, math.fsum(row))
        factors = np.abs(rng.standard_normal((3, 130))) + 0.05
        high, low, exponent = repair.compensated_row_product(factors)
        for i in range(3):
            exact = Fraction(1)
            for value in factors[i]:
                exact *= Fraction(float(value))
            got = (Fraction(float(high[i])) + Fraction(float(low[i]))) * Fraction(2) ** int(exponent[i])
            self.assertLess(abs(float((got - exact) / exact)), 1.0e-28)

    def test_reference_matrices_differentiate_a_polynomial_exactly(self) -> None:
        from decimal import Decimal, localcontext

        with localcontext() as context:
            context.prec = repair.DIGITS
            for degree in (2, 3, 9):
                nodes = [Decimal(float(u)) for u in repair.half_angle_nodes(degree, 1.0e-5, 1.0)]
                values, firsts, seconds = repair.polynomial(nodes, 1.0e-5, 1.0, degree)
                reference = repair.Reference(nodes, {"p": ([v[0] for v in values], [v[1] for v in values])})
                for order, analytic in ((0, firsts), (1, seconds)):
                    for product, exact in zip(reference.products["p"][order], analytic):
                        self.assertLess(abs(product[0] - exact[0]) + abs(product[1] - exact[1]), Decimal("1e-35"))

    def test_every_construction_keeps_the_grid_contract(self) -> None:
        for name in repair.CONSTRUCTIONS:
            for degree in (2, 3, 16, 17):
                nodes, first, second = repair.construct(name, degree, 2.0, 5.0)
                self.assertEqual((nodes[0], nodes[-1]), (2.0, 5.0))
                self.assertTrue(np.all(np.diff(nodes) > 0.0))
                self.assertFalse(first.flags.writeable or second.flags.writeable or nodes.flags.writeable)
                np.testing.assert_allclose(first @ np.ones(degree + 1), 0.0, atol=1.0e-12)
                np.testing.assert_allclose(first @ nodes, 1.0, rtol=0.0, atol=1.0e-11)
                np.testing.assert_allclose(second @ nodes**2, 2.0, rtol=0.0, atol=1.0e-9)

    def test_legacy_copy_is_the_production_construction(self) -> None:
        from holoforge.numerics import chebyshev_lobatto_grid

        for degree, lower, upper in ((12, -0.7, 2.3), (40, 1.0e-5, 1.0)):
            nodes, first, second = repair.construct("current", degree, lower, upper)
            grid = chebyshev_lobatto_grid(degree, lower, upper)
            self.assertEqual(nodes.tobytes(), grid.nodes.tobytes())
            self.assertEqual(first.tobytes(), grid.first_derivative.tobytes())
            self.assertEqual(second.tobytes(), grid.second_derivative.tobytes())

    def test_grid_metrics_are_finite_and_small(self) -> None:
        matrices = {name: repair.construct(name, 9, 0.0, 1.0) for name in repair.CONSTRUCTIONS}
        metrics = repair.grid_metrics(9, 0.0, 1.0, repair.CONSTRUCTIONS, matrices)
        for name in repair.CONSTRUCTIONS:
            self.assertLess(max(metrics[name]["exactness"].values()), 1.0e-12)
            self.assertLess(max(metrics[name]["a"].values()), 1.0e-12)
            self.assertEqual(len(metrics[name]["b"]), 36)


class SelectionRuleTests(unittest.TestCase):
    @staticmethod
    def _result(candidate_value, current_value=1.0e-15, metric_c=1.0e-17, exactness=1.0e-14):
        def entry(value):
            return {"a": {"D1_stored": value, "D1_ideal": 1.0}, "b": {"D2_stored_v1_uv": value},
                    "exactness": {"D1": exactness, "D2": exactness}}

        grid = {"current": entry(current_value)}
        metric = {"current": {"worst_rows_1_3_scaled": 1.0e-15, "worst_rows_1_3_abs": 1.0e-4}}
        for name in repair.CANDIDATES:
            grid[name] = entry(candidate_value)
            metric[name] = {"worst_rows_1_3_scaled": metric_c, "worst_rows_1_3_abs": 1.0e-6}
        return {"build_label": "B1", "grids": {"16|0.0|1.0": grid}, "metric_c": metric}

    def test_a_candidate_within_the_factor_qualifies_and_is_selected(self) -> None:
        outcome = repair.selection([self._result(2.0e-15)])
        self.assertTrue(outcome["passed"])
        self.assertIn(outcome["selected"], repair.CANDIDATES)

    def test_no_rounding_floor_is_applied(self) -> None:
        outcome = repair.selection([self._result(3.0e-17, current_value=1.0e-17)])
        self.assertFalse(outcome["passed"])
        self.assertEqual(outcome["stopped"], "no candidate qualifies")
        sizes = outcome["qualification"]["B1"]["C-S1"]["failures_by_candidate_size"]
        self.assertEqual(sizes["below_1_eps"], 2)

    def test_exactness_and_improvement_are_required(self) -> None:
        self.assertFalse(repair.selection([self._result(1.0e-15, exactness=1.0e-9)])["passed"])
        weak = repair.selection([self._result(1.0e-15, metric_c=2.0e-16)])
        self.assertFalse(weak["passed"])
        self.assertEqual(weak["stopped"], "no qualified candidate reaches the required improvement")

    def test_zero_baseline_with_nonzero_candidate_fails(self) -> None:
        self.assertFalse(repair.selection([self._result(1.0e-18, current_value=0.0)])["passed"])


if __name__ == "__main__":
    unittest.main()
