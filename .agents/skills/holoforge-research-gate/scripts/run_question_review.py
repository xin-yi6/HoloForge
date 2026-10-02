#!/usr/bin/env python3
"""Run one input-limited question or claim review and preserve its receipt.

The author of a card uses this script instead of a manual handoff. It passes
the fixed reviewer prompt and one card to a reviewer command that the owner
approved in a private configuration file, stores the command's output
unchanged and writes an execution receipt. A scope brief is handled the same
way with the fixed proposal prompt: the command then returns independent
candidate questions instead of a review. The script names no provider and
contains no network code or credentials: each reviewer is a local
non-interactive command, and its provider, account and approvals come from the
owner's configuration.

It refuses a card class the owner has not approved for the reviewer, a
reviewer of the author's own family without a recorded fallback decision, an
oversized card and any overwrite of a preserved report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence


RUNNER_VERSION = 1
CARD_KINDS = ("question", "claim", "brief")
# A brief asks for candidate proposals; there is no report to rebut.
REVIEW_KINDS = ("question", "claim")
# A card is a short record. The cap keeps a manuscript, data file or code
# listing from being sent under the name of a card.
MAX_CARD_CHARS = 12000
DEFAULT_TIMEOUT_SECONDS = 1800
SECRET_WORDS = ("key", "token", "secret", "password")

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_PROMPT = ROOT / "docs/templates/question-review-prompt.md"
DEFAULT_PROPOSAL_PROMPT = ROOT / "docs/templates/candidate-proposal-prompt.md"
DEFAULT_REBUTTAL_PROMPT = ROOT / "docs/templates/question-review-rebuttal-prompt.md"

SCOPE_WITH_LITERATURE = (
    "the card below and public literature that you can search and cite"
)
SCOPE_WITHOUT_LITERATURE = (
    "the card below only. You have no literature search in this run. Answer "
    "item 3 from what you know, say so, and use `concern` where you cannot "
    "support a statement"
)

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_REFUSED = 2


class Refused(Exception):
    """The request is outside the owner's recorded approval or the policy."""


class ReviewFailed(Exception):
    """The reviewer could not be run or returned nothing usable."""


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()


def write_new_text(path: Path, text: str) -> None:
    """Write a file that must not exist yet, without newline translation."""
    with path.open("x", encoding="utf-8", newline="") as handle:
        handle.write(text)


def load_config(path: Path) -> tuple[dict[str, Any], str]:
    try:
        text = read_text(path)
        config = json.loads(text)
    except (OSError, json.JSONDecodeError) as error:
        raise Refused(f"reviewer configuration is unreadable: {error}") from error
    if not isinstance(config, dict):
        raise Refused("reviewer configuration must be a JSON object")
    approval = config.get("owner_approval")
    if not isinstance(approval, str) or not approval.strip():
        raise Refused("configuration lacks the owner_approval decision record")
    reviewers = config.get("reviewers")
    if not isinstance(reviewers, dict) or not reviewers:
        raise Refused("configuration names no reviewers")
    for name, reviewer in reviewers.items():
        validate_reviewer(name, reviewer)
    return config, text


def validate_reviewer(name: str, reviewer: Any) -> None:
    if not isinstance(reviewer, dict):
        raise Refused(f"reviewer {name!r} must be a JSON object")
    if any(word in field.lower() for field in reviewer for word in SECRET_WORDS):
        raise Refused(
            f"reviewer {name!r}: keep credentials out of the configuration; "
            "the reviewer command finds its own login"
        )
    family = reviewer.get("family")
    if not isinstance(family, str) or not family.strip():
        raise Refused(f"reviewer {name!r} lacks a provider or model family")
    command = reviewer.get("command")
    if (
        not isinstance(command, list)
        or not command
        or any(not isinstance(part, str) or not part for part in command)
    ):
        raise Refused(f"reviewer {name!r}: command must be a list of strings")
    approved = reviewer.get("approved_cards")
    if (
        not isinstance(approved, list)
        or any(card not in CARD_KINDS for card in approved)
    ):
        raise Refused(
            f"reviewer {name!r}: approved_cards must list only {CARD_KINDS}"
        )
    if not isinstance(reviewer.get("literature_access"), bool):
        raise Refused(f"reviewer {name!r}: literature_access must be true or false")
    model = reviewer.get("model")
    if model is not None and (not isinstance(model, str) or not model.strip()):
        raise Refused(f"reviewer {name!r}: model, if given, must be a name")


