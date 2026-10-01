"""Diagnostics for the Chebyshev differentiation-matrix construction repair.

Implements the frozen plan in
``docs/numerics/chebyshev-construction-repair-plan.md``. Subcommands (each
prints JSON; exit 2 means the diagnostic itself failed):

    python tools/chebyshev_repair.py p0
    python tools/chebyshev_repair.py p0-revalidate
    python tools/chebyshev_repair.py s0 --build-label B1
    python tools/chebyshev_repair.py build-agreement --arrays DIR --other-label B3 --s0 B1.json B3.json
    python tools/chebyshev_repair.py select B1.json B3.json --build-agreement AGREEMENT.json

``p0`` and ``p0-revalidate`` are static checks: they read source, committed
records and synthetic records only, and run no verifier. ``select`` admits
only complete, successful evidence of both builds and then applies the
frozen rule. ``qualification_v2`` is a proposed amendment and is not used
by any stage. Nothing here changes a gate, threshold or record.
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
# Regression-table extraction (plan Section 8.2) and P0 revalidation
# ---------------------------------------------------------------------------
#
# Each extractor returns ``{"leaves", "controls", "report_only"}``. A leaf is
# ``{"value", "estimators": {name: absolute value}}``; complex values are
# Python complex numbers. Missing fields, duplicate keys and unmatched states
# raise ``ExtractionError``: nothing is skipped silently.

SYNTHETIC_RECORDS = Path("docs/generated/chebyshev-repair/synthetic-records")
CHIRAL_OBSERVABLES = ("m_pi_MeV", "m_rho_MeV", "m_a1_MeV", "f_pi_MeV", "sqrt_F_rho_MeV", "sqrt_F_a1_MeV", "g_rho_pi_pi")
GR_NAME_MAP = {"mu_bh": "mu_bh", "energy_density": "hat_epsilon", "entropy_density": "hat_s",
               "charge_density": "hat_rho", "temperature": "temperature", "chemical_potential": "Omega"}
DGR_FIELDS = ("temperature_BH", "entropy_BH", "susceptibility_integral", "chi_2_over_T2_BH")
DGR_POINT_FIELDS = ("temperature_BH", "mu_BH", "entropy_BH", "rho_canonical_BH")
DGR_CRITICAL_FIELDS = ("phi_H", "eta", "T_BH", "mu_BH", "rho_canonical_BH")
SOFT_WALL_TABLE = ("spectral-40", "spectral-56", "spectral-64", "spectral-100", "spectral-64-modes-6")
SOFT_WALL_VERDICT = ("spectral-64-zmax-4", "spectral-64-zmax-6")


class ExtractionError(RuntimeError):
    pass


def expand_pointer(pointer: str) -> List[str]:
    """Expand ``{a,b}`` alternatives in a pointer."""

    start = pointer.find("{")
    if start < 0:
        return [pointer]
    end = pointer.index("}", start)
    expanded: List[str] = []
    for choice in pointer[start + 1:end].split(","):
        expanded.extend(expand_pointer(pointer[:start] + choice.strip() + pointer[end + 1:]))
    return expanded


def resolve_strict(node: Any, pointer: str) -> Tuple[List[Any], int]:
    """Resolve a pointer and count the wildcard elements that lack the path.

    Unlike ``resolve_pointer``, an element under ``*`` that does not contain
    the remaining path is counted as missing, and an empty container under
    ``*`` counts as one missing element.
    """

    missing = 0

    def walk(current: Any, parts: Sequence[str]) -> List[Any]:
        nonlocal missing
        if not parts:
            return [current]
        head, rest = parts[0], parts[1:]
        if head == "*":
            items = list(current.values()) if isinstance(current, dict) else current if isinstance(current, list) else None
            if not items:
                missing += 1
                return []
            found: List[Any] = []
            for item in items:
                found.extend(walk(item, rest))
            return found
        if isinstance(current, dict) and head in current:
            return walk(current[head], rest)
        if isinstance(current, list) and head.lstrip("-").isdigit() and -len(current) <= int(head) < len(current):
            return walk(current[int(head)], rest)
        missing += 1
        return []

    values = walk(node, [part for part in pointer.split("/") if part])
    return values, missing


def _number(value: Any, what: str) -> float:
    if not _is_number(value) or not math.isfinite(float(value)):
        raise ExtractionError(f"{what} is not a finite number")
    return float(value)


def _get(node: Any, *path: Any) -> Any:
    current = node
    for part in path:
        try:
            current = current[part]
        except (KeyError, IndexError, TypeError):
            raise ExtractionError(f"missing {'/'.join(str(item) for item in path)}") from None
    return current


def _add(target: Dict[str, Any], key: str, value: Any) -> None:
    if key in target:
        raise ExtractionError(f"duplicate key {key}")
    target[key] = value


def _leaf(value: Any, estimators: Mapping[str, float]) -> Dict[str, Any]:
    cleaned = {name: _number(item, f"estimator {name}") for name, item in estimators.items()}
    if not cleaned:
        raise ExtractionError("a table leaf has no estimator")
    if any(item < 0.0 for item in cleaned.values()):
        raise ExtractionError("an estimator is negative")
    return {"value": value, "estimators": cleaned}


def _complex(record: Any, what: str) -> complex:
    return complex(_number(_get(record, "real"), what), _number(_get(record, "imag"), what))


def extract_soft_wall(records: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Dict[str, Any]] = {"leaves": {}, "controls": {}, "report_only": {}}
    for command in SOFT_WALL_TABLE:
        record = _get(records, command)
        if _get(record, "numerical_method", "route") != "spectral":
            raise ExtractionError(f"{command} is not a spectral record")
        for row in _get(record, "results"):
            value = _number(_get(row, "numerical_mass_squared_gev2"), "eigenvalue")
            analytic = _number(_get(row, "analytic_mass_squared_gev2"), "analytic eigenvalue")
            relative = _number(_get(row, "relative_error"), "relative error")
            if abs(abs(value - analytic) / analytic - relative) > 1.0e-9 * max(relative, EPS):
                raise ExtractionError(f"{command}: relative_error is not abs(numerical - analytic)/analytic")
            _add(out["leaves"], f"{command}|n={_get(row, 'n')}", _leaf(value, {"analytic_error": relative * analytic}))
        for level in _get(record, "spectral_convergence", "levels"):
            _add(out["report_only"], f"{command}|level={_get(level, 'degree')}",
                 _number(_get(level, "max_relative_error"), "level error"))
    for command in SOFT_WALL_VERDICT:
        record = _get(records, command)
        _add(out["controls"], f"{command}|verdicts",
             tuple((check["id"], bool(check["passed"])) for check in _get(record, "acceptance_checks")))
        for row in _get(record, "results"):
            _add(out["report_only"], f"{command}|n={_get(row, 'n')}",
                 _number(_get(row, "numerical_mass_squared_gev2"), "eigenvalue"))
    for row in _get(records, "finite-difference", "results"):
        _add(out["controls"], f"finite-difference|n={_get(row, 'n')}",
             _number(_get(row, "numerical_mass_squared_gev2"), "eigenvalue"))
    return out


def extract_hard_wall_vector(records: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Dict[str, Any]] = {"leaves": {}, "controls": {}, "report_only": {}}
    spectral = _get(records, "spectral")
    final = _number(_get(spectral, "spectral_convergence", "successive_max_relative_differences")[-1], "difference")
    shooting = {(_get(row, "n")): row for row in _get(records, "shooting", "results")}
    for row in _get(spectral, "results"):
        n = _get(row, "n")
        if n not in shooting:
            raise ExtractionError(f"mode {n} has no shooting counterpart")
        mass = _number(_get(row, "numerical_m_z_m"), "mass")
        ratio = _number(_get(row, "numerical_ratio"), "ratio")
        _add(out["leaves"], f"spectral|m|n={n}", _leaf(mass, {
            "refinement": final * abs(mass),
            "shooting_difference": abs(mass - _number(_get(shooting[n], "numerical_m_z_m"), "mass"))}))
        if n == min(shooting):
            _add(out["controls"], f"spectral|ratio|n={n}", ratio)
        else:
            _add(out["leaves"], f"spectral|ratio|n={n}", _leaf(ratio, {
                "refinement": 2.0 * final * abs(ratio),
                "shooting_difference": abs(ratio - _number(_get(shooting[n], "numerical_ratio"), "ratio"))}))
    for route in ("shooting", "collocation"):
        for row in _get(records, route, "results"):
            _add(out["controls"], f"{route}|m|n={_get(row, 'n')}", _number(_get(row, "numerical_m_z_m"), "mass"))
    return out


def extract_hard_wall_chiral(records: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Dict[str, Any]] = {"leaves": {}, "controls": {}, "report_only": {}}
    results = _get(records, "default", "results")
    levels = {int(_get(level, "degree")): _get(level, "observables") for level in _get(results, "levels")}
    if sorted(levels) != [64, 80, 96]:
        raise ExtractionError(f"levels are {sorted(levels)}, not 64, 80, 96")
    independent = _get(results, "independent")
    table = {_get(row, "observable"): row for row in _get(results, "table")}
    if sorted(table) != sorted(CHIRAL_OBSERVABLES):
        raise ExtractionError("table rows are not the seven observables")
    for name in CHIRAL_OBSERVABLES:
        fine = _number(_get(levels[96], name), name)
        middle = _number(_get(levels[80], name), name)
        coarse = _number(_get(levels[64], name), name)
        last = _number(_get(results, "refinement", name, "N80_to_N96"), "refinement") * abs(middle)
        first = _number(_get(results, "refinement", name, "N64_to_N80"), "refinement") * abs(coarse)
        for converted, direct, what in ((last, abs(fine - middle), "N80_to_N96"), (first, abs(middle - coarse), "N64_to_N80")):
            if abs(converted - direct) > 1.0e-6 * max(direct, EPS * abs(fine)):
                raise ExtractionError(f"{name}: {what} conversion does not reproduce the level difference")
        extra: Dict[str, float] = {}
        if name in _get(results, "cutoff_changes"):
            extra["cutoff"] = _number(results["cutoff_changes"][name], "cutoff") * abs(_number(_get(independent[-2], name), name))
            extra["cross_route"] = _number(_get(results, "cross_route_differences", name), "cross route") * abs(fine)
        if name == "f_pi_MeV":
            extra["f_pi_route"] = max(
                _number(_get(item, "f_pi_route_relative_difference"), "route") * abs(_number(_get(item, "f_pi_dop853_MeV"), "f_pi"))
                for item in independent)
        _add(out["leaves"], f"level=96|{name}", _leaf(fine, dict(extra, refinement=last)))
        _add(out["leaves"], f"level=80|{name}", _leaf(middle, dict(extra, refinement=first)))
        _add(out["leaves"], f"level=64|{name}", _leaf(coarse, dict(extra, refinement=first)))
        _add(out["leaves"], f"table|{name}", _leaf(_number(_get(table[name], "computed"), name), dict(extra, refinement=last)))
    for item in independent:
        epsilon = _get(item, "epsilon")
        for key in ("m_pi_MeV", "m_a1_MeV", "sqrt_F_a1_MeV", "g_rho_pi_pi", "f_pi_bvp_MeV", "f_pi_dop853_MeV"):
            _add(out["controls"], f"independent|epsilon={epsilon!r}|{key}", _number(_get(item, key), key))
    for row in _get(results, "gmor"):
        for key in ("m_pi_MeV", "f_pi_MeV", "R_GMOR"):
            _add(out["report_only"], f"gmor|factor={_get(row, 'm_q_factor')!r}|{key}", _number(_get(row, key), key))
    return out


def extract_gubser_nellore(records: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Dict[str, Any]] = {"leaves": {}, "controls": {}, "report_only": {}}
    presets = _get(records, "default", "results", "presets")
    if not isinstance(presets, dict) or sorted(presets) != ["cosh-calibration", "qcd-like"]:
        raise ExtractionError("presets is not the mapping of the two presets")
    for preset, result in presets.items():
        change = _number(_get(result, "refinement", "maximum_final_change"), "refinement")
        derivative = _number(_get(result, "maximum_derivative_disagreement"), "derivative disagreement")
        for position, point in enumerate(_get(result, "curve")):
            coordinate = _number(_get(point, "x_h"), "x_h")
            temperature = _number(_get(point, "temperature_L"), "temperature")
            sound = _number(_get(point, "sound_speed_squared"), "sound speed")
            entry = _leaf(temperature, {"refinement": change * abs(temperature)})
            entry["key_coordinate"] = coordinate
            _add(out["leaves"], f"{preset}|{position}|temperature_L", entry)
            entry = _leaf(sound, {"refinement": change * abs(sound), "derivative_disagreement": derivative})
            entry["key_coordinate"] = coordinate
            _add(out["leaves"], f"{preset}|{position}|sound_speed_squared", entry)
            _add(out["report_only"], f"{preset}|{position}|phi_h", _number(_get(point, "phi_h"), "phi_h"))
        for item in _get(result, "independent_comparisons"):
            target = _get(item, "target_phi_h")
            for key in ("temperature_relative_error", "entropy_relative_error", "sound_speed_relative_error"):
                _add(out["report_only"], f"{preset}|target_phi_h={target!r}|{key}", _number(_get(item, key), key))
        _add(out["report_only"], f"{preset}|maximum_collocation_residual",
             _number(_get(result, "maximum_collocation_residual"), "collocation residual"))
    return out


def extract_gubser_rocha(records: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Dict[str, Any]] = {"leaves": {}, "controls": {}, "report_only": {}}
    results = _get(records, "default", "results")
    refinement = {_get(row, "xi"): _get(row, "observables") for row in _get(results, "refinement", "cases")}
    cases = _get(results, "cases")
    if sorted(refinement) != sorted(_get(case, "xi") for case in cases) or len(refinement) != len(cases):
        raise ExtractionError("refinement cases do not match the thermodynamic cases by xi")
    for case in cases:
        xi = _get(case, "xi")
        for name, field in GR_NAME_MAP.items():
            value = _number(_get(case, "thermodynamics", field), field)
            exact = _number(_get(case, "source_exact_thermodynamics", field), field)
            change = _number(_get(refinement[xi], name, "middle_to_fine"), "refinement")
            _add(out["leaves"], f"xi={xi!r}|{field}", _leaf(value, {
                "refinement": change * max(1.0, abs(value)), "closed_form": abs(value - exact)}))
        _add(out["report_only"], f"xi={xi!r}|maxwell_flux", _number(_get(case, "thermodynamics", "maxwell_flux"), "flux"))
    return out


def extract_dgr_neutral(records: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Dict[str, Any]] = {"leaves": {}, "controls": {}, "report_only": {}}
    record = _get(records, "default")
    results = _get(record, "results")
    targets = _get(record, "configuration", "physical_phi_h_targets")
    branches = _get(results, "degree_branches")
    if not isinstance(branches, dict) or sorted(branches, key=int) != ["80", "120", "150"]:
        raise ExtractionError("degree_branches is not the mapping of degrees 80, 120, 150")
    points = {degree: _get(branch, "points") for degree, branch in branches.items()}
    curve = _get(results, "curve")
    quadrature = _get(results, "quadrature_refinement", "records")
    if not (len(curve) == len(targets) == len(quadrature) and all(len(item) == len(targets) for item in points.values())):
        raise ExtractionError("curve, branches and quadrature records do not match the configured targets by position")
    largest = 0.0
    for position in range(len(targets)):
        if abs(_number(_get(quadrature[position], "phi_h"), "phi_h") - _number(_get(curve[position], "phi_h"), "phi_h")) \
                > 1.0e-9 * abs(curve[position]["phi_h"]):
            raise ExtractionError("quadrature record does not match the curve point at its position")
        quadrature_change = _number(_get(quadrature[position], "middle_to_fine_change"), "quadrature change")
        for field in DGR_FIELDS:
            fine = _number(_get(points["150"][position], field), field)
            middle = _number(_get(points["120"][position], field), field)
            coarse = _number(_get(points["80"][position], field), field)
            if field != "chi_2_over_T2_BH":
                largest = max(largest, abs(fine - middle) / max(abs(fine), abs(middle), 1.0e-300))
            high = {"refinement": abs(fine - middle)}
            low = {"refinement": abs(middle - coarse)}
            if field in ("susceptibility_integral", "chi_2_over_T2_BH"):
                high["quadrature"] = quadrature_change * abs(fine)
            _add(out["leaves"], f"curve|{position}|{field}", _leaf(_number(_get(curve[position], field), field), high))
            _add(out["leaves"], f"degree=150|{position}|{field}", _leaf(fine, high))
            _add(out["leaves"], f"degree=120|{position}|{field}", _leaf(middle, low))
            _add(out["leaves"], f"degree=80|{position}|{field}", _leaf(coarse, low))
        for field in ("phi_h", "x_h", "temperature_MeV", "s_over_T3_plot", "chi_2_over_T2_plot"):
            _add(out["report_only"], f"curve|{position}|{field}", _number(_get(curve[position], field), field))
    recorded = _number(_get(results, "refinement", "maximum_final_change"), "refinement")
    if largest > recorded * (1.0 + 1.0e-6):
        raise ExtractionError("per-position refinement differences exceed the recorded maximum_final_change")
    _add(out["report_only"], "refinement|maximum_final_change", recorded)
    out["consistency"] = {"largest_150_to_120_relative_change_in_three_fields": largest, "recorded_maximum_final_change": recorded}
    return out


def extract_dgr_critical(records: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Dict[str, Any]] = {"leaves": {}, "controls": {}, "report_only": {}}
    results = _get(records, "default", "results")
    states = {int(_get(state, "degree")): state for state in _get(results, "refinement", "states")}
    if len(states) != len(_get(results, "refinement", "states")):
        raise ExtractionError("refinement states are not unique by degree")
    changes: Dict[int, Tuple[int, Mapping[str, Any]]] = {}
    for item in _get(results, "refinement", "changes"):
        changes[int(_get(item, "fine_degree"))] = (int(_get(item, "coarse_degree")), _get(item, "changes"))
    ordered = sorted(states)
    for degree in ordered:
        for field in DGR_POINT_FIELDS:
            primary = _number(_get(states[degree], "primary", "point", field), field)
            explicit = _number(_get(states[degree], "explicit", "point", field), field)
            estimators = {"route_difference": abs(primary - explicit)}
            fine_degree = degree if degree in changes else ordered[1]
            coarse_degree, change = changes[fine_degree]
            fine_value = _number(_get(states[fine_degree], "primary", "point", field), field)
            coarse_value = _number(_get(states[coarse_degree], "primary", "point", field), field)
            scale = max(1.0, abs(coarse_value), abs(fine_value))
            converted = _number(_get(change, field), "change") * scale
            if abs(converted - abs(fine_value - coarse_value)) > 1.0e-6 * max(abs(fine_value - coarse_value), EPS * scale):
                raise ExtractionError(f"{field}: scaled change does not reproduce the state difference")
            estimators["refinement"] = converted
            _add(out["leaves"], f"state|degree={degree}|primary|{field}", _leaf(primary, estimators))
            _add(out["leaves"], f"state|degree={degree}|explicit|{field}", _leaf(explicit, estimators))
    labels = [_get(item, "label") for item in _get(results, "controls")]
    if len(labels) != len(set(labels)):
        raise ExtractionError("control states are not unique by label")
    for item in results["controls"]:
        for field in DGR_POINT_FIELDS:
            primary = _number(_get(item, "primary", "point", field), field)
            explicit = _number(_get(item, "explicit", "point", field), field)
            estimators = {"route_difference": abs(primary - explicit)}
            _add(out["leaves"], f"control|{item['label']}|primary|{field}", _leaf(primary, estimators))
            _add(out["leaves"], f"control|{item['label']}|explicit|{field}", _leaf(explicit, estimators))
    roots = _get(results, "critical", "step_roots")
    step = _get(results, "critical", "scaled_step_changes")[-1]
    for field in DGR_CRITICAL_FIELDS:
        final = _number(_get(roots[-1], field), field)
        previous = _number(_get(roots[-2], field), field)
        _add(out["leaves"], f"critical|{field}", _leaf(final, {
            "step_change": _number(_get(step, field), "step change") * max(1.0, abs(previous), abs(final))}))
    return out


def _optical_response(out: Dict[str, Dict[str, Any]], key: str, response: Mapping[str, Any]) -> None:
    spectral = _complex(_get(response, "spectral_conductivity"), "conductivity")
    independent = _complex(_get(response, "independent_conductivity"), "conductivity")
    scale = 1.0 + abs(spectral)
    estimators = {
        "resolution": _number(_get(response, "resolution_change"), "resolution") * scale,
        "series_truncation": _number(_get(response, "series_truncation_change"), "truncation") * scale,
        "route": _number(_get(response, "route_relative_difference"), "route") * (1.0 + abs(independent)),
    }
    if "background_cutoff_change" in response:
        estimators["background_cutoff"] = _number(response["background_cutoff_change"], "cutoff") * scale
    _add(out["leaves"], f"{key}|spectral_conductivity", _leaf(spectral, estimators))
    _add(out["controls"], f"{key}|independent_conductivity", independent)
    for gate in ("equation_residual", "numerical_gate_ratio"):
        _add(out["report_only"], f"{key}|{gate}", _number(_get(response, gate), gate))


def extract_optical(records: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Dict[str, Any]] = {"leaves": {}, "controls": {}, "report_only": {}}
    results = _get(records, "default", "results")
    for response in _get(results, "normal_responses"):
        _optical_response(out, f"normal|omega={_get(response, 'omega_over_temperature')!r}", response)
    for response in _get(results, "figure_2_provenance", "responses"):
        _optical_response(out, f"figure_2|omega={_get(response, 'omega_over_temperature')!r}", response)
    for position, point in enumerate(_get(results, "near_critical_pole", "points")):
        for response in _get(point, "responses"):
            _optical_response(out, f"pole|{position}|omega={_get(response, 'omega_over_temperature')!r}", response)
        intercept = _number(_get(point, "pole_intercept"), "pole intercept")
        density = _number(_get(point, "static_london", "superfluid_density_over_tc"), "superfluid density")
        _add(out["leaves"], f"pole|{position}|pole_intercept", _leaf(intercept, {
            "intercept_stability": _number(_get(point, "intercept_stability"), "stability") * abs(intercept),
            "static_pole": _number(_get(point, "static_pole_relative_difference"), "static pole") * abs(density)}))
        _add(out["controls"], f"pole|{position}|static_london", density)
        _add(out["report_only"], f"pole|{position}|temperature_over_tc", _number(_get(point, "temperature_over_tc"), "T/Tc"))
    return out


EXTRACTORS: Dict[str, Callable[[Mapping[str, Any]], Dict[str, Any]]] = {
    "soft-wall-vector": extract_soft_wall,
    "hard-wall-vector": extract_hard_wall_vector,
    "hard-wall-chiral": extract_hard_wall_chiral,
    "gubser-nellore-ed": extract_gubser_nellore,
    "gubser-rocha-emd": extract_gubser_rocha,
    "dewolfe-gubser-rosen-emd": extract_dgr_neutral,
    "dewolfe-gubser-rosen-emd-finite-density": extract_dgr_critical,
    "holographic-superconductor-optical": extract_optical,
}


def records_for(consumer: Mapping[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Return the record source and the records used to validate a consumer."""

    if consumer.get("committed_record"):
        return "committed verifier record", {"default": json.loads((ROOT / consumer["committed_record"]).read_text())}
    path = ROOT / SYNTHETIC_RECORDS / f"{consumer['id']}.json"
    records = {key: value for key, value in json.loads(path.read_text()).items() if not key.startswith("_")}
    return "synthetic record (hand-built from a manual source audit; not a verifier output)", records


