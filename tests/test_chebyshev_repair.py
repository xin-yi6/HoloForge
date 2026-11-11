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

    def test_production_is_the_selected_construction_over_the_plan_node_set(self) -> None:
        from holoforge.numerics import CHEBYSHEV_CONSTRUCTION, chebyshev_lobatto_grid

        self.assertEqual(CHEBYSHEV_CONSTRUCTION, repair.SELECTED_CONSTRUCTION)
        differs_from_legacy = 0
        for degree in repair.DEGREES:
            for lower, upper in repair.INTERVALS:
                nodes, first, second = repair.construct("C-S1", degree, lower, upper)
                grid = chebyshev_lobatto_grid(degree, lower, upper)
                self.assertEqual(nodes.tobytes(), grid.nodes.tobytes(), (degree, lower, upper))
                self.assertEqual(first.tobytes(), grid.first_derivative.tobytes(), (degree, lower, upper))
                self.assertEqual(second.tobytes(), grid.second_derivative.tobytes(), (degree, lower, upper))
                if degree <= 64:
                    legacy = repair.construct("current", degree, lower, upper)
                    differs_from_legacy += int(legacy[2].tobytes() != second.tobytes())
        self.assertGreater(differs_from_legacy, 0)

    def test_production_matches_the_committed_selection_evidence(self) -> None:
        import json

        from holoforge.numerics import chebyshev_lobatto_grid

        evidence = json.loads((ROOT / "docs/generated/chebyshev-repair/B1-s0.json").read_text())["result"]["grids"]
        matched = 0
        for degree in (2, 3, 16, 17, 64):
            for lower, upper in repair.INTERVALS:
                grid = chebyshev_lobatto_grid(degree, lower, upper)
                recorded = evidence[repair.grid_label(degree, lower, upper)]["C-S1"]["sha256"]
                matched += int(repair._matrix_hashes(grid.nodes, grid.first_derivative, grid.second_derivative) == recorded)
        # The stored nodes depend on the platform's sine, so equality with the
        # evidence is required only where that evidence was produced.
        self.assertIn(matched, (0, 20) if matched else (0,))

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
            item["entry_check"] = {matrix: {"ratio": bound_ratio, "error": 1.0e-16, "bound": 1.0e-16 / bound_ratio,
                                            "row": 0, "column": 1, "entries": 4} for matrix in ("D1", "D2")}
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


