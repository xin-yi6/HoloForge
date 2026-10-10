"""Tests for the owner-gated question-review runner."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


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
        return self.run_main(*self.review_args(
            *extra, card_kind=card_kind, author=author,
        ))

    def review_args(self, *extra: str, card_kind: str = "question",
                    author: str = "family-a") -> tuple[str, ...]:
        return (
            "review", "--card", str(self.card), "--card-kind", card_kind,
            "--reviewer", "rev", "--config", str(self.config),
            "--author-family", author, "--out-dir", str(self.out), *extra,
        )

    def receipt(self, prefix: str = "") -> dict:
        return json.loads((self.out / f"{prefix}receipt.json")
                          .read_text(encoding="utf-8"))

    def assert_raw_stream(self, receipt: dict, stream: str, expected: bytes,
                          prefix: str = "") -> None:
        relative = f"{prefix}{stream}.raw"
        artifact = self.out / relative
        self.assertEqual(artifact.read_bytes(), expected)
        metadata = receipt["raw_streams"][stream]
        self.assertEqual(metadata["path"], relative)
        self.assertEqual(metadata["bytes"], len(expected))
        self.assertEqual(metadata["sha256"], hashlib.sha256(expected).hexdigest())
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(artifact.stat().st_mode), 0o600)

    def wait_for_file(self, path: Path, child: subprocess.Popen,
                      timeout: float = 5.0) -> None:
        until = time.monotonic() + timeout
        while time.monotonic() < until:
            if path.exists() and path.stat().st_size:
                return
            if child.poll() is not None:
                self.fail(f"runner exited before {path.name}: {child.returncode}")
            time.sleep(0.01)
        self.fail(f"runner did not create {path.name}")

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
        self.assertEqual(receipt["runner_version"], 2)
        self.assertEqual(receipt["outcome"], "completed")
        self.assertTrue(receipt["process_started"])
        self.assertEqual(receipt["returncode"], 0)
        self.assertIsNone(receipt["timeout_seconds"])
        self.assertTrue((self.out / "start.json").is_file())
        self.assertTrue((self.out / "process.json").is_file())
        self.assert_raw_stream(receipt, "stdout", report.encode("utf-8"))
        self.assert_raw_stream(receipt, "stderr", b"")

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

    def test_failed_reviewer_preserves_diagnostics_without_echoing_them(self) -> None:
        self.config = self.write_config(command=[
            sys.executable, "-c", "import sys; "
            "sys.stdout.write('partial answer\\n'); "
            "sys.stderr.write('private diagnostic value'); sys.exit(3)",
        ])
        code, err = self.review()
        self.assertEqual(code, runner.EXIT_FAILED)
        self.assertNotIn("private diagnostic value", err)
        self.assertFalse((self.out / "report.md").exists())
        receipt = self.receipt()
        self.assertEqual(receipt["outcome"], "nonzero_exit")
        self.assertEqual(receipt["returncode"], 3)
        self.assertTrue(receipt["process_started"])
        self.assert_raw_stream(receipt, "stdout", b"partial answer\n")
        self.assert_raw_stream(receipt, "stderr", b"private diagnostic value")
        before = (self.out / "start.json").read_bytes()
        self.assertEqual(self.review()[0], runner.EXIT_REFUSED)
        self.assertEqual((self.out / "start.json").read_bytes(), before)

    def test_timeout_is_optional_and_must_be_finite_and_positive(self) -> None:
        self.assertIsNone(runner.DEFAULT_TIMEOUT_SECONDS)
        parsed = runner.build_parser().parse_args(self.review_args())
        self.assertIsNone(parsed.timeout)
        for value in ("0", "-1", "nan", "inf", "-inf", "nonsense"):
            with self.subTest(value=value):
                with contextlib.redirect_stderr(io.StringIO()):
                    try:
                        code = runner.main(list(self.review_args(f"--timeout={value}")))
                    except SystemExit as error:
                        code = error.code
                self.assertNotEqual(code, 0)
                self.assertFalse(self.out.exists())

    def test_explicit_fractional_deadline_preserves_partial_output(self) -> None:
        self.config = self.write_config(command=[
            sys.executable, "-c", "import sys, time; "
            "sys.stdout.write('partial\\n'); sys.stdout.flush(); "
            "sys.stderr.write('progress\\n'); sys.stderr.flush(); time.sleep(30)",
        ])
        code, err = self.review("--timeout", "0.4")
        self.assertEqual(code, runner.EXIT_FAILED, err)
        receipt = self.receipt()
        self.assertEqual(receipt["outcome"], "timeout")
        self.assertEqual(receipt["timeout_seconds"], 0.4)
        self.assertTrue(receipt["process_started"])
        self.assertIsNotNone(receipt["returncode"])
        self.assert_raw_stream(receipt, "stdout", b"partial\n")
        self.assert_raw_stream(receipt, "stderr", b"progress\n")
        self.assertFalse((self.out / "report.md").exists())
        self.assertEqual(self.review()[0], runner.EXIT_REFUSED)

    def test_missing_executable_has_a_durable_launch_failure(self) -> None:
        self.config = self.write_config(command=[str(self.dir / "missing-command")])
        code, err = self.review()
        self.assertEqual(code, runner.EXIT_FAILED, err)
        receipt = self.receipt()
        self.assertEqual(receipt["outcome"], "launch_error")
        self.assertFalse(receipt["process_started"])
        self.assertIsNone(receipt["returncode"])
        self.assertTrue((self.out / "start.json").is_file())
        self.assertFalse((self.out / "report.md").exists())
        self.assert_raw_stream(receipt, "stdout", b"")
        self.assert_raw_stream(receipt, "stderr", b"")

    def test_report_write_failure_retains_raw_result_and_terminal_receipt(self) -> None:
        self.config = self.write_config(command=[
            sys.executable, "-c", "print('finished answer')",
        ])
        with mock.patch.object(
            runner, "copy_report",
            side_effect=OSError("synthetic report persistence failure"),
        ):
            code, err = self.review()
        self.assertEqual(code, runner.EXIT_FAILED, err)
        receipt = self.receipt()
        self.assertEqual(receipt["outcome"], "local_error")
        self.assertTrue(receipt["process_started"])
        self.assertEqual(receipt["returncode"], 0)
        self.assert_raw_stream(receipt, "stdout", b"finished answer\n")
        self.assertFalse((self.out / "report.md").exists())
        self.assertNotIn("report", receipt["sha256"])
        self.assertEqual(self.review()[0], runner.EXIT_REFUSED)

    def test_empty_and_invalid_reports_keep_raw_bytes_without_a_report(self) -> None:
        cases = ((b"", "empty_output"), (b" \r\n\t", "empty_output"),
                 (b"answer\xff\n", "invalid_output"))
        for index, (payload, outcome) in enumerate(cases):
            with self.subTest(outcome=outcome, payload=payload):
                self.out = self.dir / f"invalid-{index}"
                self.config = self.write_config(command=[
                    sys.executable, "-c", "import sys; "
                    f"sys.stdout.buffer.write({payload!r})",
                ])
                code, err = self.review()
                self.assertEqual(code, runner.EXIT_FAILED, err)
                receipt = self.receipt()
                self.assertEqual(receipt["outcome"], outcome)
                self.assertEqual(receipt["returncode"], 0)
                self.assert_raw_stream(receipt, "stdout", payload)
                self.assertFalse((self.out / "report.md").exists())

    def test_report_bytes_keep_crlf_and_large_dual_streams(self) -> None:
        count = 2 * 1024 * 1024
        self.config = self.write_config(command=[
            sys.executable, "-c", "import sys; "
            f"sys.stdout.buffer.write(b'x' * {count} + b'\\r\\n'); "
            f"sys.stderr.buffer.write(b'y' * {count} + b'\\r\\n')",
        ])
        code, err = self.review("--timeout", "10")
        self.assertEqual(code, runner.EXIT_OK, err)
        receipt = self.receipt()
        stdout = b"x" * count + b"\r\n"
        self.assertEqual((self.out / "report.md").read_bytes(), stdout)
        self.assert_raw_stream(receipt, "stdout", stdout)
        self.assert_raw_stream(receipt, "stderr", b"y" * count + b"\r\n")
        self.assertEqual(receipt["sha256"]["report"], hashlib.sha256(stdout).hexdigest())

    def test_inputs_and_start_record_exist_before_reviewer_runs(self) -> None:
        self.config = self.write_config(command=[
            sys.executable, "-c", "import pathlib, sys; "
            "root = pathlib.Path(sys.argv[1]); "
            "assert all((root / name).is_file() "
            "for name in ('start.json', 'card.md', 'message.md')); "
            "assert (root / 'message.md').read_bytes() == sys.stdin.buffer.read(); "
            "print('snapshots verified')", str(self.out),
        ])
        code, err = self.review()
        self.assertEqual(code, runner.EXIT_OK, err)

    def test_incomplete_attempt_cannot_be_repeated(self) -> None:
        self.out.mkdir()
        (self.out / "start.json").write_text('{"outcome": "started"}\n',
                                            encoding="utf-8")
        code, err = self.review()
        self.assertEqual(code, runner.EXIT_REFUSED, err)
        self.assertFalse((self.out / "process.json").exists())
        self.assertFalse((self.out / "report.md").exists())

    @unittest.skipUnless(os.name == "posix", "POSIX signal and permissions test")
    def test_running_attempt_refuses_second_dispatch_and_sigterm_is_recorded(self) -> None:
        self.assert_signal_cancellation(signal.SIGTERM)

    @unittest.skipUnless(os.name == "posix", "POSIX signal and permissions test")
    def test_sigint_preserves_cancellation_and_partial_output(self) -> None:
        self.assert_signal_cancellation(signal.SIGINT)

    @unittest.skipUnless(os.name == "posix", "POSIX spawn cancellation test")
    def test_signal_during_spawn_preserves_child_identity_and_reaps_it(self) -> None:
        self.config = self.write_config(command=[
            sys.executable, "-c", "import time; time.sleep(30)",
        ])
        real_popen = subprocess.Popen
        children = []
        previous_handler = signal.getsignal(signal.SIGTERM)

        def spawn_then_cancel(*args, **kwargs):
            child = real_popen(*args, **kwargs)
            children.append(child)
            # Fail safely instead of terminating the test runner if cancellation
            # handling ever regresses to the OS default inside this window.
            self.assertNotEqual(signal.getsignal(signal.SIGTERM), signal.SIG_DFL)
            self.assertNotEqual(signal.getsignal(signal.SIGTERM), signal.SIG_IGN)
            os.kill(os.getpid(), signal.SIGTERM)
            return child

        try:
            with mock.patch.object(runner.subprocess, "Popen",
                                   side_effect=spawn_then_cancel):
                code, err = self.review()
            self.assertEqual(code, runner.EXIT_FAILED, err)
            self.assertEqual(len(children), 1)
            receipt = self.receipt()
            self.assertEqual(receipt["outcome"], "cancelled")
            self.assertTrue(receipt["process_started"])
            process_record = json.loads((self.out / "process.json").read_text())
            self.assertEqual(process_record["pid"], children[0].pid)
            self.assertIsNotNone(children[0].poll())
            self.assertEqual(receipt["returncode"], children[0].returncode)
            self.assertFalse((self.out / "report.md").exists())
            self.assertEqual(signal.getsignal(signal.SIGTERM), previous_handler)
        finally:
            for child in children:
                if child.poll() is None:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                child.wait(timeout=5)

    def assert_signal_cancellation(self, signum: int) -> None:
        self.config = self.write_config(command=[
            sys.executable, "-c", "import sys, time; "
            "print('ready', flush=True); time.sleep(30)",
        ])
        child = subprocess.Popen([sys.executable, str(SCRIPT), *self.review_args()],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        process_pid = None
        try:
            self.wait_for_file(self.out / "process.json", child)
            process_pid = json.loads((self.out / "process.json").read_text())["pid"]
            self.wait_for_file(self.out / "stdout.raw", child)
            started = (self.out / "start.json").read_bytes()
            self.assertEqual(self.review()[0], runner.EXIT_REFUSED)
            self.assertEqual((self.out / "start.json").read_bytes(), started)
            child.send_signal(signum)
            self.assertNotEqual(child.wait(timeout=8), 0)
            receipt = self.receipt()
            self.assertEqual(receipt["outcome"], "cancelled")
            self.assertTrue(receipt["process_started"])
            self.assert_raw_stream(receipt, "stdout", b"ready\n")
            self.assertFalse((self.out / "report.md").exists())
            with self.assertRaises(ProcessLookupError):
                os.kill(process_pid, 0)
        finally:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=5)
            if process_pid is not None:
                try:
                    os.killpg(process_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    @unittest.skipUnless(os.name == "posix", "POSIX symlink test")
    def test_broken_artifact_symlink_is_not_followed_or_replaced(self) -> None:
        self.out.mkdir()
        target = self.dir / "never-created"
        (self.out / "start.json").symlink_to(target)
        code, err = self.review()
        self.assertEqual(code, runner.EXIT_REFUSED, err)
        self.assertTrue((self.out / "start.json").is_symlink())
        self.assertFalse(target.exists())

    @unittest.skipUnless(os.name == "posix", "POSIX process-group cleanup test")
    def test_finished_leader_cleans_descendant_before_hashing_raw_output(self) -> None:
        for returncode in (0, 3):
            with self.subTest(returncode=returncode):
                self.out = self.dir / f"descendant-{returncode}"
                heartbeat = self.dir / f"heartbeat-{returncode}"
                pid_file = self.dir / f"descendant-pid-{returncode}"
                descendant_source = (
                    "import os, pathlib, signal, sys, time\n"
                    "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
                    f"pathlib.Path({str(pid_file)!r}).write_text(str(os.getpid()))\n"
                    f"heartbeat = pathlib.Path({str(heartbeat)!r})\n"
                    "while True:\n"
                    "    with heartbeat.open('ab') as handle:\n"
                    "        handle.write(b'.')\n"
                    "    print('pulse', flush=True)\n"
                    "    time.sleep(0.01)\n"
                )
                leader_source = (
                    "import pathlib, subprocess, sys, time\n"
                    f"subprocess.Popen([sys.executable, '-c', {descendant_source!r}])\n"
                    f"heartbeat = pathlib.Path({str(heartbeat)!r})\n"
                    "until = time.monotonic() + 5\n"
                    "while not heartbeat.exists() and time.monotonic() < until:\n"
                    "    time.sleep(0.01)\n"
                    "assert heartbeat.exists(), 'descendant did not start'\n"
                    "print('leader done', flush=True)\n"
                    f"sys.exit({returncode})\n"
                )
                self.config = self.write_config(command=[
                    sys.executable, "-c", leader_source,
                ])
                try:
                    code, err = self.review("--timeout", "8")
                    expected = runner.EXIT_OK if returncode == 0 else runner.EXIT_FAILED
                    self.assertEqual(code, expected, err)
                    receipt = self.receipt()
                    outcome = "completed" if returncode == 0 else "nonzero_exit"
                    self.assertEqual(receipt["outcome"], outcome)
                    self.assertEqual(receipt["returncode"], returncode)
                    raw_before = (self.out / "stdout.raw").read_bytes()
                    heartbeat_before = heartbeat.read_bytes()
                    time.sleep(0.15)
                    self.assertEqual(heartbeat.read_bytes(), heartbeat_before)
                    self.assert_raw_stream(receipt, "stdout", raw_before)
                    self.assertIn(b"leader done\n", raw_before)
                finally:
                    if pid_file.exists():
                        try:
                            os.kill(int(pid_file.read_text()), signal.SIGKILL)
                        except ProcessLookupError:
                            pass

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
        self.assertEqual(receipt["outcome"], "completed")
        self.assertEqual(receipt["sha256"]["reply"], sha(reply.read_text(encoding="utf-8")))
        self.assertTrue((self.out / "rebuttal-start.json").is_file())
        self.assertTrue((self.out / "rebuttal-process.json").is_file())
        self.assert_raw_stream(receipt, "stdout",
                               (self.out / "rebuttal.md").read_bytes(), "rebuttal-")
        self.assert_raw_stream(receipt, "stderr", b"", "rebuttal-")

        code, err = self.run_main(*args)
        self.assertEqual(code, runner.EXIT_REFUSED)
        self.assertIn("one rebuttal round", err)

    def test_failed_initial_review_cannot_receive_rebuttal(self) -> None:
        self.config = self.write_config(command=FAILING_REVIEWER)
        self.assertEqual(self.review()[0], runner.EXIT_FAILED)
        reply = self.dir / "reply.md"
        reply.write_text("Item 1: clarification.\n", encoding="utf-8")
        self.config = self.write_config()
        code, err = self.run_main(
            "rebuttal", "--review-dir", str(self.out), "--reply", str(reply),
            "--config", str(self.config),
        )
        self.assertEqual(code, runner.EXIT_REFUSED, err)
        self.assertFalse((self.out / "rebuttal-start.json").exists())

    def test_failed_rebuttal_preserves_initial_review_and_consumes_round(self) -> None:
        self.assertEqual(self.review()[0], runner.EXIT_OK)
        original = {name: (self.out / name).read_bytes()
                    for name in ("start.json", "receipt.json", "report.md",
                                 "card.md", "message.md", "stdout.raw", "stderr.raw")}
        reply = self.dir / "reply.md"
        reply.write_text("Item 1: clarification.\n", encoding="utf-8")
        self.config = self.write_config(command=FAILING_REVIEWER)
        args = ("rebuttal", "--review-dir", str(self.out), "--reply", str(reply),
                "--config", str(self.config))
        code, err = self.run_main(*args)
        self.assertEqual(code, runner.EXIT_FAILED, err)
        receipt = self.receipt("rebuttal-")
        self.assertEqual(receipt["outcome"], "nonzero_exit")
        self.assert_raw_stream(receipt, "stdout", b"", "rebuttal-")
        self.assert_raw_stream(receipt, "stderr", b"no login", "rebuttal-")
        self.assertFalse((self.out / "rebuttal.md").exists())
        self.config = self.write_config()
        self.assertEqual(self.run_main(*args)[0], runner.EXIT_REFUSED)
        for name, before in original.items():
            with self.subTest(name=name):
                self.assertEqual((self.out / name).read_bytes(), before)

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