def p0_revalidation() -> Dict[str, Any]:
    """Corrected structural preflight (appended to the original P0 evidence).

    Executable checks: call sites, a module-local call graph, source-key
    presence, strict resolution of every table pointer, and the extraction
    with its cardinality, matching and conversion checks. Where no verifier
    record is committed, the record is synthetic, so those checks validate
    the extraction code against a manually audited structure, not against
    verifier output.
    """

    table = load_table()
    original = {item["consumer"]: item for item in p0_check()["consumers"]}
    consumers = []
    for consumer in table["consumers"]:
        source, records = records_for(consumer)
        first_record = records.get("default") or records[next(iter(records))]
        pointers: Dict[str, Any] = {}
        prose: List[str] = []
        listed = [item["pointer"] for item in consumer.get("leaves", [])] \
            + [item["pointer"] for item in consumer.get("estimators", [])] \
            + list(consumer.get("report_only", [])) + list(consumer.get("gates_reported", [])) \
            + [item["pointer"] for item in consumer.get("key_checks", [])] \
            + [item for item in consumer.get("controls", []) if isinstance(item, str)]
        for pointer in listed:
            if not pointer.startswith("/") or " " in pointer:
                prose.append(pointer)
                continue
            for concrete in expand_pointer(pointer):
                values, missing = resolve_strict(first_record, concrete)
                usable = [value for value in values if _is_number(value) or (isinstance(value, dict) and value)]
                pointers[concrete] = {"leaves": len(values), "usable": len(usable), "missing": missing,
                                      "passed": bool(values) and missing == 0 and len(usable) == len(values)}
        try:
            extracted = EXTRACTORS[consumer["id"]](records)
            extraction = {"passed": True, "table_leaves": len(extracted["leaves"]), "controls": len(extracted["controls"]),
                          "report_only": len(extracted["report_only"]),
                          "leaves_without_estimator": sum(1 for leaf in extracted["leaves"].values() if not leaf["estimators"])}
            if "consistency" in extracted:
                extraction["consistency"] = extracted["consistency"]
        except ExtractionError as error:
            extraction = {"passed": False, "error": str(error)}
        checks = {
            "original_p0": {"passed": original[consumer["id"]]["passed"]},
            "table_pointers_strict": {"detail": pointers, "passed": all(item["passed"] for item in pointers.values())},
            "extraction": extraction,
        }
        consumers.append({
            "consumer": consumer["id"], "record_source": source, "checks": checks,
            "derived_estimators_checked_by_extraction_only": prose,
            "passed": all(item["passed"] for item in checks.values()),
        })
    return {
        "table_sha256": _file_sha256(ROOT / TABLE),
        "consumers": consumers,
        "executable_checks": [
            "call sites by AST (innermost enclosing function)",
            "control routes by a module-local AST call graph (not a cross-module proof)",
            "presence of record-key strings in the module source (presence only; no parent path)",
            "strict resolution of every table pointer, with wildcard cardinality",
            "extraction with unique stable keys, matched states and estimator conversions",
        ],
        "manual_source_review": [
            "record structure and estimator normalization of the five consumers without a committed record",
            "data dependence of control routes on spectral outputs (the call graph shows call dependence only)",
            "the preset-level and record-level meaning of the GN and DGR refinement maxima",
        ],
        "committed_record_consumers": [item["consumer"] for item in consumers if item["record_source"].startswith("committed")],
        "synthetic_record_consumers": [item["consumer"] for item in consumers if item["record_source"].startswith("synthetic")],
        "passed": all(item["passed"] for item in consumers),
    }