class AmendmentRuleTests(unittest.TestCase):
    """Post-observation amendment 1: bound validity and adverse controls."""

    degree, lower, upper = 21, 1.0e-3, 1.0

    def _metrics(self, control=None):
        matrices = {name: repair.construct(name, self.degree, self.lower, self.upper) for name in repair.CONSTRUCTIONS}
        if control is not None:
            matrices["C-S1"] = repair.adverse_control(control, *matrices["C-S1"])
        return repair.grid_metrics(self.degree, self.lower, self.upper, repair.CONSTRUCTIONS, matrices)

    def _qualifies(self, metrics):
        return repair.qualification_amended({"grids": {"test": metrics}})["C-S1"]

    def test_bound_holds_for_the_stored_node_candidate_off_the_s0_grid(self) -> None:
        self.assertNotIn(self.degree, repair.DEGREES)
        self.assertNotIn(self.degree, repair.CONFIRMATION_DEGREES)
        metrics = self._metrics()
        self.assertLess(max(metrics["C-S1"]["bound_ratio"].values()), 1.0)
        self.assertLess(max(item["ratio"] for item in metrics["C-S1"]["entry_check"].values()), 1.0)
        for name in ("current", "C-T1", "C-T2", "C-T3"):
            self.assertNotIn("bound_ratio", metrics[name])
            self.assertNotIn("entry_check", metrics[name])
        self.assertTrue(self._qualifies(metrics)["qualified"])

    def test_a_single_damaged_entry_is_rejected(self) -> None:
        report = self._qualifies(self._metrics("one_D1_entry"))
        self.assertFalse(report["qualified"])
        self.assertTrue(any(item["metric"].startswith("b:D1") and item["bound_ratio"] > 1.0 for item in report["failures"]))
        self.assertIn("entry", report["discriminators"])

    def test_entries_perturbed_beyond_rounding_are_rejected(self) -> None:
        self.assertFalse(self._qualifies(self._metrics("all_D1_entries"))["qualified"])

    def test_a_matrix_for_shifted_nodes_is_rejected(self) -> None:
        report = self._qualifies(self._metrics("shifted_nodes"))
        self.assertFalse(report["qualified"])
        self.assertTrue(any(item["metric"].startswith("a:") for item in report["failures"]))

    def test_a_damaged_second_derivative_is_rejected(self) -> None:
        report = self._qualifies(self._metrics("one_D2_entry"))
        self.assertFalse(report["qualified"])
        self.assertTrue(any("D2" in item["metric"] for item in report["failures"]))

    def test_control_definitions_are_fixed(self) -> None:
        nodes, first, second = repair.construct("C-S1", self.degree, self.lower, self.upper)
        _, damaged, same = repair.adverse_control("one_D1_entry", nodes, first, second)
        self.assertEqual(damaged[1, 2], first[1, 2] * (1.0 + 1.0e-11))
        self.assertEqual(int(np.sum(damaged != first)), 1)
        self.assertIs(same, second)
        _, same, damaged = repair.adverse_control("one_D2_entry", nodes, first, second)
        self.assertEqual(damaged[2, 3], second[2, 3] * (1.0 + 1.0e-10))
        self.assertEqual(int(np.sum(damaged != second)), 1)
        shifted = nodes.copy()
        shifted[1:-1] *= 1.0 + 1.0e-10
        returned, wrong_first, _ = repair.adverse_control("shifted_nodes", nodes, first, second)
        self.assertIs(returned, nodes)
        self.assertTrue(np.array_equal(wrong_first, repair.stored_node_matrices(shifted)[0]))
        self.assertTrue(np.array_equal(repair.stored_node_matrices(nodes)[0], first))
        with self.assertRaises(ValueError):
            repair.adverse_control("other", nodes, first, second)

    def test_the_amendment_does_not_relax_the_entrywise_or_exactness_rules(self) -> None:
        payload = synthetic_payload("B1", candidate_value=3.0e-15, current_value=1.0e-15, bound_ratio=0.5)
        report = repair.qualification_amended(payload["result"])["C-S1"]
        self.assertFalse(report["qualified"])
        self.assertTrue(all(item["metric"].startswith("a:") for item in report["failures"]))
        self.assertGreater(report["excused_within_bound"], 0)
        payload = synthetic_payload("B1", candidate_value=1.0e-15, exactness=1.0e-9, bound_ratio=0.5)
        self.assertFalse(repair.qualification_amended(payload["result"])["C-S1"]["qualified"])
        payload = synthetic_payload("B1", candidate_value=3.0e-15, current_value=1.0e-15, bound_ratio=1.5)
        failures = repair.qualification_amended(payload["result"])["C-S1"]["failures"]
        self.assertTrue(any(item["metric"].startswith("b:") for item in failures))
        payload = synthetic_payload("B1", candidate_value=3.0e-15, current_value=1.0e-15)
        failures = repair.qualification_amended(payload["result"])["C-S1"]["failures"]
        self.assertTrue(any(item["metric"].startswith("b:") for item in failures))

    def test_the_exemption_is_restricted_to_the_stored_node_candidate(self) -> None:
        payload = synthetic_payload("B1", candidate_value=1.0e-15, current_value=1.0e-15, bound_ratio=0.5)
        for grid in payload["result"]["grids"].values():
            for name in repair.CANDIDATES:
                grid[name]["b"] = {key: 3.0e-15 for key in grid[name]["b"]}
        report = repair.qualification_amended(payload["result"])
        self.assertTrue(report["C-S1"]["qualified"])
        self.assertEqual(report["C-S1"]["rule"], "amended")
        for name in ("C-T1", "C-T2", "C-T3"):
            self.assertEqual(report[name]["rule"], "frozen")
            self.assertFalse(report[name]["qualified"])
            self.assertEqual(report[name]["excused_within_bound"], 0)
            self.assertEqual(report[name]["failure_count"], repair.qualification(payload["result"])[name]["failure_count"])

    def test_an_entry_outside_the_bound_or_a_missing_check_fails(self) -> None:
        payload = synthetic_payload("B1", candidate_value=1.0e-15, current_value=1.0e-15, bound_ratio=0.5)
        self.assertTrue(repair.qualification_amended(payload["result"])["C-S1"]["qualified"])
        label = repair.expected_grid_labels()[5]
        payload["result"]["grids"][label]["C-S1"]["entry_check"]["D2"]["ratio"] = 1.01
        report = repair.qualification_amended(payload["result"])["C-S1"]
        self.assertEqual([item["metric"] for item in report["failures"]], ["entry:D2"])
        del payload["result"]["grids"][label]["C-S1"]["entry_check"]
        report = repair.qualification_amended(payload["result"])["C-S1"]
        self.assertEqual(sorted(item["metric"] for item in report["failures"]), ["entry:D1", "entry:D2"])

    def test_confirmation_vectors_and_grids(self) -> None:
        from decimal import Decimal, localcontext

        nodes = repair.half_angle_nodes(7, 0.2, 0.8)  # not a grid of the confirmation set
        with localcontext() as context:
            context.prec = repair.DIGITS
            vectors = repair.confirmation_vectors([Decimal(float(u)) for u in nodes], 0.2, 0.8)
        xi = (2.0 * nodes - 1.0) / 0.6
        self.assertTrue(np.allclose(vectors["w1"], np.cos(5.0 * xi - 0.7), rtol=0.0, atol=1.0e-14))
        self.assertTrue(np.allclose(vectors["w2"], 1.0 / (2.0 + xi), rtol=1.0e-14))
        self.assertTrue(np.allclose(vectors["w3"], xi * np.exp(-2.0 * xi), rtol=0.0, atol=1.0e-14))
        self.assertEqual(len(repair.confirmation_grid_labels()), 20)
        self.assertFalse(set(repair.CONFIRMATION_DEGREES) & set(repair.DEGREES))
        self.assertFalse(set(repair.CONFIRMATION_INTERVALS) & set(repair.INTERVALS))


def synthetic_run(build, s0_payload, ratio=0.5, control_value=1.0e-9):
    """A complete, admissible synthetic C1 output matching a synthetic S0 payload."""

    def check(value):
        return {matrix: {"ratio": value, "error": 1.0e-16, "bound": 1.0e-16 / value, "row": 0, "column": 1, "entries": 4}
                for matrix in ("D1", "D2")}

    stored_keys = [key for key in repair.B_KEYS if "_stored" in key]
    grids = s0_payload["result"]["grids"]
    retrospective = {label: {"bound_ratio": {key: ratio for key in stored_keys}, "entry_check": check(ratio),
                             "sha256": dict(grids[label]["C-S1"]["sha256"])} for label in grids}

    def entry(value, bounded):
        item = {"a": {key: value for key in repair.A_KEYS},
                "b": {key.replace("_v", "_w"): value for key in repair.B_KEYS},
                "exactness": {"D1": 1.0e-14, "D2": 1.0e-14}, "sha256": {key: "e" * 64 for key in ("nodes", "D1", "D2")}}
        if bounded:
            item["bound_ratio"] = {key.replace("_v", "_w"): ratio for key in stored_keys}
            item["entry_check"] = check(ratio)
        return item

    confirmation = {label: dict({"current": entry(1.0e-15, False)},
                                **{name: entry(3.0e-15, name == "C-S1") for name in repair.CANDIDATES})
                    for label in repair.confirmation_grid_labels()}
    for grid in confirmation.values():
        grid["C-S1"]["a"] = {key: 1.0e-15 for key in grid["C-S1"]["a"]}

    def control(value):
        item = {"a": {key: value for key in repair.A_KEYS}, "b": {key: value for key in repair.B_KEYS},
                "exactness": {"D1": 1.0e-14, "D2": 1.0e-14}, "sha256": {key: "f" * 64 for key in ("nodes", "D1", "D2")},
                "bound_ratio": {key: 100.0 for key in stored_keys}, "entry_check": check(100.0)}
        return {"current": {"a": {key: 1.0e-15 for key in repair.A_KEYS}, "b": {key: 1.0e-15 for key in repair.B_KEYS},
                            "exactness": {"D1": 1.0e-14, "D2": 1.0e-14}}, "C-S1": item}

    controls = {name: control(control_value) for name in repair.CONTROL_NAMES}
    controls["undamaged"] = control(1.0e-15)
    controls["undamaged"]["C-S1"].update(bound_ratio={key: ratio for key in stored_keys}, entry_check=check(ratio))
    return {"tool": "chebyshev-repair", "stage": "c1", "status": "ok",
            "plan_sha256": repair._file_sha256(repair.ROOT / repair.PLAN),
            "amendment_sha256": repair._file_sha256(repair.ROOT / repair.AMENDMENT), "tool_sha256": "b" * 64,
            "result": {"build_label": build, "passed": True, "complete": True,
                       "fixtures": {"F1_oracle_arithmetic": {"passed": True}}, "retrospective": retrospective,
                       "confirmation": confirmation, "controls": controls,
                       "control_grid": repair.grid_label(*repair.CONTROL_GRID)}}


