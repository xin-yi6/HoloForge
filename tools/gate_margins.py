"""Summarize how close each declared acceptance gate is to its limit.

Reads verification records written by ``holoforge verify ... --json`` and
reports ``value / limit`` for every top-level check whose criterion has the
single upper-bound form ``... <= LIMIT``. Other criteria (ranges, compound
conditions, Boolean gates) are listed as not parsed rather than guessed.

This is telemetry for comparing platforms and settings. It is not an
acceptance gate: a ratio near one is not a failure, and the verifier's own
``passed`` state remains the only verdict.

Usage:  python tools/gate_margins.py RECORD.json [RECORD.json ...] [--json]
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


def summarize(records: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    """Summarize gate margins for records keyed by a display label."""

    parsed: List[Dict[str, Any]] = []
    unparsed: List[Dict[str, Any]] = []
    verdicts: Dict[str, Any] = {}
    for label, record in records.items():
        verdicts[label] = record.get("passed")
        for check in record.get("acceptance_checks", []):
            limit = parse_upper_bound(check.get("criterion"))
            value = check.get("value")
            entry = {
                "record": label,
                "id": check.get("id"),
                "passed": check.get("passed"),
            }
            if limit is None or not isinstance(value, (int, float)):
                entry["criterion"] = check.get("criterion")
                unparsed.append(entry)
                continue
            entry.update(
                {"value": float(value), "limit": limit, "ratio": float(value) / limit}
            )
            parsed.append(entry)
    parsed.sort(key=lambda item: item["ratio"], reverse=True)
    return {"records": verdicts, "gates": parsed, "not_parsed": unparsed}


def render_text(summary: Mapping[str, Any]) -> List[str]:
    lines = ["Record verdicts (from the verifiers):"]
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


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("records", nargs="+", type=Path)
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)

    records = {}
    for path in args.records:
        try:
            records[path.name] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"cannot read verification record {path.name}: {exc}", file=sys.stderr)
            return 2
    summary = summarize(records)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print("\n".join(render_text(summary)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
