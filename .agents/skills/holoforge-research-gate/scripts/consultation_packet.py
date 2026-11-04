#!/usr/bin/env python3
"""Preserve a local packet and an owner-returned consultation answer.

No service is contacted. An import attests local byte preservation only;
reported model metadata is supplied by the owner, not a provider receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence


VERSION = 1
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_REFUSED = 2
MESSAGE_HEADER = """# Optional consultation

Answer the exact question in the brief using the supplied physical setup,
equations, assumptions and evidence. Distinguish derivations, source-backed
claims and suggestions; state missing information and unresolved objections.
Your answer is advice for the research owner, not proof, consensus, human
review or permission to change scientific scope or acceptance criteria.
"""


class Refused(Exception):
    """An input or destination cannot be safely preserved."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def local_path(root: Path, relative: str) -> Path:
    """Use explicit relative paths without traversal or symlink components."""
    path = Path(relative)
    if not path.parts or path.is_absolute() or ".." in path.parts:
        raise Refused("paths must name a file or directory within --root")
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise Refused("symlink paths are not allowed")
    return current


def read_utf8(path: Path) -> bytes:
    if not path.is_file():
        raise Refused("each input must be an explicitly named regular file")
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise Refused("inputs and returned answers must be UTF-8 text") from error
    if not text.strip():
        raise Refused("inputs and returned answers must not be empty")
    return data


def new_directory(root: Path, relative: str) -> Path:
    path = local_path(root, relative)
    if path.exists():
        raise Refused("preserved directories are never overwritten; use a new name")
    if not path.parent.is_dir():
        raise Refused("the destination parent directory must already exist")
    path.mkdir(mode=0o700)
    return path