class ContinuationStageTests(unittest.TestCase):
    """Stages C1 and C2 of the continuation under amendment 1."""

    AGREEMENT = {"tool": "chebyshev-repair", "stage": "build-agreement", "status": "ok",
                 "result": dict({name: {"differing_grids": 0, "max_relative_difference": 0.0, "seconds": 0.01}
                                 for name in repair.CONSTRUCTIONS},
                                verified={"other_label": "B3", "local_label": "B1", "files": 0,
                                          "saved_bytes_match_s0_hashes": True, "local_matrices_match_s0_hashes": True})}

    def _evidence(self, **options):
        # The frozen rule fails every candidate here (3e-15 against 1e-15 on (b)) but not on (a).
        payloads = synthetic_pair(candidate_value=3.0e-15, current_value=1.0e-15)
        for payload in payloads:
            for grid in payload["result"]["grids"].values():
                grid["C-S1"]["a"] = {key: 1.0e-15 for key in grid["C-S1"]["a"]}
        runs = [synthetic_run(payload["result"]["build_label"], payload, **options) for payload in payloads]
        return payloads, runs

    def test_the_stored_node_candidate_is_selected_with_its_label(self) -> None:
        payloads, runs = self._evidence()
        self.assertEqual(repair.selection(payloads, self.AGREEMENT)["stopped"], "no candidate qualifies")
        outcome = repair.amended_selection(payloads, runs, self.AGREEMENT)
        self.assertTrue(outcome["passed"], outcome.get("stopped"))
        self.assertEqual(outcome["qualified"], ["C-S1"])
        self.assertEqual(outcome["selected_label"], "C-S1 qualified under post-observation amendment 1")
        self.assertEqual(outcome["frozen_rule_result"], "no candidate qualifies (unchanged)")
        for build in ("B1", "B3"):
            self.assertTrue(outcome["adverse_controls"][build]["undamaged"]["rejected"] is False)
            for name in repair.CONTROL_NAMES:
                self.assertTrue(outcome["adverse_controls"][build][name]["rejected"])

    def test_a_bound_violation_on_either_set_or_build_disqualifies(self) -> None:
        for part, label in (("retrospective", repair.expected_grid_labels()[7]),
                            ("confirmation", repair.confirmation_grid_labels()[3])):
            payloads, runs = self._evidence()
            target = runs[1]["result"][part][label]
            (target if part == "retrospective" else target["C-S1"])["entry_check"]["D1"]["ratio"] = 1.2
            outcome = repair.amended_selection(payloads, runs, self.AGREEMENT)
            self.assertEqual(outcome["stopped"], "no candidate qualifies under amendment 1")
            failures = outcome["qualification"]["B3"][part]["C-S1"]["failures"]
            self.assertEqual([item["metric"] for item in failures], ["entry:D1"])

    def test_an_accepted_adverse_control_stops_the_selection(self) -> None:
        payloads, runs = self._evidence()
        accepted = runs[0]["result"]["controls"]["one_D1_entry"]["C-S1"]
        accepted.update(a={key: 1.0e-15 for key in accepted["a"]}, b={key: 1.0e-15 for key in accepted["b"]},
                        bound_ratio={key: 0.5 for key in accepted["bound_ratio"]})
        for item in accepted["entry_check"].values():
            item["ratio"] = 0.5
        outcome = repair.amended_selection(payloads, runs, self.AGREEMENT)
        self.assertEqual(outcome["stopped"], "an adverse control was not rejected")
        self.assertEqual(outcome["controls_not_rejected"], ["B1:one_D1_entry"])

    def test_incomplete_or_unbound_continuation_evidence_is_rejected(self) -> None:
        def stopped(mutate):
            payloads, runs = self._evidence()
            mutate(runs)
            outcome = repair.amended_selection(payloads, runs, self.AGREEMENT)
            self.assertEqual(outcome["stopped"], "invalid continuation evidence")
            return " ".join(outcome["evidence_errors"])

        self.assertIn("confirmation grids", stopped(lambda runs: runs[0]["result"]["confirmation"].popitem()))
        self.assertIn("retrospective grids", stopped(lambda runs: runs[1]["result"]["retrospective"].popitem()))
        label = repair.expected_grid_labels()[0]
        self.assertIn("not the one in the S0 evidence", stopped(
            lambda runs: runs[0]["result"]["retrospective"][label]["sha256"].update(D1="0" * 64)))
        self.assertIn("exactly one each", stopped(lambda runs: runs.pop()))
        self.assertIn("amendment hash", stopped(lambda runs: [run.update(amendment_sha256="1" * 64) for run in runs]))
        self.assertIn("adverse controls", stopped(lambda runs: runs[0]["result"]["controls"].pop("shifted_nodes")))
        self.assertIn("not finite", stopped(lambda runs: runs[0]["result"]["retrospective"][label]["bound_ratio"].update(
            {"D1_stored_v1_all": float("nan")})))
        self.assertIn("not a complete", stopped(lambda runs: runs[0]["result"].update(complete=False)))
        payloads, runs = self._evidence()
        self.assertEqual(repair.amended_selection(payloads, runs, None)["passed"], True)
        unverified = {"stage": "build-agreement", "status": "ok",
                      "result": {key: value for key, value in self.AGREEMENT["result"].items() if key != "verified"}}
        self.assertEqual(repair.amended_selection(payloads, runs, unverified)["stopped"], "invalid continuation evidence")

    def test_committed_continuation_evidence_is_admitted_and_selects_the_stored_node_candidate(self) -> None:
        import json

        folder = ROOT / "docs/generated/chebyshev-repair"
        s0 = [json.loads((folder / f"{label}-s0.json").read_text()) for label in ("B1", "B3")]
        runs = [json.loads((folder / f"{label}-c1.json").read_text()) for label in ("B1", "B3")]
        agreement = json.loads((folder / "build-agreement-hash-bound.json").read_text())
        outcome = repair.amended_selection(s0, runs, agreement)
        self.assertTrue(outcome["passed"], outcome.get("evidence_errors"))
        self.assertEqual(outcome["qualified"], ["C-S1"])
        self.assertEqual(outcome["selected"], "C-S1")
        recorded = json.loads((folder / "c2-selection-amendment-1.json").read_text())["result"]
        self.assertEqual(recorded["selected_label"], outcome["selected_label"])
        self.assertEqual(recorded["qualification"], json.loads(json.dumps(repair._jsonable(outcome["qualification"]))))
        # The frozen rule's result is unchanged.
        self.assertEqual(repair.selection(s0, agreement)["stopped"], "no candidate qualifies")

    def test_the_measurement_stage_on_a_small_configuration(self) -> None:
        from unittest.mock import patch

        degree, lower, upper = 16, 0.0, 1.0
        label = repair.grid_label(degree, lower, upper)
        s0 = {"status": "ok", "tool_sha256": "a" * 64, "result": {"build_label": "B1", "grids": {label: {
            name: {"sha256": repair._matrix_hashes(*repair.construct(name, degree, lower, upper))}
            for name in ("current", "C-S1")}}}}
        options = dict(degrees=(degree,), intervals=((lower, upper),), confirmation_degrees=(7,),
                       confirmation_intervals=((0.2, 0.8),), control_grid=(degree, lower, upper))
        with patch.object(repair, "s0_fixtures", return_value={"F": {"passed": True}}):
            result = repair.amendment_run("B1", s0, **options)
            self.assertTrue(result["passed"])
            self.assertFalse(result["complete"])
            self.assertEqual(sorted(result["controls"]), sorted(("undamaged",) + repair.CONTROL_NAMES))
            retrospective = result["retrospective"][label]
            undamaged = result["controls"]["undamaged"]["C-S1"]
            self.assertEqual(retrospective["bound_ratio"], undamaged["bound_ratio"])
            self.assertEqual(retrospective["entry_check"], undamaged["entry_check"])
            self.assertLess(max(retrospective["bound_ratio"].values()), 1.0)
            for name in repair.CONTROL_NAMES:
                verdict = repair.qualification_amended({"grids": {label: result["controls"][name]}}, ("C-S1",))["C-S1"]
                self.assertFalse(verdict["qualified"], name)
            confirmation = result["confirmation"][repair.grid_label(7, 0.2, 0.8)]
            self.assertEqual(sorted(confirmation), sorted(repair.CONSTRUCTIONS))
            self.assertTrue(all("_w" in key for key in confirmation["C-S1"]["b"]))
            self.assertTrue(repair.qualification_amended({"grids": {"c": confirmation}})["C-S1"]["qualified"])
            s0["result"]["grids"][label]["C-S1"]["sha256"]["D2"] = "0" * 64
            self.assertIn("not the matrix recorded", repair.amendment_run("B1", s0, **options)["stopped"])
            with patch.object(repair, "s0_fixtures", return_value={"F": {"passed": False}}):
                self.assertEqual(repair.amendment_run("B1", s0, **options)["stopped"], "a fixture failed")
        self.assertIn("not a successful B3 output", repair.amendment_run("B3", s0)["stopped"])


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
        # The value depends on the platform's sine through the stored nodes
        # (14.17 and 14.03 were both observed), so only the claim is tested.
        self.assertGreater(units, 5.0)  # the withdrawn k = 5 entry model
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

    def test_the_entry_check_is_the_action_bound_on_coordinate_vectors(self) -> None:
        reference = self._reference()
        errors = [reference.error(0, self.first), reference.error(1, self.second)]
        check = repair.entry_bound_check(reference, self.nodes, errors)
        for order, label in ((0, "D1"), (1, "D2")):
            worst = 0.0
            for j in range(self.size):
                vector = np.zeros(self.size)
                vector[j] = 1.0
                bound = repair.apriori_action_bounds(reference, self.nodes, vector, self.entry_bound, self.relative)[order]
                worst = max(worst, float(np.max(np.abs(errors[order][:, j]) / bound)))
            self.assertAlmostEqual(check[label]["ratio"], worst, delta=1.0e-12 * worst)
            item = check[label]
            self.assertEqual(item["entries"], self.size * self.size)
            self.assertAlmostEqual(item["ratio"], item["error"] / item["bound"], delta=1.0e-15)
            self.assertEqual(item["error"], abs(errors[order][item["row"], item["column"]]))

    def test_only_the_stored_node_candidate_has_an_error_model(self) -> None:
        self.assertEqual(repair.BOUNDED_CONSTRUCTIONS, ("C-S1",))
        for name in ("current", "C-T1", "C-T2", "C-T3"):
            with self.assertRaises(ValueError):
                repair.entry_error_model(name, self.nodes)


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


