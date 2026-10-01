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


def synthetic_payload(build, candidate_value=2.0e-15, current_value=1.0e-15, metric_c=1.0e-17, exactness=1.0e-14,
                      bound_ratio=None):
    """A complete, admissible synthetic S0 output with uniform metric values."""

    def entry(value, name):
        item = {"a": {key: value for key in repair.A_KEYS}, "b": {key: value for key in repair.B_KEYS},
                "exactness": {"D1": exactness, "D2": exactness},
                "sha256": {key: (name + key).encode().hex().ljust(64, "0")[:64] for key in ("nodes", "D1", "D2")}}
        if bound_ratio is not None and name != "current":
            item["bound_ratio"] = {key: bound_ratio for key in repair.B_KEYS if "_stored" in key}
        return item

    grids = {}
    for label in repair.expected_grid_labels():
        grids[label] = {"current": entry(current_value, "current")}
        for name in repair.CANDIDATES:
            grids[label][name] = entry(candidate_value, name)
    artifacts = [{"artifact": f"artifact-{index}.npz"} for index in range(repair.ARTIFACT_COUNT)]
    metric = {"current": {"worst_rows_1_3_scaled": 1.0e-15, "worst_rows_1_3_abs": 1.0e-4,
                          "worst_all_rows_scaled": 1.0e-12, "artifacts": artifacts}}
    for name in repair.CANDIDATES:
        metric[name] = {"worst_rows_1_3_scaled": metric_c, "worst_rows_1_3_abs": 1.0e-6,
                        "worst_all_rows_scaled": 1.0e-15, "artifacts": artifacts}
    return {
        "tool": "chebyshev-repair", "stage": "s0", "status": "ok",
        "plan_sha256": repair._file_sha256(repair.ROOT / repair.PLAN), "tool_sha256": "a" * 64,
        "result": {"build_label": build, "passed": True, "production_equals_current_construction": True,
                   "fixtures": {name: {"passed": True} for name in repair.REQUIRED_FIXTURES},
                   "grids": grids, "metric_c": metric},
    }


def synthetic_pair(**options):
    return [synthetic_payload("B1", **options), synthetic_payload("B3", **options)]


class SelectionRuleTests(unittest.TestCase):
    def test_a_candidate_within_the_factor_qualifies_and_is_selected(self) -> None:
        agreement = {"tool": "chebyshev-repair", "stage": "build-agreement", "status": "ok",
                     "result": {name: {"differing_grids": 0, "max_relative_difference": 0.0, "seconds": 0.01}
                                for name in repair.CONSTRUCTIONS}}
        agreement["result"]["verified"] = {"other_label": "B3", "local_label": "B1", "files": 0,
                                           "saved_bytes_match_s0_hashes": True,
                                           "local_matrices_match_s0_hashes": True}
        outcome = repair.selection(synthetic_pair(), agreement)
        self.assertTrue(outcome["passed"], outcome.get("stopped"))
        self.assertIn(outcome["selected"], repair.CANDIDATES)
        del agreement["result"]["verified"]
        self.assertEqual(repair.selection(synthetic_pair(), agreement)["stopped"], "invalid build-agreement evidence")

    def test_a_tie_without_build_agreement_is_not_selected(self) -> None:
        outcome = repair.selection(synthetic_pair())
        self.assertFalse(outcome["passed"])
        self.assertEqual(outcome["stopped"], "a tie needs build-agreement evidence")

    def test_no_rounding_floor_is_applied(self) -> None:
        outcome = repair.selection(synthetic_pair(candidate_value=3.0e-17, current_value=1.0e-17))
        self.assertFalse(outcome["passed"])
        self.assertEqual(outcome["stopped"], "no candidate qualifies")
        sizes = outcome["qualification"]["B1"]["C-S1"]["failures_by_candidate_size"]
        self.assertEqual(sizes["below_1_eps"], 84 * (2 + 18))

    def test_exactness_and_improvement_are_required(self) -> None:
        self.assertFalse(repair.selection(synthetic_pair(candidate_value=1.0e-15, exactness=1.0e-9))["passed"])
        weak = repair.selection(synthetic_pair(candidate_value=1.0e-15, metric_c=2.0e-16))
        self.assertFalse(weak["passed"])
        self.assertEqual(weak["stopped"], "no qualified candidate reaches the required improvement")

    def test_zero_baseline_with_nonzero_candidate_fails(self) -> None:
        self.assertFalse(repair.selection(synthetic_pair(candidate_value=1.0e-18, current_value=0.0))["passed"])