def fill_template(template: str, values: Mapping[str, str]) -> str:
    for placeholder in values:
        if template.count("{{" + placeholder + "}}") != 1:
            raise Refused(
                f"prompt template must contain {{{{{placeholder}}}}} exactly once"
            )
    # Replace in one pass so inserted text cannot introduce a placeholder.
    return re.sub(
        r"\{\{([A-Z_]+)\}\}",
        lambda match: values.get(match.group(1), match.group(0)),
        template,
    )


def call_reviewer(
    reviewer: Mapping[str, Any], message: str, timeout: int
) -> dict[str, Any]:
    """Run the reviewer command in a fresh empty directory, prompt on stdin."""
    workdir = Path(tempfile.mkdtemp(prefix="question-review-"))
    try:
        try:
            completed = subprocess.run(
                reviewer["command"],
                input=message,
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=workdir,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError as error:
            raise ReviewFailed(f"reviewer command not found: {error}") from error
        except subprocess.TimeoutExpired as error:
            raise ReviewFailed(f"reviewer timed out after {timeout} s") from error
        left_empty = not any(workdir.iterdir())
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    if completed.returncode != 0:
        tail = completed.stderr.strip()[-600:]
        raise ReviewFailed(
            f"reviewer command exited with {completed.returncode}: {tail}"
        )
    if not completed.stdout.strip():
        raise ReviewFailed("reviewer returned an empty report")
    return {"output": completed.stdout, "working_directory_left_empty": left_empty}


def base_receipt(
    stage: str, name: str, reviewer: Mapping[str, Any], config: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "runner": Path(__file__).name,
        "runner_version": RUNNER_VERSION,
        "stage": stage,
        "reviewer": name,
        "reviewer_family": reviewer["family"],
        "requested_model": reviewer.get("model", "unspecified"),
        "reported_model": "unavailable",
        "command": reviewer["command"],
        "literature_access": reviewer["literature_access"],
        "owner_approval": config["owner_approval"],
    }


def run_review(args: argparse.Namespace) -> Path:
    config, config_text = load_config(args.config)
    if args.reviewer not in config["reviewers"]:
        raise Refused(f"reviewer {args.reviewer!r} is not in the configuration")
    reviewer = config["reviewers"][args.reviewer]

    if args.card_kind not in reviewer["approved_cards"]:
        raise Refused(
            f"the owner's configuration does not approve sending a "
            f"{args.card_kind} card to reviewer {args.reviewer!r}"
        )
    same_family = (
        reviewer["family"].strip().casefold()
        == args.author_family.strip().casefold()
    )
    if same_family and not args.fallback_decision:
        raise Refused(
            "reviewer and author share a provider or model family; a fallback "
            "needs the owner's recorded decision (--fallback-decision)"
        )

    card = read_text(args.card)
    if not card.strip():
        raise Refused("the card is empty")
    if len(card) > MAX_CARD_CHARS:
        raise Refused(
            f"the card has {len(card)} characters; a card is limited to "
            f"{MAX_CARD_CHARS}. Send a card, not a manuscript, data or code"
        )

    prompt_path = args.prompt or (
        DEFAULT_PROPOSAL_PROMPT if args.card_kind == "brief" else DEFAULT_PROMPT
    )
    template = read_text(prompt_path)
    scope = (
        SCOPE_WITH_LITERATURE
        if reviewer["literature_access"]
        else SCOPE_WITHOUT_LITERATURE
    )
    message = fill_template(template, {"INPUT_SCOPE": scope, "CARD": card})

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in ("card.md", "message.md", "report.md", "receipt.json"):
        if (out_dir / name).exists():
            raise Refused(
                f"{name} already exists in the output directory; a preserved "
                "review is never overwritten"
            )

    started = utc_now()
    result = call_reviewer(reviewer, message, args.timeout)
    finished = utc_now()

    write_new_text(out_dir / "card.md", card)
    write_new_text(out_dir / "message.md", message)
    write_new_text(out_dir / "report.md", result["output"])
    stage = "proposal" if args.card_kind == "brief" else "review"
    receipt = base_receipt(stage, args.reviewer, reviewer, config)
    receipt.update(
        {
            "card_kind": args.card_kind,
            "author_family": args.author_family,
            "fallback_decision": args.fallback_decision,
            "input_scope": "fixed prompt and one card; empty working directory",
            "working_directory_left_empty": result["working_directory_left_empty"],
            "started_utc": started,
            "finished_utc": finished,
            "sha256": {
                "card": sha256_text(card),
                "prompt_template": sha256_text(template),
                "message": sha256_text(message),
                "report": sha256_text(result["output"]),
                "configuration": sha256_text(config_text),
            },
        }
    )
    write_new_text(
        out_dir / "receipt.json", json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    )
    return out_dir


def run_rebuttal(args: argparse.Namespace) -> Path:
    review_dir = args.review_dir
    try:
        receipt = json.loads(read_text(review_dir / "receipt.json"))
        card = read_text(review_dir / "card.md")
        report = read_text(review_dir / "report.md")
    except (OSError, json.JSONDecodeError) as error:
        raise Refused(f"no preserved review in {review_dir.name}: {error}") from error
    if receipt.get("card_kind") not in REVIEW_KINDS:
        raise Refused("only a question or claim review has a rebuttal round")
    if sha256_text(report) != receipt["sha256"]["report"]:
        raise Refused("the preserved report no longer matches its receipt")
    if sha256_text(card) != receipt["sha256"]["card"]:
        raise Refused("the preserved card no longer matches its receipt")
    for name in ("rebuttal-message.md", "rebuttal.md", "rebuttal-receipt.json"):
        if (review_dir / name).exists():
            raise Refused("one rebuttal round is allowed and it already exists")

    config, config_text = load_config(args.config)
    name = receipt["reviewer"]
    if name not in config["reviewers"]:
        raise Refused(f"reviewer {name!r} is not in the configuration")
    reviewer = config["reviewers"][name]
    if receipt["card_kind"] not in reviewer["approved_cards"]:
        raise Refused("the owner's configuration no longer approves this card class")

    reply = read_text(args.reply)
    if not reply.strip():
        raise Refused("the author reply is empty")
    if len(reply) > MAX_CARD_CHARS:
        raise Refused(f"the author reply is limited to {MAX_CARD_CHARS} characters")
    template = read_text(args.prompt)
    message = fill_template(
        template, {"CARD": card, "REPORT": report, "REPLY": reply}
    )

    started = utc_now()
    result = call_reviewer(reviewer, message, args.timeout)
    finished = utc_now()

    write_new_text(review_dir / "rebuttal-message.md", message)
    write_new_text(review_dir / "rebuttal.md", result["output"])
    rebuttal_receipt = base_receipt("rebuttal", name, reviewer, config)
    rebuttal_receipt.update(
        {
            "card_kind": receipt["card_kind"],
            "input_scope": (
                "fixed rebuttal prompt, the card, the preserved report and "
                "the author reply; empty working directory"
            ),
            "working_directory_left_empty": result["working_directory_left_empty"],
            "started_utc": started,
            "finished_utc": finished,
            "sha256": {
                "card": sha256_text(card),
                "report": sha256_text(report),
                "reply": sha256_text(reply),
                "prompt_template": sha256_text(template),
                "message": sha256_text(message),
                "rebuttal": sha256_text(result["output"]),
                "configuration": sha256_text(config_text),
            },
        }
    )
    write_new_text(
        review_dir / "rebuttal-receipt.json",
        json.dumps(rebuttal_receipt, indent=2, sort_keys=True) + "\n",
    )
    return review_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="stage", required=True)

    review = commands.add_parser(
        "review", help="send one card or scope brief to one reviewer"
    )
    review.add_argument("--card", type=Path, required=True)
    review.add_argument("--card-kind", choices=CARD_KINDS, required=True)
    review.add_argument("--reviewer", required=True)
    review.add_argument("--config", type=Path, required=True)
    review.add_argument(
        "--author-family",
        required=True,
        help="provider or model family of the agent that wrote the card",
    )
    review.add_argument("--out-dir", type=Path, required=True)
    review.add_argument(
        "--prompt",
        type=Path,
        help="fixed prompt template; defaults to the one for the card kind",
    )
    review.add_argument(
        "--fallback-decision",
        help="owner decision record allowing a reviewer of the author's family",
    )
    review.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    review.set_defaults(run=run_review)

    rebuttal = commands.add_parser(
        "rebuttal", help="send the author reply for the single rebuttal round"
    )
    rebuttal.add_argument("--review-dir", type=Path, required=True)
    rebuttal.add_argument("--reply", type=Path, required=True)
    rebuttal.add_argument("--config", type=Path, required=True)
    rebuttal.add_argument("--prompt", type=Path, default=DEFAULT_REBUTTAL_PROMPT)
    rebuttal.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    rebuttal.set_defaults(run=run_rebuttal)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        out_dir = args.run(args)
    except Refused as error:
        print(f"refused: {error}", file=sys.stderr)
        return EXIT_REFUSED
    except (ReviewFailed, OSError) as error:
        print(f"failed: {error}", file=sys.stderr)
        return EXIT_FAILED
    print(f"preserved in {out_dir}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