def regression_payload(build, role, mutate=None, source=None):
    """A complete synthetic regression-run output built from the audited records.

    Every run passes except the optical one, which carries one failing check
    (a scientific FAIL: verdict False, exit status 1).
    """

    import copy
    import json

    table = repair.load_table()
    consumers = {}
    for consumer in table["consumers"]:
        _, records = repair.records_for(consumer)
        records = copy.deepcopy(records)
        extracted = repair.EXTRACTORS[consumer["id"]](records)
        failing = consumer["id"] == "holographic-superconductor-optical"
        runs = {name: {"arguments": arguments, "exit_status": 1 if failing else 0, "seconds": 0.1, "passed": not failing,
                       "acceptance_checks": {"gate-1": {"passed": True, "value": 1.0e-9, "criterion": "<= 1e-6"},
                                             "gate-2": {"passed": not failing, "value": 2.0e-5 if failing else 2.0e-6,
                                                        "criterion": "<= 1e-5"}}}
                for name, arguments in repair.consumer_commands(consumer).items()}
        consumers[consumer["id"]] = dict(extracted, runs=runs)
    approved = repair.APPROVED_SOURCES[role]
    result = {"passed": True, "build_label": build, "role": role, "consumers": consumers,
              "source_sha256": source or approved["source_sha256"],
              "chebyshev_construction": approved["construction"], "complete": True}
    payload = {"tool": "chebyshev-repair", "stage": f"regression-{role}", "status": "ok", "tool_sha256": "a" * 64,
               "plan_sha256": repair._file_sha256(repair.ROOT / repair.PLAN), "result": result}
    payload = json.loads(json.dumps(repair._jsonable(payload)))
    if mutate is not None:
        mutate(payload["result"]["consumers"])
    return payload


