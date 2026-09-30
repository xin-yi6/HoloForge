"""Summarize how close each declared acceptance gate is to its limit.

Reads verification records written by ``holoforge verify ... --json`` and
reports ``value / limit`` for every top-level check whose criterion has the
single upper-bound form ``... <= LIMIT``. Other criteria (ranges, compound
conditions, Boolean gates) are listed as not parsed rather than guessed.

This is telemetry for comparing platforms and settings. It is not an
acceptance gate: a ratio near one is not a failure, and the verifier's own
``passed`` state remains the only verdict. A legitimate scientific FAIL is
reported normally. A malformed or internally inconsistent record, which
indicates broken execution or evidence rather than a scientific verdict,
makes the command exit with status 2.

Usage:  python tools/gate_margins.py RECORD.json [RECORD.json ...] [--json]

Each record is labelled by the path exactly as given, so downloaded records
with the same file name from different platforms stay distinct. Passing the
same path twice is rejected.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence


_UPPER_BOUND = re.compile(
    r"^[^<>=]*<=\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*$"
)
_COMPOUND = re.compile(r"\b(?:and|or)\b", re.IGNORECASE)


class MalformedRecordError(ValueError):
    """A record that cannot be a valid verifier result."""


def parse_upper_bound(criterion: Any) -> Optional[float]:
    """Return LIMIT for a single ``... <= LIMIT`` criterion, else ``None``."""

    if not isinstance(criterion, str) or _COMPOUND.search(criterion):
        return None
    match = _UPPER_BOUND.match(criterion.strip())
    if match is None:
        return None
    limit = float(match.group(1))
    if not math.isfinite(limit) or limit <= 0.0:
        return None
    return limit


def validate_record(label: str, record: Any) -> None:
    """Reject records that no successful verifier execution could produce."""

    if not isinstance(record, Mapping):
        raise MalformedRecordError(f"{label}: record is not a JSON object")
    if not isinstance(record.get("passed"), bool):
        raise MalformedRecordError(f"{label}: 'passed' is not a Boolean")
    checks = record.get("acceptance_checks")
    if not isinstance(checks, list) or not checks:
        raise MalformedRecordError(f"{label}: 'acceptance_checks' is missing or empty")
    for index, check in enumerate(checks):
        where = f"{label}: acceptance_checks[{index}]"
        if not isinstance(check, Mapping):
            raise MalformedRecordError(f"{where} is not an object")
        if not isinstance(check.get("id"), str) or not check["id"].strip():
            raise MalformedRecordError(f"{where} has no identifier")
        if not isinstance(check.get("passed"), bool):
            raise MalformedRecordError(f"{where} 'passed' is not a Boolean")
        if "value" in check:
            value = check["value"]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise MalformedRecordError(f"{where} 'value' is not a finite number")
    if record["passed"] != all(check["passed"] for check in checks):
        raise MalformedRecordError(
            f"{label}: record verdict disagrees with its acceptance checks"
        )


def summarize(records: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    """Summarize gate margins for validated records keyed by a unique label."""

    parsed: List[Dict[str, Any]] = []
    unparsed: List[Dict[str, Any]] = []
    verdicts: Dict[str, bool] = {}
    for label, record in records.items():
        validate_record(label, record)
        verdicts[label] = record["passed"]
        for check in record["acceptance_checks"]:
            limit = parse_upper_bound(check.get("criterion"))
            entry: Dict[str, Any] = {
                "record": label,
                "id": check["id"],
                "passed": check["passed"],
            }
            if limit is None or "value" not in check:
                entry["criterion"] = check.get("criterion")
                unparsed.append(entry)
                continue
            value = float(check["value"])
            entry.update({"value": value, "limit": limit, "ratio": value / limit})
            parsed.append(entry)
    parsed.sort(key=lambda item: item["ratio"], reverse=True)
    return {"records": verdicts, "gates": parsed, "not_parsed": unparsed}


def render_text(summary: Mapping[str, Any]) -> List[str]:
    lines = ["Record verdicts (scientific results reported by the verifiers):"]
    for label, passed in summary["records"].items():
        lines.append(f"  {label}: {'PASS' if passed else 'FAIL'}")
    lines.append("")
    lines.append("   ratio  passed  record / gate: value <= limit")
    for gate in summary["gates"]:
        lines.append(
            f"{gate['ratio']:8.4f}  {str(gate['passed']):6s}  "
            f"{gate['record']} / {gate['id']}: "
            f"{gate['value']:.6e} <= {gate['limit']:.6e}"
        )
    if summary["not_parsed"]:
        lines.append("")
        lines.append("Not parsed (no single upper bound):")
        for gate in summary["not_parsed"]:
            lines.append(
                f"  {gate['record']} / {gate['id']}: passed={gate['passed']}"
            )
    return lines


def _reject_constants(value: str) -> Any:
    raise ValueError(f"non-finite JSON constant {value}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("records", nargs="+", type=Path)
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)

    records: Dict[str, Any] = {}
    for path in args.records:
        label = path.as_posix()
        if label in records:
            print(f"record {label} was given more than once", file=sys.stderr)
            return 2
        try:
            records[label] = json.loads(
                path.read_text(encoding="utf-8"), parse_constant=_reject_constants
            )
        except (OSError, ValueError) as exc:
            print(f"cannot read verification record {label}: {exc}", file=sys.stderr)
            return 2
    try:
        summary = summarize(records)
    except MalformedRecordError as exc:
        print(f"malformed verification record: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print("\n".join(render_text(summary)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