class EvidenceAdmissionTests(unittest.TestCase):
    """Codex R55-1: invalid or incomplete evidence must be rejected."""

    def _rejected(self, payloads, agreement=None):
        outcome = repair.selection(payloads, agreement)
        self.assertFalse(outcome["passed"])
        self.assertIn(outcome["stopped"], ("invalid evidence", "invalid build-agreement evidence"))
        return outcome["evidence_errors"]

    def test_valid_synthetic_evidence_is_admitted(self) -> None:
        self.assertEqual(repair.validate_evidence(synthetic_pair()), [])

    def test_failed_fixture_failed_run_and_wrong_production_are_rejected(self) -> None:
        payloads = synthetic_pair()
        payloads[0]["result"]["passed"] = False
        payloads[0]["result"]["fixtures"] = {"F1": {"passed": False}}
        payloads[0]["result"]["production_equals_current_construction"] = False
        errors = " ".join(self._rejected(payloads))
        self.assertIn("did not pass", errors)
        self.assertIn("fixture", errors)
        self.assertIn("legacy construction", errors)

    def test_empty_or_partial_grids_are_rejected(self) -> None:
        payloads = synthetic_pair()
        payloads[1]["result"]["grids"] = {}
        self.assertIn("grid set", " ".join(self._rejected(payloads)))
        payloads = synthetic_pair()
        del payloads[0]["result"]["grids"]["640|1e-05|1.0"]
        self.assertIn("grid set", " ".join(self._rejected(payloads)))

    def test_non_finite_or_negative_metrics_are_rejected(self) -> None:
        payloads = synthetic_pair()
        payloads[0]["result"]["metric_c"]["current"]["worst_rows_1_3_scaled"] = float("inf")
        self.assertIn("metric (c)", " ".join(self._rejected(payloads)))
        for bad in (float("nan"), -1.0e-16, None, True):
            payloads = synthetic_pair()
            payloads[1]["result"]["grids"]["16|0.0|1.0"]["C-S1"]["b"]["D1_stored_v1_uv"] = bad
            self.assertIn("non-finite or negative", " ".join(self._rejected(payloads)), bad)

    def test_missing_duplicate_and_unknown_builds_are_rejected(self) -> None:
        self.assertIn("not exactly", " ".join(self._rejected([synthetic_payload("B1")])))
        self.assertIn("duplicate", " ".join(self._rejected([synthetic_payload("B1"), synthetic_payload("B1")])))
        self.assertIn("not exactly", " ".join(self._rejected([synthetic_payload("B1"), synthetic_payload("B9")])))

    def test_status_plan_tool_and_metric_coverage_are_checked(self) -> None:
        payloads = synthetic_pair()
        payloads[0]["status"] = "stopped"
        self.assertIn("status", " ".join(self._rejected(payloads)))
        payloads = synthetic_pair()
        payloads[0]["plan_sha256"] = "0" * 64
        self.assertIn("plan hash", " ".join(self._rejected(payloads)))
        payloads = synthetic_pair()
        payloads[1]["tool_sha256"] = "b" * 64
        self.assertIn("different tool versions", " ".join(self._rejected(payloads)))
        payloads = synthetic_pair()
        del payloads[0]["result"]["grids"]["2|2.0|5.0"]["C-T2"]["b"]["D2_stored_v3_ir"]
        self.assertIn("metric group b incomplete", " ".join(self._rejected(payloads)))
        payloads = synthetic_pair()
        payloads[0]["result"]["metric_c"]["C-S1"]["artifacts"] = payloads[0]["result"]["metric_c"]["C-S1"]["artifacts"][:3]
        self.assertIn("artifacts", " ".join(self._rejected(payloads)))

    def test_unreadable_input_is_rejected_at_the_command_line(self) -> None:
        import contextlib
        import io
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            good = Path(directory) / "good.json"
            good.write_text(json.dumps(synthetic_payload("B1")))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = repair.main(["select", str(good), str(Path(directory) / "missing.json")])
            payload = json.loads(output.getvalue())
        self.assertEqual(status, 2)
        self.assertEqual(payload["result"]["stopped"], "invalid evidence")

    def test_build_agreement_must_match_the_hashes(self) -> None:
        payloads = synthetic_pair()
        payloads[1]["result"]["grids"]["64|0.0|1.0"]["C-T1"]["sha256"]["D2"] = "c" * 64
        claims_equal = {"tool": "chebyshev-repair", "stage": "build-agreement", "status": "ok",
                        "result": {name: {"differing_grids": 0, "max_relative_difference": 0.0, "seconds": 0.01}
                                   for name in repair.CONSTRUCTIONS}}
        self.assertIn("hashes give 1", " ".join(self._rejected(payloads, claims_equal)))

    def test_build_agreement_does_not_infer_equality_from_an_empty_folder(self) -> None:
        import tempfile

        payloads = synthetic_pair()
        payloads[1]["result"]["grids"]["64|0.0|1.0"]["C-T1"]["sha256"]["D2"] = "c" * 64
        with tempfile.TemporaryDirectory() as directory:
            result = repair.build_agreement(Path(directory), "B3", payloads)
        self.assertEqual(result["stopped"], "saved matrices do not match the grids whose hashes differ")
        self.assertEqual(result["missing"], ["B3-C-T1-64-0.0-1.0.npz"])

    def test_committed_evidence_is_admitted_and_reproduces_the_stop(self) -> None:
        import json

        folder = ROOT / "docs/generated/chebyshev-repair"
        payloads = [json.loads((folder / f"{label}-s0.json").read_text()) for label in ("B1", "B3")]
        self.assertEqual(repair.validate_evidence(payloads), [])
        outcome = repair.selection(payloads, json.loads((folder / "build-agreement-hash-bound.json").read_text()))
        self.assertEqual(outcome["stopped"], "no candidate qualifies")
        counts = {build: [outcome["qualification"][build][name]["failure_count"] for name in repair.CANDIDATES]
                  for build in ("B1", "B3")}
        self.assertEqual(counts, {"B1": [126, 112, 112, 26], "B3": [125, 111, 111, 26]})


