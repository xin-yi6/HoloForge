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
            for order, matrix, label in ((0, first, "D1"), (1, second, "D2")):
                stored_error = reference.error(order, matrix)
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
        "seconds_by_grid_max": max(timings.values()), "seconds_total_grids": sum(timings.values()),
    }
    if metric_c is not None:
        fixtures["F4_artifacts_and_continuity"] = continuity_fixture(metric_c["current"], build_label)
    result["passed"] = all(item["passed"] for item in fixtures.values())
    if not result["passed"]:
        result["stopped"] = "a fixture failed"
    return result


def build_agreement(arrays: Path, other_label: str) -> Dict[str, Any]:
    """Metric (d): entrywise agreement of each construction between two builds.

    ``arrays`` holds the matrices the other build's S0 saved because their
    hashes differed from this build's. Constructions with no saved file are
    bit-identical across the builds. Also times each construction.
    """

    report: Dict[str, Any] = {name: {"differing_grids": 0, "max_relative_difference": 0.0} for name in CONSTRUCTIONS}
    for path in sorted(arrays.glob(f"{other_label}-*.npz")):
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
        report[name]["differing_grids"] += 1
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


def selection(results: Sequence[Mapping[str, Any]], build_agreement: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Apply the frozen selection rule to the S0 results of all builds."""

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
    if len(tied) > 1 and build_agreement is not None:
        tied.sort(key=lambda name: (build_agreement.get(name, {}).get("max_relative_difference", math.inf),
                                    build_agreement.get(name, {}).get("seconds", math.inf)))
    else:
        tied.sort(key=lambda name: metric[name]["worst_rows_1_3_scaled"])
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
    s0 = commands.add_parser("s0")
    s0.add_argument("--build-label", required=True, choices=("B1", "B3"))
    s0.add_argument("--degrees", help="comma-separated subset, for development only")
    s0.add_argument("--reference", type=Path, help="another build's S0 output; identical matrices inherit its metrics")
    s0.add_argument("--save-dir", type=Path, help="where differing matrices are saved for metric (d)")
    agreement = commands.add_parser("build-agreement")
    agreement.add_argument("--arrays", type=Path, required=True, help="matrices saved by the other build's S0")
    agreement.add_argument("--other-label", required=True)
    select = commands.add_parser("select")
    select.add_argument("s0", nargs="+", type=Path, help="S0 outputs of every build")
    select.add_argument("--build-agreement", type=Path)
    args = parser.parse_args(argv)
    started = time.perf_counter()
    if args.stage == "p0":
        return emit("p0", p0_check(), started)
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
        return emit("build-agreement", build_agreement(args.arrays, args.other_label), started)
    if args.stage == "select":
        results = [json.loads(path.read_text())["result"] for path in args.s0]
        agreement = json.loads(args.build_agreement.read_text())["result"] if args.build_agreement else None
        return emit("select", selection(results, agreement), started)
    raise SystemExit(f"unknown stage {args.stage}")


if __name__ == "__main__":
    raise SystemExit(main())