# ---------------------------------------------------------------------------
# S0: reference operators, candidates, fixtures and metrics
# ---------------------------------------------------------------------------

DEGREES = (2, 3, 16, 17, 40, 41, 64, 80, 96, 120, 128, 150, 160, 192, 256, 320, 384, 512, 640, 1024, 1280)
INTERVALS = ((-1.0, 1.0), (1.0e-5, 1.0), (0.0, 1.0), (2.0, 5.0))
CANDIDATES = ("C-T1", "C-T2", "C-T3", "C-S1")
CONSTRUCTIONS = ("current",) + CANDIDATES
POLYNOMIAL = ((1, 0), (2, -1), (-3, 0.5), (0.25, 4), (5, 0), (0, -2), (1.5, 1))
EXACTNESS_LIMIT = 1.0e-10
WORSENING_FACTOR = 2.0
IMPROVEMENT_FACTOR = 10.0
TIE_FACTOR = 1.5
PI_LITERAL = "3.14159265358979323846264338327950288419716939937510582097494"
OC_EVIDENCE = Path("docs/generated/optical-oc")
OC_ARTIFACTS = Path("output/optical-oc-artifacts")


def row_sets(degree: int) -> Dict[str, List[int]]:
    """Row sets of the plan (Section 4); never empty for degree >= 2."""

    if degree < 2:
        raise ValueError("degree must be at least 2")
    return {
        "all": list(range(degree + 1)),
        "uv": list(range(1, min(3, degree - 1) + 1)),
        "ir": list(range(max(1, degree - 3), degree)),
    }


# -- 50-digit arithmetic ------------------------------------------------------

def dec_pi() -> Decimal:
    """Pi by Machin's formula in the active context."""

    def arctan_inverse(n: int) -> Decimal:
        x = Decimal(1) / n
        square = x * x
        total, term, k = x, x, 1
        while True:
            term = -term * square
            k += 2
            piece = term / k
            if abs(piece) < Decimal(10) ** (-(getcontext_prec() + 5)):
                return total
            total += piece

    return 16 * arctan_inverse(5) - 4 * arctan_inverse(239)


def getcontext_prec() -> int:
    from decimal import getcontext

    return getcontext().prec


def dec_sin_cos(x: Decimal) -> Tuple[Decimal, Decimal]:
    """Sine and cosine by Taylor series; ``|x|`` should be at most about 10."""

    limit = Decimal(10) ** (-(getcontext_prec() + 5))
    square = x * x
    sine, term, k = x, x, 1
    while True:
        term = -term * square / ((k + 1) * (k + 2))
        k += 2
        if abs(term) < limit:
            break
        sine += term
    cosine, term, k = Decimal(1), Decimal(1), 0
    while True:
        term = -term * square / ((k + 1) * (k + 2))
        k += 2
        if abs(term) < limit:
            break
        cosine += term
    return sine, cosine


def ideal_nodes(degree: int, lower: float, upper: float) -> List[Decimal]:
    """Ideal Lobatto nodes ``lower + width sin^2(pi k/(2N))`` in 50 digits."""

    pi = dec_pi()
    low, high = Decimal(lower), Decimal(upper)
    width = high - low
    nodes = []
    for k in range(degree + 1):
        if 2 * k <= degree:
            sine, _ = dec_sin_cos(pi * k / (2 * degree))
            nodes.append(low + width * sine * sine)
        else:
            sine, _ = dec_sin_cos(pi * (degree - k) / (2 * degree))
            nodes.append(high - width * sine * sine)
    nodes[0], nodes[-1] = low, high
    return nodes


def decimal_matrices(nodes: Sequence[Decimal]):
    """Exact D1 and D2 (lists of Decimal rows) of the interpolant on ``nodes``."""

    size = len(nodes)
    weights = []
    for j, node in enumerate(nodes):
        product = Decimal(1)
        for k, other in enumerate(nodes):
            if k != j:
                product *= node - other
        weights.append(1 / product)
    first, second = [], []
    zero = Decimal(0)
    for i in range(size):
        node, inverse_weight = nodes[i], 1 / weights[i]
        inverses = [zero if j == i else 1 / (node - nodes[j]) for j in range(size)]
        row1 = [weight * inverse_weight * inverse for weight, inverse in zip(weights, inverses)]
        diagonal = -sum(row1, zero)
        row2 = [2 * entry * (diagonal - inverse) for entry, inverse in zip(row1, inverses)]
        row1[i] = diagonal
        row2[i] = zero
        row2[i] = -sum(row2, zero)
        first.append(row1)
        second.append(row2)
    return first, second