def write_new(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def export_packet(args: argparse.Namespace, root: Path) -> tuple[Path, str]:
    sources = [args.brief, *args.evidence]
    files = [local_path(root, source) for source in sources]
    if len(set(files)) != len(files):
        raise Refused("name each input file only once")
    contents = [read_utf8(path) for path in files]
    inputs = []
    message = MESSAGE_HEADER.encode("utf-8")
    for index, (source, data) in enumerate(zip(sources, contents)):
        name = "brief.md" if index == 0 else f"evidence-{index:03d}.txt"
        inputs.append({"source": str(Path(source)), "snapshot": f"inputs/{name}",
                       "sha256": sha256(data)})
        message += f"\n\n## Supplied file: {name}\n\n".encode("utf-8") + data
    manifest = {
        "version": VERSION,
        "created_utc": utc_now(),
        "author_family": args.author_family,
        "inputs": inputs,
        "message_sha256": sha256(message),
        "action": "local_export_only",
    }
    manifest_bytes = json_bytes(manifest)
    out = new_directory(root, args.out_dir)
    (out / "inputs").mkdir(mode=0o700)
    for record, data in zip(inputs, contents):
        write_new(out / record["snapshot"], data)
    write_new(out / "message.md", message)
    # Written last: a partial export cannot pass the import checks.
    write_new(out / "packet.json", manifest_bytes)
    return out, sha256(manifest_bytes)


def check_packet(packet: Path, expected_hash: str) -> dict:
    manifest_bytes = read_utf8(local_path(packet, "packet.json"))
    if sha256(manifest_bytes) != expected_hash:
        raise Refused("packet manifest differs from the pinned export hash")
    try:
        manifest = json.loads(manifest_bytes)
    except (ValueError, UnicodeDecodeError) as error:
        raise Refused("packet manifest is not valid JSON") from error
    if (not isinstance(manifest, dict) or manifest.get("version") != VERSION
            or manifest.get("action") != "local_export_only"
            or not isinstance(manifest.get("author_family"), str)
            or not isinstance(manifest.get("inputs"), list)
            or not manifest["inputs"]):
        raise Refused("unsupported or incomplete packet manifest")
    expected_inputs = set()
    for index, record in enumerate(manifest["inputs"]):
        name = "brief.md" if index == 0 else f"evidence-{index:03d}.txt"
        if (not isinstance(record, dict)
                or record.get("snapshot") != f"inputs/{name}"
                or not isinstance(record.get("source"), str)):
            raise Refused("packet input paths differ from the export layout")
        expected_inputs.add(name)
        data = read_utf8(local_path(packet, record["snapshot"]))
        if sha256(data) != record.get("sha256"):
            raise Refused("packet input differs from its preserved hash")
    message = read_utf8(local_path(packet, "message.md"))
    if sha256(message) != manifest.get("message_sha256"):
        raise Refused("packet message differs from its preserved hash")
    if ({path.name for path in packet.iterdir()} != {"packet.json", "message.md", "inputs"}
            or {path.name for path in (packet / "inputs").iterdir()} != expected_inputs):
        raise Refused("packet contains files outside its export manifest")
    return manifest


def family_relation(author: str, reported: str) -> str:
    families = [value.strip().casefold() for value in (author, reported)]
    if any(value in ("", "unavailable", "unknown") for value in families):
        return "unavailable"
    return "same_family" if families[0] == families[1] else "different_family_reported"


def import_answer(args: argparse.Namespace, root: Path) -> tuple[Path, str]:
    packet = local_path(root, args.packet_dir)
    manifest = check_packet(packet, args.packet_sha256)
    answer_path = local_path(root, args.answer)
    answer = read_utf8(answer_path)
    destination = local_path(root, args.out_dir)
    if destination == packet or packet in destination.parents:
        raise Refused("the answer destination must be outside the preserved packet")
    receipt = {
        "version": VERSION,
        "imported_utc": utc_now(),
        "action": "local_import_only",
        "outcome": "imported",
        "packet": {"path": str(Path(args.packet_dir)), "sha256": args.packet_sha256},
        "answer": {"source": str(Path(args.answer)), "snapshot": "answer.md",
                   "sha256": sha256(answer), "bytes": len(answer)},
        "owner_reported": {"model": args.reported_model, "mode": args.reported_mode,
                           "family": args.reported_family},
        "family_relation": family_relation(manifest["author_family"], args.reported_family),
        "provider_execution_receipt": "unavailable",
        "external_execution_verified": False,
        "cross_family_independence_verified": False,
    }
    out = new_directory(root, args.out_dir)
    write_new(out / "answer.md", answer)
    write_new(out / "receipt.json", json_bytes(receipt))
    return out, args.packet_sha256


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="stage", required=True)
    export = commands.add_parser("export", help="prepare a local manual-handoff packet")
    returned = commands.add_parser("import", help="preserve an owner-returned answer")
    for command in (export, returned):
        command.add_argument("--root", type=Path, default=Path.cwd(),
                             help="workspace root; all other paths are relative to it")
        command.add_argument("--out-dir", required=True, help="new destination directory")
    export.add_argument("--brief", required=True, help="UTF-8 physics brief and exact question")
    export.add_argument("--evidence", action="append", default=[],
                        help="explicit UTF-8 supporting file; repeat for each file")
    export.add_argument("--author-family", default="unavailable")
    export.set_defaults(run=export_packet)
    returned.add_argument("--packet-dir", required=True)
    returned.add_argument("--packet-sha256", required=True,
                          help="original manifest hash printed by export; keep it separately")
    returned.add_argument("--answer", required=True, help="full returned UTF-8 answer")
    returned.add_argument("--reported-model", default="unavailable")
    returned.add_argument("--reported-mode", default="unavailable")
    returned.add_argument("--reported-family", default="unavailable")
    returned.set_defaults(run=import_answer)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        if not root.is_dir():
            raise Refused("--root must be an existing workspace directory")
        out, digest = args.run(args, root)
    except Refused as error:
        print(f"refused: {error}", file=sys.stderr)
        return EXIT_REFUSED
    except OSError as error:
        print(f"failed: {error.strerror or type(error).__name__}", file=sys.stderr)
        return EXIT_FAILED
    print(f"preserved in {out}\npacket SHA-256: {digest}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
