"""Regression checks for public, cross-agent onboarding."""

import re
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]


class AgentOnboardingTests(unittest.TestCase):
    def test_instruction_links_resolve_files_and_sections(self) -> None:
        paths = [
            ROOT / "AGENTS.md",
            ROOT / "docs/agent-maintenance.md",
            ROOT / "docs/agent-quickstart.md",
            ROOT / "docs/research-gate-workflow.md",
            ROOT / "docs/private-research-workflow.md",
            ROOT / "docs/physics-manuscript-writing.md",
            ROOT / "docs/physics-writing-reading-study.md",
        ]
        paths.extend((ROOT / ".agents/skills").glob("*/SKILL.md"))
        for path in paths:
            # Examples inside code blocks are not navigation links.
            text = re.sub(
                r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S
            )
            for href in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
                link = urlsplit(href)
                if link.scheme or link.netloc:
                    continue
                target = (
                    (path.parent / unquote(link.path)).resolve()
                    if link.path else path
                )
                with self.subTest(source=path.relative_to(ROOT), href=href):
                    self.assertTrue(target.is_file(), f"Missing reference: {href}")
                    self.assertIn(
                        ROOT, target.parents,
                        f"Reference leaves public repository: {href}",
                    )
                    if link.fragment:
                        headings = re.findall(
                            r"^#{1,6}\s+(.+?)\s*#*\s*$",
                            target.read_text(encoding="utf-8"), re.M,
                        )
                        anchors = {
                            re.sub(
                                r"\s", "-",
                                re.sub(r"[^\w\- ]", "", heading.lower()),
                            )
                            for heading in headings
                        }
                        self.assertIn(
                            unquote(link.fragment), anchors,
                            f"Missing section: {href}",
                        )

    def test_gate_router_keeps_controlling_policy_reachable(self) -> None:
        path = ROOT / ".agents/skills/holoforge-research-gate/SKILL.md"
        skill = path.read_text(encoding="utf-8")
        links = set()
        for href in re.findall(r"\[[^\]]+\]\(([^)]+)\)", skill):
            link = urlsplit(href)
            target = (path.parent / unquote(link.path)).resolve()
            if target == ROOT / "docs/research-gate-workflow.md":
                links.add(unquote(link.fragment))
        # These are lifecycle policy dependencies, not required copies of prose.
        required = {
            "one-gate-one-bounded-question",
            "use-an-owner-approved-bounded-autonomy-window",
            "three-statuses-that-must-not-be-confused",
            "local-git-record-for-private-research",
            "assess-scientific-opportunity-before-execution-readiness",
            "declare-portfolio-intent-and-search-scope",
            "record-opportunity-and-qualify-the-next-gate",
            "use-a-claim-sufficiency-checkpoint",
            "check-the-version-of-record-before-a-source-stop",
            "use-a-bounded-impasse-protocol",
            "treat-a-model-derived-repair-as-a-new-gate",
            "update-research-knowledge-during-the-gate",
            "every-decision-request-includes-a-recommendation",
            "give-the-owner-clear-response-paths",
            "repeat-the-choices-after-a-gate-closes",
            "learn-from-every-closed-gate",
            "owner-review-pdf-packet",
            "agent-updated-workflow-snapshot",
        }
        self.assertFalse(
            required - links, f"Unreachable gate controls: {required - links}"
        )

    def test_agent_entrypoints_are_linked_and_consistent(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("docs/agent-quickstart.md", agents)
        self.assertIn("@AGENTS.md", claude)
        self.assertIn("docs/agent-quickstart.md", readme)
        for workflow in (
            "holoforge-add-benchmark",
            "holoforge-research-gate",
            "holoforge-public-export",
        ):
            self.assertIn(workflow, agents)

    def test_quickstart_covers_supported_agent_paths_and_boundaries(self) -> None:
        guide = (ROOT / "docs" / "agent-quickstart.md").read_text(
            encoding="utf-8"
        )
        lower = " ".join(guide.lower().split())

        for expected in (
            "codex",
            "claude code",
            "other agents",
            "inspect-only first prompt",
            "separate access-controlled repository",
            "human disclosure approval",
            "python -m unittest discover -s tests -v",
        ):
            self.assertIn(expected, lower)

    def test_onboarding_is_public_safe(self) -> None:
        onboarding = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                ROOT / "AGENTS.md",
                ROOT / "CLAUDE.md",
                ROOT / "docs" / "agent-quickstart.md",
            )
        )
        lower = onboarding.lower()

        self.assertNotIn("/users/", lower)
        self.assertNotIn("holoforge-explore-private", lower)
        for private_identifier in ("c01", "c02", "c03", "d001", "m001"):
            self.assertNotIn(private_identifier, lower)

    def test_claude_local_instructions_are_not_committed(self) -> None:
        ignored = {
            line.strip()
            for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        }
        self.assertIn("CLAUDE.local.md", ignored)

    def test_manuscript_workflow_is_reachable_and_preserves_scope(self) -> None:
        target = "physics-manuscript-writing.md"
        for source in ("AGENTS.md", "README.md", "docs/agent-quickstart.md",
                       "docs/research-gate-workflow.md"):
            with self.subTest(source=source):
                self.assertIn(target, (ROOT / source).read_text(encoding="utf-8"))
        guide = " ".join((ROOT / "docs" / target).read_text(encoding="utf-8").split())
        for boundary in ("not a new scientific gate", "must never conceal",
                         "Preserve the original draft", "separate disclosure decision",
                         "not an independent mathematical proof"):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, guide)

    def test_writing_study_records_scope_and_is_not_a_quality_certificate(self) -> None:
        guide = (ROOT / "docs/physics-manuscript-writing.md").read_text(encoding="utf-8")
        self.assertIn("physics-writing-reading-study.md", guide)
        study = " ".join((ROOT / "docs/physics-writing-reading-study.md").read_text(
            encoding="utf-8").split())
        for boundary in ("Selected-section reading", "not necessarily the latest",
                         "not a new fixed reading quota", "neither publication-readiness",
                         "do not change HoloForge's", "physical question"):
            # These checks establish navigation and stated boundaries, not prose quality.
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, study)


if __name__ == "__main__":
    unittest.main()