class PreflightCoverageTests(unittest.TestCase):
    """Codex R55-2: pointer cardinality, matching and estimator conversions."""

    def test_revalidation_passes_and_labels_its_record_sources(self) -> None:
        result = repair.p0_revalidation()
        self.assertTrue(result["passed"], [item["consumer"] for item in result["consumers"] if not item["passed"]])
        self.assertEqual(len(result["committed_record_consumers"]), 3)
        self.assertEqual(len(result["synthetic_record_consumers"]), 5)

    def test_strict_resolution_detects_a_missing_row(self) -> None:
        values, missing = repair.resolve_strict({"rows": [{"value": 1}, {}]}, "/rows/*/value")
        self.assertEqual((values, missing), ([1], 1))
        self.assertEqual(repair.resolve_strict({"rows": []}, "/rows/*/value"), ([], 1))
        self.assertEqual(repair.expand_pointer("/a/{x,y}/b/{p,q}"), ["/a/x/b/p", "/a/x/b/q", "/a/y/b/p", "/a/y/b/q"])

    def test_a_wrong_estimator_pointer_fails_revalidation(self) -> None:
        import copy
        from unittest.mock import patch

        table = copy.deepcopy(repair.load_table())
        table["consumers"][0]["estimators"][0]["pointer"] = "/results/*/DOES_NOT_EXIST"
        with patch.object(repair, "load_table", return_value=table):
            result = repair.p0_revalidation()
        self.assertFalse(result["passed"])
        self.assertFalse(result["consumers"][0]["checks"]["table_pointers_strict"]["passed"])

    def test_extractors_reject_missing_duplicate_and_inconsistent_records(self) -> None:
        import copy
        import json

        table = {item["id"]: item for item in repair.load_table()["consumers"]}
        _, rocha = repair.records_for(table["gubser-rocha-emd"])
        broken = copy.deepcopy(rocha)
        del broken["default"]["results"]["cases"][1]["thermodynamics"]["hat_s"]
        with self.assertRaises(repair.ExtractionError):
            repair.extract_gubser_rocha(broken)
        broken = copy.deepcopy(rocha)
        broken["default"]["results"]["cases"][1]["xi"] = broken["default"]["results"]["cases"][0]["xi"]
        with self.assertRaises(repair.ExtractionError):
            repair.extract_gubser_rocha(broken)
        _, chiral = repair.records_for(table["hard-wall-chiral"])
        broken = copy.deepcopy(chiral)
        broken["default"]["results"]["refinement"]["m_rho_MeV"]["N80_to_N96"] *= 3.0
        with self.assertRaises(repair.ExtractionError):
            repair.extract_hard_wall_chiral(broken)
        _, soft = repair.records_for(table["soft-wall-vector"])
        broken = copy.deepcopy(soft)
        broken["spectral-64"]["results"][0]["relative_error"] *= 2.0
        with self.assertRaises(repair.ExtractionError):
            repair.extract_soft_wall(broken)
        self.assertIsInstance(json.dumps(sorted(repair.extract_soft_wall(soft)["leaves"])), str)

    def test_estimator_conversions_on_synthetic_records(self) -> None:
        table = {item["id"]: item for item in repair.load_table()["consumers"]}
        _, rocha = repair.records_for(table["gubser-rocha-emd"])
        leaf = repair.extract_gubser_rocha(rocha)["leaves"]["xi=1.0|hat_s"]
        self.assertAlmostEqual(leaf["estimators"]["refinement"], 4.0e-11 * max(1.0, abs(leaf["value"])), delta=1e-24)
        self.assertAlmostEqual(leaf["estimators"]["closed_form"], 2.0e-11, delta=1e-15)
        _, hard = repair.records_for(table["hard-wall-vector"])
        leaves = repair.extract_hard_wall_vector(hard)["leaves"]
        self.assertAlmostEqual(leaves["spectral|m|n=2"]["estimators"]["refinement"], 4.0e-12 * leaves["spectral|m|n=2"]["value"])
        self.assertAlmostEqual(leaves["spectral|ratio|n=2"]["estimators"]["refinement"],
                               2 * 4.0e-12 * leaves["spectral|ratio|n=2"]["value"])
        self.assertNotIn("spectral|ratio|n=1", leaves)
        _, optical = repair.records_for(table["holographic-superconductor-optical"])
        extracted = repair.extract_optical(optical)
        leaf = extracted["leaves"]["figure_2|omega=60.0|spectral_conductivity"]
        self.assertAlmostEqual(leaf["estimators"]["background_cutoff"], 5.0e-9 * (1.0 + abs(leaf["value"])))
        self.assertIn("figure_2|omega=60.0|independent_conductivity", extracted["controls"])
        _, critical = repair.records_for(table["dewolfe-gubser-rosen-emd-finite-density"])
        leaves = repair.extract_dgr_critical(critical)["leaves"]
        self.assertAlmostEqual(leaves["state|degree=150|primary|entropy_BH"]["estimators"]["refinement"], 1.0e-9, delta=1e-12)
        self.assertEqual(set(leaves["control|charged|primary|mu_BH"]["estimators"]), {"route_difference"})