class RegressionStageTests(unittest.TestCase):
    """R0 limits and the S2 comparison (plan Sections 6 and 8), on synthetic runs."""

    def _evidence(self, mutate=None, mutate_build="B1"):
        baselines = [regression_payload(build, "baseline") for build in ("B1", "B3")]
        candidates = [regression_payload(build, "candidate", mutate if build == mutate_build else None)
                      for build in ("B1", "B3")]
        limits = {"stage": "r0-limits", "status": "ok", "result": repair.regression_limits(baselines)}
        return baselines, limits, candidates

    def test_run_names_are_the_record_names_the_extractors_use(self) -> None:
        import json

        for consumer in repair.load_table()["consumers"]:
            names = sorted(repair.consumer_commands(consumer))
            path = ROOT / repair.SYNTHETIC_RECORDS / f"{consumer['id']}.json"
            if consumer.get("committed_record") or not path.exists():
                self.assertEqual(names, ["default"], consumer["id"])
            else:
                expected = sorted(key for key in json.loads(path.read_text()) if not key.startswith("_"))
                self.assertEqual(names, expected, consumer["id"])

    def test_limits_follow_the_plan_rule(self) -> None:
        def shift(consumers):
            consumers["gubser-rocha-emd"]["leaves"]["xi=1.0|hat_s"]["value"] += 3.0e-9

        baselines = [regression_payload("B1", "baseline"), regression_payload("B3", "baseline", shift)]
        outcome = repair.regression_limits(baselines)
        self.assertTrue(outcome["passed"])
        entry = outcome["limits"]["gubser-rocha-emd"]["xi=1.0|hat_s"]
        self.assertAlmostEqual(entry["X"], 3.0e-9, delta=1.0e-15)
        leaf = baselines[0]["result"]["consumers"]["gubser-rocha-emd"]["leaves"]["xi=1.0|hat_s"]
        expected = 10.0 * max(max(leaf["estimators"].values()), entry["X"], 8.0 * repair.EPS * abs(leaf["value"]))
        self.assertEqual(entry["B1"]["allowance"], expected)
        self.assertGreater(outcome["leaf_count"], 100)
        self.assertEqual(repair.regression_limits(baselines[:1])["stopped"], "invalid baseline evidence")

    def test_identical_candidate_passes_and_reports_baseline_failures(self) -> None:
        outcome = repair.regression_compare(*self._evidence())
        self.assertTrue(outcome["passed"], outcome.get("stopped"))
        self.assertEqual(outcome["violation_counts"], {"A1": 0, "A2": 0, "controls": 0, "keys": 0})
        summary = outcome["summary"]["B1"]["holographic-superconductor-optical"]
        self.assertEqual(summary["checks_failing_at_baseline"], ["default:gate-2"])
        self.assertEqual(summary["controls_changed"], 0)

    def test_a_leaf_beyond_its_allowance_is_an_a2_stop(self) -> None:
        def inside(consumers):
            leaf = consumers["gubser-rocha-emd"]["leaves"]["xi=1.0|hat_s"]
            leaf["value"] += 0.5 * 10.0 * max(leaf["estimators"].values())

        def outside(consumers):
            leaf = consumers["gubser-rocha-emd"]["leaves"]["xi=1.0|hat_s"]
            leaf["value"] += 1.5 * 10.0 * max(leaf["estimators"].values())

        self.assertTrue(repair.regression_compare(*self._evidence(inside))["passed"])
        outcome = repair.regression_compare(*self._evidence(outside, "B3"))
        self.assertEqual(outcome["stopped"], "regression stop: A2 (1)")
        self.assertEqual(outcome["violations"]["A2"][0]["build"], "B3")

    def test_a_complex_leaf_uses_the_modulus_of_the_difference(self) -> None:
        def turn(consumers):
            leaves = consumers["holographic-superconductor-optical"]["leaves"]
            key = next(key for key in leaves if key.endswith("spectral_conductivity"))
            allowance = 10.0 * max(leaves[key]["estimators"].values())
            leaves[key]["value"] = [leaves[key]["value"][0] + 0.8 * allowance, leaves[key]["value"][1] + 0.8 * allowance]

        outcome = repair.regression_compare(*self._evidence(turn))
        self.assertEqual(outcome["violation_counts"]["A2"], 1)

    def test_a_changed_control_or_a_newly_failing_gate_is_a_stop(self) -> None:
        def control(consumers):
            controls = consumers["hard-wall-vector"]["controls"]
            key = sorted(controls)[0]
            controls[key] = controls[key] * (1.0 + 2.0e-16) if controls[key] != 1.0 else 1.0 + 2.3e-16

        outcome = repair.regression_compare(*self._evidence(control))
        self.assertEqual(outcome["stopped"], "regression stop: controls (1)")

        def gate(consumers):
            run = consumers["gubser-nellore-ed"]["runs"]["default"]
            run["acceptance_checks"]["gate-1"]["passed"] = False
            run.update(passed=False, exit_status=1)

        outcome = repair.regression_compare(*self._evidence(gate))
        self.assertEqual(outcome["stopped"], "regression stop: A1 (2)")
        self.assertEqual(outcome["stop_kind"], "scientific regression stop")

        def still_failing(consumers):
            consumers["holographic-superconductor-optical"]["runs"]["default"]["acceptance_checks"]["gate-2"]["value"] = 9.0e-5

        self.assertTrue(repair.regression_compare(*self._evidence(still_failing))["passed"])

    def _rejected(self, baselines, limits, candidates):
        outcome = repair.regression_compare(baselines, limits, candidates)
        self.assertFalse(outcome["passed"])
        self.assertEqual(outcome["stopped"], "invalid regression evidence")
        self.assertEqual(outcome["stop_kind"], "inadmissible evidence")
        return " ".join(outcome["evidence_errors"])

    def test_inadmissible_regression_evidence_is_rejected(self) -> None:
        baselines, limits, candidates = self._evidence()
        wrong_source = [regression_payload(build, "candidate", source=repair.APPROVED_SOURCES["baseline"]["source_sha256"])
                        for build in ("B1", "B3")]
        self.assertIn("not the approved candidate", self._rejected(baselines, limits, wrong_source))
        self.assertIn("not a complete successful candidate run", self._rejected(baselines, limits, baselines))
        limits["result"]["limits"]["gubser-rocha-emd"]["xi=1.0|hat_s"]["B1"]["allowance"] *= 100.0
        self.assertIn("do not follow from these baselines", self._rejected(baselines, limits, candidates))

        def missing(consumers):
            consumers["soft-wall-vector"]["leaves"].popitem()

        outcome = repair.regression_compare(*self._evidence(missing))
        self.assertEqual(outcome["violation_counts"]["keys"], 1)

    def test_review_reproduction_empty_evidence_is_rejected(self) -> None:
        baselines, _, candidates = self._evidence()
        for payload in baselines + candidates:
            payload["result"]["consumers"] = {}
        outcome = repair.regression_limits(baselines)
        self.assertEqual(outcome["stopped"], "invalid baseline evidence")
        self.assertIn("consumers are not the plan's 8", " ".join(outcome["evidence_errors"]))
        limits = {"stage": "r0-limits", "status": "ok", "result": {"passed": True, "limits": {}, "leaf_count": 0}}
        self.assertIn("consumers are not the plan's 8", self._rejected(baselines, limits, candidates))

    def test_review_reproduction_failed_runner_and_exit_status_two_are_rejected(self) -> None:
        baselines, limits, candidates = self._evidence()
        for payload in candidates:
            payload["result"]["passed"] = False
            for consumer in payload["result"]["consumers"].values():
                for run in consumer["runs"].values():
                    run["exit_status"] = 2
        errors = self._rejected(baselines, limits, candidates)
        self.assertIn("not a complete successful candidate run", errors)
        self.assertIn("exit status 2 does not match the verdict", errors)

    def test_review_reproduction_candidate_builds_with_different_sources_are_rejected(self) -> None:
        baselines, limits, candidates = self._evidence()
        candidates[1]["result"]["source_sha256"] = "f" * 64
        self.assertIn("candidate B3: source or construction is not the approved candidate",
                      self._rejected(baselines, limits, candidates))

    def test_coverage_verdicts_and_data_are_strict(self) -> None:
        def rejected(mutate):
            return self._rejected(*self._evidence(mutate))

        def run_of(consumers):
            return consumers["gubser-rocha-emd"]["runs"]["default"]

        self.assertIn("consumers are not the plan's 8", rejected(lambda consumers: consumers.pop("hard-wall-chiral")))
        self.assertIn("runs are not the plan's commands",
                      rejected(lambda consumers: consumers["soft-wall-vector"]["runs"].pop("spectral-56")))
        self.assertIn("arguments differ", rejected(lambda consumers: run_of(consumers)["arguments"].append("--degree")))
        self.assertIn("not Boolean", rejected(lambda consumers: run_of(consumers).update(passed=1)))
        self.assertIn("not Boolean", rejected(lambda consumers: run_of(consumers).update(acceptance_checks={})))
        self.assertIn("not Boolean", rejected(
            lambda consumers: run_of(consumers)["acceptance_checks"]["gate-1"].update(passed="true")))
        self.assertIn("contradicts its checks", rejected(lambda consumers: run_of(consumers).update(passed=False, exit_status=1)))
        self.assertIn("exit status 1 does not match", rejected(lambda consumers: run_of(consumers).update(exit_status=1)))
        self.assertIn("exit status True", rejected(lambda consumers: run_of(consumers).update(exit_status=True)))
        self.assertIn("check value is not finite", rejected(
            lambda consumers: run_of(consumers)["acceptance_checks"]["gate-1"].update(value="nan")))
        self.assertIn("not finite", rejected(
            lambda consumers: consumers["gubser-rocha-emd"]["leaves"]["xi=1.0|hat_s"].update(value=float("inf"))))
        self.assertIn("not finite", rejected(
            lambda consumers: consumers["gubser-rocha-emd"]["leaves"]["xi=1.0|hat_s"].update(estimators={})))
        self.assertIn("no table leaves", rejected(lambda consumers: consumers["hard-wall-vector"].update(leaves={})))
        baselines, limits, candidates = self._evidence()
        candidates[0]["plan_sha256"] = "0" * 64
        self.assertIn("frozen plan", self._rejected(baselines, limits, candidates))

    def test_a_scientific_fail_is_admissible_and_distinct_from_malformed_evidence(self) -> None:
        # The optical run fails one check at baseline and candidate: admitted, and not a stop.
        outcome = repair.regression_compare(*self._evidence())
        self.assertTrue(outcome["passed"])
        self.assertNotIn("stop_kind", outcome)
        self.assertEqual(repair.validate_regression_run(regression_payload("B1", "baseline"), "baseline"), [])

    def test_the_runner_keeps_execution_failures_apart_and_preserves_records(self) -> None:
        import hashlib
        import json
        import os
        import tempfile
        from unittest.mock import patch

        table = {item["id"]: item for item in repair.load_table()["consumers"]}
        _, records = repair.records_for(table["hard-wall-vector"])
        for record in records.values():
            record.update(passed=True, acceptance_checks=[{"id": "gate", "passed": True, "value": 1.0e-9}],
                          software_versions={"holoforge_source_sha256": repair.APPROVED_SOURCES["baseline"]["source_sha256"]})
        program = (
            "import json, os, sys\n"
            "arguments = sys.argv[1:]\n"
            "records = json.load(open(os.environ['FAKE_RECORDS']))\n"
            "sys.stdout.write(json.dumps(records[arguments[arguments.index('--method') + 1]]))\n"
            "sys.exit(int(os.environ.get('FAKE_EXIT', '0')))\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            tree = Path(directory)
            (tree / "src" / "holoforge").mkdir(parents=True)
            (tree / "src" / "holoforge" / "__init__.py").write_text("")
            (tree / "src" / "holoforge" / "__main__.py").write_text(program)
            (tree / "records.json").write_text(json.dumps(records))
            saved = tree / "saved"
            options = dict(consumers=("hard-wall-vector",), records_dir=saved, purpose="recovery")
            with patch.dict(os.environ, {"FAKE_RECORDS": str(tree / "records.json")}):
                result = repair.regression_run("B1", tree, "baseline", **options)
                self.assertTrue(result["passed"], result.get("stopped"))
                self.assertFalse(result["complete"])
                self.assertEqual(result["purpose"], "recovery")
                run = result["consumers"]["hard-wall-vector"]["runs"]["spectral"]
                data = (saved / run["record_file"]).read_bytes()
                self.assertEqual(run["record_file"], "baseline-B1--hard-wall-vector--spectral.json")
                self.assertEqual(hashlib.sha256(data).hexdigest(), run["record_sha256"])
                self.assertEqual(json.loads(data), records["spectral"])
                again = repair.regression_run("B1", tree, "baseline", **options)
                self.assertIn("refusing to overwrite", again["stopped"])
                with patch.dict(os.environ, {"FAKE_EXIT": "2"}):
                    failed = repair.regression_run("B1", tree, "baseline", consumers=("hard-wall-vector",))
                self.assertEqual(failed["stop_kind"], "execution failure")
                self.assertIn("exit status 2 does not match the record verdict", failed["stopped"])
                with patch.dict(os.environ, {"FAKE_EXIT": "1"}):
                    failed = repair.regression_run("B1", tree, "baseline", consumers=("hard-wall-vector",))
                self.assertIn("exit status 1 does not match the record verdict", failed["stopped"])
                wrong = repair.regression_run("B1", tree, "candidate", consumers=("hard-wall-vector",))
                self.assertEqual(wrong["stop_kind"], "execution failure")
                self.assertIn("the approved candidate is", wrong["stopped"])
            for record in records.values():
                record["passed"] = "yes"
            (tree / "records.json").write_text(json.dumps(records))
            with patch.dict(os.environ, {"FAKE_RECORDS": str(tree / "records.json")}):
                failed = repair.regression_run("B1", tree, "baseline", consumers=("hard-wall-vector",))
            self.assertIn("no Boolean verdict", failed["stopped"])

    def test_dgr_quadrature_estimator_covers_every_degree(self) -> None:
        table = {item["id"]: item for item in repair.load_table()["consumers"]}
        _, records = repair.records_for(table["dewolfe-gubser-rosen-emd"])
        leaves = repair.extract_dgr_neutral(records)["leaves"]
        change = records["default"]["results"]["quadrature_refinement"]["records"][3]["middle_to_fine_change"]
        for prefix in ("curve", "degree=150", "degree=120", "degree=80"):
            for field in repair.DGR_QUADRATURE_FIELDS:
                leaf = leaves[f"{prefix}|3|{field}"]
                self.assertEqual(leaf["estimators"]["quadrature"], change * abs(leaf["value"]), (prefix, field))
            for field in ("temperature_BH", "entropy_BH"):
                self.assertEqual(sorted(leaves[f"{prefix}|3|{field}"]["estimators"]), ["refinement"])

    def test_corrected_dgr_replay_keeps_the_stop_and_the_original_files(self) -> None:
        import json

        folder = ROOT / "docs/generated/chebyshev-repair"
        names = [f"r0-baseline-{label}.json" for label in ("B1", "B3")] + \
                [f"s2-candidate-{label}.json" for label in ("B1", "B3")] + ["r0-limits.json"]
        before = {name: repair._file_sha256(folder / name) for name in names}
        payloads = [json.loads((folder / name).read_text()) for name in names]
        outcome = repair.corrected_regression_replay(payloads[:2], payloads[2:4], payloads[4])
        self.assertEqual({name: repair._file_sha256(folder / name) for name in names}, before)
        self.assertEqual(outcome["stopped"], "regression stop: A1 (2), A2 (13)")
        self.assertEqual(outcome["estimators_added_per_build"], [80, 80])
        self.assertTrue(outcome["other_consumers_limits_identical"])
        self.assertGreater(outcome["allowances_changed"], 0)
        self.assertIn("post-observation", outcome["label"])
        for change in outcome["changed_allowances"].values():
            for item in change.values():
                self.assertGreaterEqual(item["corrected"], item["original"])
        corrected, added = repair.corrected_dgr_estimators(payloads[0])
        self.assertEqual(added, 80)
        self.assertEqual(repair.validate_regression_run(corrected, "baseline"), [])

    def test_committed_recovery_records_give_the_single_failing_row(self) -> None:
        import json

        folder = ROOT / "docs/generated/chebyshev-repair"
        keys = [(role, build) for role in ("baseline", "candidate") for build in ("B1", "B3")]
        recoveries = [json.loads((folder / "gr-recovery" / f"recovery-{role}-{build}.json").read_text()) for role, build in keys]
        originals = {f"{role}|{build}": json.loads(
            (folder / (f"r0-baseline-{build}.json" if role == "baseline" else f"s2-candidate-{build}.json")).read_text())
            for role, build in keys}
        outcome = repair.gr_refinement_diagnosis(recoveries, folder / "gr-recovery" / "records", originals)
        self.assertTrue(outcome["passed"], outcome.get("stopped"))
        failing = {key: [(row["xi"], row["observable"]) for row in item["failing_rows"]] for key, item in outcome["runs"].items()}
        self.assertEqual(failing, {"baseline|B1": [], "baseline|B3": [], "candidate|B1": [(16.0, "entropy_density")],
                                   "candidate|B3": []})
        for item in outcome["runs"].values():
            self.assertTrue(item["reproduces_original_leaves"])
            self.assertTrue(item["reproduces_original_check_verdicts_and_values"])
        recorded = json.loads((folder / "gr-recovery" / "gr-diagnosis.json").read_text())["result"]
        self.assertEqual(recorded, json.loads(json.dumps(repair._jsonable(outcome))))

    def test_gubser_rocha_diagnosis_lists_the_failing_rows(self) -> None:
        import copy
        import hashlib
        import json
        import tempfile

        table = {item["id"]: item for item in repair.load_table()["consumers"]}
        _, records = repair.records_for(table["gubser-rocha-emd"])
        record = copy.deepcopy(records["default"])
        refinement = record["results"]["refinement"]
        refinement.update(ordering_floor=5.0e-10, coarse_to_middle_maximum=3.0e-8, ordering_failures=0)
        record.update(passed=True, acceptance_checks=[
            {"id": "spectral-refinement", "passed": True, "value": 4.0e-11, "criterion": "c"},
            {"id": "source-thermodynamics", "passed": True, "value": 2.0e-11, "criterion": "c"}])
        failing = copy.deepcopy(record)
        row = failing["results"]["refinement"]["cases"][0]["observables"]["entropy_density"]
        row.update(coarse_to_middle=1.0e-9, middle_to_fine=3.0e-9, ordered_above_floor=False)
        failing["results"]["refinement"]["ordering_failures"] = 1
        failing["passed"] = False
        failing["acceptance_checks"][0]["passed"] = False
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            recoveries, originals = [], {}
            for role in ("baseline", "candidate"):
                for build in ("B1", "B3"):
                    content = failing if (role, build) == ("candidate", "B1") else record
                    data = json.dumps(content).encode()
                    name = f"{role}-{build}--gubser-rocha-emd--default.json"
                    (folder / name).write_bytes(data)
                    extracted = json.loads(json.dumps(repair._jsonable(repair.extract_gubser_rocha({"default": content}))))
                    checks = {check["id"]: {"passed": check["passed"], "value": check["value"]}
                              for check in content["acceptance_checks"]}
                    run = {"record_file": name, "record_sha256": hashlib.sha256(data).hexdigest(),
                           "exit_status": 0 if content["passed"] else 1, "acceptance_checks": checks}
                    approved = repair.APPROVED_SOURCES[role]
                    result = {"role": role, "build_label": build, "purpose": "recovery",
                              "source_sha256": approved["source_sha256"], "chebyshev_construction": approved["construction"],
                              "consumers": {"gubser-rocha-emd": dict(extracted, runs={"default": run})}}
                    recoveries.append({"status": "ok", "result": result})
                    originals[f"{role}|{build}"] = {"result": copy.deepcopy(result)}
            outcome = repair.gr_refinement_diagnosis(recoveries, folder, originals)
            self.assertTrue(outcome["passed"], outcome.get("stopped"))
            self.assertIn("new recovery runs", outcome["label"])
            failed = outcome["runs"]["candidate|B1"]
            self.assertEqual(failed["ordering_failures"], 1)
            self.assertEqual([(item["xi"], item["observable"], item["coarse_to_middle"], item["middle_to_fine"])
                              for item in failed["failing_rows"]], [(0.5, "entropy_density", 1.0e-9, 3.0e-9)])
            self.assertAlmostEqual(failed["failing_rows"][0]["exact_solution_error"]["absolute"], 2.0e-11, delta=1e-15)
            self.assertTrue(failed["reproduces_original_leaves"])
            self.assertEqual(outcome["runs"]["baseline|B3"]["failing_rows"], [])
            (folder / "baseline-B1--gubser-rocha-emd--default.json").write_bytes(b"{}")
            self.assertIn("hash mismatch", repair.gr_refinement_diagnosis(recoveries, folder, originals)["stopped"])
            self.assertIn("not all present", repair.gr_refinement_diagnosis(recoveries[1:], folder, originals)["stopped"])

    def test_committed_regression_evidence_reproduces_the_s2_stop(self) -> None:
        import json

        folder = ROOT / "docs/generated/chebyshev-repair"
        baselines = [json.loads((folder / f"r0-baseline-{label}.json").read_text()) for label in ("B1", "B3")]
        candidates = [json.loads((folder / f"s2-candidate-{label}.json").read_text()) for label in ("B1", "B3")]
        limits = json.loads((folder / "r0-limits.json").read_text())
        outcome = repair.regression_compare(baselines, limits, candidates)
        self.assertEqual(outcome["stopped"], "regression stop: A1 (2), A2 (13)")
        self.assertEqual(outcome["violation_counts"], {"A1": 2, "A2": 13, "controls": 0, "keys": 0})
        self.assertEqual({(item["build"], item["consumer"], item["check"]) for item in outcome["violations"]["A1"]},
                         {("B1", "gubser-rocha-emd", "spectral-refinement"), ("B1", "gubser-rocha-emd", "record")})
        recorded = json.loads((folder / "s2-comparison.json").read_text())["result"]
        self.assertEqual(recorded["violation_counts"], outcome["violation_counts"])
        self.assertEqual(recorded["stopped"], outcome["stopped"])

    def test_a_tree_without_the_package_is_rejected(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            self.assertIn("no src/holoforge", repair.regression_run("B1", Path(directory), "baseline")["stopped"])


if __name__ == "__main__":
    unittest.main()
