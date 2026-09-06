"""Tests for the reusable project-local research-progress snapshot."""

from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents" / "skills" / "holoforge-research-gate"
SCRIPT = SKILL / "scripts" / "render_research_progress.py"
EXAMPLE = SKILL / "assets" / "research-progress.example.json"

SPEC = importlib.util.spec_from_file_location("render_research_progress", SCRIPT)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import guard
    raise RuntimeError(f"could not load {SCRIPT}")
RENDERER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RENDERER)


class ResearchProgressTests(unittest.TestCase):
    def load_example(self):
        return json.loads(EXAMPLE.read_text(encoding="utf-8"))

    def test_example_renders_research_graph_and_owner_choices(self) -> None:
        markdown = RENDERER.render_markdown(self.load_example())

        self.assertIn("```mermaid", markdown)
        self.assertIn("Discovery and framing", markdown)
        self.assertIn("Theoretical consistency checks", markdown)
        self.assertIn("Discriminating calculation", markdown)
        self.assertIn("Current stage | Owner review and decision", markdown)
        self.assertIn("Figure style | compact", markdown)
        self.assertIn("Advance to the next bounded gate", markdown)
        self.assertIn("Pause or close", markdown)
        self.assertIn("A **(Recommended)**", markdown)
        self.assertIn("Status walkthrough only", markdown)
        self.assertIn("scientific-support level", markdown)
        self.assertIn("not background telemetry", markdown)

    def test_compact_dot_uses_stage_rail_status_and_feedback_edges(self) -> None:
        dot = RENDERER.render_dot(self.load_example())

        self.assertIn("digraph research_progress", dot)
        self.assertNotIn("subgraph cluster_", dot)
        self.assertIn('shape="box"', dot)
        self.assertIn('fillcolor="#dcfce7"', dot)
        self.assertIn('fillcolor="#fef3c7"', dot)
        self.assertIn(r"\nCURRENT", dot)
        self.assertIn('style="dashed"', dot)
        self.assertIn('constraint="false"', dot)

    def test_compact_dot_can_wrap_a_long_path_without_changing_transitions(self) -> None:
        state = self.load_example()
        state["compact_wrap_after"] = 6

        dot = RENDERER.render_dot(state)

        self.assertIn('group="wrap_col_1"', dot)
        self.assertIn('group="wrap_col_2"', dot)
        self.assertIn("{ rank=same;", dot)
        self.assertIn('style="invis"', dot)
        self.assertIn('label="advance"', dot)
        self.assertIn('constraint="false"', dot)

    def test_compact_wrap_requires_vertical_compact_style(self) -> None:
        state = self.load_example()
        state["compact_wrap_after"] = 1
        with self.assertRaisesRegex(RENDERER.ProgressError, "integer >= 2"):
            RENDERER.validate_state(state)

        state["compact_wrap_after"] = 6
        state["figure_style"] = "grouped"
        with self.assertRaisesRegex(RENDERER.ProgressError, "compact style"):
            RENDERER.validate_state(state)

        state["figure_style"] = "compact"
        state["layout_direction"] = "LR"
        with self.assertRaisesRegex(RENDERER.ProgressError, "TB direction"):
            RENDERER.validate_state(state)

    def test_missing_style_retains_grouped_backward_compatibility(self) -> None:
        state = self.load_example()
        state.pop("figure_style")

        dot = RENDERER.render_dot(state)

        self.assertIn("subgraph cluster_", dot)
        self.assertIn('shape="diamond"', dot)

    def test_stage_status_label_refines_visible_wording(self) -> None:
        state = self.load_example()
        state["stages"][8]["status_label"] = "PROPOSED"

        markdown = RENDERER.render_markdown(state)
        dot = RENDERER.render_dot(state)

        self.assertIn("[PROPOSED]", markdown)
        self.assertIn("PROPOSED", dot)

    def test_unknown_figure_style_fails_closed(self) -> None:
        state = self.load_example()
        state["figure_style"] = "private-copy"

        with self.assertRaisesRegex(RENDERER.ProgressError, "figure_style"):
            RENDERER.validate_state(state)

    def test_cli_writes_markdown_and_dot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            markdown = root / "research-progress.md"
            dot = root / "research-progress.dot"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(EXAMPLE),
                    "--output",
                    str(markdown),
                    "--dot-output",
                    str(dot),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            markdown_text = markdown.read_text(encoding="utf-8")
            dot_text = dot.read_text(encoding="utf-8")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("# Research progress:", markdown_text)
        self.assertIn("digraph research_progress", dot_text)

    @unittest.skipUnless(shutil.which("dot"), "Graphviz dot is not installed")
    def test_cli_renders_standalone_vector_and_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            svg = root / "research-progress.svg"
            pdf = root / "research-progress.pdf"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(EXAMPLE),
                    "--figure-output",
                    str(svg),
                    "--figure-output",
                    str(pdf),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            svg_text = svg.read_text(encoding="utf-8")
            pdf_prefix = pdf.read_bytes()[:4]

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("<svg", svg_text)
        self.assertEqual(pdf_prefix, b"%PDF")

    def test_multiple_current_stages_fail_closed(self) -> None:
        state = copy.deepcopy(self.load_example())
        state["stages"][0]["status"] = "current"

        with self.assertRaisesRegex(RENDERER.ProgressError, "exactly one stage"):
            RENDERER.validate_state(state)

    def test_unknown_transition_stage_fails_closed(self) -> None:
        state = copy.deepcopy(self.load_example())
        state["transitions"][0]["to"] = "missing_stage"

        with self.assertRaisesRegex(RENDERER.ProgressError, "unknown stage"):
            RENDERER.validate_state(state)

    def test_incomplete_response_menu_fails_closed(self) -> None:
        state = copy.deepcopy(self.load_example())
        state["response_options"].pop()

        with self.assertRaisesRegex(
            RENDERER.ProgressError, "exactly five response options"
        ):
            RENDERER.validate_state(state)

    def test_snapshot_before_owner_review_omits_decision_menu(self) -> None:
        state = copy.deepcopy(self.load_example())
        state["stages"][4]["status"] = "current"
        state["stages"][7]["status"] = "pending"
        state["current_stage"] = "calculation"
        state["awaiting_owner"] = False
        state["owner_decisions"] = []
        state["recommended_option"] = None
        state["response_options"] = []

        markdown = RENDERER.render_markdown(state)

        self.assertIn("Current stage | Discriminating calculation", markdown)
        self.assertIn("Awaiting owner | No", markdown)
        self.assertNotIn("### Response options", markdown)

    def test_workflow_and_pdf_template_define_research_snapshot(self) -> None:
        workflow = (ROOT / "docs" / "research-gate-workflow.md").read_text(
            encoding="utf-8"
        ).lower()
        snapshot_guide = (ROOT / "docs" / "research-progress-snapshots.md").read_text(
            encoding="utf-8"
        ).lower()
        template = (
            ROOT / "docs" / "templates" / "review-packet-template.tex"
        ).read_text(encoding="utf-8").lower()
        # The skill routes here; presentation policy belongs in these references.
        combined = " ".join("\n".join((workflow, snapshot_guide, template)).split())

        for expected in (
            "research-progress.example.json",
            "render_research_progress.py",
            "state of one research project",
            "standalone svg",
            "figure_style",
            "compact",
            "compact_wrap_after",
            "holoforgeincludeprogress",
            "researchprogressfile",
            "does not itself raise a claim's scientific-support level",
        ):
            self.assertIn(expected, combined)


if __name__ == "__main__":
    unittest.main()
