"""Diagnostics for the Chebyshev differentiation-matrix construction repair.

Implements the frozen plan in
``docs/numerics/chebyshev-construction-repair-plan.md``. Subcommands (each
prints JSON; exit 2 means the diagnostic itself failed):

    python tools/chebyshev_repair.py p0
    python tools/chebyshev_repair.py s0 --build-label B1
    python tools/chebyshev_repair.py select B1.json B3.json
    python tools/chebyshev_repair.py extract RUN_DIR
    python tools/chebyshev_repair.py limits B1-extract.json B3-extract.json
    python tools/chebyshev_repair.py compare BASELINE.json CANDIDATE.json LIMITS.json
    python tools/chebyshev_repair.py s3 --build-label B1

``p0`` is a static check: it reads source and committed records only and
runs no verifier. Nothing here changes a gate, threshold or record.
"""

from __future__ import annotations

import argparse
import ast
from decimal import Decimal, localcontext
import hashlib
import importlib.util
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
try:  # Running from a checkout without installation.
    import holoforge  # noqa: F401
except ImportError:  # pragma: no cover - exercised only outside the test setup
    sys.path.insert(0, str(ROOT / "src"))

from holoforge.core.provenance import runtime_versions

PLAN = Path("docs/numerics/chebyshev-construction-repair-plan.md")
TABLE = Path("docs/generated/chebyshev-repair/regression-table.json")
ROUTINE = "chebyshev_lobatto_grid"
EPS = float(np.finfo(float).eps)
DIGITS = 50


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_table() -> Dict[str, Any]:
    return json.loads((ROOT / TABLE).read_text())


# ---------------------------------------------------------------------------
# P0: structural preflight (static; no verifier, no candidate)
# ---------------------------------------------------------------------------


def resolve_pointer(node: Any, pointer: str) -> List[Any]:
    """Resolve a JSON pointer with ``*`` wildcards (lists and mappings)."""

    def walk(current: Any, parts: Sequence[str]) -> List[Any]:
        if not parts:
            return [current]
        head, rest = parts[0], parts[1:]
        found: List[Any] = []
        if head == "*":
            items = current.values() if isinstance(current, dict) else current if isinstance(current, list) else []
            for item in items:
                found.extend(walk(item, rest))
        elif isinstance(current, dict) and head in current:
            found.extend(walk(current[head], rest))
        elif isinstance(current, list) and head.lstrip("-").isdigit() and -len(current) <= int(head) < len(current):
            found.extend(walk(current[int(head)], rest))
        return found

    return walk(node, [part for part in pointer.split("/") if part])


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def module_call_graph(path: Path) -> Dict[str, set]:
    """Map every function in a module to the names it calls (by AST)."""

    tree = ast.parse(path.read_text())
    graph: Dict[str, set] = {}

    def visit(node: ast.AST, owner: Optional[str]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                graph.setdefault(child.name, set())
                visit(child, child.name)
            else:
                if isinstance(child, ast.Call) and owner is not None:
                    function = child.func
                    if isinstance(function, ast.Name):
                        graph[owner].add(function.id)
                    elif isinstance(function, ast.Attribute):
                        graph[owner].add(function.attr)
                visit(child, owner)

    visit(tree, None)
    return graph


def reachable(graph: Mapping[str, set], start: str) -> set:
    seen, stack = set(), [start]
    while stack:
        name = stack.pop()
        for callee in graph.get(name, ()):
            if callee not in seen:
                seen.add(callee)
                if callee in graph:
                    stack.append(callee)
    return seen


def p0_check() -> Dict[str, Any]:
    """Validate the regression table against source and committed records."""

    table = load_table()
    results = []
    for consumer in table["consumers"]:
        module = ROOT / consumer["module"]
        source = module.read_text()
        graph = module_call_graph(module)
        call_sites = sorted(name for name, callees in graph.items() if ROUTINE in callees)
        checks: Dict[str, Any] = {
            "call_sites": {"found": call_sites, "expected": sorted(consumer["call_sites"]),
                           "passed": call_sites == sorted(consumer["call_sites"])},
        }
        controls = {}
        for function in consumer.get("control_functions", []):
            reach = reachable(graph, function)
            reaches = ROUTINE in reach or bool(reach & set(call_sites))
            controls[function] = {"defined": function in graph, "reaches_routine": reaches}
        checks["control_functions"] = {
            "detail": controls,
            "passed": all(item["defined"] and not item["reaches_routine"] for item in controls.values()),
        }
        if "imports_solver_from" in consumer:
            checks["imports_solver"] = {"passed": f"from {consumer['imports_solver_from']} import" in source}
        missing = [key for key in consumer.get("source_keys", []) if f'"{key}"' not in source]
        checks["source_keys"] = {"missing": missing, "passed": not missing}
        if consumer.get("committed_record"):
            record = json.loads((ROOT / consumer["committed_record"]).read_text())
            pointers = {}
            for pointer in consumer.get("record_pointers", []):
                found = resolve_pointer(record, pointer)
                pointers[pointer] = {"leaves": len(found), "numeric": sum(1 for value in found if _is_number(value))}
            absent = {pointer: len(resolve_pointer(record, pointer)) for pointer in consumer.get("absent_pointers", [])}
            checks["record_pointers"] = {
                "detail": pointers, "absent": absent,
                "passed": all(item["leaves"] > 0 and item["leaves"] == item["numeric"] for item in pointers.values())
                and all(count == 0 for count in absent.values()),
            }
        results.append({"consumer": consumer["id"], "checks": checks,
                        "passed": all(item["passed"] for item in checks.values())})
    return {"table_sha256": _file_sha256(ROOT / TABLE), "consumers": results,
            "passed": all(item["passed"] for item in results)}


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in (sorted(value) if isinstance(value, set) else value)]
    if isinstance(value, np.ndarray):
        return _jsonable(value.tolist())
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return _jsonable(float(value))
    if isinstance(value, (complex, np.complexfloating)):
        value = complex(value)
        return [_jsonable(value.real), _jsonable(value.imag)]
    if isinstance(value, Decimal):
        return _jsonable(float(value))
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


def emit(stage: str, result: Mapping[str, Any], started: float) -> int:
    payload = {
        "tool": "chebyshev-repair",
        "stage": stage,
        "plan": PLAN.as_posix(),
        "plan_sha256": _file_sha256(ROOT / PLAN),
        "tool_sha256": _file_sha256(Path(__file__).resolve()),
        "status": "ok" if result.get("passed", True) and "stopped" not in result else "stopped",
        "runtime": runtime_versions(),
        "wall_seconds": time.perf_counter() - started,
        "result": result,
    }
    print(json.dumps(_jsonable(payload), indent=2, sort_keys=True, allow_nan=False))
    return 0 if payload["status"] == "ok" else 2


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="stage", required=True)
    commands.add_parser("p0")
    args = parser.parse_args(argv)
    started = time.perf_counter()
    if args.stage == "p0":
        return emit("p0", p0_check(), started)
    raise SystemExit(f"unknown stage {args.stage}")


if __name__ == "__main__":
    raise SystemExit(main())
