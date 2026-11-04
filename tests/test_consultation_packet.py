"""Synthetic local round trips for owner-mediated consultations."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".agents/skills/holoforge-research-gate/scripts/consultation_packet.py"
SPEC = importlib.util.spec_from_file_location("consultation_packet", SCRIPT)
packet = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(packet)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ConsultationPacketTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.brief = "Question: does δX vanish?\r\nEquation: X = Y.\r\n".encode("utf-8")
        self.evidence = b"Synthetic source excerpt; conditional assumptions.\n"
        self.answer = "First line.\r\n\r\n完整回答: δX = 0 conditionally.\r\nLast line.\r\n".encode("utf-8")
        (self.root / "brief.md").write_bytes(self.brief)
        (self.root / "evidence.txt").write_bytes(self.evidence)
        (self.root / "answer-source.md").write_bytes(self.answer)
        self.out = self.root / "packet"
        self.returned = self.root / "returned"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_main(self, *arguments: str) -> tuple[int, str]:
        stderr = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            result = packet.main([arguments[0], "--root", str(self.root), *arguments[1:]])
        return result, stderr.getvalue()

    def export(self, *extra: str) -> tuple[int, str]:
        return self.run_main("export", "--brief", "brief.md", "--evidence", "evidence.txt",
                             "--author-family", "family-a", "--out-dir", "packet", *extra)

    def import_answer(self, *extra: str) -> tuple[int, str]:
        return self.run_main("import", "--packet-dir", "packet", "--packet-sha256", self.digest,
                             "--answer", "answer-source.md", "--out-dir", "returned", *extra)

    def prepare(self) -> None:
        code, error = self.export()
        self.assertEqual(code, packet.EXIT_OK, error)
        self.digest = sha((self.out / "packet.json").read_bytes())

    def test_round_trip_preserves_exact_bytes_and_reported_provenance(self) -> None:
        # Unselected neighboring files must never become packet inputs.
        (self.root / "unselected.txt").write_text("not-for-this-packet", encoding="utf-8")
        self.prepare()
        manifest = json.loads((self.out / "packet.json").read_bytes())
        self.assertEqual(manifest["action"], "local_export_only")
        self.assertEqual(len(manifest["inputs"]), 2)
        for entry, expected in zip(manifest["inputs"], (self.brief, self.evidence)):
            self.assertEqual((self.out / entry["snapshot"]).read_bytes(), expected)
            self.assertEqual(entry["sha256"], sha(expected))
        message = (self.out / "message.md").read_bytes()
        self.assertIn(self.brief, message)
        self.assertIn(self.evidence, message)
        self.assertNotIn(b"not-for-this-packet", message)
        self.assertNotIn(str(self.root).encode(), (self.out / "packet.json").read_bytes())
        self.assertEqual(manifest["message_sha256"], sha(message))
        code, error = self.import_answer("--reported-model", "model-label", "--reported-mode",
                                         "mode-label", "--reported-family", " FAMILY-A ")
        self.assertEqual(code, packet.EXIT_OK, error)
        self.assertEqual((self.returned / "answer.md").read_bytes(), self.answer)
        receipt = json.loads((self.returned / "receipt.json").read_bytes())
        self.assertEqual(receipt["packet"]["sha256"], self.digest)
        self.assertEqual(receipt["answer"]["sha256"], sha(self.answer))
        self.assertEqual(receipt["answer"]["source"], "answer-source.md")
        self.assertEqual(receipt["answer"]["bytes"], len(self.answer))
        self.assertEqual(receipt["action"], "local_import_only")
        self.assertEqual(receipt["outcome"], "imported")
        self.assertEqual(receipt["owner_reported"]["model"], "model-label")
        self.assertEqual(receipt["owner_reported"]["mode"], "mode-label")
        self.assertEqual(receipt["family_relation"], "same_family")
        self.assertEqual(receipt["provider_execution_receipt"], "unavailable")
        self.assertFalse(receipt["external_execution_verified"])
        self.assertFalse(receipt["cross_family_independence_verified"])
        if os.name == "posix":
            for path in (self.out, self.out / "inputs", self.returned):
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)
            for path in (*self.out.rglob("*"), *self.returned.iterdir()):
                if path.is_file():
                    self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_unavailable_and_different_family_metadata_do_not_attest_independence(self) -> None:
        self.prepare()
        for index, flags in enumerate(((), ("--reported-family", "family-b"))):
            with self.subTest(flags=flags):
                name = f"returned-{index}"
                code, error = self.import_answer("--out-dir", name, *flags)
                self.assertEqual(code, packet.EXIT_OK, error)
                receipt = json.loads((self.root / name / "receipt.json").read_bytes())
                expected = "different_family_reported" if flags else "unavailable"
                self.assertEqual(receipt["family_relation"], expected)
                self.assertEqual(receipt["owner_reported"]["mode"], "unavailable")
                self.assertFalse(receipt["cross_family_independence_verified"])

    def test_original_inputs_can_change_after_the_packet_is_sealed(self) -> None:
        self.prepare()
        (self.root / "brief.md").write_text("later draft", encoding="utf-8")
        (self.root / "evidence.txt").unlink()
        self.assertEqual(self.import_answer()[0], packet.EXIT_OK)
        self.assertEqual((self.out / "inputs/brief.md").read_bytes(), self.brief)

    def test_export_and_import_refuse_existing_destinations(self) -> None:
        self.prepare()
        before = (self.out / "packet.json").read_bytes()
        self.assertEqual(self.export()[0], packet.EXIT_REFUSED)
        self.assertEqual((self.out / "packet.json").read_bytes(), before)
        self.assertEqual(self.import_answer()[0], packet.EXIT_OK)
        (self.root / "answer-source.md").write_text("new answer", encoding="utf-8")
        self.assertEqual(self.import_answer()[0], packet.EXIT_REFUSED)
        self.assertEqual((self.returned / "answer.md").read_bytes(), self.answer)

    def test_each_modified_or_missing_packet_artifact_is_refused(self) -> None:
        self.prepare()
        for relative in ("packet.json", "message.md", "inputs/brief.md", "inputs/evidence-001.txt"):
            path = self.out / relative
            original = path.read_bytes()
            for replacement in (b"modified", None):
                with self.subTest(relative=relative, replacement=replacement):
                    if replacement is None:
                        path.unlink()
                    else:
                        path.write_bytes(replacement)
                    self.assertEqual(self.import_answer()[0], packet.EXIT_REFUSED)
                    self.assertFalse(self.returned.exists())
                    path.write_bytes(original)

    def test_rehashing_an_altered_packet_does_not_match_the_original_pin(self) -> None:
        self.prepare()
        manifest_path = self.out / "packet.json"
        manifest = json.loads(manifest_path.read_bytes())
        changed = b"replaced input"
        (self.out / "inputs/brief.md").write_bytes(changed)
        manifest["inputs"][0]["sha256"] = sha(changed)
        manifest_path.write_bytes(packet.json_bytes(manifest))
        code, error = self.import_answer()
        self.assertEqual(code, packet.EXIT_REFUSED)
        self.assertIn("pinned export hash", error)

    def test_extra_packet_files_and_nested_output_are_refused(self) -> None:
        self.prepare()
        for relative in ("extra.md", "inputs/extra.txt"):
            with self.subTest(relative=relative):
                extra = self.out / relative
                extra.write_text("extra", encoding="utf-8")
                self.assertEqual(self.import_answer()[0], packet.EXIT_REFUSED)
                extra.unlink()
        code, error = self.import_answer("--out-dir", "packet/returned")
        self.assertEqual(code, packet.EXIT_REFUSED)
        self.assertIn("outside the preserved packet", error)

    def test_malformed_manifests_and_injected_snapshot_paths_are_refused(self) -> None:
        self.prepare()
        manifest_path = self.out / "packet.json"
        original = json.loads(manifest_path.read_bytes())
        invalid = (b"{", b"[]", b"{}", packet.json_bytes({**original, "inputs": []}),
                   packet.json_bytes({**original, "inputs": [{"source": "brief.md",
                       "snapshot": "../answer-source.md", "sha256": sha(self.answer)}]}))
        for data in invalid:
            with self.subTest(data=data):
                manifest_path.write_bytes(data)
                code, _ = self.import_answer("--packet-sha256", sha(data))
                self.assertEqual(code, packet.EXIT_REFUSED)
                self.assertFalse(self.returned.exists())

    def test_input_output_and_answer_path_escapes_are_refused(self) -> None:
        for flags in (("--brief", "../brief.md"), ("--brief", str(self.root / "brief.md")),
                      ("--out-dir", "../escaped"), ("--out-dir", ".")):
            with self.subTest(flags=flags):
                self.assertEqual(self.export(*flags)[0], packet.EXIT_REFUSED)
                self.assertFalse(self.out.exists())
        self.prepare()
        for flags in (("--answer", "../answer-source.md"), ("--out-dir", "../escaped"),
                      ("--packet-dir", "../packet")):
            with self.subTest(flags=flags):
                self.assertEqual(self.import_answer(*flags)[0], packet.EXIT_REFUSED)
                self.assertFalse(self.returned.exists())

    def test_symlink_inputs_destinations_and_parent_paths_are_refused(self) -> None:
        (self.root / "brief-link.md").symlink_to(self.root / "brief.md")
        (self.root / "dir-link").symlink_to(self.root, target_is_directory=True)
        (self.root / "dangling").symlink_to(self.root / "missing")
        for flags in (("--brief", "brief-link.md"), ("--out-dir", "dangling"),
                      ("--out-dir", "dir-link/new"), ("--brief", "dir-link/brief.md")):
            with self.subTest(flags=flags):
                self.assertEqual(self.export(*flags)[0], packet.EXIT_REFUSED)
                self.assertFalse(self.out.exists())
        self.prepare()
        for flags in (("--answer", "brief-link.md"), ("--out-dir", "dir-link/new"),
                      ("--packet-dir", "dir-link/packet")):
            with self.subTest(flags=flags):
                self.assertEqual(self.import_answer(*flags)[0], packet.EXIT_REFUSED)
                self.assertFalse(self.returned.exists())

    def test_symlink_replacement_inside_packet_is_refused_even_with_matching_bytes(self) -> None:
        self.prepare()
        brief = self.out / "inputs/brief.md"
        brief.unlink()
        brief.symlink_to(self.root / "brief.md")
        self.assertEqual(self.import_answer()[0], packet.EXIT_REFUSED)
        self.assertFalse(self.returned.exists())

    def test_empty_invalid_utf8_directory_glob_and_duplicate_inputs_are_refused(self) -> None:
        for data in (b"", b" \r\n\t", b"invalid \xff"):
            with self.subTest(data=data):
                (self.root / "brief.md").write_bytes(data)
                self.assertEqual(self.export()[0], packet.EXIT_REFUSED)
                self.assertFalse(self.out.exists())
        (self.root / "brief.md").write_bytes(self.brief)
        (self.root / "directory").mkdir()
        for flags in (("--brief", "directory"), ("--brief", "*.md"),
                      ("--evidence", "brief.md"), ("--out-dir", "missing/new")):
            with self.subTest(flags=flags):
                self.assertEqual(self.export(*flags)[0], packet.EXIT_REFUSED)
                self.assertFalse(self.out.exists())

    def test_empty_or_invalid_utf8_returned_answers_are_refused(self) -> None:
        self.prepare()
        for data in (b"", b" \r\n\t", b"answer \xff"):
            with self.subTest(data=data):
                (self.root / "answer-source.md").write_bytes(data)
                self.assertEqual(self.import_answer()[0], packet.EXIT_REFUSED)
                self.assertFalse(self.returned.exists())

    def test_partial_write_is_not_overwritten_or_mistaken_for_an_import(self) -> None:
        self.prepare()
        original_write = packet.write_new

        def fail_receipt(path: Path, data: bytes) -> None:
            if path.name == "receipt.json":
                raise OSError("synthetic persistence failure")
            original_write(path, data)

        with mock.patch.object(packet, "write_new", side_effect=fail_receipt):
            self.assertEqual(self.import_answer()[0], packet.EXIT_FAILED)
        self.assertEqual((self.returned / "answer.md").read_bytes(), self.answer)
        self.assertFalse((self.returned / "receipt.json").exists())
        self.assertEqual(self.import_answer()[0], packet.EXIT_REFUSED)

    def test_cli_exports_without_a_service_or_reviewer_configuration(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "export", "--root", str(self.root),
             "--brief", "brief.md", "--out-dir", "packet"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(completed.returncode, packet.EXIT_OK, completed.stderr)
        digest = sha((self.out / "packet.json").read_bytes())
        self.assertIn(f"packet SHA-256: {digest}", completed.stdout)
        self.assertEqual(json.loads((self.out / "packet.json").read_bytes())["author_family"],
                         "unavailable")


if __name__ == "__main__":
    unittest.main()