class ProposedAmendmentTests(unittest.TestCase):
    """Proposed amendment 1 (not adopted): bound validity and adverse controls."""

    degree, lower, upper = 21, 1.0e-3, 1.0

    def _metrics(self, damaged=None):
        matrices = {name: repair.construct(name, self.degree, self.lower, self.upper) for name in repair.CONSTRUCTIONS}
        if damaged is not None:
            matrices["C-S1"] = damaged(*matrices["C-S1"])
        return repair.grid_metrics(self.degree, self.lower, self.upper, repair.CONSTRUCTIONS, matrices)

    def _qualifies(self, metrics):
        return repair.qualification_v2({"grids": {"test": metrics}})["C-S1"]

    def test_bound_holds_for_the_stored_node_candidate_off_the_s0_grid(self) -> None:
        self.assertNotIn(self.degree, repair.DEGREES)
        metrics = self._metrics()
        self.assertLess(max(metrics["C-S1"]["bound_ratio"].values()), 1.0)
        self.assertNotIn("bound_ratio", metrics["current"])
        self.assertTrue(self._qualifies(metrics)["qualified"])

    def test_a_single_damaged_entry_is_rejected(self) -> None:
        def damage(nodes, first, second):
            first = first.copy()
            first[1, 2] *= 1.0 + 1.0e-11
            return nodes, first, second

        report = self._qualifies(self._metrics(damage))
        self.assertFalse(report["qualified"])
        self.assertTrue(any(item["metric"].startswith("b:D1") and item["bound_ratio"] > 1.0 for item in report["failures"]))

    def test_entries_perturbed_beyond_rounding_are_rejected(self) -> None:
        def damage(nodes, first, second):
            rng = np.random.default_rng(3)
            size = nodes.size
            off = ~np.eye(size, dtype=bool)
            first = np.where(off, first * (1.0 + 1.0e-12 * rng.standard_normal((size, size))), 0.0)
            first[np.arange(size), np.arange(size)] = -repair.compensated_row_sum(first)
            return nodes, first, second

        self.assertFalse(self._qualifies(self._metrics(damage))["qualified"])

    def test_a_matrix_for_shifted_nodes_is_rejected(self) -> None:
        def damage(nodes, first, second):
            shifted = nodes.copy()
            shifted[1:-1] *= 1.0 + 1.0e-10
            _, wrong_first, wrong_second = _matrices_for(shifted)
            return nodes, wrong_first, wrong_second

        def _matrices_for(nodes):
            differences = nodes[:, None] - nodes[None, :]
            rows = np.arange(nodes.size)
            first, diagonal, safe = repair._first_from_differences(differences, repair._stored_node_weights(differences), rows)
            second = repair._explicit_second(first, diagonal, safe, rows)
            first[rows, rows] = diagonal
            return nodes, first, second

        report = self._qualifies(self._metrics(damage))
        self.assertFalse(report["qualified"])
        self.assertTrue(any(item["metric"].startswith("a:") for item in report["failures"]))

    def test_a_damaged_second_derivative_is_rejected(self) -> None:
        def damage(nodes, first, second):
            second = second.copy()
            second[2, 3] *= 1.0 + 1.0e-10
            return nodes, first, second

        report = self._qualifies(self._metrics(damage))
        self.assertFalse(report["qualified"])
        self.assertTrue(any("D2" in item["metric"] for item in report["failures"]))

    def test_the_amendment_does_not_relax_the_entrywise_or_exactness_rules(self) -> None:
        payload = synthetic_payload("B1", candidate_value=3.0e-15, current_value=1.0e-15, bound_ratio=0.5)
        report = repair.qualification_v2(payload["result"])["C-S1"]
        self.assertFalse(report["qualified"])
        self.assertTrue(all(item["metric"].startswith("a:") for item in report["failures"]))
        self.assertGreater(report["excused_within_bound"], 0)
        payload = synthetic_payload("B1", candidate_value=1.0e-15, exactness=1.0e-9, bound_ratio=0.5)
        self.assertFalse(repair.qualification_v2(payload["result"])["C-S1"]["qualified"])
        payload = synthetic_payload("B1", candidate_value=3.0e-15, current_value=1.0e-15, bound_ratio=1.5)
        failures = repair.qualification_v2(payload["result"])["C-S1"]["failures"]
        self.assertTrue(any(item["metric"].startswith("b:") for item in failures))
        payload = synthetic_payload("B1", candidate_value=3.0e-15, current_value=1.0e-15)
        failures = repair.qualification_v2(payload["result"])["C-S1"]["failures"]
        self.assertTrue(any(item["metric"].startswith("b:") for item in failures))


