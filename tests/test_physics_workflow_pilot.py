"""Fixture qualification is separate from measuring agent performance."""

import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "evals/agent-workflows/physics-pilot"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


prepare = module("physics_prepare", PILOT / "prepare.py")
spectral = module("physics_spectral", PILOT / "worker/spectral.py")
indexer = module("physics_index", ROOT / "tools/claim_evidence.py")


class PhysicsWorkflowPilotTests(unittest.TestCase):
    def test_worker_staging_excludes_rubric_other_cases_and_existing_destinations(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            before = prepare.prepare(base / "baseline", "case-01")
            after = prepare.prepare(base / "treatment", "case-01", "evidence-index")
            self.assertEqual(before, {k: v for k, v in after.items() if k != "claim_evidence.py"})
            self.assertFalse(any("evaluator" in path or "case-02" in path for path in before))
            self.assertNotIn("claim_evidence.py", before)
            with self.assertRaises(ValueError):
                prepare.prepare(base / "baseline", "case-01")
            with self.assertRaises(ValueError):
                prepare.prepare(base / "escape", "../evaluator")

    def test_all_case_indexes_are_fresh_including_scientifically_wrong_claims(self):
        for number in range(1, 7):
            directory = PILOT / "worker" / ("case-%02d" % number)
            index = json.loads((directory / "index.json").read_text())
            with self.subTest(case=number):
                report = indexer.inspect_index(index, directory)
                self.assertFalse(report["attention_required"])
                self.assertTrue(json.loads(report["resources"][0]["excerpt"])["generated_by_ai"])

    def test_valid_spectrum_passes_and_wrong_boundary_converges_to_wrong_problem(self):
        exact = [(n * math.pi)**2 for n in (1, 2, 3)]
        valid = spectral.spectrum(255, 1.0, "dirichlet")
        self.assertLess(max(abs(a / b - 1) for a, b in zip(valid, exact)), 0.001)
        previous = None
        for points in (63, 127, 255):
            values = spectral.spectrum(points, 1.0, "neumann")
            target = [((n + 0.5) * math.pi)**2 for n in range(3)]
            error = max(abs(a / b - 1) for a, b in zip(values, target))
            if previous is not None:
                self.assertLess(error, previous)
            previous = error
        self.assertGreater(abs(values[0] / exact[0] - 1), 0.7)

    def test_saved_numbers_reproduce_and_cache_identity_is_not_state_compatibility(self):
        for number in (1, 2):
            directory = PILOT / "worker" / ("case-%02d" % number)
            saved = json.loads((directory / "calculation.json").read_text())
            for run in saved["runs"]:
                calculated = spectral.spectrum(run["points"], run["length"], saved["right_boundary_used"])
                for actual, expected in zip(calculated, run["eigenvalues"]):
                    self.assertAlmostEqual(actual, expected, delta=1e-7)
        directory = PILOT / "worker/case-06"
        calculation = json.loads((directory / "calculation.json").read_text())
        retained = json.loads((directory / "mode-0.json").read_text())
        stale = json.loads((directory / "mode-1.json").read_text())
        self.assertEqual(retained["state"], calculation["current_state"])
        self.assertNotEqual(stale["state"], calculation["current_state"])
        self.assertAlmostEqual(stale["eigenvalue"] * 4, spectral.spectrum(255, 1.0, "dirichlet")[1], delta=1e-7)

    def test_protocol_preserves_old_pilot_and_separates_measurements(self):
        protocol = json.loads((PILOT / "protocol.json").read_text())
        self.assertEqual(protocol["status"], "prepared-not-run")
        self.assertEqual(len(protocol["case_ids"]), 6)
        self.assertFalse(protocol["aggregate_scientific_score"])
        self.assertEqual(protocol["limits"]["live_agent_runs_in_implementation"], 0)
        reference = json.loads((PILOT / "evaluator/rubric.json").read_text())
        self.assertEqual(set(reference), set(protocol["case_ids"]))


if __name__ == "__main__":
    unittest.main()