def _split(row: Sequence[Decimal]) -> Tuple[List[float], List[float]]:
    high = [float(value) for value in row]
    low = [float(value - Decimal(h)) for value, h in zip(row, high)]
    return high, low


class Reference:
    """Exact matrices in double-double form: ``R = hi + lo`` to about 32 digits.

    ``products`` holds, for each supplied complex Decimal vector, the exact
    50-digit products ``R1 v`` and ``R2 v`` (as Decimal pairs per row).
    """

    def __init__(self, nodes: Sequence[Decimal], vectors: Optional[Mapping[str, Tuple[List[Decimal], List[Decimal]]]] = None):
        first, second = decimal_matrices(nodes)
        size = len(nodes)
        self.hi = [np.empty((size, size)), np.empty((size, size))]
        self.lo = [np.empty((size, size)), np.empty((size, size))]
        self.products: Dict[str, List[List[Tuple[Decimal, Decimal]]]] = {name: [[], []] for name in (vectors or {})}
        zero = Decimal(0)
        for order, matrix in enumerate((first, second)):
            for i, row in enumerate(matrix):
                high, low = _split(row)
                self.hi[order][i, :] = high
                self.lo[order][i, :] = low
                for name, (real, imaginary) in (vectors or {}).items():
                    self.products[name][order].append(
                        (sum(map(Decimal.__mul__, row, real), zero), sum(map(Decimal.__mul__, row, imaginary), zero))
                    )

    def error(self, order: int, matrix: np.ndarray) -> np.ndarray:
        """``R - D`` for a double matrix, exact to double-double accuracy."""

        return (self.hi[order] - matrix) + self.lo[order]


# -- constructions (double) ---------------------------------------------------

def _lobatto_weights(degree: int) -> np.ndarray:
    weights = np.ones(degree + 1)
    weights[1::2] = -1.0
    weights[0] *= 0.5
    weights[-1] *= 0.5
    return weights