class CorrectedBoundTests(unittest.TestCase):
    """Re-review R55-F1: subtraction errors entering the weight products.

    The exact values use ``fractions.Fraction`` on the stored nodes and are
    independent of the tool's 50-digit reference.
    """

    degree, lower, upper = 30, 1.0e-3, 1.0

    @classmethod
    def setUpClass(cls) -> None:
        from fractions import Fraction

        cls.nodes, cls.first, cls.second = repair.construct("C-S1", cls.degree, cls.lower, cls.upper)
        cls.exact_nodes = [Fraction(float(value)) for value in cls.nodes]
        cls.size = cls.nodes.size
        cls.products = []
        for i, x in enumerate(cls.exact_nodes):
            product = Fraction(1)
            for k, y in enumerate(cls.exact_nodes):
                if k != i:
                    product *= x - y
            cls.products.append(product)
        cls.unit = Fraction(1, 2 ** 53)
        cls.entry_bound, cls.relative = repair.stored_node_entry_errors(cls.nodes)

    def _exact_entry(self, i, j):
        return self.products[i] / self.products[j] / (self.exact_nodes[i] - self.exact_nodes[j])

    def _reference(self):
        from decimal import Decimal, localcontext

        with localcontext() as context:
            context.prec = repair.DIGITS
            return repair.Reference([Decimal(float(value)) for value in self.nodes])

    def test_the_review_counterexample_refutes_a_uniform_constant_and_is_inside_the_bound(self) -> None:
        from fractions import Fraction

        i, j = 7, 8
        exact = self._exact_entry(i, j)
        error = abs(Fraction(float(self.first[i, j])) - exact) / abs(exact)
        units = float(error / self.unit)
        self.assertGreater(units, 5.0)  # the withdrawn k = 5 entry model
        self.assertAlmostEqual(units, 14.172087803131994, places=6)
        self.assertLessEqual(units, self.entry_bound[i, j] / repair.UNIT_ROUNDOFF)
        vector = np.zeros(self.size)
        vector[j] = 1.0
        reference = self._reference()
        bound, _ = repair.apriori_action_bounds(reference, self.nodes, vector, self.entry_bound, self.relative)
        action = abs((reference.error(0, self.first) @ vector)[i])
        self.assertLessEqual(action, bound[i])
        self.assertAlmostEqual(action, float(error * abs(exact)), delta=1.0e-20)

    def test_input_product_error_accounting_matches_exact_arithmetic(self) -> None:
        from fractions import Fraction

        exact_nodes, size, unit = self.exact_nodes, self.size, self.unit
        delta = [[Fraction(0)] * size for _ in range(size)]
        for i in range(size):
            for k in range(size):
                if i != k:
                    true = exact_nodes[i] - exact_nodes[k]
                    delta[i][k] = (Fraction(float(self.nodes[i] - self.nodes[k])) - true) / true
                    self.assertLessEqual(abs(delta[i][k]), unit)
                    self.assertAlmostEqual(float(abs(delta[i][k])), self.relative[i, k], delta=1.0e-24)
        rows = [sum(delta[i]) for i in range(size)]
        worst_rounding = worst_input = worst_total = Fraction(0)
        for i in range(size):
            for j in range(size):
                if i == j:
                    continue
                exact = self._exact_entry(i, j)
                error = (Fraction(float(self.first[i, j])) - exact) / exact
                # P_i / P_j carries sum_k delta_ik - sum_k delta_jk, in which
                # delta_ij cancels; the final division by d_ij removes it once more.
                predicted = (rows[i] - delta[i][j]) - (rows[j] - delta[j][i]) - delta[i][j]
                worst_rounding = max(worst_rounding, abs(error - predicted))
                worst_input = max(worst_input, abs(predicted))
                worst_total = max(worst_total, abs(error))
                self.assertLessEqual(float(abs(error)), self.entry_bound[i, j] * (1.0 + 1.0e-9))
        # What is left after the input errors is the four rounded operations.
        self.assertLessEqual(float(worst_rounding / unit), repair.STORED_ENTRY_ROUNDINGS * (1.0 + 1.0e-9))
        # The input errors are a first-order term and exceed the withdrawn constant.
        self.assertGreater(float(worst_input / unit), 5.0)
        self.assertGreater(float(worst_total / unit), 5.0)
        self.assertLessEqual(self.entry_bound.max(), (2 * self.degree + 3) * repair.UNIT_ROUNDOFF)

    def test_every_entry_of_both_matrices_is_inside_the_bound(self) -> None:
        reference = self._reference()
        errors = [np.abs(reference.error(0, self.first)), np.abs(reference.error(1, self.second))]
        worst = [0.0, 0.0]
        for j in range(self.size):
            vector = np.zeros(self.size)
            vector[j] = 1.0
            bounds = repair.apriori_action_bounds(reference, self.nodes, vector, self.entry_bound, self.relative)
            for order in (0, 1):
                self.assertTrue(np.all(bounds[order] > 0.0))
                worst[order] = max(worst[order], float(np.max(errors[order][:, j] / bounds[order])))
        self.assertLessEqual(worst[0], 1.0)
        self.assertLessEqual(worst[1], 1.0)

    def test_closed_form_weight_candidates_keep_a_uniform_model(self) -> None:
        entry, difference = repair.entry_error_model("C-T2", self.nodes)
        off = ~np.eye(self.size, dtype=bool)
        self.assertTrue(np.all(entry[off] == repair.TRIG_ENTRY_ERROR_UNITS * repair.UNIT_ROUNDOFF))
        self.assertTrue(np.all(difference[off] == repair.TRIG_DIFFERENCE_ERROR_UNITS * repair.UNIT_ROUNDOFF))
        with self.assertRaises(ValueError):
            repair.entry_error_model("current", self.nodes)


