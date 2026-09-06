"""Regression checks for HoloForge's public/private research boundary."""

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PublicContentPolicyTests(unittest.TestCase):
    def test_research_acceleration_stays_physics_first_and_private_safe(self) -> None:
        paths = (
            ROOT / "docs/research-objective.md",
            ROOT / "docs/research-acceleration-plan-v3.md",
            ROOT / "docs/research-acceleration-agent-brief-v3.md",
            ROOT / "docs/version-0.5.9.md",
        )
        combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        lowered = combined.lower()
        self.assertIn("physical discriminator", lowered)
        self.assertIn("private vertical slice", lowered)
        self.assertIn("scientific opportunity", lowered)
        self.assertIn("strategic development", lowered)
        self.assertIn("must not certify novelty", lowered)
        self.assertIn("not a physical negative result", lowered)
        self.assertNotIn("/Users/", combined)
        self.assertNotIn("HoloForge-Explore-Private", combined)
        for private_identifier in ("C01", "C02", "C03", "D001", "M001"):
            self.assertNotIn(private_identifier, combined)

    def test_autonomous_workflow_is_generic_private_safe_and_fail_closed(self):
        paths = (
            ROOT / "docs/autonomous-research-workflow.md",
            ROOT / ".agents/skills/holoforge-auto-research/SKILL.md",
            ROOT / ".agents/skills/holoforge-auto-research/references/campaign-workflow.md",
            ROOT / ".agents/skills/holoforge-auto-research/references/no-touch-policy.md",
        )
        combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        lowered = combined.lower()

        self.assertIn("submission-ready candidate", lowered)
        self.assertIn("cannot honestly guarantee", lowered)
        self.assertIn("sole canonical writer", lowered)
        self.assertIn("read-only", lowered)
        self.assertIn("frozen", lowered)
        self.assertIn("no-touch", lowered)
        self.assertIn("stopped outcome", lowered)
        self.assertIn("human", lowered)
        self.assertNotIn("/Users/", combined)
        self.assertNotIn("HoloForge-Explore-Private", combined)
        for private_identifier in ("C01", "C02", "C03", "D001", "M001"):
            self.assertNotIn(private_identifier, combined)

    def test_private_workspace_names_are_ignored(self) -> None:
        entries = {
            line.strip()
            for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        }
        self.assertIn("/.private-research/", entries)
        self.assertIn("/unpublished/", entries)

    def test_public_incubator_example_makes_no_novelty_claim(self) -> None:
        with (
            ROOT / "incubator/examples/hypothesis-card.example.json"
        ).open(encoding="utf-8") as handle:
            card = json.load(handle)

        self.assertTrue(card["title"].startswith("Example only:"))
        self.assertEqual(
            card["target_domain"], "unspecified-strongly-coupled-system"
        )
        self.assertEqual(card["prior_work"]["search_status"], "not-searched")
        self.assertEqual(card["claims"][0]["support_level"], "hypothesis")
        self.assertEqual(card["claims"][0]["review_status"], "unreviewed")

    def test_policy_requires_an_external_private_repository(self) -> None:
        constitution = (ROOT / "CONSTITUTION.md").read_text(encoding="utf-8")
        workflow = (ROOT / "docs/private-research-workflow.md").read_text(
            encoding="utf-8"
        )
        incubator = (ROOT / "incubator/README.md").read_text(encoding="utf-8")

        combined = "\n".join((constitution, workflow, incubator)).lower()
        self.assertIn("separate private repository", combined)
        self.assertIn("journal acceptance", combined)
        self.assertIn("explicit", combined)
        self.assertNotIn("/users/", combined)

    def test_synthetic_dry_run_stops_before_a_claim(self) -> None:
        dry_run = (ROOT / "docs/explore-public-dry-run.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("not a novel research project", dry_run.lower())
        self.assertIn("stop: novelty", dry_run.lower())
        self.assertIn("do not promote", dry_run.lower())

    def test_generic_gate_workflow_preserves_three_tracks_and_boundaries(self):
        workflow = (ROOT / "docs/research-gate-workflow.md").read_text(
            encoding="utf-8"
        ).lower()

        self.assertIn("new-domain application", workflow)
        self.assertIn("new-subfield or new-phenomenon application", workflow)
        self.assertIn("method transfer or model improvement", workflow)
        self.assertIn("assess scientific opportunity before execution readiness", workflow)
        self.assertRegex(
            workflow,
            r"named human\s+research owner makes the final",
        )
        self.assertIn("three research horizons", workflow)
        self.assertIn("frozen contract", workflow)
        self.assertIn("hostile critic report", workflow)
        self.assertIn("owner review", workflow)
        self.assertIn("scientific support", workflow)
        self.assertIn("research authorization", workflow)
        self.assertIn("disclosure status", workflow)

    def test_review_packet_template_is_generic_and_privacy_safe(self):
        template = (
            ROOT / "docs/templates/review-packet-template.tex"
        ).read_text(encoding="utf-8")
        workflow = (ROOT / "docs/research-gate-workflow.md").read_text(
            encoding="utf-8"
        )
        combined = "\n".join((template, workflow))

        self.assertIn("Outcome.", template)
        self.assertIn("Supported:", template)
        self.assertIn("Not supported:", template)
        self.assertIn("Owner decisions", template)
        self.assertNotIn("/Users/", combined)
        self.assertNotIn("HoloForge-Explore-Private", combined)
        for private_identifier in ("C01", "C02", "C03", "D001", "M001"):
            self.assertNotIn(private_identifier, combined)

    def test_review_packet_uses_accessible_status_colors_and_critic_leads(self):
        template = (
            ROOT / "docs/templates/review-packet-template.tex"
        ).read_text(encoding="utf-8")
        workflow = " ".join(
            (ROOT / "docs/research-gate-workflow.md")
            .read_text(encoding="utf-8")
            .lower()
            .split()
        )
        skill = " ".join(
            (ROOT / ".agents/skills/holoforge-research-gate/SKILL.md")
            .read_text(encoding="utf-8")
            .lower()
            .split()
        )

        for command in (
            r"\statuspass",
            r"\statusfail",
            r"\statusstop",
            r"\statuspending",
            r"\statusskipped",
            r"\statusclosed",
            r"\statusretained",
        ):
            self.assertIn(command, template)

        self.assertIn("color is never the only carrier of meaning", workflow)
        self.assertIn("short bold challenge sentence", workflow)
        self.assertIn("#owner-review-pdf-packet", skill)

    def test_pdf_review_rule_covers_explore_and_forge_verify(self):
        workflow = " ".join(
            (ROOT / "docs/research-gate-workflow.md")
            .read_text(encoding="utf-8")
            .lower()
            .split()
        )
        benchmark_skill = " ".join(
            (ROOT / ".agents/skills/holoforge-add-benchmark/SKILL.md")
            .read_text(encoding="utf-8")
            .lower()
            .split()
        )

        self.assertIn("private explore gates", workflow)
        self.assertIn("public forge/verify scientific-contract reviews", workflow)
        self.assertIn("difficult to review reliably in markdown", benchmark_skill)
        self.assertIn("before requesting owner approval", benchmark_skill)
        self.assertIn("docs/templates/review-packet-template.tex", benchmark_skill)
        self.assertIn("compile twice", benchmark_skill)
        self.assertIn("render every page", benchmark_skill)
        self.assertIn("not itself approval", benchmark_skill)

        ignored = {
            line.strip()
            for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        }
        self.assertIn("/output/", ignored)
        self.assertIn("/tmp/", ignored)

    def test_every_owner_decision_request_requires_a_recommendation(self):
        workflow = (ROOT / "docs/research-gate-workflow.md").read_text(
            encoding="utf-8"
        ).lower()
        template = (
            ROOT / "docs/templates/review-packet-template.tex"
        ).read_text(encoding="utf-8").lower()

        self.assertIn("every decision request includes a recommendation", workflow)
        self.assertIn("maps each numbered decision", workflow)
        self.assertIn("evidence-based reason", workflow)
        self.assertIn("what work the recommendation opens", workflow)
        self.assertIn("tradeoff or uncertainty", workflow)
        self.assertIn("recommendation is to pause", workflow)
        self.assertIn("recommendation is advice, not owner approval", workflow)
        self.assertIn("recommended selections", template)
        self.assertIn("reason and scope effect", template)

    def test_post_closure_handoff_repeats_status_and_response_paths(self):
        workflow = " ".join(
            (ROOT / "docs/research-gate-workflow.md")
            .read_text(encoding="utf-8")
            .lower()
            .split()
        )
        private_workflow = " ".join(
            (ROOT / "docs/private-research-workflow.md")
            .read_text(encoding="utf-8")
            .lower()
            .split()
        )
        skill = " ".join(
            (ROOT / ".agents/skills/holoforge-research-gate/SKILL.md")
            .read_text(encoding="utf-8")
            .lower()
            .split()
        )

        for text in (workflow, private_workflow):
            self.assertIn("after", text)
            self.assertIn("closed", text)
            self.assertIn("completed/current/next", text)
            self.assertIn("a-e", text)
            self.assertIn("remain paused", text)

        self.assertIn("#repeat-the-choices-after-a-gate-closes", skill)
        self.assertIn("awaiting_owner: false", workflow)
        self.assertIn("must not receive a fabricated pending owner menu", workflow)
        self.assertIn("does not reopen the completed gate", private_workflow)

    def test_explore_intake_separates_opportunity_from_next_gate_readiness(self):
        workflow = (ROOT / "docs/research-gate-workflow.md").read_text(
            encoding="utf-8"
        ).lower()
        skill = (
            ROOT / ".agents/skills/holoforge-research-gate/SKILL.md"
        ).read_text(encoding="utf-8").lower()
        scorecard = (
            ROOT
            / ".agents/skills/holoforge-research-gate/assets/explore-intake-scorecard.example.md"
        ).read_text(encoding="utf-8").lower()
        combined = " ".join("\n".join((workflow, skill, scorecard)).split())

        for readiness_test in (
            "gate-complete inputs",
            "invariant target beyond the generic baseline",
            "cheapest discriminating test",
            "positive-result endpoint",
            "cost ceiling",
        ):
            self.assertIn(readiness_test, combined)

        for opportunity_row in (
            "physical importance",
            "gap plausibility",
            "falsifiability",
            "physical or conceptual holographic leverage",
            "computational or representational holographic leverage",
            "explanatory or predictive depth",
            "outcome value",
            "owner fit",
        ):
            self.assertIn(opportunity_row, combined)

        for horizon in (
            "open discovery",
            "strategic development",
            "short-horizon execution",
        ):
            self.assertIn(horizon, combined)

        self.assertIn("named human owner decides", combined)
        self.assertIn("does not by itself show", combined)
        self.assertIn("planned model or capability construction is not a numerical repair", combined)
        self.assertIn("capability receipts", combined)
        self.assertIn("capability availability cannot decide which physics questions", combined)
        self.assertIn("best nonholographic baseline", combined)
        self.assertIn("one extra dimension", combined)
        self.assertIn("construction effort, and compute cost", combined)
        self.assertIn("not a novelty", scorecard)
        self.assertIn("prior-knowledge review", scorecard)
        self.assertIn("stable knowledge or lesson id", combined)
        self.assertIn("stable lesson id", combined)
        self.assertIn("primary evidence", combined)
        self.assertIn("candidate-specific control", combined)
        self.assertIn("if no item applies", scorecard)
        self.assertIn("previous gate's failure", scorecard)
        self.assertNotIn("/users/", scorecard)
        self.assertNotIn("holoforge-explore-private", scorecard)

    def test_model_derived_repair_requires_a_separate_gate(self):
        workflow = (
            ROOT / "docs/research-gate-workflow.md"
        ).read_text(encoding="utf-8").lower()
        skill = (
            ROOT / ".agents/skills/holoforge-research-gate/SKILL.md"
        ).read_text(encoding="utf-8").lower()
        combined = " ".join("\n".join((workflow, skill)).split())

        for required_term in (
            "model-derived repair",
            "separate derivation gate",
            "preserve the source-stop result",
            "same-order",
            "physical observable",
            "normalization",
            "field redefinition",
            "counterterm",
            "algebraic kill tests",
            "cancellations",
            "before numerical work",
            "does not establish that the correction is nonzero",
        ):
            self.assertIn(required_term, combined)

        self.assertNotIn("/users/", combined)
        self.assertNotIn("holoforge-explore-private", combined)
        for private_identifier in ("c01", "c02", "c03", "d001", "m001"):
            self.assertNotIn(private_identifier, combined)

    def test_intake_records_portfolio_intent_scope_and_publication_path(self):
        workflow = (
            ROOT / "docs/research-gate-workflow.md"
        ).read_text(encoding="utf-8").lower()
        private_workflow = (
            ROOT / "docs/private-research-workflow.md"
        ).read_text(encoding="utf-8").lower()
        skill = (
            ROOT / ".agents/skills/holoforge-research-gate/SKILL.md"
        ).read_text(encoding="utf-8").lower()
        scorecard = (
            ROOT
            / ".agents/skills/holoforge-research-gate/assets/explore-intake-scorecard.example.md"
        ).read_text(encoding="utf-8").lower()
        combined = " ".join(
            "\n".join((workflow, private_workflow, skill, scorecard)).split()
        )

        for required_term in (
            "portfolio intent",
            "publication-targeted",
            "search shape",
            "domains considered",
            "domains intentionally excluded",
            "domain-coverage",
            "scientific-opportunity assessment",
            "publication-pathway assessment",
            "paper-shaped question",
            "physical discriminator or mechanism",
            "research horizon",
            "construction, repair, and pivot budgets",
        ):
            self.assertIn(required_term, combined)

        self.assertIn("holographic qcd", workflow)
        self.assertIn("not a quota", combined)
        self.assertIn("does not establish novelty", scorecard)
        self.assertIn("does not establish novelty", workflow)
        self.assertIn("not a scientific-value veto", workflow)
        self.assertNotIn("/users/", combined)
        self.assertNotIn("holoforge-explore-private", combined)

    def test_publication_targeted_intake_is_physics_first(self):
        paths = (
            ROOT / "AGENTS.md",
            ROOT / "CONTRIBUTING.md",
            ROOT / "docs/research-gate-workflow.md",
            ROOT / "docs/private-research-workflow.md",
            ROOT / "docs/agent-quickstart.md",
            ROOT / ".agents/skills/holoforge-research-gate/SKILL.md",
            ROOT
            / ".agents/skills/holoforge-research-gate/assets/explore-intake-scorecard.example.md",
        )
        combined = " ".join(
            "\n".join(path.read_text(encoding="utf-8") for path in paths)
            .lower()
            .split()
        )

        for required_term in (
            "scientific opportunity",
            "human research owner",
            "open discovery",
            "strategic development",
            "short-horizon execution",
            "minimum publishable physical claim",
            "first physical-discriminator gate",
            "numerical-dependence lane",
            "campaign construction budget",
            "candidate-wide numerical-repair budget",
            "physical-claim progress",
            "source and novelty readiness",
            "numerical credibility",
            "portfolio-level reassessment",
            "first or second detailed gate",
        ):
            self.assertIn(required_term, combined)

        self.assertIn("cannot be reset", combined)
        self.assertIn("directly unlocks", combined)
        self.assertIn("only the short-horizon", combined)
        self.assertIn("planned model or capability construction is not a numerical repair", combined)
        self.assertIn("capability availability cannot decide which physics questions", combined)
        self.assertIn("do not weaken numerical acceptance gates", combined)
        self.assertNotIn("/users/", combined)
        self.assertNotIn("holoforge-explore-private", combined)

    def test_claim_sufficiency_returns_numerical_work_to_physics(self):
        paths = (
            ROOT / "CONSTITUTION.md",
            ROOT / "AGENTS.md",
            ROOT / "docs/research-gate-workflow.md",
            ROOT / "docs/templates/bounded-autonomy-window-template.md",
            ROOT / "docs/templates/research-retrospective-template.md",
            ROOT / ".agents/skills/holoforge-research-gate/SKILL.md",
        )
        texts = {
            path: " ".join(path.read_text(encoding="utf-8").lower().split())
            for path in paths
        }
        combined = "\n".join(texts.values())

        for required_term in (
            "numerics serve the physical question",
            "claim-bearing physical decision",
            "claim-sufficient",
            "residual",
            "convergence",
            "smoothness",
            "constraint",
            "reproducibility",
            "independent",
            "numerical uncertainty",
            "source",
            "dictionary",
            "boundary-condition",
            "ensemble",
            "artifact",
            "distinct physical alternative",
            "materially strengthen the claim",
            "which claim-bearing physical decision",
            "return to physical interpretation",
        ):
            self.assertIn(required_term, combined)

        workflow = texts[ROOT / "docs/research-gate-workflow.md"]
        for protected_case in (
            "bifurcation",
            "instability",
            "non-smooth",
            "numerical method",
            "strategic-development milestone",
        ):
            self.assertIn(protected_case, workflow)

        self.assertIn("never obtain sufficiency by weakening a threshold", combined)
        self.assertIn("dropping a failed check", combined)
        self.assertIn("after seeing the result", combined)
        self.assertNotIn("/users/", combined)
        self.assertNotIn("holoforge-explore-private", combined)
        for private_identifier in ("c01", "c02", "c03", "d001", "m001"):
            self.assertNotIn(private_identifier, combined)

    def test_repeated_blockers_use_a_bounded_impasse_protocol(self):
        workflow = (
            ROOT / "docs/research-gate-workflow.md"
        ).read_text(encoding="utf-8").lower()
        private_workflow = (
            ROOT / "docs/private-research-workflow.md"
        ).read_text(encoding="utf-8").lower()
        skill = (
            ROOT / ".agents/skills/holoforge-research-gate/SKILL.md"
        ).read_text(encoding="utf-8").lower()
        instructions = (ROOT / "AGENTS.md").read_text(encoding="utf-8").lower()
        quickstart = (
            ROOT / "docs/agent-quickstart.md"
        ).read_text(encoding="utf-8").lower()
        combined = " ".join(
            "\n".join(
                (workflow, private_workflow, skill, instructions, quickstart)
            ).split()
        )

        for required_term in (
            "bounded impasse protocol",
            "classify the blocker",
            "targeted external evidence",
            "independent physics audit",
            "official documentation",
            "conditioning",
            "maintained library",
            "one bounded repair",
            "model-derived repair",
            "technical stop",
        ):
            self.assertIn(required_term, combined)

        self.assertIn("internet result is a locator for evidence", workflow)
        self.assertIn("does not validate a fix", skill)
        self.assertIn("do not loosen a threshold", workflow)
        self.assertNotIn("/users/", combined)
        self.assertNotIn("holoforge-explore-private", combined)

    def test_bounded_autonomy_window_reduces_interruptions_without_scope_drift(self):
        paths = (
            ROOT / "AGENTS.md",
            ROOT / "CONTRIBUTING.md",
            ROOT / "docs/research-gate-workflow.md",
            ROOT / "docs/private-research-workflow.md",
            ROOT / "docs/agent-quickstart.md",
            ROOT / "docs/templates/bounded-autonomy-window-template.md",
            ROOT / ".agents/skills/holoforge-research-gate/SKILL.md",
        )
        texts = {
            path: " ".join(path.read_text(encoding="utf-8").lower().split())
            for path in paths
        }
        combined = "\n".join(texts.values())

        for path, text in texts.items():
            with self.subTest(path=path.name):
                self.assertIn("bounded autonomy window", text)

        template = texts[
            ROOT / "docs/templates/bounded-autonomy-window-template.md"
        ]
        for required_boundary in (
            "frozen contract",
            "return milestone",
            "cost and repair ceilings",
            "mandatory return triggers",
            "acceptance threshold",
            "physical interpretation",
            "public export",
            "push, merge, release, branch deletion",
            "never rolls over",
            "standard a--e owner response paths",
        ):
            self.assertIn(required_boundary, template)

        self.assertIn(
            "without asking the owner to approve each intermediate step",
            combined,
        )
        self.assertIn(
            "one local commit only when the owner explicitly checks",
            combined,
        )
        self.assertIn("never implies permission to push, merge, release", combined)
        self.assertNotIn("/users/", combined)
        self.assertNotIn("holoforge-explore-private", combined)
        for private_identifier in ("i13", "c01", "c02", "c03", "d001", "m001"):
            self.assertNotIn(private_identifier, combined)

    def test_closed_gate_requires_a_generic_research_retrospective(self):
        workflow = (
            ROOT / "docs/research-gate-workflow.md"
        ).read_text(encoding="utf-8").lower()
        lesson_guide = (
            ROOT / "docs/learning-from-results.md"
        ).read_text(encoding="utf-8").lower()
        template = (
            ROOT / "docs/templates/research-retrospective-template.md"
        ).read_text(encoding="utf-8").lower()
        skill = (
            ROOT / ".agents/skills/holoforge-research-gate/SKILL.md"
        ).read_text(encoding="utf-8").lower()
        combined = "\n".join((workflow, lesson_guide, template, skill))

        for outcome in (
            "positive",
            "negative",
            "inconclusive",
            "conditional",
            "source stop",
            "prior-art stop",
            "technical stop",
        ):
            self.assertIn(outcome, combined)

        for required_boundary in (
            "what must not be inferred",
            "reopening trigger",
            "feed forward",
            "must not retroactively change",
            "physical negative result",
            "agent retrieval loop",
            "applicability to future gates",
            "stable lesson id",
            "retrieval tags",
        ):
            self.assertIn(required_boundary, combined)

        self.assertIn("research-retrospective-template.md", workflow)
        self.assertIn("research-retrospective-template.md", skill)
        self.assertNotIn("/users/", combined)
        self.assertNotIn("holoforge-explore-private", combined)
        for private_identifier in ("c01", "c02", "c03", "d001", "m001"):
            self.assertNotIn(private_identifier, combined)

    def test_source_stop_requires_a_version_of_record_audit(self):
        workflow = (
            ROOT / "docs/research-gate-workflow.md"
        ).read_text(encoding="utf-8").lower()
        skill = (
            ROOT / ".agents/skills/holoforge-research-gate/SKILL.md"
        ).read_text(encoding="utf-8").lower()
        combined = " ".join("\n".join((workflow, skill)).split())

        for required_term in (
            "source-normalization stop",
            "version of record",
            "accepted manuscript",
            "correction",
            "erratum",
            "doi",
            "version and date",
            "exact locator",
            "preprint evidence",
            "author intent",
            "private code",
        ):
            self.assertIn(required_term, combined)

        self.assertNotIn("/users/", combined)
        self.assertNotIn("holoforge-explore-private", combined)
        for private_identifier in ("c01", "c02", "c03", "d001", "m001"):
            self.assertNotIn(private_identifier, combined)

    def test_research_knowledge_covers_more_than_failure_lessons(self):
        workflow = (
            ROOT / "docs/research-gate-workflow.md"
        ).read_text(encoding="utf-8").lower()
        lesson_guide = (
            ROOT / "docs/learning-from-results.md"
        ).read_text(encoding="utf-8").lower()
        template = (
            ROOT / "docs/templates/research-knowledge-template.md"
        ).read_text(encoding="utf-8").lower()
        skill = (
            ROOT / ".agents/skills/holoforge-research-gate/SKILL.md"
        ).read_text(encoding="utf-8").lower()
        instructions = (ROOT / "AGENTS.md").read_text(encoding="utf-8").lower()
        combined = "\n".join(
            (workflow, lesson_guide, template, skill, instructions)
        )

        for required_term in (
            "working knowledge",
            "reviewed knowledge",
            "stable knowledge id",
            "stable lesson id",
            "knowledge class",
            "durable milestone",
            "provisional",
            "corroborated",
            "challenged",
            "ready for owner review",
            "promoted",
            "retired",
            "primary evidence",
            "what must not be inferred",
            "not background telemetry",
            "research-knowledge-template.md",
        ):
            self.assertIn(required_term, combined)

        for knowledge_class in (
            "literature/source",
            "model/dictionary",
            "analytic/derivation",
            "numerical/method",
            "data/comparison",
            "result",
            "decision/workflow",
            "tooling/reproducibility",
        ):
            self.assertIn(knowledge_class, combined)

        self.assertIn("named human", combined)
        self.assertIn("exact source version", combined)
        self.assertIn("do not ingest every paper", combined)
        self.assertIn("owner-reviewed closure", combined)
        self.assertIn("must not retroactively change", combined)
        self.assertNotIn("/users/", combined)
        self.assertNotIn("holoforge-explore-private", combined)
        for private_identifier in ("c01", "c02", "c03", "d001", "m001"):
            self.assertNotIn(private_identifier, combined)

    def test_readme_leads_with_the_general_platform_not_example_domains(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        overview, implementations = readme.split(
            "## Included reference implementations", maxsplit=1
        )
        lower_overview = " ".join(overview.lower().split())

        self.assertIn("bottom-up gauge/gravity", lower_overview)
        self.assertIn("do not define holoforge's scientific scope", lower_overview)
        for example_specific_term in (
            "qcd",
            "soft-wall",
            "hard-wall",
            "vector-meson",
            "superconductor",
            "pdg",
            "kappa",
            "m_n^2",
        ):
            self.assertNotIn(example_specific_term, lower_overview)

        self.assertIn("holoforge verify soft-wall-vector", implementations)
        self.assertIn("holoforge verify holographic-superconductor", implementations)


if __name__ == "__main__":
    unittest.main()
