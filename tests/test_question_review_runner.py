"""Tests for the owner-gated question-review runner."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents/skills/holoforge-research-gate"
SCRIPT = SKILL / "scripts" / "run_question_review.py"
SPEC = importlib.util.spec_from_file_location("run_question_review", SCRIPT)
runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(runner)

# A stand-in reviewer: reports its working directory contents and echoes the
# end of the prompt it received on stdin.
FAKE_REVIEWER = [
    sys.executable,
    "-c",
    "import os, sys; text = sys.stdin.read(); "
    "print('files-at-start:', sorted(os.listdir('.'))); "
    "print('received-tail:', text[-24:].strip())",
]
FAILING_REVIEWER = [
    sys.executable, "-c", "import sys; sys.stderr.write('no login'); sys.exit(3)",
]


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class QuestionReviewRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.card = self.dir / "card.md"
        self.card.write_text("Question: does X follow from Y? END-OF-CARD\n",
                             encoding="utf-8")
        self.out = self.dir / "review-1"
        self.config = self.write_config()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_config(self, **overrides) -> Path:
        reviewer = {
            "family": "family-b",
            "command": FAKE_REVIEWER,
            "approved_cards": ["question"],
            "literature_access": True,
        }
        reviewer.update(overrides)
        path = self.dir / "reviewers.json"
        path.write_text(json.dumps({
            "owner_approval": "decision D-test, 2026-10-02",
            "reviewers": {"rev": reviewer},
        }), encoding="utf-8")
        return path

    def run_main(self, *argv: str) -> tuple[int, str]:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), \
                contextlib.redirect_stdout(io.StringIO()):
            code = runner.main(list(argv))
        return code, stderr.getvalue()

    def review(self, *extra: str, card_kind: str = "question",
               author: str = "family-a") -> tuple[int, str]:
        return self.run_main(
            "review", "--card", str(self.card), "--card-kind", card_kind,
            "--reviewer", "rev", "--config", str(self.config),
            "--author-family", author, "--out-dir", str(self.out), *extra,
        )

    def test_review_preserves_output_message_and_hashes(self) -> None:
        code, err = self.review()
        self.assertEqual(code, runner.EXIT_OK, err)

        report = (self.out / "report.md").read_text(encoding="utf-8")
        message = (self.out / "message.md").read_text(encoding="utf-8")
        receipt = json.loads((self.out / "receipt.json").read_text(encoding="utf-8"))
        self.assertIn("files-at-start: []", report)
        self.assertIn("received-tail:", report)
        self.assertIn("Y? END-OF-CARD", report)
        self.assertIn("END-OF-CARD", message)
        self.assertIn(runner.SCOPE_WITH_LITERATURE, message)
        self.assertNotIn("{{", message)
        self.assertEqual(receipt["sha256"]["report"], sha(report))
        self.assertEqual(receipt["sha256"]["message"], sha(message))
        self.assertEqual(
            receipt["sha256"]["card"],
            sha(self.card.read_text(encoding="utf-8")),
        )
        self.assertEqual(receipt["owner_approval"], "decision D-test, 2026-10-02")
        self.assertEqual(receipt["reported_model"], "unavailable")
        self.assertTrue(receipt["working_directory_left_empty"])

    def test_scope_says_when_reviewer_has_no_literature_search(self) -> None:
        self.config = self.write_config(literature_access=False)
        self.assertEqual(self.review()[0], runner.EXIT_OK)
        message = (self.out / "message.md").read_text(encoding="utf-8")
        self.assertIn("no literature search", message)

    def test_unapproved_card_class_is_refused_before_anything_is_sent(self) -> None:
        code, err = self.review(card_kind="claim")
        self.assertEqual(code, runner.EXIT_REFUSED)
        self.assertIn("does not approve", err)
        self.assertFalse(self.out.exists())

    def test_same_family_needs_a_recorded_fallback_decision(self) -> None:
        code, err = self.review(author="FAMILY-B")
        self.assertEqual(code, runner.EXIT_REFUSED)
        self.assertIn("fallback", err)

        code, err = self.review("--fallback-decision", "D-fallback",
                                author="family-b")
        self.assertEqual(code, runner.EXIT_OK, err)
        receipt = json.loads((self.out / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["fallback_decision"], "D-fallback")

    def test_preserved_review_is_never_overwritten(self) -> None:
        self.assertEqual(self.review()[0], runner.EXIT_OK)
        before = (self.out / "report.md").read_bytes()
        code, err = self.review()
        self.assertEqual(code, runner.EXIT_REFUSED)
        self.assertIn("never overwritten", err)
        self.assertEqual((self.out / "report.md").read_bytes(), before)

    def test_oversized_card_is_refused(self) -> None:
        self.card.write_text("x" * (runner.MAX_CARD_CHARS + 1), encoding="utf-8")
        code, err = self.review()
        self.assertEqual(code, runner.EXIT_REFUSED)
        self.assertIn("not a manuscript", err)

    def test_credentials_in_configuration_are_refused(self) -> None:
        self.config = self.write_config(api_token="do-not-store")
        code, err = self.review()
        self.assertEqual(code, runner.EXIT_REFUSED)
        self.assertIn("credentials", err)
        self.assertNotIn("do-not-store", err)

    def test_missing_owner_approval_is_refused(self) -> None:
        data = json.loads(self.config.read_text(encoding="utf-8"))
        data["owner_approval"] = " "
        self.config.write_text(json.dumps(data), encoding="utf-8")
        code, err = self.review()
        self.assertEqual(code, runner.EXIT_REFUSED)
        self.assertIn("owner_approval", err)

    def test_failed_reviewer_preserves_nothing(self) -> None:
        self.config = self.write_config(command=FAILING_REVIEWER)
        code, err = self.review()
        self.assertEqual(code, runner.EXIT_FAILED)
        self.assertIn("exited with 3", err)
        self.assertFalse((self.out / "report.md").exists())
        self.assertFalse((self.out / "receipt.json").exists())

    def test_template_placeholders_are_required_and_not_reexpanded(self) -> None:
        with self.assertRaises(runner.Refused):
            runner.fill_template("no placeholders", {"CARD": "c"})
        filled = runner.fill_template(
            "A {{CARD}} B {{INPUT_SCOPE}}",
            {"CARD": "card says {{INPUT_SCOPE}}", "INPUT_SCOPE": "scope"},
        )
        self.assertEqual(filled, "A card says {{INPUT_SCOPE}} B scope")

    def test_single_rebuttal_round_checks_integrity(self) -> None:
        self.assertEqual(self.review()[0], runner.EXIT_OK)
        reply = self.dir / "reply.md"
        reply.write_text("Item 1: Disputed. REPLY-END\n", encoding="utf-8")
        args = ("rebuttal", "--review-dir", str(self.out), "--reply", str(reply),
                "--config", str(self.config))

        code, err = self.run_main(*args)
        self.assertEqual(code, runner.EXIT_OK, err)
        message = (self.out / "rebuttal-message.md").read_text(encoding="utf-8")
        self.assertIn("REPLY-END", message)
        self.assertIn("END-OF-CARD", message)
        receipt = json.loads(
            (self.out / "rebuttal-receipt.json").read_text(encoding="utf-8")
        )
        self.assertEqual(receipt["stage"], "rebuttal")
        self.assertEqual(receipt["sha256"]["reply"], sha(reply.read_text(encoding="utf-8")))

        code, err = self.run_main(*args)
        self.assertEqual(code, runner.EXIT_REFUSED)
        self.assertIn("one rebuttal round", err)

    def test_rebuttal_refuses_an_altered_report(self) -> None:
        self.assertEqual(self.review()[0], runner.EXIT_OK)
        with (self.out / "report.md").open("a", encoding="utf-8") as handle:
            handle.write("edited later\n")
        reply = self.dir / "reply.md"
        reply.write_text("Item 1: Disputed.\n", encoding="utf-8")
        code, err = self.run_main(
            "rebuttal", "--review-dir", str(self.out), "--reply", str(reply),
            "--config", str(self.config),
        )
        self.assertEqual(code, runner.EXIT_REFUSED)
        self.assertIn("no longer matches", err)

    def test_scope_brief_uses_the_proposal_prompt_and_its_own_approval(self) -> None:
        # A reviewer approved only for question cards must not receive a brief.
        code, err = self.review(card_kind="brief")
        self.assertEqual(code, runner.EXIT_REFUSED)
        self.assertIn("does not approve", err)
        self.assertFalse(self.out.exists())

        self.config = self.write_config(approved_cards=["brief"])
        code, err = self.review(card_kind="brief")
        self.assertEqual(code, runner.EXIT_OK, err)
        message = (self.out / "message.md").read_text(encoding="utf-8")
        proposal_prompt = runner.DEFAULT_PROPOSAL_PROMPT.read_text(encoding="utf-8")
        self.assertIn("--- SCOPE BRIEF ---", message)
        self.assertIn("END-OF-CARD", message)
        self.assertNotIn("Strongest supported referee objection", message)
        receipt = json.loads((self.out / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["stage"], "proposal")
        self.assertEqual(receipt["card_kind"], "brief")
        self.assertEqual(receipt["sha256"]["prompt_template"], sha(proposal_prompt))

    def test_proposals_have_no_rebuttal_round(self) -> None:
        self.config = self.write_config(approved_cards=["brief"])
        self.assertEqual(self.review(card_kind="brief")[0], runner.EXIT_OK)
        reply = self.dir / "reply.md"
        reply.write_text("Candidate 1: declined.\n", encoding="utf-8")
        code, err = self.run_main(
            "rebuttal", "--review-dir", str(self.out), "--reply", str(reply),
            "--config", str(self.config),
        )
        self.assertEqual(code, runner.EXIT_REFUSED)
        self.assertIn("only a question or claim review", err)
        self.assertFalse((self.out / "rebuttal.md").exists())

    def test_derivation_setup_uses_its_prompt_and_its_own_approval(self) -> None:
        # Approval for claim cards does not cover derivation setups.
        self.config = self.write_config(approved_cards=["question", "claim"])
        code, err = self.review(card_kind="derivation")
        self.assertEqual(code, runner.EXIT_REFUSED)
        self.assertIn("does not approve", err)
        self.assertFalse(self.out.exists())

        self.config = self.write_config(approved_cards=["derivation"])
        code, err = self.review(card_kind="derivation")
        self.assertEqual(code, runner.EXIT_OK, err)
        message = (self.out / "message.md").read_text(encoding="utf-8")
        derivation_prompt = runner.DEFAULT_DERIVATION_PROMPT.read_text(encoding="utf-8")
        self.assertIn("--- SETUP ---", message)
        self.assertIn("END-OF-CARD", message)
        self.assertNotIn("Strongest supported referee objection", message)
        receipt = json.loads((self.out / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["stage"], "derivation")
        self.assertEqual(receipt["card_kind"], "derivation")
        self.assertEqual(receipt["sha256"]["prompt_template"], sha(derivation_prompt))

    def test_derivation_has_no_rebuttal_round(self) -> None:
        self.config = self.write_config(approved_cards=["derivation"])
        self.assertEqual(self.review(card_kind="derivation")[0], runner.EXIT_OK)
        reply = self.dir / "reply.md"
        reply.write_text("Result differs.\n", encoding="utf-8")
        code, err = self.run_main(
            "rebuttal", "--review-dir", str(self.out), "--reply", str(reply),
            "--config", str(self.config),
        )
        self.assertEqual(code, runner.EXIT_REFUSED)
        self.assertIn("only a question or claim review", err)

    def test_shipped_templates_and_example_are_valid_and_provider_neutral(self) -> None:
        review_prompt = runner.DEFAULT_PROMPT.read_text(encoding="utf-8")
        rebuttal_prompt = runner.DEFAULT_REBUTTAL_PROMPT.read_text(encoding="utf-8")
        proposal_prompt = runner.DEFAULT_PROPOSAL_PROMPT.read_text(encoding="utf-8")
        derivation_prompt = runner.DEFAULT_DERIVATION_PROMPT.read_text(encoding="utf-8")
        choice_prompt = (
            ROOT / "docs/templates/construction-choice-prompt.md"
        ).read_text(encoding="utf-8")
        runner.fill_template(choice_prompt, {"INPUT_SCOPE": "s", "CARD": "c"})
        runner.fill_template(review_prompt, {"INPUT_SCOPE": "s", "CARD": "c"})
        runner.fill_template(proposal_prompt, {"INPUT_SCOPE": "s", "CARD": "c"})
        runner.fill_template(derivation_prompt, {"INPUT_SCOPE": "s", "CARD": "c"})
        runner.fill_template(
            rebuttal_prompt, {"CARD": "c", "REPORT": "r", "REPLY": "p"}
        )
        example = json.loads(
            (SKILL / "assets/question-review-reviewers.example.json")
            .read_text(encoding="utf-8")
        )
        for name, reviewer in example["reviewers"].items():
            runner.validate_reviewer(name, reviewer)

        public_texts = (
            review_prompt,
            rebuttal_prompt,
            proposal_prompt,
            derivation_prompt,
            choice_prompt,
            SCRIPT.read_text(encoding="utf-8"),
            json.dumps(example),
        )
        for text in public_texts:
            lowered = text.lower()
            for provider in (
                "codex", "claude", "gpt", "deepseek", "openai", "anthropic",
            ):
                self.assertNotIn(provider, lowered)
            self.assertNotIn("/users/", lowered)
            self.assertNotIn("holoforge-explore-private", lowered)


if __name__ == "__main__":
    unittest.main()