class DuplicateSourceRowTests(unittest.TestCase):
    """Re-review R55-F2: duplicate source rows are rejected before mapping."""

    SITES = (
        ("hard-wall-chiral", ("default", "results", "table")),
        ("hard-wall-chiral", ("default", "results", "levels")),
        ("gubser-rocha-emd", ("default", "results", "refinement", "cases")),
        ("gubser-rocha-emd", ("default", "results", "cases")),
        ("hard-wall-vector", ("shooting", "results")),
        ("hard-wall-vector", ("spectral", "results")),
        ("dewolfe-gubser-rosen-emd-finite-density", ("default", "results", "refinement", "states")),
        ("dewolfe-gubser-rosen-emd-finite-density", ("default", "results", "refinement", "changes")),
        ("dewolfe-gubser-rosen-emd-finite-density", ("default", "results", "controls")),
    )

    @staticmethod
    def _scaled(node, factor):
        if isinstance(node, dict):
            return {key: (value if key in ("xi", "n", "degree", "fine_degree", "coarse_degree", "label", "observable")
                          else DuplicateSourceRowTests._scaled(value, factor)) for key, value in node.items()}
        if isinstance(node, list):
            return [DuplicateSourceRowTests._scaled(value, factor) for value in node]
        if isinstance(node, float):
            return node * factor
        return node

    def test_exact_and_conflicting_duplicates_are_rejected_at_every_mapping_site(self) -> None:
        import copy

        table = {item["id"]: item for item in repair.load_table()["consumers"]}
        for consumer, path in self.SITES:
            _, records = repair.records_for(table[consumer])
            repair.EXTRACTORS[consumer](records)
            for factor in (1.0, 2.0):
                with self.subTest(consumer=consumer, path=path, factor=factor):
                    changed = copy.deepcopy(records)
                    rows = changed
                    for key in path:
                        rows = rows[key]
                    rows.append(self._scaled(copy.deepcopy(rows[0]), factor))
                    with self.assertRaisesRegex(repair.ExtractionError, "duplicate"):
                        repair.EXTRACTORS[consumer](changed)

    def test_the_two_review_reproductions_are_rejected(self) -> None:
        import copy

        table = {item["id"]: item for item in repair.load_table()["consumers"]}
        _, chiral = repair.records_for(table["hard-wall-chiral"])
        changed = copy.deepcopy(chiral)
        row = copy.deepcopy(changed["default"]["results"]["table"][0])
        row["computed"] *= 2.0
        changed["default"]["results"]["table"].append(row)
        with self.assertRaisesRegex(repair.ExtractionError, "duplicate table row"):
            repair.extract_hard_wall_chiral(changed)
        _, rocha = repair.records_for(table["gubser-rocha-emd"])
        changed = copy.deepcopy(rocha)
        row = copy.deepcopy(changed["default"]["results"]["refinement"]["cases"][0])
        for item in row["observables"].values():
            item["middle_to_fine"] *= 1.0e6
        changed["default"]["results"]["refinement"]["cases"].append(row)
        with self.assertRaisesRegex(repair.ExtractionError, "duplicate refinement case row"):
            repair.extract_gubser_rocha(changed)

    def test_a_mapping_in_place_of_rows_is_rejected(self) -> None:
        with self.assertRaises(repair.ExtractionError):
            repair._unique_rows({"a": 1}, lambda row: row, "table")