def half_angle_nodes(degree: int, lower: float, upper: float) -> np.ndarray:
    """Candidate nodes: half-angle formula with integer-index angles."""

    width = upper - lower
    index = np.arange(degree + 1)
    low_side = 2 * index <= degree
    nodes = np.empty(degree + 1)
    nodes[low_side] = lower + width * np.sin(np.pi * index[low_side] / (2 * degree)) ** 2
    nodes[~low_side] = upper - width * np.sin(np.pi * (degree - index[~low_side]) / (2 * degree)) ** 2
    if degree % 2 == 0:
        # sin^2(pi/4) is exactly 1/2; the rounded sine would shift the midpoint.
        nodes[degree // 2] = lower + 0.5 * width
    nodes[0], nodes[-1] = lower, upper
    return nodes


def _trig_differences(degree: int, width: float, rows: np.ndarray) -> np.ndarray:
    """``u_i - u_j`` for the given rows from integer-argument sines.

    ``sin(pi m/(2N))`` with ``m = i + j`` uses the complementary integer
    ``2N - m`` when ``m > N``, so no near-pi sine is evaluated.
    """

    columns = np.arange(degree + 1)
    total = rows[:, None] + columns[None, :]
    total = np.minimum(total, 2 * degree - total)
    plus = np.sin(np.pi * total / (2 * degree))
    minus = np.sin(np.pi * (rows[:, None] - columns[None, :]) / (2 * degree))
    return width * plus * minus


def _two_sum(a: np.ndarray, b: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Error-free transformation: ``a + b = s + e`` exactly."""

    total = a + b
    shadow = total - a
    return total, (a - (total - shadow)) + (b - shadow)


def _two_product(a: np.ndarray, b: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Error-free transformation: ``a b = p + e`` exactly (Dekker, Veltkamp)."""

    product = a * b
    split_a = 134217729.0 * a
    a_high = split_a - (split_a - a)
    a_low = a - a_high
    split_b = 134217729.0 * b
    b_high = split_b - (split_b - b)
    b_low = b - b_high
    return product, ((a_high * b_high - product) + a_high * b_low + a_low * b_high) + a_low * b_low


def compensated_row_sum(matrix: np.ndarray) -> np.ndarray:
    """Row sums by pairwise double-double reduction (rounding near one ulp of the sum)."""

    high = np.array(matrix, dtype=float)
    low = np.zeros_like(high)
    while high.shape[1] > 1:
        if high.shape[1] % 2:
            high = np.concatenate([high, np.zeros((high.shape[0], 1))], axis=1)
            low = np.concatenate([low, np.zeros((low.shape[0], 1))], axis=1)
        total, error = _two_sum(high[:, 0::2], high[:, 1::2])
        high, low = total, low[:, 0::2] + low[:, 1::2] + error
    return (high + low)[:, 0]


def compensated_row_product(matrix: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Row products as ``(high + low) 2^exponent`` by pairwise double-double reduction."""

    high, exponent = np.frexp(np.array(matrix, dtype=float))
    exponent = exponent.astype(np.int64)
    low = np.zeros_like(high)
    while high.shape[1] > 1:
        if high.shape[1] % 2:
            high = np.concatenate([high, np.ones((high.shape[0], 1))], axis=1)
            low = np.concatenate([low, np.zeros((low.shape[0], 1))], axis=1)
            exponent = np.concatenate([exponent, np.zeros((exponent.shape[0], 1), dtype=np.int64)], axis=1)
        product, error = _two_product(high[:, 0::2], high[:, 1::2])
        error = error + high[:, 0::2] * low[:, 1::2] + low[:, 0::2] * high[:, 1::2]
        product, error = _two_sum(product, error)
        mantissa, shift = np.frexp(product)
        high, low = mantissa, np.ldexp(error, -shift)
        exponent = exponent[:, 0::2] + exponent[:, 1::2] + shift
    return high[:, 0], low[:, 0], exponent[:, 0]


def _first_from_differences(differences: np.ndarray, weights: Any, rows: np.ndarray):
    """Off-diagonal ``D1`` rows and negative-sum diagonal for ``rows``.

    ``weights`` is a weight vector, or the ``(high, low)`` pair of the
    reciprocal weights from ``_stored_node_weights``. The diagonal is the
    negative row sum, taken in compensated arithmetic.
    """

    safe = differences.copy()
    safe[np.arange(rows.size), rows] = 1.0
    if isinstance(weights, tuple):
        high, low = weights
        quotient = high[rows][:, None] / high[None, :]
        ratio = quotient + quotient * (low[rows] / high[rows])[:, None] - quotient * (low / high)[None, :]
    else:
        ratio = weights[None, :] / weights[rows][:, None]
    first = ratio / safe
    first[np.arange(rows.size), rows] = 0.0
    diagonal = -compensated_row_sum(first)
    return first, diagonal, safe


def _explicit_second(first: np.ndarray, diagonal: np.ndarray, safe: np.ndarray, rows: np.ndarray) -> np.ndarray:
    second = 2.0 * first * (diagonal[:, None] - 1.0 / safe)
    second[np.arange(rows.size), rows] = 0.0
    second[np.arange(rows.size), rows] = -compensated_row_sum(second)
    return second


def construct(name: str, degree: int, lower: float, upper: float):
    """Return ``(nodes, D1, D2)`` for a declared construction (read-only arrays)."""

    lower, upper = float(lower), float(upper)
    if name == "current":
        nodes, first, second = _construct_current(degree, lower, upper)
    else:
        width = upper - lower
        nodes = half_angle_nodes(degree, lower, upper)
        weights = _lobatto_weights(degree)
        all_rows = np.arange(degree + 1)
        if name in ("C-T1", "C-T2"):
            differences = _trig_differences(degree, width, all_rows)
            first, diagonal, safe = _first_from_differences(differences, weights, all_rows)
            if name == "C-T2":
                second = _explicit_second(first, diagonal, safe, all_rows)
            first[all_rows, all_rows] = diagonal
            if name == "C-T1":
                second = first @ first
        elif name == "C-T3":
            rows = np.arange(degree // 2 + 1)
            differences = _trig_differences(degree, width, rows)
            half_first, diagonal, safe = _first_from_differences(differences, weights, rows)
            half_second = _explicit_second(half_first, diagonal, safe, rows)
            half_first[np.arange(rows.size), rows] = diagonal
            first = np.empty((degree + 1, degree + 1))
            second = np.empty((degree + 1, degree + 1))
            first[rows, :] = half_first
            second[rows, :] = half_second
            mirror = np.arange(degree // 2 + 1, degree + 1)
            first[mirror, :] = -first[degree - mirror, ::-1]
            second[mirror, :] = second[degree - mirror, ::-1]
        elif name == "C-S1":
            differences = nodes[:, None] - nodes[None, :]
            weights = _stored_node_weights(differences)
            first, diagonal, safe = _first_from_differences(differences, weights, all_rows)
            second = _explicit_second(first, diagonal, safe, all_rows)
            first[all_rows, all_rows] = diagonal
        else:
            raise ValueError(f"unknown construction {name!r}")
    for array in (nodes, first, second):
        array.setflags(write=False)
    return nodes, first, second


def _stored_node_weights(differences: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Reciprocal barycentric weights of the stored nodes as a ``(high, low)`` pair.

    ``1/w_j = prod_{k != j} (u_j - u_k)`` up to a common factor. The products
    are accumulated in double-double arithmetic as mantissas with separate
    binary exponents (their log2 magnitudes) and explicit signs, so nothing
    overflows and the result is accurate to about one ulp.
    """

    size = differences.shape[0]
    work = differences.copy()
    work[np.arange(size), np.arange(size)] = 1.0
    signs = np.where(np.sum(work < 0.0, axis=1) % 2 == 0, 1.0, -1.0)
    high, low, exponent = compensated_row_product(np.abs(work))
    shift = (exponent - exponent[size // 2]).astype(int)
    return signs * np.ldexp(high, shift), signs * np.ldexp(low, shift)


def _construct_current(degree: int, lower: float, upper: float):
    """The pre-repair production construction, kept for comparison."""

    indices = np.arange(degree + 1)
    descending = np.cos(np.pi * indices / degree)
    endpoint = np.ones(degree + 1)
    endpoint[0] = 2.0
    endpoint[-1] = 2.0
    endpoint *= (-1.0) ** indices
    differences = descending[:, np.newaxis] - descending[np.newaxis, :]
    derivative = np.outer(endpoint, 1.0 / endpoint) / (differences + np.eye(degree + 1))
    derivative -= np.diag(np.sum(derivative, axis=1))
    canonical_nodes = descending[::-1].copy()
    canonical = derivative[::-1, ::-1].copy()
    half_width = 0.5 * (upper - lower)
    midpoint = 0.5 * (upper + lower)
    nodes = midpoint + half_width * canonical_nodes
    nodes[0] = lower
    nodes[-1] = upper
    first = canonical / half_width
    second = first @ first
    return nodes, first, second


# -- test vectors and the polynomial -------------------------------------------

def _xi(node: Decimal, lower: Decimal, upper: Decimal) -> Decimal:
    return (2 * node - lower - upper) / (upper - lower)


def sample_vectors(nodes: Sequence[Decimal], lower: float, upper: float) -> Dict[str, np.ndarray]:
    """``v1, v2, v3`` evaluated in 50 digits at ``nodes`` and rounded to double."""

    low, high = Decimal(lower), Decimal(upper)
    vectors = {"v1": [], "v2": [], "v3": []}
    two_pi = 2 * dec_pi()
    for node in nodes:
        xi = _xi(node, low, high)
        vectors["v1"].append(float((3 * xi).exp()))
        angle = 8 * xi + Decimal("0.3")
        angle -= two_pi * (angle / two_pi).to_integral_value()
        vectors["v2"].append(float(dec_sin_cos(angle)[0]))
        vectors["v3"].append(float(1 / (1 + 4 * xi * xi)))
    return {name: np.array(values) for name, values in vectors.items()}


def polynomial(nodes: Sequence[Decimal], lower: float, upper: float, degree: int):
    """``P_d`` and its first two ``u``-derivatives at ``nodes`` (50 digits).

    Returns three lists of (real, imaginary) Decimal pairs. ``d = min(6, N)``.
    """

    low, high = Decimal(lower), Decimal(upper)
    scale = 2 / (high - low)
    order = min(len(POLYNOMIAL) - 1, degree)
    coefficients = [(Decimal(a), Decimal(b)) for a, b in POLYNOMIAL[: order + 1]]
    values, firsts, seconds = [], [], []
    zero = Decimal(0)
    for node in nodes:
        xi = _xi(node, low, high)
        powers = [Decimal(1)]
        for _ in range(order):
            powers.append(powers[-1] * xi)
        value = [zero, zero]
        first = [zero, zero]
        second = [zero, zero]
        for k, (a, b) in enumerate(coefficients):
            value[0] += a * powers[k]
            value[1] += b * powers[k]
            if k >= 1:
                first[0] += a * k * powers[k - 1]
                first[1] += b * k * powers[k - 1]
            if k >= 2:
                second[0] += a * k * (k - 1) * powers[k - 2]
                second[1] += b * k * (k - 1) * powers[k - 2]
        values.append((value[0], value[1]))
        firsts.append((first[0] * scale, first[1] * scale))
        seconds.append((second[0] * scale * scale, second[1] * scale * scale))
    return values, firsts, seconds


# -- metrics ---------------------------------------------------------------------

def _required(value: float, what: str) -> float:
    """A required metric must be defined (plan Section 4)."""

    if not math.isfinite(value):
        raise RequiredMetricUndefined(what)
    return float(value)


class RequiredMetricUndefined(RuntimeError):
    pass


def grid_metrics(degree: int, lower: float, upper: float, names: Sequence[str],
                 matrices: Mapping[str, Tuple[np.ndarray, np.ndarray, np.ndarray]],
                 keep: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Metrics (a), (b) and polynomial exactness for constructions on one grid."""

    sets = row_sets(degree)
    with localcontext() as context:
        context.prec = DIGITS
        ideal = ideal_nodes(degree, lower, upper)
        ideal_reference = Reference(ideal)
        ideal_vectors = sample_vectors(ideal, lower, upper)
        scales = {}
        for order in (0, 1):
            for name, vector in ideal_vectors.items():
                scale = np.abs(ideal_reference.hi[order]) @ np.abs(vector)
                if not np.all(scale > 0.0):
                    raise RequiredMetricUndefined(f"zero common denominator at degree {degree}")
                scales[(order, name)] = scale
        references: Dict[bytes, Tuple[Reference, Dict[str, np.ndarray], Any]] = {}
        results: Dict[str, Any] = {}
        for name in names:
            nodes, first, second = matrices[name]
            key = nodes.tobytes()
            if key not in references:
                exact_nodes = [Decimal(float(u)) for u in nodes]
                values, firsts, seconds = polynomial(exact_nodes, lower, upper, degree)
                rounded = np.array([complex(float(a), float(b)) for a, b in values])
                rounded_pairs = ([Decimal(float(z.real)) for z in rounded], [Decimal(float(z.imag)) for z in rounded])
                reference = Reference(exact_nodes, {"p": rounded_pairs})
                oracle = []
                for order, analytic in ((0, firsts), (1, seconds)):
                    oracle.append(np.array([
                        complex(float(product[0] - exact[0]), float(product[1] - exact[1]))
                        for product, exact in zip(reference.products["p"][order], analytic)
                    ]))
                references[key] = (reference, sample_vectors(exact_nodes, lower, upper), (rounded, oracle))
            reference, vectors, (rounded, oracle) = references[key]
            entry: Dict[str, Any] = {"a": {}, "b": {}, "exactness": {}}
            stored_errors: List[np.ndarray] = []
            for order, matrix, label in ((0, first, "D1"), (1, second, "D2")):
                stored_error = reference.error(order, matrix)
                stored_errors.append(stored_error)
                ideal_error = ideal_reference.error(order, matrix)
                for target, error, hi in (("stored", stored_error, reference.hi[order]),
                                          ("ideal", ideal_error, ideal_reference.hi[order])):
                    row_max = np.max(np.abs(hi), axis=1)
                    if not np.all(row_max > 0.0):
                        raise RequiredMetricUndefined(f"zero reference row at degree {degree}")
                    entry["a"][f"{label}_{target}"] = _required(
                        float(np.max(np.max(np.abs(error), axis=1) / row_max)), "metric (a)")
                    for vector_name, vector in vectors.items():
                        action = np.abs(error @ vector) / scales[(order, vector_name)]
                        for set_name, rows in sets.items():
                            entry["b"][f"{label}_{target}_{vector_name}_{set_name}"] = _required(
                                float(np.max(action[rows])), "metric (b)")
                denominator = np.abs(reference.hi[order]) @ np.abs(rounded)
                if not np.all(denominator > 0.0):
                    raise RequiredMetricUndefined(f"zero exactness denominator at degree {degree}")
                defect = -(stored_error @ rounded) + oracle[order]
                entry["exactness"][label] = _required(float(np.max(np.abs(defect) / denominator)), "exactness")
                if keep is not None:
                    keep[(name, degree, lower, upper, order)] = stored_error
            if name in ENTRY_ERROR_UNITS:
                # Recorded for proposed amendment 1; not used by the frozen rule.
                entry["bound_ratio"] = bound_ratios(reference, scales, nodes, vectors, stored_errors, name, degree)
            entry["sha256"] = {
                "nodes": hashlib.sha256(nodes.tobytes()).hexdigest(),
                "D1": hashlib.sha256(first.tobytes()).hexdigest(),
                "D2": hashlib.sha256(second.tobytes()).hexdigest(),
            }
            results[name] = entry
    return results


def artifact_metric(errors: Mapping[Any, np.ndarray], name: str, build_label: str) -> Dict[str, Any]:
    """Metric (c): the D-dependent operator action on each preserved O-C artifact.

    ``c = (T_R - T_cand) x`` uses the artifact's stored solution by index and
    its fixed row scale. The artifact files are read-only and hash-checked.
    """

    committed = {}
    for label in ("B1", "B3"):
        evidence = json.loads((ROOT / OC_EVIDENCE / f"{label}-optical-oc.json").read_text())
        for record in evidence["result"]["records"]:
            committed[Path(record["artifact"]["relative_path"]).name] = record["artifact"]["sha256"]
    rows_out = []
    for file_name in sorted(committed):
        path = ROOT / OC_ARTIFACTS / file_name
        if _file_sha256(path) != committed[file_name]:
            raise RequiredMetricUndefined(f"O-C artifact {file_name} does not match its committed hash")
        with np.load(path) as saved:
            solution = saved["stored_solution"]
            coefficient = saved["first_coefficient"]
            scale = np.abs(saved["assembled_operator"]) @ np.abs(solution) + np.abs(saved["rhs"])
        size = solution.size - 1
        degree = size - 1
        field = solution[:size]
        first_error = errors[(name, degree, 1.0e-5, 1.0, 0)]
        second_error = errors[(name, degree, 1.0e-5, 1.0, 1)]
        first_action = first_error @ field
        contribution = np.zeros(size + 1, dtype=complex)
        interior = np.arange(1, size - 1)
        contribution[interior] = (second_error @ field)[interior] + coefficient * first_action[interior]
        contribution[size - 1] = first_action[size - 1]
        contribution[size] = first_action[0]
        ratio = np.abs(contribution) / scale
        rows_out.append({
            "artifact": file_name,
            "degree": int(degree),
            "rows_1_3": [complex(value) for value in contribution[1:4]],
            "rows_1_3_abs_max": float(np.max(np.abs(contribution[1:4]))),
            "rows_1_3_scaled_max": float(np.max(ratio[1:4])),
            "all_rows_abs_max": float(np.max(np.abs(contribution))),
            "all_rows_scaled_max": float(np.max(ratio)),
        })
    return {
        "artifacts": rows_out,
        "worst_rows_1_3_scaled": max(item["rows_1_3_scaled_max"] for item in rows_out),
        "worst_rows_1_3_abs": max(item["rows_1_3_abs_max"] for item in rows_out),
        "worst_all_rows_scaled": max(item["all_rows_scaled_max"] for item in rows_out),
    }


# -- fixtures ----------------------------------------------------------------------

def s0_fixtures(build_label: str) -> Dict[str, Any]:
    checks: Dict[str, Any] = {}
    with localcontext() as context:
        context.prec = DIGITS
        pi = dec_pi()
        worst = abs(pi - Decimal(PI_LITERAL))
        sixth, _ = dec_sin_cos(pi / 6)
        half, _ = dec_sin_cos(pi / 2)
        worst = max(worst, abs(sixth - Decimal("0.5")), abs(half - 1))
        for k in range(1000):
            sine, cosine = dec_sin_cos(pi * (2 * k - 999) / 1000)
            worst = max(worst, abs(sine * sine + cosine * cosine - 1))
        checks["F1_oracle_arithmetic"] = {"max_error": float(worst), "limit": 1.0e-45,
                                          "passed": bool(worst <= Decimal("1e-45"))}

        worst2 = Decimal(0)
        for degree in (2, 3, 16, 17, 64):
            for nodes in (ideal_nodes(degree, -1.0, 1.0),
                          [Decimal(float(u)) for u in half_angle_nodes(degree, 1.0e-5, 1.0)]):
                first, second = decimal_matrices(nodes)
                largest = max(abs(value) for row in second for value in row)
                for i in range(degree + 1):
                    for j in range(degree + 1):
                        product = sum((first[i][k] * first[k][j] for k in range(degree + 1)), Decimal(0))
                        worst2 = max(worst2, abs(product - second[i][j]) / largest)
        checks["F2_recurrence_independence"] = {"max_relative_difference": float(worst2), "limit": 1.0e-40,
                                                "passed": bool(worst2 <= Decimal("1e-40"))}

        worst3 = Decimal(0)
        for degree in (2, 3, 16, 17, 640):
            for nodes in ([Decimal(float(u)) for u in half_angle_nodes(degree, 1.0e-5, 1.0)],
                          ideal_nodes(degree, 1.0e-5, 1.0)):
                values, firsts, seconds = polynomial(nodes, 1.0e-5, 1.0, degree)
                reference = Reference(nodes, {"p": ([v[0] for v in values], [v[1] for v in values])})
                for order, analytic in ((0, firsts), (1, seconds)):
                    largest = max(_cabs(value) for value in analytic)
                    error = max(_cabs((product[0] - exact[0], product[1] - exact[1]))
                                for product, exact in zip(reference.products["p"][order], analytic))
                    worst3 = max(worst3, error / largest if largest > 0 else error)
        checks["F3_oracle_polynomial_exactness"] = {"max_relative_error": float(worst3), "limit": 1.0e-30,
                                                    "passed": bool(worst3 <= Decimal("1e-30"))}

    api = True
    for degree in DEGREES:
        for lower, upper in INTERVALS:
            for name in CANDIDATES:
                nodes, first, second = construct(name, degree, lower, upper)
                api = api and bool(
                    nodes[0] == lower and nodes[-1] == upper and np.all(np.diff(nodes) > 0.0)
                    and first.shape == second.shape == (degree + 1, degree + 1)
                    and np.all(np.isfinite(first)) and np.all(np.isfinite(second))
                    and not nodes.flags.writeable and not first.flags.writeable and not second.flags.writeable
                )
    checks["F5_candidate_api"] = {"passed": api}
    return checks


def _cabs(value) -> Decimal:
    return (value[0] * value[0] + value[1] * value[1]).sqrt()


def continuity_fixture(metric_current: Mapping[str, Any], build_label: str) -> Dict[str, Any]:
    """F4: metric (c) of the current construction reproduces the O-C evidence."""

    evidence = json.loads((ROOT / OC_EVIDENCE / f"{build_label}-optical-oc.json").read_text())
    record = next(item for item in evidence["result"]["records"]
                  if item["omega_over_temperature"] == 60.0 and item["degree"] == 640)
    saved = {row["row"]: row for row in record["row_decomposition"]["rows"]}
    name = Path(record["artifact"]["relative_path"]).name
    computed = next(item for item in metric_current["artifacts"] if item["artifact"] == name)
    worst = 0.0
    for offset, row in enumerate((1, 2, 3)):
        contributions = saved[row]["contributions"]
        expected = complex(*contributions["D-construction"]) + complex(*contributions["D@D-product"])
        worst = max(worst, abs(computed["rows_1_3"][offset] - expected) / abs(expected))
    return {"max_relative_difference": worst, "limit": 1.0e-6, "passed": bool(worst <= 1.0e-6)}


# -- S0 driver -----------------------------------------------------------------------

def s0_run(build_label: str, degrees: Sequence[int] = DEGREES, intervals=INTERVALS,
           reference: Optional[Mapping[str, Any]] = None, save_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Fixtures, then metrics (a)-(c) and hashes for every construction and grid.

    With ``reference`` (another build's S0 result), a construction whose
    nodes and matrices are bit-identical to that build's inherits its
    metrics; only differing matrices are measured again and, with
    ``save_dir``, saved for the build-agreement metric (d).
    """

    fixtures = s0_fixtures(build_label)
    if not all(item["passed"] for item in fixtures.values()):
        return {"fixtures": fixtures, "passed": False, "stopped": "a fixture failed"}
    from holoforge.numerics import chebyshev_lobatto_grid

    grids: Dict[str, Any] = {}
    errors: Dict[Any, np.ndarray] = {}
    timings: Dict[str, float] = {}
    production_matches = {"current": True}
    inherited = 0
    measured = 0
    for degree in degrees:
        for lower, upper in intervals:
            label = f"{degree}|{lower!r}|{upper!r}"
            started = time.perf_counter()
            matrices = {name: construct(name, degree, lower, upper) for name in CONSTRUCTIONS}
            production = chebyshev_lobatto_grid(degree, lower, upper)
            current = matrices["current"]
            production_matches["current"] = production_matches["current"] and bool(
                production.nodes.tobytes() == current[0].tobytes()
                and production.first_derivative.tobytes() == current[1].tobytes()
                and production.second_derivative.tobytes() == current[2].tobytes())
            hashes = {name: {"nodes": hashlib.sha256(value[0].tobytes()).hexdigest(),
                             "D1": hashlib.sha256(value[1].tobytes()).hexdigest(),
                             "D2": hashlib.sha256(value[2].tobytes()).hexdigest()} for name, value in matrices.items()}
            needed = list(CONSTRUCTIONS)
            entry: Dict[str, Any] = {}
            if reference is not None:
                other = reference["grids"][label]
                needed = [name for name in CONSTRUCTIONS if other[name]["sha256"] != hashes[name]]
                for name in CONSTRUCTIONS:
                    if name not in needed:
                        entry[name] = dict(other[name], inherited=True)
                        inherited += 1
                if save_dir is not None:
                    for name in needed:
                        np.savez(save_dir / f"{build_label}-{name}-{degree}-{lower!r}-{upper!r}.npz",
                                 nodes=matrices[name][0], D1=matrices[name][1], D2=matrices[name][2])
            keep = errors if (lower, upper) == (1.0e-5, 1.0) and degree in (512, 640) else None
            force = list(CONSTRUCTIONS) if keep is not None else needed
            if force:
                computed = grid_metrics(degree, lower, upper, force, matrices, keep)
                for name in needed:
                    entry[name] = computed[name]
                    measured += 1
            grids[label] = entry
            timings[label] = time.perf_counter() - started
    metric_c = {name: artifact_metric(errors, name, build_label) for name in CONSTRUCTIONS} \
        if all((name, 640, 1.0e-5, 1.0, 0) in errors for name in CONSTRUCTIONS) else None
    result: Dict[str, Any] = {
        "build_label": build_label, "fixtures": fixtures, "grids": grids, "metric_c": metric_c,
        "production_equals_current_construction": production_matches["current"],
        "inherited_entries": inherited, "measured_entries": measured,
        "complete": tuple(degrees) == DEGREES and tuple(intervals) == INTERVALS,
        "seconds_by_grid_max": max(timings.values()), "seconds_total_grids": sum(timings.values()),
    }
    if metric_c is not None:
        fixtures["F4_artifacts_and_continuity"] = continuity_fixture(metric_c["current"], build_label)
    result["passed"] = all(item["passed"] for item in fixtures.values())
    if not result["passed"]:
        result["stopped"] = "a fixture failed"
    return result


def build_agreement(arrays: Path, other_label: str, payloads: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Metric (d): entrywise agreement of each construction between two builds.

    The grids at which a construction differs between the builds come from
    the matrix hashes in the two S0 outputs. ``arrays`` must hold the other
    build's matrices for exactly those grids; a missing or unexpected file
    is a stop. Equality is never inferred from an empty folder. Also times
    each construction.
    """

    errors = validate_evidence(payloads)
    if errors:
        return {"passed": False, "stopped": "invalid evidence", "evidence_errors": errors[:200]}
    results = sorted((payload["result"] for payload in payloads), key=lambda item: item["build_label"])
    differing = hash_agreement(results)
    expected = {f"{other_label}-{name}-{label.replace('|', '-')}.npz"
                for name, labels in differing.items() for label in labels}
    found = {path.name for path in arrays.glob(f"{other_label}-*.npz")} if arrays.is_dir() else set()
    if found != expected:
        return {"passed": False, "stopped": "saved matrices do not match the grids whose hashes differ",
                "missing": sorted(expected - found)[:20], "unexpected": sorted(found - expected)[:20]}
    report: Dict[str, Any] = {name: {"differing_grids": len(differing[name]), "max_relative_difference": 0.0}
                              for name in CONSTRUCTIONS}
    for file_name in sorted(found):
        path = arrays / file_name
        rest = path.stem.split("-", 1)[1]
        name = next(candidate for candidate in CONSTRUCTIONS if rest.startswith(candidate + "-"))
        with np.load(path) as saved:
            other = (saved["nodes"], saved["D1"], saved["D2"])
        degree, lower, upper = _parse_grid(path.stem, name)
        mine = construct(name, degree, lower, upper)
        worst = 0.0
        if mine[0].tobytes() != other[0].tobytes():
            worst = math.inf
        for a, b in zip(mine[1:], other[1:]):
            row_max = np.max(np.abs(a), axis=1)
            worst = max(worst, float(np.max(np.max(np.abs(a - b), axis=1) / row_max)))
        report[name]["max_relative_difference"] = max(report[name]["max_relative_difference"], worst)
    for name in CONSTRUCTIONS:
        started = time.perf_counter()
        for _ in range(3):
            construct(name, 640, 1.0e-5, 1.0)
        report[name]["seconds"] = (time.perf_counter() - started) / 3.0
    return report


def _parse_grid(stem: str, name: str) -> Tuple[int, float, float]:
    """Parse ``<label>-<name>-<degree>-<lower>-<upper>`` (names and numbers may contain '-')."""

    rest = stem.split("-" + name + "-", 1)[1]
    degree, bounds = rest.split("-", 1)
    for cut in range(1, len(bounds)):
        if bounds[cut] == "-":
            try:
                return int(degree), float(bounds[:cut]), float(bounds[cut + 1:])
            except ValueError:
                continue
    raise ValueError(f"cannot parse grid from {stem!r}")


# -- proposed amendment 1 (post-observation; NOT adopted) ---------------------------------
#
# docs/numerics/chebyshev-construction-repair-amendment-1.md. The frozen rule
# above stays the rule of record until the owner approves an amendment.

UNIT_ROUNDOFF = EPS / 2.0  # u = 2^-53, round to nearest
# First-order relative error of one off-diagonal D1 entry, in units of u, from
# the operation count of each declared construction (amendment Section 3).
ENTRY_ERROR_UNITS = {"C-S1": 5.0, "C-T1": 12.0, "C-T2": 12.0, "C-T3": 12.0}
# First-order relative error of one computed node difference, in units of u.
DIFFERENCE_ERROR_UNITS = {"C-S1": 1.0, "C-T1": 11.0, "C-T2": 11.0, "C-T3": 11.0}
EXPLICIT_SECOND = ("C-T2", "C-T3", "C-S1")


def apriori_action_bounds(reference: "Reference", nodes: np.ndarray, vector: np.ndarray,
                          entry_units: float, difference_units: float) -> Tuple[np.ndarray, np.ndarray]:
    """First-order a-priori bounds on ``|((R - D) v)_i|`` for D1 and explicit D2.

    Assumptions (amendment Section 3): off-diagonal D1 entries have relative
    error at most ``entry_units * u``; computed node differences at most
    ``difference_units * u``; diagonals are negative row sums rounded once;
    ``D2_ij = 2 D1_ij (D1_ii - 1/d_ij)``. Second-order terms are neglected.
    """

    u = UNIT_ROUNDOFF
    first = np.abs(reference.hi[0])
    second = np.abs(reference.hi[1])
    size = nodes.size
    off = ~np.eye(size, dtype=bool)
    spread = np.abs(vector[None, :] - vector[:, None])
    magnitude = np.abs(vector)
    entry = entry_units * u
    first_off = np.where(off, first, 0.0)
    bound_first = entry * np.sum(first_off * spread, axis=1) + u * np.diag(first) * magnitude
    diagonal_error = entry * np.sum(first_off, axis=1) + u * np.diag(first)
    inverse = np.zeros((size, size))
    inverse[off] = 1.0 / np.abs(nodes[:, None] - nodes[None, :])[off]
    second_entry = 2.0 * first_off * (diagonal_error[:, None] + (difference_units + 1.0) * u * inverse) \
        + (entry + 2.0 * u) * np.where(off, second, 0.0)
    bound_second = np.sum(second_entry * spread, axis=1) + u * np.diag(second) * magnitude
    return bound_first, bound_second


def bound_ratios(reference: "Reference", ideal_scales: Mapping[Tuple[int, str], np.ndarray], nodes: np.ndarray,
                 vectors: Mapping[str, np.ndarray], errors: Sequence[np.ndarray], name: str, degree: int) -> Dict[str, float]:
    """``max_i e_i / B_i`` per matrix, vector and row set for one construction."""

    sets = row_sets(degree)
    ratios: Dict[str, float] = {}
    for vector_name, vector in vectors.items():
        bounds = apriori_action_bounds(reference, nodes, vector, ENTRY_ERROR_UNITS[name], DIFFERENCE_ERROR_UNITS[name])
        for order, label in ((0, "D1"), (1, "D2")):
            if order == 1 and name not in EXPLICIT_SECOND:
                continue
            action = np.abs(errors[order] @ vector)
            bound = bounds[order]
            if not np.all(bound > 0.0):
                raise RequiredMetricUndefined(f"a-priori bound is zero at degree {degree}")
            for set_name, rows in sets.items():
                ratios[f"{label}_stored_{vector_name}_{set_name}"] = float(np.max(action[rows] / bound[rows]))
    return ratios


def qualification_v2(result: Mapping[str, Any]) -> Dict[str, Any]:
    """PROPOSED amendment 1; not the rule of record.

    Metric (a) and polynomial exactness keep the frozen rule. A metric (b)
    component is a regression only if it exceeds twice the current value
    AND the candidate's own a-priori rounding bound (``bound_ratio > 1``).
    A component with no recorded bound ratio keeps the frozen rule.
    """

    report: Dict[str, Any] = {}
    for name in CANDIDATES:
        failures: List[Dict[str, Any]] = []
        excused = 0
        for label, grid in result["grids"].items():
            candidate, current = grid[name], grid["current"]
            ratios = candidate.get("bound_ratio", {})
            for matrix, value in candidate["exactness"].items():
                if not value <= EXACTNESS_LIMIT:
                    failures.append({"grid": label, "metric": f"exactness:{matrix}", "candidate": value})
            for key, value in candidate["a"].items():
                if "_stored" in key and not value <= WORSENING_FACTOR * current["a"][key]:
                    failures.append({"grid": label, "metric": f"a:{key}", "candidate": value, "current": current["a"][key]})
            for key, value in candidate["b"].items():
                if "_stored" not in key or value <= WORSENING_FACTOR * current["b"][key]:
                    continue
                ratio = ratios.get(key)
                if ratio is not None and _valid_metric(ratio) and ratio <= 1.0:
                    excused += 1
                    continue
                failures.append({"grid": label, "metric": f"b:{key}", "candidate": value, "current": current["b"][key],
                                 "bound_ratio": ratio})
        report[name] = {"qualified": not failures, "failure_count": len(failures), "excused_within_bound": excused,
                        "failures": failures[:40]}
    return report


# -- S1: qualification and selection (plan Section 5) ---------------------------------

def qualification(result: Mapping[str, Any]) -> Dict[str, Any]:
    """Apply the frozen qualification rule to one build's S0 result.

    Every operator-agreement component against ``R_stored`` (each matrix,
    each test vector and each row set separately) must be at most
    ``WORSENING_FACTOR`` times the current construction's, and polynomial
    exactness at most ``EXACTNESS_LIMIT``, at every grid.
    """

    report: Dict[str, Any] = {}
    for name in CANDIDATES:
        failures: List[Dict[str, Any]] = []
        worst_ratio = 0.0
        worst_exactness = 0.0
        comparisons = 0
        for label, grid in result["grids"].items():
            candidate, current = grid[name], grid["current"]
            for matrix, value in candidate["exactness"].items():
                worst_exactness = max(worst_exactness, value)
                if not value <= EXACTNESS_LIMIT:
                    failures.append({"grid": label, "metric": f"exactness:{matrix}", "candidate": value})
            for group in ("a", "b"):
                for key, value in candidate[group].items():
                    if "_stored" not in key:
                        continue
                    comparisons += 1
                    base = current[group][key]
                    if value <= WORSENING_FACTOR * base:
                        ratio = value / base if base > 0.0 else 0.0
                    else:
                        ratio = value / base if base > 0.0 else math.inf
                        failures.append({"grid": label, "metric": f"{group}:{key}", "candidate": value,
                                         "current": base, "ratio": ratio})
                    worst_ratio = max(worst_ratio, ratio)
        sizes = [item["candidate"] for item in failures if "current" in item]
        report[name] = {
            "qualified": not failures, "failure_count": len(failures), "comparisons": comparisons,
            "worst_ratio_to_current": worst_ratio, "worst_exactness": worst_exactness,
            # Information only; the rule has no rounding floor.
            "failures_by_candidate_size": {
                "below_1_eps": sum(1 for value in sizes if value < EPS),
                "1_to_4_eps": sum(1 for value in sizes if EPS <= value < 4 * EPS),
                "4_to_8_eps": sum(1 for value in sizes if 4 * EPS <= value < 8 * EPS),
                "8_to_64_eps": sum(1 for value in sizes if 8 * EPS <= value < 64 * EPS),
                "at_least_64_eps": sum(1 for value in sizes if value >= 64 * EPS),
                "largest": max(sizes) if sizes else 0.0,
            },
            "failures": sorted(failures, key=lambda item: -item.get("ratio", math.inf))[:40],
        }
    return report


REQUIRED_BUILDS = ("B1", "B3")
REQUIRED_FIXTURES = ("F1_oracle_arithmetic", "F2_recurrence_independence", "F3_oracle_polynomial_exactness",
                     "F4_artifacts_and_continuity", "F5_candidate_api")
A_KEYS = frozenset(f"{matrix}_{target}" for matrix in ("D1", "D2") for target in ("stored", "ideal"))
B_KEYS = frozenset(f"{matrix}_{target}_{vector}_{rows}" for matrix in ("D1", "D2") for target in ("stored", "ideal")
                   for vector in ("v1", "v2", "v3") for rows in ("all", "uv", "ir"))
METRIC_C_KEYS = ("worst_rows_1_3_scaled", "worst_rows_1_3_abs", "worst_all_rows_scaled")
ARTIFACT_COUNT = 8


def expected_grid_labels() -> List[str]:
    return [f"{degree}|{lower!r}|{upper!r}" for degree in DEGREES for lower, upper in INTERVALS]


def _valid_metric(value: Any) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(float(value)) and float(value) >= 0.0)


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def validate_evidence(payloads: Sequence[Mapping[str, Any]]) -> List[str]:
    """Return every reason the S0 evidence cannot be admitted to selection.

    Admission requires one complete, successful S0 output for each required
    build, produced under the frozen plan by one tool version: all fixtures
    passed, production equal to the legacy construction, the full grid and
    metric sets present, and every metric finite and non-negative.
    """

    errors: List[str] = []
    labels: List[str] = []
    for index, payload in enumerate(payloads):
        where = f"input {index}"
        if not isinstance(payload, Mapping) or not isinstance(payload.get("result"), Mapping):
            errors.append(f"{where}: not an S0 output")
            continue
        result = payload["result"]
        label = result.get("build_label")
        where = f"input {index} ({label})"
        labels.append(label)
        if payload.get("tool") != "chebyshev-repair" or payload.get("stage") != "s0":
            errors.append(f"{where}: not a chebyshev-repair s0 output")
        if payload.get("status") != "ok":
            errors.append(f"{where}: status is {payload.get('status')!r}")
        if payload.get("plan_sha256") != _file_sha256(ROOT / PLAN):
            errors.append(f"{where}: plan hash does not match the frozen plan")
        if not _is_sha256(payload.get("tool_sha256")):
            errors.append(f"{where}: tool hash missing")
        if result.get("passed") is not True or "stopped" in result:
            errors.append(f"{where}: S0 did not pass")
        fixtures = result.get("fixtures")
        for name in REQUIRED_FIXTURES:
            if not isinstance(fixtures, Mapping) or not isinstance(fixtures.get(name), Mapping) \
                    or fixtures[name].get("passed") is not True:
                errors.append(f"{where}: fixture {name} missing or not passed")
        if result.get("production_equals_current_construction") is not True:
            errors.append(f"{where}: production was not the legacy construction")
        grids = result.get("grids")
        expected = expected_grid_labels()
        if not isinstance(grids, Mapping) or sorted(grids) != sorted(expected):
            count = len(grids) if isinstance(grids, Mapping) else 0
            errors.append(f"{where}: grid set is not the plan's {len(expected)} grids (found {count})")
        else:
            for grid_label, grid in grids.items():
                if not isinstance(grid, Mapping) or sorted(grid) != sorted(CONSTRUCTIONS):
                    errors.append(f"{where}: {grid_label}: construction set incomplete")
                    continue
                for name, entry in grid.items():
                    place = f"{where}: {grid_label}: {name}"
                    if not isinstance(entry, Mapping):
                        errors.append(f"{place}: entry missing")
                        continue
                    for group, keys in (("a", A_KEYS), ("b", B_KEYS), ("exactness", frozenset(("D1", "D2")))):
                        values = entry.get(group)
                        if not isinstance(values, Mapping) or frozenset(values) != keys:
                            errors.append(f"{place}: metric group {group} incomplete")
                        elif not all(_valid_metric(value) for value in values.values()):
                            errors.append(f"{place}: metric group {group} has a non-finite or negative value")
                    hashes = entry.get("sha256")
                    if not isinstance(hashes, Mapping) or sorted(hashes) != ["D1", "D2", "nodes"] \
                            or not all(_is_sha256(value) for value in hashes.values()):
                        errors.append(f"{place}: matrix hashes missing")
        metric = result.get("metric_c")
        if not isinstance(metric, Mapping) or sorted(metric) != sorted(CONSTRUCTIONS):
            errors.append(f"{where}: metric (c) incomplete")
        else:
            for name, item in metric.items():
                if not isinstance(item, Mapping) or not all(_valid_metric(item.get(key)) for key in METRIC_C_KEYS):
                    errors.append(f"{where}: metric (c) of {name} has a missing, non-finite or negative value")
                artifacts = item.get("artifacts") if isinstance(item, Mapping) else None
                names = [entry.get("artifact") for entry in artifacts] if isinstance(artifacts, list) else []
                if len(names) != ARTIFACT_COUNT or len(set(names)) != ARTIFACT_COUNT:
                    errors.append(f"{where}: metric (c) of {name} does not cover the {ARTIFACT_COUNT} artifacts")
            current = metric.get("current", {})
            if isinstance(current, Mapping) and _valid_metric(current.get("worst_rows_1_3_scaled")) \
                    and not current["worst_rows_1_3_scaled"] > 0.0:
                errors.append(f"{where}: baseline metric (c) is not positive")
    if len(labels) != len(set(labels)):
        errors.append(f"duplicate build labels: {labels}")
    if sorted(str(label) for label in labels) != sorted(REQUIRED_BUILDS):
        errors.append(f"builds {labels} are not exactly {list(REQUIRED_BUILDS)}")
    tools = {payload.get("tool_sha256") for payload in payloads if isinstance(payload, Mapping)}
    if len(tools) > 1:
        errors.append("inputs were produced by different tool versions")
    return errors


def hash_agreement(results: Sequence[Mapping[str, Any]]) -> Dict[str, List[str]]:
    """Grids at which each construction's matrices differ between the two builds."""

    first, second = results
    differing: Dict[str, List[str]] = {name: [] for name in CONSTRUCTIONS}
    for label in expected_grid_labels():
        for name in CONSTRUCTIONS:
            if first["grids"][label][name]["sha256"] != second["grids"][label][name]["sha256"]:
                differing[name].append(label)
    return differing


def validate_agreement(payload: Optional[Mapping[str, Any]], results: Sequence[Mapping[str, Any]]) -> List[str]:
    """Check that build-agreement evidence is consistent with the matrix hashes.

    Equality between builds is established by the hashes in the S0 evidence,
    never by the absence of a saved matrix file.
    """

    differing = hash_agreement(results)
    if payload is None:
        return []
    errors: List[str] = []
    result = payload.get("result") if isinstance(payload, Mapping) else None
    if not isinstance(result, Mapping) or payload.get("stage") != "build-agreement" or payload.get("status") != "ok":
        return ["build-agreement input is not a successful build-agreement output"]
    for name in CONSTRUCTIONS:
        item = result.get(name)
        if not isinstance(item, Mapping):
            errors.append(f"build agreement: {name} missing")
            continue
        if item.get("differing_grids") != len(differing[name]):
            errors.append(f"build agreement: {name} reports {item.get('differing_grids')} differing grids; "
                          f"the hashes give {len(differing[name])}")
        value = item.get("max_relative_difference")
        if not _valid_metric(value) or (len(differing[name]) > 0) != (value > 0.0):
            errors.append(f"build agreement: {name} difference is inconsistent with the hashes")
        if not _valid_metric(item.get("seconds")):
            errors.append(f"build agreement: {name} timing missing")
    return errors


def selection(payloads: Sequence[Mapping[str, Any]], agreement: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Admit the evidence, then apply the frozen selection rule.

    ``payloads`` are complete S0 outputs (not bare results). Invalid,
    incomplete, duplicate or partial evidence is rejected, never selected
    from.
    """

    errors = validate_evidence(payloads)
    if errors:
        return {"passed": False, "stopped": "invalid evidence", "evidence_errors": errors[:200],
                "evidence_error_count": len(errors)}
    results = sorted((payload["result"] for payload in payloads), key=lambda item: item["build_label"])
    errors = validate_agreement(agreement, results)
    if errors:
        return {"passed": False, "stopped": "invalid build-agreement evidence", "evidence_errors": errors}
    outcome = selection_rule(results, agreement["result"] if agreement is not None else None)
    outcome["evidence"] = {"plan_sha256": payloads[0]["plan_sha256"], "tool_sha256": payloads[0]["tool_sha256"],
                           "differing_grids": {name: len(labels) for name, labels in hash_agreement(results).items()}}
    return outcome


def selection_rule(results: Sequence[Mapping[str, Any]], build_agreement: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """The frozen selection rule (plan Section 5) on already admitted results."""

    per_build = {result["build_label"]: qualification(result) for result in results}
    qualified = [name for name in CANDIDATES if all(report[name]["qualified"] for report in per_build.values())]
    metric: Dict[str, Any] = {}
    for name in CONSTRUCTIONS:
        metric[name] = {
            "worst_rows_1_3_scaled": max(result["metric_c"][name]["worst_rows_1_3_scaled"] for result in results),
            "worst_rows_1_3_abs": max(result["metric_c"][name]["worst_rows_1_3_abs"] for result in results),
        }
    baseline = metric["current"]["worst_rows_1_3_scaled"]
    if not baseline > 0.0:
        return {"passed": False, "stopped": "required metric undefined: baseline metric (c) is not positive",
                "qualification": per_build}
    for name in CANDIDATES:
        metric[name]["improvement"] = baseline / metric[name]["worst_rows_1_3_scaled"] \
            if metric[name]["worst_rows_1_3_scaled"] > 0.0 else math.inf
    outcome: Dict[str, Any] = {"qualification": per_build, "qualified": qualified, "metric_c": metric,
                               "build_agreement": build_agreement}
    eligible = [name for name in qualified if metric[name]["improvement"] >= IMPROVEMENT_FACTOR]
    if not eligible:
        outcome.update({"passed": False, "selected": None,
                        "stopped": "no qualified candidate reaches the required improvement"
                        if qualified else "no candidate qualifies"})
        return outcome
    best = min(metric[name]["worst_rows_1_3_scaled"] for name in eligible)
    tied = [name for name in eligible if metric[name]["worst_rows_1_3_scaled"] <= TIE_FACTOR * best]
    if len(tied) > 1:
        if build_agreement is None:
            outcome.update({"passed": False, "selected": None, "tied": tied,
                            "stopped": "a tie needs build-agreement evidence"})
            return outcome
        tied.sort(key=lambda name: (build_agreement[name]["max_relative_difference"],
                                    build_agreement[name]["seconds"]))
    outcome.update({"passed": True, "selected": tied[0], "tied": tied})
    return outcome


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


def _read_json(path: Path) -> Any:
    """Read an evidence file; an unreadable file becomes an inadmissible input."""

    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as error:
        return {"unreadable": f"{Path(path).name}: {type(error).__name__}"}


def emit(stage: str, result: Mapping[str, Any], started: float, compact: bool = False) -> int:
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
    layout = {"separators": (",", ":")} if compact else {"indent": 2}
    print(json.dumps(_jsonable(payload), sort_keys=True, allow_nan=False, **layout))
    return 0 if payload["status"] == "ok" else 2


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="stage", required=True)
    commands.add_parser("p0")
    commands.add_parser("p0-revalidate")
    s0 = commands.add_parser("s0")
    s0.add_argument("--build-label", required=True, choices=("B1", "B3"))
    s0.add_argument("--degrees", help="comma-separated subset, for development only")
    s0.add_argument("--reference", type=Path, help="another build's S0 output; identical matrices inherit its metrics")
    s0.add_argument("--save-dir", type=Path, help="where differing matrices are saved for metric (d)")
    agreement = commands.add_parser("build-agreement")
    agreement.add_argument("--arrays", type=Path, required=True, help="matrices saved by the other build's S0")
    agreement.add_argument("--other-label", required=True)
    agreement.add_argument("--s0", nargs=2, type=Path, required=True, help="S0 outputs of both builds")
    select = commands.add_parser("select")
    select.add_argument("s0", nargs="+", type=Path, help="S0 outputs of every build")
    select.add_argument("--build-agreement", type=Path)
    args = parser.parse_args(argv)
    started = time.perf_counter()
    if args.stage == "p0":
        return emit("p0", p0_check(), started)
    if args.stage == "p0-revalidate":
        return emit("p0-revalidate", p0_revalidation(), started)
    if args.stage == "s0":
        degrees = DEGREES if not args.degrees else tuple(int(value) for value in args.degrees.split(","))
        reference = json.loads(args.reference.read_text())["result"] if args.reference else None
        if args.save_dir:
            args.save_dir.mkdir(parents=True, exist_ok=True)
        try:
            result = s0_run(args.build_label, degrees, INTERVALS, reference, args.save_dir)
        except RequiredMetricUndefined as error:
            result = {"passed": False, "stopped": f"required metric undefined: {error}"}
        return emit("s0", result, started, compact=True)
    if args.stage == "build-agreement":
        payloads = [_read_json(path) for path in args.s0]
        return emit("build-agreement", build_agreement(args.arrays, args.other_label, payloads), started)
    if args.stage == "select":
        payloads = [_read_json(path) for path in args.s0]
        agreement = _read_json(args.build_agreement) if args.build_agreement else None
        return emit("select", selection(payloads, agreement), started)
    raise SystemExit(f"unknown stage {args.stage}")


if __name__ == "__main__":
    raise SystemExit(main())
