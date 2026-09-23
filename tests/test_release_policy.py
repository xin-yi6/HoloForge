"""Regression checks for the Version 0.5 public compatibility contract."""

from pathlib import Path
import unittest

import holoforge
from holoforge import benchmarks, comparisons, core


ROOT = Path(__file__).resolve().parents[1]


class Version05PolicyTests(unittest.TestCase):
    def test_every_deliberate_package_export_is_documented(self) -> None:
        policy = "\n".join(
            (
                (ROOT / "docs/version-0.5-compatibility-policy.md").read_text(),
                (ROOT / "docs/version-0.6.md").read_text(),
            )
        )
        for module in (core, benchmarks, comparisons):
            for name in module.__all__:
                with self.subTest(module=module.__name__, name=name):
                    self.assertIn(f"`{module.__name__}.{name}`", policy)

    def test_policy_freezes_commands_schemas_and_failure_meanings(self) -> None:
        policy = (ROOT / "docs/version-0.5-compatibility-policy.md").read_text()
        for command in (
            "holoforge verify soft-wall-vector",
            "holoforge verify hard-wall-vector",
            "holoforge verify hard-wall-chiral",
            "holoforge verify holographic-superconductor",
            "holoforge verify holographic-superconductor-optical",
            "holoforge verify linear-axion-dc",
            "holoforge verify dewolfe-gubser-rosen-emd",
            "holoforge verify dewolfe-gubser-rosen-emd-finite-density",
            "holoforge verify gubser-nellore-ed",
            "holoforge verify gubser-rocha-emd",
            "holoforge compare vector-spectrum",
            "holoforge audit bundle",
            "holoforge audit compatibility",
        ):
            self.assertIn(command, policy)
        for schema_version in ("`0.1`", "`0.3`", "`0.4`"):
            self.assertIn(schema_version, policy)
        for exit_code in ("Exit `0`", "Exit `1`", "Exit `2`"):
            self.assertIn(exit_code, policy)
        self.assertIn("fail closed", policy)
        self.assertIn("rest of `0.5.x`", policy)

    def test_security_policy_uses_a_private_route(self) -> None:
        policy = (ROOT / "SECURITY.md").read_text()
        normalized = " ".join(policy.split())
        self.assertIn("security/advisories/new", policy)
        self.assertIn("Do not include the sensitive details", normalized)
        self.assertIn("unpublished research", policy)

    def test_ci_covers_wheel_relocation_on_three_operating_systems(self) -> None:
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        for runner in ("ubuntu-latest", "macos-latest", "windows-latest"):
            self.assertIn(runner, workflow)
        self.assertIn("python -m build --wheel", workflow)
        self.assertIn("--force-reinstall dist/*.whl", workflow)
        self.assertIn("holoforge verify linear-axion-dc", workflow)
        self.assertIn("python -m unittest discover -s tests -v", workflow)
        self.assertIn("historical-audit:", workflow)
        self.assertIn(
            "tests.extended.historical_holographic_superconductor_optical",
            workflow,
        )
        self.assertIn(
            "tests.extended.historical_dewolfe_gubser_rosen_emd_finite_density",
            workflow,
        )
        dgr_tests = (ROOT / "tests/test_dewolfe_gubser_rosen_emd.py").read_text()
        self.assertIn("verify_dewolfe_gubser_rosen_emd()", dgr_tests)
        self.assertEqual(
            workflow.splitlines().count(
                "          holoforge verify dewolfe-gubser-rosen-emd"
            ),
            0,
        )
        self.assertIn(
            "'dewolfe-gubser-rosen-emd-finite-density'",
            workflow,
        )
        self.assertNotIn("tests.test_dewolfe_gubser_rosen_emd", workflow)
        self.assertIn("holoforge verify hard-wall-chiral", workflow)
        self.assertIn("tests.test_hard_wall_chiral", workflow)
        self.assertIn(
            "'holographic-superconductor-optical'", workflow
        )
        self.assertNotIn(
            "          holoforge verify holographic-superconductor-optical",
            workflow,
        )
        self.assertIn("load_reference_dataset", workflow)
        self.assertIn("holoforge audit bundle relocated/portability-bundle", workflow)
        self.assertNotIn("continue-on-error", workflow)

    def test_policy_documents_current_and_historical_ci_tiers(self) -> None:
        policy = (ROOT / "docs/version-0.5-compatibility-policy.md").read_text()
        self.assertIn("runs every current scientific verifier", policy)
        self.assertIn("explicit extended audit", policy)
        self.assertIn("repeat the long Phase 4 or Phase 5", policy)

    def test_scientific_json_hashes_are_checkout_portable(self) -> None:
        attributes = (ROOT / ".gitattributes").read_text()
        self.assertIn("*.json text eol=lf", attributes)

    def test_release_metadata_is_synchronized(self) -> None:
        self.assertEqual(holoforge.__version__, "0.7.0")
        citation = (ROOT / "CITATION.cff").read_text()
        changelog = (ROOT / "CHANGELOG.md").read_text()
        readme = (ROOT / "README.md").read_text()
        self.assertIn("version: 0.7.0", citation)
        self.assertIn("date-released: 2026-09-23", citation)
        self.assertIn("## [0.7.0] - 2026-09-23", changelog)
        self.assertIn("latest public release is [`0.7.0`](docs/version-0.7.md)", readme)


if __name__ == "__main__":
    unittest.main()