class ArtifactBindingTests(unittest.TestCase):
    """Re-review R55-F3: saved and local matrices are bound to the S0 hashes."""

    grid, file_name = "64|0.0|1.0", "B3-C-T1-64-0.0-1.0.npz"

    def setUp(self) -> None:
        import tempfile

        self.local = repair.construct("C-T1", 64, 0.0, 1.0)
        other_second = self.local[2].copy()
        other_second[1, 2] *= 1.0 + 1.0e-12
        self.other = (self.local[0], self.local[1], other_second)
        self.payloads = synthetic_pair()
        self.payloads[0]["result"]["grids"][self.grid]["C-T1"]["sha256"] = repair._matrix_hashes(*self.local)
        self.payloads[1]["result"]["grids"][self.grid]["C-T1"]["sha256"] = repair._matrix_hashes(*self.other)
        self._directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._directory.cleanup)
        self.arrays = Path(self._directory.name)

    def _save(self, **arrays) -> None:
        np.savez(self.arrays / self.file_name, **arrays)

    def _run(self):
        return repair.build_agreement(self.arrays, "B3", self.payloads)

    def test_matching_matrices_are_admitted_and_marked_verified(self) -> None:
        self._save(nodes=self.other[0], D1=self.other[1], D2=self.other[2])
        result = self._run()
        self.assertNotIn("stopped", result)
        self.assertEqual(result["verified"], {"other_label": "B3", "local_label": "B1", "files": 1,
                                              "saved_bytes_match_s0_hashes": True,
                                              "local_matrices_match_s0_hashes": True})
        self.assertGreater(result["C-T1"]["max_relative_difference"], 0.0)
        envelope = {"stage": "build-agreement", "status": "ok", "result": result}
        results = [item["result"] for item in self.payloads]
        self.assertEqual(repair.validate_agreement(envelope, results), [])
        unverified = {"stage": "build-agreement", "status": "ok",
                      "result": {key: value for key, value in result.items() if key != "verified"}}
        self.assertIn("not verified", " ".join(repair.validate_agreement(unverified, results)))

    def test_a_correctly_named_file_with_other_bytes_stops(self) -> None:
        damaged = self.other[2].copy()
        damaged[3, 4] *= 1.0 + 1.0e-12
        self._save(nodes=self.other[0], D1=self.other[1], D2=damaged)
        result = self._run()
        self.assertIn("saved bytes do not match the B3 S0 hashes", result["stopped"])
        self.assertNotIn("C-T1", result)

    def test_the_review_reproduction_stops(self) -> None:
        self.payloads[1]["result"]["grids"][self.grid]["C-T1"]["sha256"]["D2"] = "c" * 64
        self._save(nodes=self.other[0], D1=self.other[1], D2=self.other[2])
        result = self._run()
        self.assertIn("saved bytes do not match", result["stopped"])
        self.assertFalse(result["passed"])

    def test_a_local_matrix_that_is_not_the_recorded_one_stops(self) -> None:
        self.payloads[0]["result"]["grids"][self.grid]["C-T1"]["sha256"]["D1"] = "d" * 64
        self._save(nodes=self.other[0], D1=self.other[1], D2=self.other[2])
        result = self._run()
        self.assertIn("local matrices do not match the B1 S0 hashes", result["stopped"])
        self.assertNotIn("C-T1", result)

    def test_missing_arrays_wrong_types_shapes_and_non_finite_values_stop(self) -> None:
        nodes, first, second = self.other
        bad_second = second.copy()
        bad_second[0, 0] = np.nan
        cases = ({"nodes": nodes, "D1": first},
                 {"nodes": nodes, "D1": first, "D2": second.astype(np.float32)},
                 {"nodes": nodes, "D1": first, "D2": second[:-1]},
                 {"nodes": nodes, "D1": first, "D2": bad_second})
        for arrays in cases:
            with self.subTest(keys=sorted(arrays), dtype=str(arrays.get("D2", first).dtype)):
                self._save(**arrays)
                result = self._run()
                self.assertIn("stopped", result)
                self.assertIn(self.file_name, result["stopped"])

    def test_an_unknown_other_build_stops(self) -> None:
        self._save(nodes=self.other[0], D1=self.other[1], D2=self.other[2])
        result = repair.build_agreement(self.arrays, "B2", self.payloads)
        self.assertIn("is not one of", result["stopped"])


if __name__ == "__main__":
    unittest.main()
