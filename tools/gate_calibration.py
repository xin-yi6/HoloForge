"""Read-only calibration diagnostics for three platform-sensitive gates.

Implements the frozen plan in ``docs/numerics/gate-calibration-2026-09-plan.md``
(Batch 2a). It reuses production solvers and never changes a production
solver, gate, threshold or record. Every reconstruction of a production
quantity is checked against the production value before it is used, and
those identity checks are reported in the output.

Subcommands (each prints JSON):

    python tools/gate_calibration.py soft-wall
    python tools/gate_calibration.py gn
    python tools/gate_calibration.py optical
    python tools/gate_calibration.py optical-ob
    python tools/gate_calibration.py optical-oc --build-label B1

``optical-ob`` implements the separate O-B plan,
``docs/numerics/optical-ob-diagnosis-plan.md``: a 50-digit evaluation of
the stored optical solution's polynomial at the single-node spike. It has
no adverse controls or confirmation cases. ``optical-oc`` implements
``docs/numerics/optical-oc-diagnosis-plan.md`` and writes its large arrays
to the Git-ignored ``output/optical-oc-artifacts/``.

``--adverse`` adds the plan's adverse controls. ``--case-set confirmation``
selects the reserved confirmation cases, which Batch 2a must not run.

Exit status: 0 when every identity check and fixture passes and every
diagnostic number is finite, whatever the scientific values; 2 when the
diagnostic itself failed (the JSON is still printed, with ``status`` and
``diagnostic_errors``). Identity checks compare the maximum of each
reconstructed residual with production, not every node.

The soft-wall ``relative_floor_estimates`` are the first-order perturbation
scale ``eps ||H||_2 kappa_j / |lambda_j|`` for a simple eigenvalue. It is an
order-of-magnitude reference, not a proved lower error floor.
"""

from __future__ import annotations

import argparse
import dataclasses
from decimal import Decimal, localcontext
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple
from unittest.mock import patch

import numpy as np
from scipy.linalg import eig

try:  # Running from a checkout without installation.
    import holoforge  # noqa: F401
except ImportError:  # pragma: no cover - exercised only outside the test setup
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from holoforge.core.provenance import runtime_versions
from holoforge.numerics import chebyshev_lobatto_grid


EPS = float(np.finfo(float).eps)
HIGH_PRECISION_DIGITS = 50


def rounding_gamma(count: int) -> float:
    """Return the standard rounding constant ``n eps / (1 - n eps)``."""

    product = count * EPS
    return product / (1.0 - product)


# ---------------------------------------------------------------------------
# Soft-wall spectral refinement
# ---------------------------------------------------------------------------

SOFT_WALL_CASES = {
    "calibration": {
        "degrees": tuple(range(24, 121, 8)),
        "kappas": (1.0,),
        "z_max_factors": (None,),
    },
    "confirmation": {
        "degrees": (60, 76, 92),
        "kappas": (0.5, 2.0),
        "z_max_factors": (None,),
    },
}


def soft_wall_degree_record(
    degree: int, kappa: float = 1.0, z_max_factor: Optional[float] = None, modes: int = 4
) -> Dict[str, Any]:
    """Errors, eigenvalue condition numbers and floor estimates at one degree."""

    from holoforge.benchmarks import soft_wall_vector as soft_wall

    z_max = None if z_max_factor is None else z_max_factor / kappa
    config = soft_wall.SoftWallConfig(
        kappa_gev=kappa, z_max_gev_inverse=z_max, spectral_degree=max(degree, 24)
    )
    production, _ = soft_wall._spectral_spectrum(config, modes, degree)
    analytic = soft_wall.analytic_mass_squared(modes, kappa)
    errors = np.abs(production - analytic) / analytic

    grid = chebyshev_lobatto_grid(degree, 0.0, config.resolved_z_max_gev_inverse)
    interior = slice(1, -1)
    operator = -grid.second_derivative[interior, interior] + np.diag(
        soft_wall.schrodinger_potential(grid.nodes[interior], kappa)
    )
    values, left, right = eig(operator, left=True, right=True)
    norm = float(np.linalg.norm(operator, 2))
    conditions = []
    floors = []
    for target in production:
        index = int(np.argmin(np.abs(values - target)))
        x = right[:, index]
        y = left[:, index]
        condition = float(
            np.linalg.norm(x) * np.linalg.norm(y) / abs(np.vdot(y, x))
        )
        conditions.append(condition)
        floors.append(EPS * norm * condition / abs(float(target)))
    return {
        "degree": int(degree),
        "kappa_gev": float(kappa),
        "z_max_gev_inverse": float(config.resolved_z_max_gev_inverse),
        "relative_errors": [float(value) for value in errors],
        "max_relative_error": float(np.max(errors)),
        "eigenvalue_condition_numbers": conditions,
        "operator_two_norm": norm,
        "relative_floor_estimates": floors,
        "max_error_to_floor": float(np.max(errors / np.asarray(floors))),
    }


def soft_wall_run(case_set: str, adverse: bool) -> Dict[str, Any]:
    cases = SOFT_WALL_CASES[case_set]
    records = [
        soft_wall_degree_record(degree, kappa, factor)
        for kappa in cases["kappas"]
        for factor in cases["z_max_factors"]
        for degree in cases["degrees"]
    ]
    result: Dict[str, Any] = {"records": records}
    if adverse:
        result["adverse"] = soft_wall_adverse()
    return result


def soft_wall_adverse() -> Dict[str, Any]:
    from holoforge.benchmarks import soft_wall_vector as soft_wall

    controls: Dict[str, Any] = {}
    for degree in (24, 32):
        controls[f"coarse-degree-{degree}"] = soft_wall_degree_record(degree)
    for factor in (4.0, 6.0):
        controls[f"z-max-{factor:g}-over-kappa"] = [
            soft_wall_degree_record(degree, 1.0, factor) for degree in (48, 56, 64)
        ]
    analytic = soft_wall.analytic_mass_squared(4, 1.0)
    config = soft_wall.SoftWallConfig(spectral_degree=64)
    production, _ = soft_wall._spectral_spectrum(config, 4, 64)
    swapped = production.copy()
    swapped[[0, 1]] = swapped[[1, 0]]
    controls["swapped-eigenvalues"] = {
        "max_relative_error": float(np.max(np.abs(swapped - analytic) / analytic)),
        "production_spectrum_tolerance": soft_wall.DEFAULT_TOLERANCE,
    }
    nonfinite = production.copy()
    nonfinite[2] = np.nan
    errors = np.abs(nonfinite - analytic) / analytic
    controls["non-finite-eigenvalue"] = {
        "any_nonfinite_error": bool(not np.all(np.isfinite(errors))),
    }
    return controls


# ---------------------------------------------------------------------------
# Candidate soft-wall refinement rule S-A (docs/numerics/soft-wall-refinement-sa-contract.md)
# ---------------------------------------------------------------------------

SA_CONTRACT = Path("docs/numerics/soft-wall-refinement-sa-contract.md")
SA_MODES = 4
SA_MATCH_FACTOR = 1.0
SA_PLATEAU_FACTOR = 1.0

SA_CASES = {
    "calibration": {
        "cases": tuple((n, 1.0, None) for n in range(24, 121, 8)),
        "adverse": tuple((n, 1.0, factor) for factor in (4.0, 6.0) for n in (48, 56, 64)),
    },
    "confirmation": {
        "cases": tuple((n, kappa, None) for kappa in (0.5, 0.7, 2.0) for n in (60, 76, 92)),
        "adverse": (),
    },
}


def soft_wall_level(degree: int, kappa: float, z_max_factor: Optional[float]) -> Dict[str, Any]:
    """Production eigenvalues and per-mode perturbation data at one degree."""

    from holoforge.benchmarks import soft_wall_vector as soft_wall

    z_max = None if z_max_factor is None else z_max_factor / kappa
    config = soft_wall.SoftWallConfig(
        kappa_gev=kappa, z_max_gev_inverse=z_max, spectral_degree=max(degree, 24)
    )
    eigenvalues, _ = soft_wall._spectral_spectrum(config, SA_MODES, degree)
    analytic = soft_wall.analytic_mass_squared(SA_MODES, kappa)
    grid = chebyshev_lobatto_grid(degree, 0.0, config.resolved_z_max_gev_inverse)
    interior = slice(1, -1)
    operator = -grid.second_derivative[interior, interior] + np.diag(
        soft_wall.schrodinger_potential(grid.nodes[interior], kappa)
    )
    values, left, right = eig(operator, left=True, right=True)
    norm = float(np.linalg.norm(operator, 2))
    matched, conditions = [], []
    for target in eigenvalues:
        index = int(np.argmin(np.abs(values - target)))
        x, y = right[:, index], left[:, index]
        conditions.append(float(np.linalg.norm(x) * np.linalg.norm(y) / abs(np.vdot(y, x))))
        matched.append(complex(values[index]))
    return {
        "degree": int(degree),
        "eigenvalues": [float(value) for value in eigenvalues],
        "analytic": [float(value) for value in analytic],
        "matched_with_vectors": [[value.real, value.imag] for value in matched],
        "condition_numbers": conditions,
        "operator_two_norm": norm,
    }


def sa_verdict(levels: Sequence[Mapping[str, Any]], spectrum_tolerance: float = 2.0e-4,
               accuracy: float = 1.0e-8) -> Dict[str, Any]:
    """Evaluate the current rule and candidate S-A on three refinement levels.

    Pure function of the recorded level data, so synthetic adverse cases can
    be evaluated without a solve.
    """

    def errors(level):
        lam = np.asarray(level["eigenvalues"], dtype=float)
        exact = np.asarray(level["analytic"], dtype=float)
        return np.abs(lam - exact) / exact

    def scales(level):
        lam = np.asarray(level["eigenvalues"], dtype=float)
        return EPS * level["operator_two_norm"] * np.asarray(level["condition_numbers"]) / np.abs(lam)

    per_level = [errors(level) for level in levels]
    maxima = [float(np.max(item)) if np.all(np.isfinite(item)) else float("nan") for item in per_level]
    finite = all(math.isfinite(value) for value in maxima)
    branch_a = finite and maxima[0] > maxima[1] > maxima[2]
    branch_b = finite and maxima[2] <= accuracy
    spectrum = finite and maxima[2] <= spectrum_tolerance

    plateau_rows = []
    branch_p = finite
    for level, err in zip(levels[1:], per_level[1:]):
        lam = np.asarray(level["eigenvalues"], dtype=float)
        scale = scales(level)
        mu = np.asarray([complex(a, b) for a, b in level["matched_with_vectors"]])
        match = np.abs(mu - lam) / np.abs(lam)
        ok_finite = bool(np.all(np.isfinite(lam)) and np.all(np.isfinite(err)) and np.all(np.isfinite(scale)))
        ok_match = ok_finite and bool(np.all(match <= SA_MATCH_FACTOR * scale))
        ok_plateau = ok_finite and bool(np.all(err <= SA_PLATEAU_FACTOR * scale))
        branch_p = branch_p and ok_finite and ok_match and ok_plateau
        plateau_rows.append({
            "degree": level["degree"],
            "max_error_to_scale": float(np.max(err / scale)) if ok_finite else None,
            "max_match_to_scale": float(np.max(match / scale)) if ok_finite else None,
            "finite": ok_finite, "match": ok_match, "plateau": ok_plateau,
        })
    stability = None
    if branch_p:
        fine, middle = levels[2], levels[1]
        lam_n = np.asarray(fine["eigenvalues"])
        lam_m = np.asarray(middle["eigenvalues"])
        allowed = scales(fine) + scales(middle)
        ratio = np.abs(lam_n - lam_m) / np.abs(lam_n) / allowed
        stability = float(np.max(ratio))
        branch_p = branch_p and bool(np.all(ratio <= 1.0))
    return {
        "max_errors": maxima,
        "current_rule_pass": bool(branch_a and branch_b),
        "sa_pass": bool(branch_b and (branch_a or branch_p)),
        "branch_a_strict_decrease": bool(branch_a),
        "branch_b_accuracy": bool(branch_b),
        "branch_p_plateau": bool(branch_p),
        "spectrum_tolerance_pass": bool(spectrum),
        "plateau_levels": plateau_rows,
        "stability_to_allowed": stability,
    }


def soft_wall_sa_case(n: int, kappa: float, z_max_factor: Optional[float]) -> Dict[str, Any]:
    from holoforge.benchmarks import soft_wall_vector as soft_wall

    levels = [soft_wall_level(d, kappa, z_max_factor) for d in (n - 16, n - 8, n)]
    verdict = sa_verdict(levels)
    z_max = None if z_max_factor is None else z_max_factor / kappa
    production = soft_wall.solve_spectrum(
        soft_wall.SoftWallConfig(kappa_gev=kappa, z_max_gev_inverse=z_max, spectral_degree=n),
        num_modes=SA_MODES, method="spectral",
    )
    record = production.to_dict(soft_wall.DEFAULT_TOLERANCE)
    production_refinement = next(
        check["passed"] for check in record["acceptance_checks"]
        if check["id"] == "spectral-degree-refinement"
    )
    # Production declares its rule version. Version 1 (no declaration) is the
    # strictly-decreasing rule; version 2 is S-A, which production now uses.
    production_rule = record["numerical_method"].get("refinement_rule", "version-1")
    expected = verdict["sa_pass"] if production_rule.endswith("-v2") else verdict["current_rule_pass"]
    identity = (
        list(production.spectral_refinement_errors) == verdict["max_errors"]
        and production_refinement == expected
    )
    return {
        "N": int(n), "kappa_gev": float(kappa),
        "z_max_factor": z_max_factor,
        "levels": levels,
        "verdict": verdict,
        "identity_check": {
            "production_refinement_errors": list(production.spectral_refinement_errors),
            "production_refinement_pass": bool(production_refinement),
            "production_refinement_rule": production_rule,
            "exact_match": bool(identity),
        },
    }


def soft_wall_sa_synthetic(base: Mapping[str, Any]) -> Dict[str, Any]:
    """Swapped and non-finite eigenvalue controls on a recorded plateau case."""

    swapped = [dict(level) for level in base["levels"]]
    finest = list(swapped[2]["eigenvalues"])
    finest[0], finest[1] = finest[1], finest[0]
    swapped[2] = {**swapped[2], "eigenvalues": finest}
    nonfinite = [dict(level) for level in base["levels"]]
    finest = list(nonfinite[2]["eigenvalues"])
    finest[2] = float("nan")
    nonfinite[2] = {**nonfinite[2], "eigenvalues": finest}
    swapped_verdict = sa_verdict(swapped)
    nonfinite_verdict = sa_verdict(nonfinite)
    # A non-finite value is the expected input of this control, not a tool failure.
    nonfinite_verdict["max_errors"] = [str(value) for value in nonfinite_verdict["max_errors"]]
    return {
        "base_N": base["N"],
        "swapped": {k: swapped_verdict[k] for k in ("current_rule_pass", "sa_pass", "spectrum_tolerance_pass")},
        "non_finite": {k: nonfinite_verdict[k] for k in ("current_rule_pass", "sa_pass", "spectrum_tolerance_pass")},
    }


def soft_wall_sa_run(case_set: str, adverse: bool) -> Dict[str, Any]:
    spec = SA_CASES[case_set]
    records = [soft_wall_sa_case(n, kappa, factor) for n, kappa, factor in spec["cases"]]
    result: Dict[str, Any] = {
        "contract_sha256": _file_sha256(Path(__file__).resolve().parents[1] / SA_CONTRACT),
        "records": records,
    }
    if adverse:
        result["adverse"] = [soft_wall_sa_case(n, kappa, factor) for n, kappa, factor in spec["adverse"]]
        plateau = next((r for r in records if r["N"] == 64 and r["kappa_gev"] == 1.0), records[-1])
        result["synthetic"] = soft_wall_sa_synthetic(plateau)
    return result


# ---------------------------------------------------------------------------
# Gubser--Nellore collocation residual
# ---------------------------------------------------------------------------

GN_CASES = {
    "calibration": {
        "qcd-like": {"degrees": (80, 120, 150), "cases": ((150, 1.23), (80, 1.04), (150, 1.10))},
        "cosh-calibration": {"degrees": (40, 60, 80), "cases": ("worst",)},
    },
    "confirmation": {
        "qcd-like": {"degrees": (80, 100, 140), "cases": ("worst",)},
        "cosh-calibration": {"degrees": (40, 60, 70), "cases": ("worst",)},
    },
}


def gn_branch_grid(identifier: str) -> np.ndarray:
    if identifier == "qcd-like":
        return np.linspace(0.20, 1.25, 106)
    return np.geomspace(0.10, 35.5, 100)


def gn_raw_terms(
    preset: Any,
    x_h: float,
    u: np.ndarray,
    fields: Mapping[str, np.ndarray],
    *,
    absolute: bool = False,
) -> Dict[str, List[np.ndarray]]:
    """Return the individual terms of the three scaled coupled equations.

    With ``absolute=True`` every signed constant and potential term is
    replaced by its magnitude. Passing absolute inputs, with derivatives
    replaced by ``|D| |x|``, then gives the magnitude that bounds rounding in
    evaluating the terms.
    """

    f, fu, fuu = fields["f"], fields["fu"], fields["fuu"]
    c, cu, cuu = fields["c"], fields["cu"], fields["cuu"]
    q, qu, quu = fields["q"], fields["qu"], fields["quu"]
    p = preset.uv_power
    sign = abs if absolute else (lambda value: value)
    a_x_scaled = 2.0 * u * c + u**2 * cu
    scalar_x = q + u * qu
    # The signed branch repeats the production operation order exactly.
    if absolute:
        f_coefficient = 3.0 * x_h**2 * u * a_x_scaled + abs(1.0 - 4.0 / p)
    else:
        f_coefficient = 3.0 * x_h**2 * u * a_x_scaled + 1.0 - 4.0 / p
    f_terms = [u * fuu, f_coefficient * fu]
    warp_terms = [
        2.0 * c + 4.0 * u * cu + u**2 * cuu,
        sign(1.0 + 1.0 / p) * (2.0 * c + u * cu),
        sign(-1.0) * x_h**2 * a_x_scaled**2,
        scalar_x**2 / 6.0,
    ]
    scalar = x_h * u * q
    a_e = x_h**2 * u**2 * (fields["c_signed"] if absolute else c)
    if absolute:
        potential_prime = (
            12.0 * preset.gamma * np.abs(np.sinh(preset.gamma * scalar))
            + 2.0 * preset.b * np.abs(scalar)
        )
    else:
        potential_prime = np.asarray(preset.first_derivative(scalar), dtype=float)
    third = np.zeros_like(u)
    mask = u != 0.0
    third[mask] = (
        sign(-1.0) * np.exp(2.0 * a_e[mask]) * potential_prime[mask]
        / (p**2 * x_h * u[mask])
    )
    scalar_terms = [
        u * f * (2.0 * qu + u * quu),
        (3.0 * x_h**2 * u * f * a_x_scaled + sign(1.0 - 4.0 / p) * f + u * fu)
        * scalar_x,
        third,
    ]
    return {"f": f_terms, "warp": warp_terms, "scalar": scalar_terms}


def gn_normalized(terms: Sequence[np.ndarray]) -> np.ndarray:
    return sum(terms) / (1.0 + sum(np.abs(term) for term in terms))


def gn_fields(degree: int, f: np.ndarray, c: np.ndarray, q: np.ndarray) -> Dict[str, Any]:
    grid = chebyshev_lobatto_grid(int(degree), 0.0, 1.0)
    d1, d2 = grid.first_derivative, grid.second_derivative
    fields = {
        "f": f, "fu": d1 @ f, "fuu": d2 @ f,
        "c": c, "cu": d1 @ c, "cuu": d2 @ c,
        "q": q, "qu": d1 @ q, "quu": d2 @ q,
    }
    absolute = {
        "f": np.abs(f), "fu": np.abs(d1) @ np.abs(f), "fuu": np.abs(d2) @ np.abs(f),
        "c": np.abs(c), "cu": np.abs(d1) @ np.abs(c), "cuu": np.abs(d2) @ np.abs(c),
        "q": np.abs(q), "qu": np.abs(d1) @ np.abs(q), "quu": np.abs(d2) @ np.abs(q),
        "c_signed": c,
    }
    return {"grid": grid, "fields": fields, "absolute": absolute}


def gn_double_residual(preset: Any, x_h: float, degree: int, f, c, q) -> Dict[str, np.ndarray]:
    """Reconstruct the production solver residual, including boundary rows."""

    data = gn_fields(degree, f, c, q)
    terms = gn_raw_terms(preset, x_h, data["grid"].nodes, data["fields"])
    residual = {name: gn_normalized(items) for name, items in terms.items()}
    residual["f"] = residual["f"].copy()
    residual["scalar"] = residual["scalar"].copy()
    residual["f"][0] = f[0] - 1.0
    residual["f"][-1] = f[-1]
    residual["scalar"][0] = q[0] - 1.0
    return residual


def gn_rounding_bound(preset: Any, x_h: float, degree: int, f, c, q) -> Dict[str, np.ndarray]:
    """A-priori bound on rounding in evaluating each normalized residual."""

    data = gn_fields(degree, f, c, q)
    u = data["grid"].nodes
    signed = gn_raw_terms(preset, x_h, u, data["fields"])
    magnitude = gn_raw_terms(preset, x_h, u, data["absolute"], absolute=True)
    count = int(degree) + 1 + 16
    bound = {}
    for name in signed:
        denominator = 1.0 + sum(np.abs(term) for term in signed[name])
        bound[name] = rounding_gamma(count) * sum(magnitude[name]) / denominator
    for name, index in (("f", 0), ("f", -1), ("scalar", 0)):
        bound[name] = bound[name].copy()
        bound[name][index] = EPS
    return bound


def gn_high_precision_residual(
    preset: Any, x_h: float, degree: int, f, c, q, digits: int = HIGH_PRECISION_DIGITS
) -> Dict[str, np.ndarray]:
    """Evaluate the solver residual of the stored double solution in Decimal.

    The double derivative matrices and inputs are converted exactly, so the
    result is the residual of the stored discrete problem without evaluation
    rounding (to ``digits`` digits).
    """

    grid = chebyshev_lobatto_grid(int(degree), 0.0, 1.0)
    with localcontext() as context:
        context.prec = int(digits)
        D = Decimal

        def vector(values):
            return [D(float(value)) for value in values]

        def matvec(matrix, values):
            return [sum(D(float(a)) * b for a, b in zip(row, values)) for row in matrix]

        u = vector(grid.nodes)
        fv, cv, qv = vector(f), vector(c), vector(q)
        fu, fuu = matvec(grid.first_derivative, fv), matvec(grid.second_derivative, fv)
        cu, cuu = matvec(grid.first_derivative, cv), matvec(grid.second_derivative, cv)
        qu, quu = matvec(grid.first_derivative, qv), matvec(grid.second_derivative, qv)
        p = D(float(preset.uv_power))
        xh = D(float(x_h))
        g = D(float(preset.gamma))
        b = D(float(preset.b))
        one, two, three, four, six, twelve = (D(v) for v in (1, 2, 3, 4, 6, 12))

        def sinh(value):
            return (value.exp() - (-value).exp()) / two

        rows: Dict[str, List[Decimal]] = {"f": [], "warp": [], "scalar": []}
        for i, ui in enumerate(u):
            a_x = two * ui * cv[i] + ui * ui * cu[i]
            s_x = qv[i] + ui * qu[i]
            f_terms = [ui * fuu[i], (three * xh * xh * ui * a_x + one - four / p) * fu[i]]
            w_terms = [
                two * cv[i] + four * ui * cu[i] + ui * ui * cuu[i],
                (one + one / p) * (two * cv[i] + ui * cu[i]),
                -xh * xh * a_x * a_x,
                s_x * s_x / six,
            ]
            phi = xh * ui * qv[i]
            a_e = xh * xh * ui * ui * cv[i]
            v_prime = -twelve * g * sinh(g * phi) + two * b * phi
            third = D(0) if ui == 0 else -(two * a_e).exp() * v_prime / (p * p * xh * ui)
            s_terms = [
                ui * fv[i] * (two * qu[i] + ui * quu[i]),
                (three * xh * xh * ui * fv[i] * a_x + (one - four / p) * fv[i] + ui * fu[i]) * s_x,
                third,
            ]
            for name, terms in (("f", f_terms), ("warp", w_terms), ("scalar", s_terms)):
                rows[name].append(sum(terms) / (one + sum(abs(t) for t in terms)))
        rows["f"][0] = fv[0] - one
        rows["f"][-1] = fv[-1]
        rows["scalar"][0] = qv[0] - one
        return {name: np.array([float(value) for value in values]) for name, values in rows.items()}


def gn_case_record(profile: Any) -> Dict[str, Any]:
    from holoforge.benchmarks import gubser_nellore_ed as gn

    preset, x_h, degree = profile.preset, profile.x_h, profile.degree
    f, c, q = profile.blackening, profile.warp_factor, profile.scalar_factor
    double = gn_double_residual(preset, x_h, degree, f, c, q)
    stacked = np.concatenate([double["f"], double["warp"], double["scalar"]])
    production = float(profile.nonlinear.final_scaled_residual)
    reconstructed = float(np.max(np.abs(stacked)))
    high = gn_high_precision_residual(preset, x_h, degree, f, c, q)
    bound = gn_rounding_bound(preset, x_h, degree, f, c, q)
    names = ("f", "warp", "scalar")
    worst = max(
        ((name, int(np.argmax(np.abs(double[name])))) for name in names),
        key=lambda item: abs(double[item[0]][item[1]]),
    )
    evaluation_error = max(float(np.max(np.abs(double[n] - high[n]))) for n in names)
    ratio = max(
        float(np.max(np.abs(double[n]) / np.maximum(bound[n], EPS))) for n in names
    )
    diagnostics = gn.coupled_equation_diagnostics(profile)
    return {
        "preset": preset.identifier,
        "degree": int(degree),
        "x_h": float(x_h),
        "nonlinear": profile.nonlinear.to_dict(),
        "identity_check": {
            "production_final_residual": production,
            "reconstructed_final_residual": reconstructed,
            "exact_match": reconstructed == production,
        },
        "max_double_residual": reconstructed,
        "max_location": {
            "equation": worst[0],
            "node": worst[1],
            "u": float(chebyshev_lobatto_grid(int(degree), 0.0, 1.0).nodes[worst[1]]),
            "rounding_bound_there": float(bound[worst[0]][worst[1]]),
        },
        "max_high_precision_residual": max(float(np.max(np.abs(high[n]))) for n in names),
        "max_evaluation_error": evaluation_error,
        "max_rounding_bound": max(float(np.max(bound[n])) for n in names),
        "max_residual_to_bound_ratio": ratio,
        "oversampled_equations": diagnostics.to_dict(),
    }


def gn_identity_fixture() -> Dict[str, Any]:
    """Check the Decimal evaluator against double evaluation off-solution."""

    from holoforge.benchmarks import gubser_nellore_ed as gn

    degree = 24
    grid = chebyshev_lobatto_grid(degree, 0.0, 1.0)
    u = grid.nodes
    rng = np.random.default_rng(20260930)
    f = 1.0 - u**2 + 0.05 * rng.standard_normal(u.size)
    c = -0.02 + 0.05 * rng.standard_normal(u.size)
    q = 1.0 + 0.05 * rng.standard_normal(u.size)
    worst = 0.0
    for preset in (gn.QCD_LIKE, gn.COSH_CALIBRATION):
        double = gn_double_residual(preset, 0.8, degree, f, c, q)
        high = gn_high_precision_residual(preset, 0.8, degree, f, c, q)
        production = gn._scaled_coupled_equations(
            preset, 0.8, u, f, grid.first_derivative @ f, grid.second_derivative @ f,
            c, grid.first_derivative @ c, grid.second_derivative @ c,
            q, grid.first_derivative @ q, grid.second_derivative @ q,
        )
        for index, name in enumerate(("f", "warp", "scalar")):
            interior = slice(1, -1)
            worst = max(
                worst,
                float(np.max(np.abs(double[name][interior] - production[index][interior]))),
                float(np.max(np.abs(double[name] - high[name]))),
            )
    return {"max_difference_off_solution": worst, "passed": worst <= 1.0e-12}


def gn_run(case_set: str, adverse: bool) -> Dict[str, Any]:
    from holoforge.benchmarks import gubser_nellore_ed as gn

    fixture = gn_identity_fixture()
    if not fixture["passed"]:
        return {"identity_fixture": fixture, "stopped": "identity fixture failed"}
    records = []
    worst_profiles = {}
    for identifier, spec in GN_CASES[case_set].items():
        preset = gn.get_preset(identifier)
        started = time.perf_counter()
        branch = gn.solve_coupled_branch(preset, gn_branch_grid(identifier), spec["degrees"])
        elapsed = time.perf_counter() - started
        profiles = [item for degree in branch.degrees for item in branch.profiles[degree]]
        worst = max(profiles, key=lambda item: item.nonlinear.final_scaled_residual)
        worst_profiles[identifier] = worst
        selected = []
        for case in spec["cases"]:
            if case == "worst":
                selected.append(worst)
            else:
                degree, x_h = case
                selected.append(
                    min(branch.profiles[degree], key=lambda item: abs(item.x_h - x_h))
                )
        for profile in selected:
            record = gn_case_record(profile)
            record["branch_seconds"] = elapsed
            records.append(record)
        records.append({
            "preset": identifier,
            "branch_summary": {
                "profiles": len(profiles),
                "worst": {"degree": worst.degree, "x_h": float(worst.x_h),
                          "final_residual": float(worst.nonlinear.final_scaled_residual)},
                "count_above_5e-10": sum(
                    item.nonlinear.final_scaled_residual > 5.0e-10 for item in profiles
                ),
                "polished": sum(item.nonlinear.polish_applied for item in profiles),
            },
        })
    result: Dict[str, Any] = {"identity_fixture": fixture, "records": records}
    if adverse:
        result["adverse"] = gn_adverse()
    return result


def gn_adverse() -> Dict[str, Any]:
    from holoforge.benchmarks import gubser_nellore_ed as gn

    controls: Dict[str, Any] = {}
    branch = gn.solve_coupled_branch(gn.QCD_LIKE, gn_branch_grid("qcd-like"), (80, 120, 150))
    base = min(branch.profiles[80], key=lambda item: abs(item.x_h - 1.04))

    def summarize(profile, preset=None):
        preset = profile.preset if preset is None else preset
        double = gn_double_residual(preset, profile.x_h, profile.degree,
                                    profile.blackening, profile.warp_factor, profile.scalar_factor)
        bound = gn_rounding_bound(preset, profile.x_h, profile.degree,
                                  profile.blackening, profile.warp_factor, profile.scalar_factor)
        checked = dataclasses.replace(profile, preset=preset)
        oversampled = gn.coupled_equation_diagnostics(checked).to_dict()
        return {
            "collocation_residual": max(float(np.max(np.abs(v))) for v in double.values()),
            "residual_to_bound_ratio": max(
                float(np.max(np.abs(double[n]) / np.maximum(bound[n], EPS))) for n in double
            ),
            "oversampled_equation_residual": oversampled["maximum_equation_residual"],
            "oversampled_boundary_residual": oversampled["maximum_boundary_residual"],
        }

    controls["reference"] = summarize(base)
    u = base.u
    # 1e-6 and 1e-8 are the frozen plan's controls. 1e-10 and 1e-11 are
    # supplementary (added after the first run and disclosed in the report)
    # to probe the band between the 1e-9 collocation and 1e-7 oversampled limits.
    for amplitude in (1.0e-6, 1.0e-8, 1.0e-10, 1.0e-11):
        bump = amplitude * np.exp(-(((u - 0.5) / 0.05) ** 2))
        label = f"bump-{amplitude:g}" + ("" if amplitude >= 1.0e-8 else "-supplementary")
        controls[label] = summarize(
            dataclasses.replace(base, blackening=base.blackening + bump)
        )
    violated = base.blackening.copy()
    violated[-1] = 1.0e-6
    controls["horizon-condition-1e-6"] = summarize(
        dataclasses.replace(base, blackening=violated)
    )
    controls["potential-b-times-1.01"] = summarize(
        base, preset=dataclasses.replace(gn.QCD_LIKE, b=1.01 * gn.QCD_LIKE.b)
    )
    try:
        coarse = gn.solve_coupled_profile(gn.QCD_LIKE, 1.04, 24)
        controls["degree-24"] = summarize(coarse)
        controls["degree-24"]["solver_success"] = coarse.nonlinear.success
    except (RuntimeError, ValueError) as exc:
        controls["degree-24"] = {"solve_error": type(exc).__name__}
    return controls


# ---------------------------------------------------------------------------
# HHH optical equation residual
# ---------------------------------------------------------------------------

OPTICAL_CASES = {
    "calibration": {
        "frequencies": ((60.0, 640), (50.0, 640), (70.0, 640), (58.0, 640),
                        (59.0, 640), (61.0, 640), (62.0, 640), (60.0, 512), (60.0, 384)),
    },
    "confirmation": {
        "frequencies": ((55.0, 640), (65.0, 640), (75.0, 640), (60.0, 576)),
    },
}


def optical_background():
    from holoforge.benchmarks import holographic_superconductor_optical as optical
    from holoforge.benchmarks.holographic_superconductor import verify_superconductor

    protected = verify_superconductor()
    conditioned = optical.solve_conditioned_background(
        critical_tc_over_sqrt_rho=protected.onset.tc_over_sqrt_rho
    )
    return conditioned.target


def optical_solve_with_capture(frequency: float, degree: int, background) -> Tuple[Any, Dict[str, Any]]:
    """Run the production solve, recording its residual-function inputs."""

    from holoforge.benchmarks import holographic_superconductor_optical as optical

    original = optical._independent_element_equation_residual
    captured: Dict[str, Any] = {}

    def spy(*args, **kwargs):
        captured["args"] = args
        return original(*args, **kwargs)

    with patch.object(optical, "_independent_element_equation_residual", spy):
        response = optical.solve_series_transferred_spectral_response(
            frequency,
            background.scalar_profile,
            scalar_response=background.scalar_response,
            horizon_scalar=background.horizon_scalar,
            degree=degree,
            series_order=4,
        )
    return response, captured


def optical_residual_profiles(
    nodes, regular, scalar_profile, frequency, degree, lower, upper,
    *, exponent_override=None, frequency_squared_scale: float = 1.0,
    first_index: int = 3,
) -> Dict[str, Any]:
    """Per-point A-form (production formula) and a-form residuals.

    ``first_index`` is the first check node included; production excludes
    three per endpoint. A smaller value is used only to report diagnostic
    values at excluded nodes, never for a production maximum.
    """

    from holoforge.benchmarks import holographic_superconductor_optical as optical
    from holoforge.numerics.interpolation import deterministic_barycentric_interpolator

    width = float(upper - lower)
    check = chebyshev_lobatto_grid(2 * int(degree), lower, upper)
    coordinate = check.nodes
    local_nodes = (np.asarray(nodes, dtype=float) - lower) / width
    local = (coordinate - lower) / width
    interpolator = deterministic_barycentric_interpolator(local_nodes, regular)
    a = np.asarray(interpolator(local), dtype=complex)
    a1 = np.asarray(interpolator.derivative(local, der=1), dtype=complex)
    a2 = np.asarray(interpolator.derivative(local, der=2), dtype=complex)
    scalar = np.asarray(scalar_profile(coordinate), dtype=float)
    selected = np.arange(int(first_index), check.size - 3)
    uu = coordinate[selected]
    one_minus = 1.0 - uu
    s = optical.ingoing_exponent(frequency) if exponent_override is None else exponent_override
    phase = np.exp(s * np.log(one_minus))
    field = phase * a[selected]
    field_first = phase * (a1[selected] - width * s * a[selected] / one_minus)
    field_second = phase * (
        a2[selected]
        - 2.0 * width * s * a1[selected] / one_minus
        + width**2 * s * (s - 1.0) * a[selected] / one_minus**2
    )
    blackening = 1.0 - uu**3
    blackening_prime = -3.0 * uu**2
    omega_squared = frequency_squared_scale * frequency**2
    potential = omega_squared / blackening**2 - 2.0 * scalar[selected] ** 2 / (uu**2 * blackening)
    terms_a_form = (
        field_second,
        width * blackening_prime / blackening * field_first,
        width**2 * potential * field,
    )
    # Same operation order as the production residual, so the maximum is
    # reproduced bit for bit.
    residual = terms_a_form[0] + terms_a_form[1] + terms_a_form[2]
    scale = (
        np.abs(field_second)
        + np.abs(width * blackening_prime / blackening * field_first)
        + width**2 * np.abs(potential) * np.abs(field)
        + width**2
    )
    normalized = np.abs(residual) / scale

    first_coefficient = blackening_prime / blackening - 2.0 * s / one_minus
    regular_potential = (
        s * (s - 1.0) / one_minus**2
        - s * blackening_prime / (one_minus * blackening)
        + potential
    )
    regular_terms = (a2[selected], width * first_coefficient * a1[selected],
                     width**2 * regular_potential * a[selected])
    regular_residual = sum(regular_terms)
    regular_scale = sum(np.abs(term) for term in regular_terms) + width**2
    regular_normalized = np.abs(regular_residual) / regular_scale
    index = int(np.argmax(normalized))
    return {
        "normalized": normalized,
        "regular_normalized": regular_normalized,
        "coordinates": uu,
        "maximum": float(normalized[index]),
        "maximum_coordinate": float(uu[index]),
        "maximum_index": index,
        "terms_at_maximum": [complex(term[index]) for term in terms_a_form],
        "scale_at_maximum": float(scale[index]),
        "field_abs_at_maximum": float(abs(field[index])),
        "regular_maximum": float(np.max(regular_normalized)),
        "regular_maximum_coordinate": float(uu[int(np.argmax(regular_normalized))]),
        "regular_at_production_maximum": float(regular_normalized[index]),
        "field_abs_max": float(np.max(np.abs(field))),
        # Per-node arrays on ``selected`` (O-B), plus the inputs they use.
        "selected": selected,
        "check_coordinate": coordinate,
        "check_local": local,
        "local_nodes": local_nodes,
        "width": width,
        "scalar": scalar[selected],
        "a": a[selected],
        "a1": a1[selected],
        "a2": a2[selected],
        "phase": phase,
        "residual": residual,
        "scale": scale,
        "regular_residual": regular_residual,
        "regular_scale": regular_scale,
    }


def optical_case_record(frequency: float, degree: int, background, *, draws: int = 8) -> Dict[str, Any]:
    response, captured = optical_solve_with_capture(frequency, degree, background)
    args = captured["args"]
    profile = optical_residual_profiles(*args)
    nodes, regular = args[0], args[1]
    rng = np.random.default_rng(20260930 + int(frequency * 10) + degree)
    changes = []
    for _ in range(draws):
        noise = 1.0 + EPS * (rng.standard_normal(regular.size) + 1j * rng.standard_normal(regular.size))
        perturbed = optical_residual_profiles(nodes, regular * noise, *args[2:])
        changes.append(abs(perturbed["maximum"] - profile["maximum"]))
    return {
        "omega_over_temperature": float(frequency),
        "degree": int(degree),
        "identity_check": {
            "production_equation_residual": float(response.equation_residual),
            "production_maximum_coordinate": float(response.bulk_element_residual.maximum_coordinate),
            "reconstructed_maximum": profile["maximum"],
            "exact_match": profile["maximum"] == float(response.equation_residual),
        },
        "maximum_coordinate": profile["maximum_coordinate"],
        "distance_to_horizon": 1.0 - profile["maximum_coordinate"],
        "terms_at_maximum_abs": [abs(term) for term in profile["terms_at_maximum"]],
        "scale_at_maximum": profile["scale_at_maximum"],
        "field_abs_at_maximum": profile["field_abs_at_maximum"],
        "field_abs_max": profile["field_abs_max"],
        "regular_form_maximum": profile["regular_maximum"],
        "regular_form_maximum_coordinate": profile["regular_maximum_coordinate"],
        "regular_form_at_production_maximum": profile["regular_at_production_maximum"],
        "eps_perturbation_max_change": float(max(changes)),
        "conductivity": [float(response.conductivity.real), float(response.conductivity.imag)],
        "condition_number": float(response.condition_number),
    }


def optical_run(case_set: str, adverse: bool) -> Dict[str, Any]:
    background = optical_background()
    records = [optical_case_record(freq, degree, background)
               for freq, degree in OPTICAL_CASES[case_set]["frequencies"]]
    result: Dict[str, Any] = {"records": records}
    if adverse:
        result["adverse"] = optical_adverse(background)
    return result


def optical_adverse(background) -> Dict[str, Any]:
    from holoforge.benchmarks import holographic_superconductor_optical as optical

    _, captured = optical_solve_with_capture(60.0, 640, background)
    args = captured["args"]
    nodes, regular, scalar_profile, frequency, degree, lower, upper = args
    reference = optical_residual_profiles(*args)
    controls: Dict[str, Any] = {
        "reference": {"a_form": reference["maximum"], "regular_form": reference["regular_maximum"]}
    }
    conjugate = np.conj(optical.ingoing_exponent(frequency))
    wrong = optical_residual_profiles(*args, exponent_override=conjugate)
    controls["conjugated-exponent"] = {"a_form": wrong["maximum"], "regular_form": wrong["regular_maximum"]}
    scaled = optical_residual_profiles(*args, frequency_squared_scale=1.01)
    controls["frequency-squared-times-1.01"] = {"a_form": scaled["maximum"], "regular_form": scaled["regular_maximum"]}
    local = (np.asarray(nodes) - lower) / (upper - lower)
    # Correction 1 (recorded in the report): a relative bump centred at mid
    # element was invisible because |a| there is about 1e-16 on this
    # background. Perturb where the field is O(1), and separately add an
    # absolute bump in the bulk.
    relative = 1.0 + 1.0e-6 * np.exp(-(((local - 0.02) / 0.01) ** 2))
    perturbed = optical_residual_profiles(nodes, regular * relative, *args[2:])
    controls["relative-perturbation-1e-6-near-uv"] = {
        "a_form": perturbed["maximum"], "regular_form": perturbed["regular_maximum"],
    }
    absolute = 1.0e-6 * np.exp(-(((local - 0.5) / 0.05) ** 2))
    perturbed = optical_residual_profiles(nodes, regular + absolute, *args[2:])
    controls["absolute-perturbation-1e-6-bulk"] = {
        "a_form": perturbed["maximum"], "regular_form": perturbed["regular_maximum"],
    }
    controls["field_abs_mid_element"] = float(
        np.max(np.abs(regular[np.abs(local - 0.5) < 0.05]))
    )
    coarse_response, coarse_capture = optical_solve_with_capture(60.0, 192, background)
    coarse = optical_residual_profiles(*coarse_capture["args"])
    controls["degree-192"] = {
        "a_form": coarse["maximum"], "regular_form": coarse["regular_maximum"],
        "production_equation_residual": float(coarse_response.equation_residual),
    }
    return controls


# ---------------------------------------------------------------------------
# Optical single-node diagnosis (O-B)
# ---------------------------------------------------------------------------
#
# Implements ``docs/numerics/optical-ob-diagnosis-plan.md``. Complex Decimal
# numbers are (real, imaginary) pairs; every Decimal operation follows the
# active context, set by the caller.

OPTICAL_OB_PLAN = Path("docs/numerics/optical-ob-diagnosis-plan.md")
OPTICAL_OB_CASES = ((50.0, 640), (58.0, 640), (59.0, 640), (60.0, 640),
                    (61.0, 640), (62.0, 640), (70.0, 640), (60.0, 512))
OPTICAL_OB_NEIGHBOURS = 2
OPTICAL_OB_LOCAL_NODES = 12
OPTICAL_OB_CROSS_CHECK_DIGITS = 70
# Section 4 of the plan. "Accounts for" is taken to mean that the residual
# change implied by the derivative differences alone is within a factor of
# two of the double-minus-50-digit residual difference.
OPTICAL_OB_ARTIFACT_FACTOR = 10.0
OPTICAL_OB_DEFECT_FACTOR = 2.0


def _dc(value: Any) -> Tuple[Decimal, Decimal]:
    """Convert a double (complex) value to an exact Decimal pair."""

    value = complex(value)
    return Decimal(value.real), Decimal(value.imag)


def _cadd(a, b):
    return a[0] + b[0], a[1] + b[1]


def _csub(a, b):
    return a[0] - b[0], a[1] - b[1]


def _cmul(a, b):
    return a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]


def _cscale(a, factor):
    return a[0] * factor, a[1] * factor


def _cabs(a) -> Decimal:
    return (a[0] * a[0] + a[1] * a[1]).sqrt()


def _cfloat(a) -> complex:
    return complex(float(a[0]), float(a[1]))


def decimal_barycentric_weights(nodes: Sequence[Decimal]) -> List[Decimal]:
    """Return ``w_j = 1 / prod_{k != j} (x_j - x_k)`` for the given nodes."""

    weights = []
    for j, node in enumerate(nodes):
        product = Decimal(1)
        for k, other in enumerate(nodes):
            if k != j:
                product *= node - other
        weights.append(1 / product)
    return weights


def _decimal_nodal_derivatives(nodes, weights, values, index):
    """Value and first two derivatives at node ``index`` (Berrut-Trefethen)."""

    node, weight, value = nodes[index], weights[index], values[index]
    entries = []
    diagonal = Decimal(0)
    for j, other in enumerate(nodes):
        if j != index:
            entry = (weights[j] / weight) / (node - other)
            entries.append((j, entry))
            diagonal -= entry
    first = (Decimal(0), Decimal(0))
    second = (Decimal(0), Decimal(0))
    for j, entry in entries:
        difference = _csub(values[j], value)
        first = _cadd(first, _cscale(difference, entry))
        second_entry = 2 * entry * (diagonal - 1 / (node - nodes[j]))
        second = _cadd(second, _cscale(difference, second_entry))
    return value, first, second


def decimal_interpolant_derivatives(nodes, weights, values, point):
    """Return ``p, p', p''`` at ``point`` for the polynomial through the data.

    Uses the second-kind barycentric formula with
    ``p' = -sum w_j (f_j - p)/(x - x_j)^2 / D`` and
    ``p'' = 2 sum w_j [p'/(x - x_j)^2 + (f_j - p)/(x - x_j)^3] / D``,
    ``D = sum w_j/(x - x_j)``; at an exact node, the differentiation-matrix
    row is used instead.
    """

    for index, node in enumerate(nodes):
        if node == point:
            return _decimal_nodal_derivatives(nodes, weights, values, index)
    differences = [point - node for node in nodes]
    denominator = Decimal(0)
    numerator = (Decimal(0), Decimal(0))
    for weight, difference, value in zip(weights, differences, values):
        factor = weight / difference
        denominator += factor
        numerator = _cadd(numerator, _cscale(value, factor))
    value_at = _cscale(numerator, 1 / denominator)
    first = (Decimal(0), Decimal(0))
    for weight, difference, value in zip(weights, differences, values):
        first = _cadd(first, _cscale(_csub(value, value_at), weight / (difference * difference)))
    first = _cscale(first, -1 / denominator)
    second = (Decimal(0), Decimal(0))
    for weight, difference, value in zip(weights, differences, values):
        squared = difference * difference
        term = _cadd(
            _cscale(first, 1 / squared),
            _cscale(_csub(value, value_at), 1 / (squared * difference)),
        )
        second = _cadd(second, _cscale(term, weight))
    second = _cscale(second, 2 / denominator)
    return value_at, first, second


def decimal_regular_residual(u, width, frequency, scalar, a, a1, a2) -> Dict[str, Any]:
    """Regular-factor residual ``R_a`` and the A-form scale at one node.

    ``frequency`` is the dimensionless omega. The A-form magnitudes use
    ``|(1-u)^s| = 1``, which holds for real frequency.
    """

    one = Decimal(1)
    one_minus = one - u
    blackening = one - u ** 3
    blackening_prime = -3 * u * u
    third = frequency / 3
    exponent = (Decimal(0), -third)
    exponent_product = _cmul(exponent, (Decimal(-1), -third))
    potential = (frequency * frequency / (blackening * blackening)
                 - 2 * scalar * scalar / (u * u * blackening))
    first_coefficient = _cadd((blackening_prime / blackening, Decimal(0)),
                              _cscale(exponent, Decimal(-2) / one_minus))
    regular_potential = _cadd(
        _csub(_cscale(exponent_product, 1 / (one_minus * one_minus)),
              _cscale(exponent, blackening_prime / (one_minus * blackening))),
        (potential, Decimal(0)),
    )
    terms = (
        a2,
        _cscale(_cmul(first_coefficient, a1), width),
        _cscale(_cmul(regular_potential, a), width * width),
    )
    residual = _cadd(_cadd(terms[0], terms[1]), terms[2])
    field_first = _csub(a1, _cscale(_cmul(exponent, a), width / one_minus))
    field_second = _cadd(
        _csub(a2, _cscale(_cmul(exponent, a1), 2 * width / one_minus)),
        _cscale(_cmul(exponent_product, a), width * width / (one_minus * one_minus)),
    )
    scale = (_cabs(field_second)
             + abs(width * blackening_prime / blackening) * _cabs(field_first)
             + width * width * abs(potential) * _cabs(a)
             + width * width)
    return {
        "residual": residual,
        "terms": terms,
        "scale": scale,
        "first_coefficient": first_coefficient,
        "regular_potential": regular_potential,
    }


def _decimal_node_evaluation(profile, regular, frequency, check_index, digits, weight_cache):
    """50-digit (or ``digits``) interpolant and residual at one check node."""

    with localcontext() as context:
        context.prec = digits
        key = (digits, profile["local_nodes"].tobytes())
        if key not in weight_cache:
            nodes = [Decimal(float(x)) for x in profile["local_nodes"]]
            weight_cache[key] = (nodes, decimal_barycentric_weights(nodes))
        nodes, weights = weight_cache[key]
        values = [_dc(value) for value in regular]
        point = Decimal(float(profile["check_local"][check_index]))
        a, a1, a2 = decimal_interpolant_derivatives(nodes, weights, values, point)
        position = check_index - int(profile["selected"][0])
        evaluation = decimal_regular_residual(
            Decimal(float(profile["check_coordinate"][check_index])),
            Decimal(float(profile["width"])),
            Decimal(float(frequency)),
            Decimal(float(profile["scalar"][position])),
            a, a1, a2,
        )
        evaluation.update({"a": a, "a1": a1, "a2": a2})
        return evaluation


def optical_ob_interpretation(double_abs: float, high_abs: float, residual_difference: float,
                              derivative_part: float) -> str:
    """Apply the plan's prospective interpretation rules (Section 4).

    Every magnitude must be a finite, non-negative real number; otherwise
    ``ValueError`` is raised. When both residuals are exactly zero there is
    no defect to classify, and ``"zero-residual"`` is returned.
    """

    for magnitude in (double_abs, high_abs, residual_difference, derivative_part):
        if (isinstance(magnitude, (bool, np.bool_))
                or not isinstance(magnitude, (int, float, np.integer, np.floating))
                or not math.isfinite(float(magnitude)) or float(magnitude) < 0.0):
            raise ValueError(f"invalid residual magnitude {magnitude!r}")
    if double_abs == 0.0 and high_abs == 0.0:
        return "zero-residual"
    accounts = (residual_difference > 0.0
                and 1.0 / OPTICAL_OB_DEFECT_FACTOR
                <= derivative_part / residual_difference
                <= OPTICAL_OB_DEFECT_FACTOR)
    if high_abs * OPTICAL_OB_ARTIFACT_FACTOR <= double_abs and accounts:
        return "evaluation-artifact"
    if double_abs / OPTICAL_OB_DEFECT_FACTOR <= high_abs <= OPTICAL_OB_DEFECT_FACTOR * double_abs:
        return "polynomial-defect"
    return "unresolved"


def optical_ob_node(profile, regular, frequency, check_index, weight_cache) -> Dict[str, Any]:
    """Measurement 2 at one check node: double versus 50-digit evaluation."""

    position = check_index - int(profile["selected"][0])
    double = {
        "a": complex(profile["a"][position]),
        "a1": complex(profile["a1"][position]),
        "a2": complex(profile["a2"][position]),
    }
    double_residual = complex(profile["regular_residual"][position])
    high = _decimal_node_evaluation(profile, regular, frequency, check_index,
                                    HIGH_PRECISION_DIGITS, weight_cache)
    with localcontext() as context:
        context.prec = HIGH_PRECISION_DIGITS
        differences = {name: _csub(_dc(double[name]), high[name]) for name in ("a", "a1", "a2")}
        width = Decimal(float(profile["width"]))
        derivative_part = _cadd(
            _cadd(differences["a2"],
                  _cscale(_cmul(high["first_coefficient"], differences["a1"]), width)),
            _cscale(_cmul(high["regular_potential"], differences["a"]), width * width),
        )
        residual_difference = _cabs(_csub(_dc(double_residual), high["residual"]))
        high_abs = _cabs(high["residual"])
        record = {
            "check_index": int(check_index),
            "coordinate": float(profile["check_coordinate"][check_index]),
            "local_coordinate": float(profile["check_local"][check_index]),
            "double": {name: double[name] for name in double},
            "high_precision": {name: _cfloat(high[name]) for name in ("a", "a1", "a2")},
            "relative_differences": {
                name: float(_cabs(differences[name]) / _cabs(high[name])) for name in differences
            },
            "double_regular_residual_abs": abs(double_residual),
            "double_a_form_numerator_abs": float(abs(profile["residual"][position])),
            "double_a_form_normalized": float(profile["normalized"][position]),
            "high_precision_regular_residual": _cfloat(high["residual"]),
            "high_precision_regular_residual_abs": float(high_abs),
            "high_precision_terms_abs": [float(_cabs(term)) for term in high["terms"]],
            "high_precision_a_form_scale": float(high["scale"]),
            "high_precision_a_form_normalized": float(high_abs / high["scale"]),
            "residual_difference_abs": float(residual_difference),
            "derivative_difference_residual_abs": float(_cabs(derivative_part)),
        }
    return record


def _nearest_collocation(local_nodes: np.ndarray, point: float) -> Dict[str, Any]:
    distances = np.abs(local_nodes - point)
    index = int(np.argmin(distances))
    lower = local_nodes[max(index - 1, 0)]
    upper = local_nodes[min(index + 1, local_nodes.size - 1)]
    spacing = float(max(upper - lower, 0.0) / 2.0)
    return {
        "collocation_index": index,
        "local_distance": float(distances[index]),
        "distance_over_local_spacing": float(distances[index] / spacing) if spacing > 0 else None,
    }


def optical_ob_case_record(frequency: float, degree: int, background, weight_cache,
                           *, draws: int = 8) -> Dict[str, Any]:
    response, captured = optical_solve_with_capture(frequency, degree, background)
    args = captured["args"]
    nodes, regular, dimensionless = args[0], args[1], args[3]
    profile = optical_residual_profiles(*args)
    wide = optical_residual_profiles(*args, first_index=1)
    spike_position = profile["maximum_index"]
    spike = int(profile["selected"][spike_position])

    # Measurement 1: raw numerators, identity and a common denominator.
    residual = profile["residual"]
    regular_residual = profile["regular_residual"]
    scale = profile["scale"]
    # The plan's relative defect is large wherever |R_A| is itself at
    # rounding level, so the defect under the common denominator is also kept.
    identity_numerator = np.abs(residual - profile["phase"] * regular_residual)
    identity_defect = identity_numerator / np.abs(residual)
    identity_common = identity_numerator / scale
    common_a_form = np.abs(residual) / scale
    common_regular = np.abs(regular_residual) / scale
    measurement_1 = {
        "maximum_identity_defect": float(np.max(identity_defect)),
        "maximum_identity_defect_check_index": int(profile["selected"][int(np.argmax(identity_defect))]),
        "maximum_identity_defect_common_denominator": float(np.max(identity_common)),
        "common_denominator_maximum": {
            "a_form": float(np.max(common_a_form)),
            "a_form_check_index": int(profile["selected"][int(np.argmax(common_a_form))]),
            "regular_form": float(np.max(common_regular)),
            "regular_form_check_index": int(profile["selected"][int(np.argmax(common_regular))]),
        },
        "at_spike": {
            "check_index": spike,
            "a_form_numerator": complex(residual[spike_position]),
            "regular_numerator": complex(regular_residual[spike_position]),
            "a_form_numerator_abs": float(abs(residual[spike_position])),
            "regular_numerator_abs": float(abs(regular_residual[spike_position])),
            "a_form_scale": float(scale[spike_position]),
            "regular_scale": float(profile["regular_scale"][spike_position]),
            "identity_defect": float(identity_defect[spike_position]),
            "a_form_common": float(common_a_form[spike_position]),
            "regular_form_common": float(common_regular[spike_position]),
            "regular_form_own_denominator": float(profile["regular_normalized"][spike_position]),
        },
    }

    # Measurement 2: 50-digit polynomial at the spike and its neighbours.
    neighbours = range(max(spike - OPTICAL_OB_NEIGHBOURS, 1), spike + OPTICAL_OB_NEIGHBOURS + 1)
    measurement_2 = [optical_ob_node(wide, regular, dimensionless, index, weight_cache)
                     for index in neighbours]
    at_spike = next(item for item in measurement_2 if item["check_index"] == spike)
    cross = _decimal_node_evaluation(wide, regular, dimensionless, spike,
                                     OPTICAL_OB_CROSS_CHECK_DIGITS, weight_cache)
    with localcontext() as context:
        context.prec = OPTICAL_OB_CROSS_CHECK_DIGITS
        base = _decimal_node_evaluation(wide, regular, dimensionless, spike,
                                        HIGH_PRECISION_DIGITS, weight_cache)
        precision_check = max(
            float(_cabs(_csub(base[name], cross[name])) / _cabs(cross[name]))
            for name in ("a", "a1", "a2", "residual")
        )
    double_abs = at_spike["double_regular_residual_abs"]
    rejected = None
    try:
        interpretation = optical_ob_interpretation(
            double_abs,
            at_spike["high_precision_regular_residual_abs"],
            at_spike["residual_difference_abs"],
            at_spike["derivative_difference_residual_abs"],
        )
    except ValueError as error:
        interpretation, rejected = None, f"interpretation rejected: {error}"

    # Measurement 3: input sensitivity (eps perturbations, as in Batch 2a).
    rng = np.random.default_rng(20260930 + int(frequency * 10) + degree)
    maximum_changes, spike_changes = [], []
    for _ in range(draws):
        noise = 1.0 + EPS * (rng.standard_normal(regular.size) + 1j * rng.standard_normal(regular.size))
        perturbed = optical_residual_profiles(nodes, regular * noise, *args[2:])
        maximum_changes.append(abs(perturbed["maximum"] - profile["maximum"]))
        spike_changes.append(abs(perturbed["residual"][spike_position] - residual[spike_position]))
    measurement_3 = {
        "eps_perturbation_max_change": float(max(maximum_changes)),
        "eps_perturbation_spike_numerator_change": float(max(spike_changes)),
        "evaluation_error_spike_numerator": at_spike["residual_difference_abs"],
        "draws": int(draws),
    }

    # Measurement 4: local structure at the first checked nodes.
    measurement_4 = []
    for position in range(OPTICAL_OB_LOCAL_NODES):
        check_index = int(profile["selected"][position])
        entry = {
            "check_index": check_index,
            "coordinate": float(profile["check_coordinate"][check_index]),
            "a_form_normalized": float(profile["normalized"][position]),
            "a_form_numerator_abs": float(abs(residual[position])),
            "a_form_scale": float(scale[position]),
        }
        entry.update(_nearest_collocation(profile["local_nodes"],
                                          float(profile["check_local"][check_index])))
        measurement_4.append(entry)

    return {
        "omega_over_temperature": float(frequency),
        "degree": int(degree),
        "dimensionless_omega": float(dimensionless),
        "identity_check": {
            "production_equation_residual": float(response.equation_residual),
            "reconstructed_maximum": profile["maximum"],
            "exact_match": profile["maximum"] == float(response.equation_residual),
        },
        "spike_check_index": spike,
        "spike_coordinate": profile["maximum_coordinate"],
        "measurement_1": measurement_1,
        "measurement_2": measurement_2,
        "precision_cross_check": {
            "digits": [HIGH_PRECISION_DIGITS, OPTICAL_OB_CROSS_CHECK_DIGITS],
            "max_relative_difference_at_spike": precision_check,
        },
        "measurement_3": measurement_3,
        "measurement_4": measurement_4,
        "interpretation": interpretation,
        "condition_number": float(response.condition_number),
        **({"stopped": rejected} if rejected else {}),
    }


def optical_ob_identity_fixture() -> Dict[str, Any]:
    """Check the 50-digit evaluator before any production case is examined.

    (1) The plan's check: reproduce the double interpolant and derivatives to
    ``1e-10`` relative at a well-separated point. (2) Exact reproduction, to
    ``1e-30`` relative, of a known polynomial on degree-640 nodes near the
    UV end, off-node and at a node.
    """

    from holoforge.numerics.interpolation import deterministic_barycentric_interpolator

    checks: Dict[str, Any] = {}
    grid = chebyshev_lobatto_grid(16, 0.0, 1.0).nodes
    values = np.exp(2.0 * grid) + 1j * np.cos(3.0 * grid)
    point = 0.5 * (grid[7] + grid[8])
    interpolator = deterministic_barycentric_interpolator(grid, values)
    double = [complex(interpolator(point)),
              complex(interpolator.derivative(point, der=1)),
              complex(interpolator.derivative(point, der=2))]
    with localcontext() as context:
        context.prec = HIGH_PRECISION_DIGITS
        nodes = [Decimal(float(x)) for x in grid]
        high = decimal_interpolant_derivatives(
            nodes, decimal_barycentric_weights(nodes), [_dc(v) for v in values],
            Decimal(float(point)),
        )
    difference = max(abs(_cfloat(h) - d) / abs(d) for h, d in zip(high, double))
    checks["double_agreement_well_separated"] = {
        "max_relative_difference": float(difference), "limit": 1.0e-10,
        "passed": bool(difference <= 1.0e-10),
    }

    grid = chebyshev_lobatto_grid(640, 0.0, 1.0).nodes
    check = chebyshev_lobatto_grid(1280, 0.0, 1.0).nodes
    with localcontext() as context:
        context.prec = HIGH_PRECISION_DIGITS
        coefficients = [(Decimal(c), Decimal(d)) for c, d in
                        ((1, 0), (2, -1), (-3, 0.5), (0.25, 4), (5, 0), (0, -2), (1.5, 1))]

        def polynomial(x):
            # Powers by repeated multiplication: Decimal leaves 0 ** 0 undefined.
            powers = [Decimal(1)]
            for _ in coefficients[1:]:
                powers.append(powers[-1] * x)
            value = first = second = (Decimal(0), Decimal(0))
            for power, coefficient in enumerate(coefficients):
                value = _cadd(value, _cscale(coefficient, powers[power]))
                if power >= 1:
                    first = _cadd(first, _cscale(coefficient, power * powers[power - 1]))
                if power >= 2:
                    second = _cadd(second, _cscale(coefficient, power * (power - 1) * powers[power - 2]))
            return value, first, second

        nodes = [Decimal(float(x)) for x in grid]
        weights = decimal_barycentric_weights(nodes)
        values = [polynomial(x)[0] for x in nodes]
        worst = Decimal(0)
        for point in (Decimal(float(check[3])), nodes[1], Decimal(float(check[641]))):
            exact = polynomial(point)
            evaluated = decimal_interpolant_derivatives(nodes, weights, values, point)
            for got, want in zip(evaluated, exact):
                worst = max(worst, _cabs(_csub(got, want)) / _cabs(want))
    checks["exact_polynomial_degree_640"] = {
        "max_relative_difference": float(worst), "limit": 1.0e-30,
        "passed": bool(worst <= Decimal("1e-30")),
    }
    return {"checks": checks, "passed": all(item["passed"] for item in checks.values())}


def optical_ob_run(case_set: str, adverse: bool) -> Dict[str, Any]:
    if case_set != "calibration":
        return {"stopped": "O-B uses only previously examined cases; reserved cases stay unused"}
    if adverse:
        return {"stopped": "the O-B plan defines no adverse controls"}
    fixture = optical_ob_identity_fixture()
    if not fixture["passed"]:
        return {"identity_fixture": fixture, "stopped": "identity fixture failed"}
    background = optical_background()
    weight_cache: Dict[Any, Any] = {}
    records = [optical_ob_case_record(frequency, degree, background, weight_cache)
               for frequency, degree in OPTICAL_OB_CASES]
    return {
        "identity_fixture": fixture,
        "interpretation_rule": {
            "evaluation_artifact": "50-digit |R_a| <= double |R_a| / 10 and derivative part "
                                   "within a factor 2 of the residual difference",
            "polynomial_defect": "50-digit |R_a| within a factor 2 of double |R_a|",
            "zero_residual": "both residuals exactly zero; no defect to classify",
            "otherwise": "unresolved",
        },
        "records": records,
    }


# ---------------------------------------------------------------------------
# Optical discrete-system diagnosis (O-C)
# ---------------------------------------------------------------------------
#
# Implements ``docs/numerics/optical-oc-diagnosis-plan.md``. Complex vectors
# of Decimals are (real list, imaginary list) pairs; single complex Decimals
# are (real, imaginary) tuples, as in O-B.

OPTICAL_OC_PLAN = Path("docs/numerics/optical-oc-diagnosis-plan.md")
OPTICAL_OC_CASES = {
    "B1": ((60.0, 640), (59.0, 640), (50.0, 640), (70.0, 640), (60.0, 512)),
    "B3": ((60.0, 640), (59.0, 640), (60.0, 512)),
}
OPTICAL_OC_CROSS_CHECK = ("B1", 60.0, 640)
OPTICAL_OC_CROSS_CHECK_DIGITS = 70
OPTICAL_OC_FIXTURE_CASE = (40.0, 64)
OPTICAL_OC_CHAIN = ("exact", "D", "D2", "coef", "asm", "eq")
OPTICAL_OC_STEPS = ("D-construction", "D@D-product", "coefficients", "assembly", "equilibration")
OPTICAL_OC_MAX_ITERATIONS = 10
# Correction 1 to F4 (reported): with a single update the "last change" is
# the whole correction, not a bound on the remaining error, so at least two
# updates are made.
OPTICAL_OC_MIN_ITERATIONS = 2
OPTICAL_OC_BACKWARD_LIMIT = 1.0e-28
OPTICAL_OC_UNCERTAINTY_LIMIT = 0.01
OPTICAL_OC_HP_FLOOR = 1.0e-40
OPTICAL_OC_ARTIFACT_DIR = Path("output/optical-oc-artifacts")
OPTICAL_OC_SPIKE_INDEX = 3
OPTICAL_OC_CONTEXT_INDICES = (1, 2, 3, 4, 5)


def _cv_from_array(values) -> Tuple[List[Decimal], List[Decimal]]:
    array = np.asarray(values, dtype=complex)
    return [Decimal(float(v)) for v in array.real], [Decimal(float(v)) for v in array.imag]


def _cv_to_array(vector) -> np.ndarray:
    return np.array([complex(float(r), float(i)) for r, i in zip(*vector)])


def _cv_pairs(vector, count=None):
    re, im = vector
    count = len(re) if count is None else count
    return [(re[k], im[k]) for k in range(count)]


def _dot(row, vector) -> Decimal:
    return sum(map(Decimal.__mul__, row, vector), Decimal(0))


def _real_matvec(matrix, vector) -> Tuple[List[Decimal], List[Decimal]]:
    """Real Decimal matrix (list of rows) times a complex Decimal vector."""

    re, im = vector
    return [_dot(row, re) for row in matrix], [_dot(row, im) for row in matrix]


def _complex_matvec(matrix_re, matrix_im, vector):
    xr, xi = vector
    rr = [_dot(a, xr) - _dot(b, xi) for a, b in zip(matrix_re, matrix_im)]
    ri = [_dot(a, xi) + _dot(b, xr) for a, b in zip(matrix_re, matrix_im)]
    return rr, ri


def _decimal_matrix(array) -> List[List[Decimal]]:
    return [[Decimal(float(v)) for v in row] for row in np.asarray(array, dtype=float)]


def decimal_differentiation_matrices(nodes: Sequence[Decimal]):
    """Exact first and second differentiation matrices of the interpolant.

    ``D1_ij = (w_j/w_i)/(x_i - x_j)`` and
    ``D2_ij = 2 D1_ij (D1_ii - 1/(x_i - x_j))`` off the diagonal, with each
    diagonal the negative row sum; evaluated in the active Decimal context.
    """

    weights = decimal_barycentric_weights(nodes)
    size = len(nodes)
    first, second = [], []
    for i in range(size):
        inverses = [None] * size
        row1 = [Decimal(0)] * size
        diagonal = Decimal(0)
        for j in range(size):
            if j != i:
                inverse = 1 / (nodes[i] - nodes[j])
                inverses[j] = inverse
                entry = weights[j] / weights[i] * inverse
                row1[j] = entry
                diagonal -= entry
        row1[i] = diagonal
        row2 = [Decimal(0)] * size
        second_diagonal = Decimal(0)
        for j in range(size):
            if j != i:
                entry = 2 * row1[j] * (diagonal - inverses[j])
                row2[j] = entry
                second_diagonal -= entry
        row2[i] = second_diagonal
        first.append(row1)
        second.append(row2)
    return first, second, weights


def decimal_equation_coefficients(u, frequency, scalar):
    """50-digit ``c1`` and ``V`` of the regular-factor equation at one node."""

    one = Decimal(1)
    one_minus = one - u
    blackening = one - u ** 3
    blackening_prime = -3 * u * u
    third = frequency / 3
    exponent = (Decimal(0), -third)
    exponent_product = _cmul(exponent, (Decimal(-1), -third))
    potential = (frequency * frequency / (blackening * blackening)
                 - 2 * scalar * scalar / (u * u * blackening))
    first = _cadd((blackening_prime / blackening, Decimal(0)),
                  _cscale(exponent, Decimal(-2) / one_minus))
    regular = _cadd(
        _csub(_cscale(exponent_product, 1 / (one_minus * one_minus)),
              _cscale(exponent, blackening_prime / (one_minus * blackening))),
        (potential, Decimal(0)),
    )
    return first, regular


def _double_coefficient_scales(u, frequency, scalar):
    """Term-magnitude sums ``C1`` and ``W`` of the F3 coefficient bound."""

    u = np.asarray(u, dtype=float)
    blackening = 1.0 - u ** 3
    prime = -3.0 * u ** 2
    one_minus = 1.0 - u
    s = abs(frequency) / 3.0
    first = np.abs(prime / blackening) + 2.0 * s / one_minus
    potential = (s * math.hypot(1.0, s) / one_minus ** 2 + s * np.abs(prime) / (one_minus * blackening)
                 + frequency ** 2 / blackening ** 2 + 2.0 * np.asarray(scalar) ** 2 / (u ** 2 * blackening))
    return first, potential


def optical_oc_capture(frequency_over_temperature: float, degree: int, background):
    """Run the production solve unmodified, capturing its inputs and solve."""

    from holoforge.benchmarks import holographic_superconductor_optical as optical

    captured: Dict[str, Any] = {"solves": []}
    original_residual = optical._independent_element_equation_residual
    original_solve = optical.solve

    def residual_spy(*args, **kwargs):
        captured["residual_args"] = args
        return original_residual(*args, **kwargs)

    def solve_spy(a, b, **kwargs):
        result = original_solve(a, b, **kwargs)
        captured["solves"].append((np.array(a, copy=True), np.array(b, copy=True),
                                   np.array(result, copy=True)))
        return result

    with patch.object(optical, "_independent_element_equation_residual", residual_spy), \
            patch.object(optical, "solve", solve_spy):
        response = optical.solve_series_transferred_spectral_response(
            frequency_over_temperature,
            background.scalar_profile,
            scalar_response=background.scalar_response,
            horizon_scalar=background.horizon_scalar,
            degree=degree,
            series_order=4,
        )
    return response, captured


def optical_oc_reconstruct(frequency: float, degree: int, background) -> Dict[str, Any]:
    """Rebuild the production operator in production's operation order."""

    from holoforge.benchmarks import holographic_superconductor_optical as optical

    transfer = optical.uv_series_transfer_coefficients(
        frequency, float(background.scalar_response), optical.ENDPOINT_SPLIT_COORDINATE,
        series_order=4,
    )
    grid = chebyshev_lobatto_grid(degree, transfer.coordinate, 1.0)
    scalar = np.asarray(background.scalar_profile(grid.nodes), dtype=float)
    exponent = optical.ingoing_exponent(frequency)
    current_index = grid.size
    total_size = grid.size + 1
    operator = np.zeros((total_size, total_size), dtype=complex)
    interior = np.arange(1, grid.size - 1)
    coordinate = grid.nodes[interior]
    blackening = 1.0 - coordinate**3
    blackening_prime = -3.0 * coordinate**2
    one_minus = 1.0 - coordinate
    first_coefficient = blackening_prime / blackening - 2.0 * exponent / one_minus
    potential = (
        exponent * (exponent - 1.0) / one_minus**2
        - exponent * blackening_prime / (one_minus * blackening)
        + frequency**2 / blackening**2
        - 2.0 * scalar[interior] ** 2 / (coordinate**2 * blackening)
    )
    operator[interior, : grid.size] = (
        grid.second_derivative[interior, :]
        + first_coefficient[:, np.newaxis] * grid.first_derivative[interior, :]
    )
    operator[interior, interior] += potential
    operator[0, 0] = 1.0
    operator[0, current_index] = -transfer.field_current
    horizon = optical.horizon_frobenius_coefficient(frequency, background.horizon_scalar)
    operator[grid.size - 1, : grid.size] = grid.first_derivative[-1, :]
    operator[grid.size - 1, grid.size - 1] += horizon
    operator[total_size - 1, : grid.size] = grid.first_derivative[0, :]
    operator[total_size - 1, current_index] = -transfer.derivative_current
    rhs = np.zeros(total_size, dtype=complex)
    rhs[0] = transfer.field_source
    rhs[total_size - 1] = transfer.derivative_source
    row_norms = np.max(np.abs(operator), axis=1)
    return {
        "grid": grid, "transfer": transfer, "scalar": scalar, "horizon": complex(horizon),
        "first_coefficient": first_coefficient, "potential": potential,
        "operator": operator, "rhs": rhs, "row_norms": row_norms,
        "equilibrated": operator / row_norms[:, np.newaxis], "equilibrated_rhs": rhs / row_norms,
    }


def _array_sha256(array) -> Dict[str, Any]:
    import hashlib

    contiguous = np.ascontiguousarray(array)
    return {"sha256": hashlib.sha256(contiguous.tobytes()).hexdigest(),
            "dtype": str(contiguous.dtype), "shape": list(contiguous.shape)}


class _OCSystem:
    """The complete discrete system of one case, with its operator chain."""

    def __init__(self, rebuilt, frequency, stored, matrix_cache):
        grid = rebuilt["grid"]
        self.size = grid.size
        self.frequency = float(frequency)
        self.stored = np.asarray(stored, dtype=complex)
        nodes = [Decimal(float(u)) for u in grid.nodes]
        key = (HIGH_PRECISION_DIGITS, grid.nodes.tobytes())
        if key not in matrix_cache:
            matrix_cache[key] = decimal_differentiation_matrices(nodes)
        self.first_exact, self.second_exact, self.weights = matrix_cache[key]
        self.nodes = nodes
        self.first_double = _decimal_matrix(grid.first_derivative)
        self.second_double = _decimal_matrix(grid.second_derivative)
        omega = Decimal(self.frequency)
        self.exact_coefficients = [
            decimal_equation_coefficients(nodes[i], omega, Decimal(float(rebuilt["scalar"][i])))
            for i in range(1, self.size - 1)
        ]
        self.double_coefficients = [
            (_dc(c1), _dc(v)) for c1, v in zip(rebuilt["first_coefficient"], rebuilt["potential"])
        ]
        transfer = rebuilt["transfer"]
        self.field_current = _dc(-transfer.field_current)
        self.derivative_current = _dc(-transfer.derivative_current)
        self.horizon = _dc(rebuilt["horizon"])
        self.rhs = _cv_from_array(rebuilt["rhs"])
        self.row_norms = [Decimal(float(n)) for n in rebuilt["row_norms"]]
        self.assembled = (_decimal_matrix(rebuilt["operator"].real), _decimal_matrix(rebuilt["operator"].imag))
        self.equilibrated = (_decimal_matrix(rebuilt["equilibrated"].real),
                             _decimal_matrix(rebuilt["equilibrated"].imag))
        self.equilibrated_rhs = _cv_from_array(rebuilt["equilibrated_rhs"])
        self.abs_assembled = np.abs(rebuilt["operator"])
        self.abs_rhs = np.abs(rebuilt["rhs"])

    def apply(self, variant: str, x):
        """Return ``T x - b`` for one operator of the chain, in 50 digits."""

        n = self.size
        if variant in ("asm", "eq"):
            if variant == "asm":
                product = _complex_matvec(*self.assembled, x)
                return ([p - b for p, b in zip(product[0], self.rhs[0])],
                        [p - b for p, b in zip(product[1], self.rhs[1])])
            product = _complex_matvec(*self.equilibrated, x)
            return ([w * (p - b) for w, p, b in zip(self.row_norms, product[0], self.equilibrated_rhs[0])],
                    [w * (p - b) for w, p, b in zip(self.row_norms, product[1], self.equilibrated_rhs[1])])
        f = (x[0][:n], x[1][:n])
        current = (x[0][n], x[1][n])
        first_matrix = self.first_exact if variant == "exact" else self.first_double
        first = _real_matvec(first_matrix, f)
        if variant == "exact":
            second = _real_matvec(self.second_exact, f)
        elif variant == "D":
            second = _real_matvec(self.first_double, first)
        else:
            second = _real_matvec(self.second_double, f)
        coefficients = self.double_coefficients if variant == "coef" else self.exact_coefficients
        out = [None] * (n + 1)
        out[0] = _cadd((f[0][0], f[1][0]), _cmul(self.field_current, current))
        for position, i in enumerate(range(1, n - 1)):
            c1, v = coefficients[position]
            term = _cadd((second[0][i], second[1][i]), _cmul(c1, (first[0][i], first[1][i])))
            out[i] = _cadd(term, _cmul(v, (f[0][i], f[1][i])))
        out[n - 1] = _cadd((first[0][n - 1], first[1][n - 1]), _cmul(self.horizon, (f[0][n - 1], f[1][n - 1])))
        out[n] = _cadd((first[0][0], first[1][0]), _cmul(self.derivative_current, current))
        re = [value[0] for value in out]
        im = [value[1] for value in out]
        return ([r - b for r, b in zip(re, self.rhs[0])], [r - b for r, b in zip(im, self.rhs[1])])

    def row_scale(self, x) -> np.ndarray:
        return self.abs_assembled @ np.abs(_cv_to_array(x)) + self.abs_rhs


def optical_oc_spike(system: "_OCSystem", check, x, index: int, digits: int = HIGH_PRECISION_DIGITS,
                     weight_cache=None) -> Tuple[Decimal, Decimal]:
    """Physical-node spike residual ``R`` of the regular part of ``x``."""

    with localcontext() as context:
        context.prec = digits
        if digits == HIGH_PRECISION_DIGITS:
            nodes, weights = system.nodes, system.weights
        else:
            key = ("oc", digits, tuple(system.nodes))
            if weight_cache is None or key not in weight_cache:
                nodes = [Decimal(float(u)) for u in system.nodes]
                weights = decimal_barycentric_weights(nodes)
                if weight_cache is not None:
                    weight_cache[key] = (nodes, weights)
            else:
                nodes, weights = weight_cache[key]
        values = _cv_pairs(x, system.size)
        point = Decimal(float(check["coordinate"][index]))
        a, a1, a2 = decimal_interpolant_derivatives(nodes, weights, values, point)
        evaluation = decimal_regular_residual(
            point, Decimal(1), Decimal(system.frequency), Decimal(float(check["scalar"][index])), a, a1, a2,
        )
        return evaluation["residual"]


def optical_oc_refine(system, variant, x0, lu, spike, *, target=None,
                      max_iterations: int = OPTICAL_OC_MAX_ITERATIONS) -> Dict[str, Any]:
    """High-precision approximation of the exact solution of one operator.

    ``target(x)`` returns ``T x - b``; by default the chain operator
    ``variant``. The correction uses the production LU in double.
    """

    from scipy.linalg import lu_solve

    residual_of = target or (lambda vector: system.apply(variant, vector))
    x = (list(x0[0]), list(x0[1]))
    history, changes = [], []
    previous = spike(x)
    with localcontext() as context:
        context.prec = HIGH_PRECISION_DIGITS
        for iteration in range(max_iterations + 1):
            residual = residual_of(x)
            scale = system.row_scale(x)
            magnitudes = np.array([float(_cabs((r, i))) for r, i in zip(*residual)])
            beta = float(np.max(magnitudes / scale))
            history.append(beta)
            converged = beta <= OPTICAL_OC_BACKWARD_LIMIT and iteration >= OPTICAL_OC_MIN_ITERATIONS
            if converged or iteration == max_iterations:
                break
            correction_rhs = np.array([complex(float(-r / n), float(-i / n))
                                       for r, i, n in zip(*residual, system.row_norms)])
            delta = lu_solve(lu, correction_rhs)
            x = ([value + Decimal(float(d.real)) for value, d in zip(x[0], delta)],
                 [value + Decimal(float(d.imag)) for value, d in zip(x[1], delta)])
            current = spike(x)
            changes.append(float(_cabs(_csub(current, previous))))
            previous = current
    return {
        "x": x, "spike": previous, "backward_errors": history, "iterations": len(changes),
        "last_spike_change": changes[-1] if changes else 0.0,
        "converged": bool(history[-1] <= OPTICAL_OC_BACKWARD_LIMIT
                          and len(changes) >= OPTICAL_OC_MIN_ITERATIONS),
    }


def optical_oc_classification(stored: float, solve: float, operator: float, discretization: float,
                              qualified: bool) -> str:
    """Apply the plan's ordered, mutually exclusive rules (Section 8)."""

    for magnitude in (stored, solve, operator, discretization):
        if (isinstance(magnitude, (bool, np.bool_))
                or not isinstance(magnitude, (int, float, np.integer, np.floating))
                or not math.isfinite(float(magnitude)) or float(magnitude) < 0.0):
            raise ValueError(f"invalid residual magnitude {magnitude!r}")
    if stored == 0.0:
        return "zero-residual"
    if not qualified:
        return "technical-stop"
    shares = {"solve": solve / stored, "operator-rounding": operator / stored,
              "discretization": discretization / stored}
    if sum(shares.values()) > 1.5:
        return "cancellation"
    for name, share in shares.items():
        others = [value for key, value in shares.items() if key != name]
        if share >= 0.8 and all(value <= 0.25 for value in others):
            return f"{name}-dominated"
    return "mixed"


def optical_oc_named_step(steps: Mapping[str, float], operator: float, qualified: bool) -> str:
    """Name the operator-rounding step only under the plan's conditions."""

    if operator <= 0.0 or not qualified:
        return "not named"
    if sum(steps.values()) > 1.5 * operator:
        return "cancellation among steps"
    name, largest = max(steps.items(), key=lambda item: item[1])
    return name if largest >= 0.8 * operator else "several steps"


def _oc_bounds(system: "_OCSystem", rebuilt, x) -> Dict[str, np.ndarray]:
    """Loose a-priori rounding bounds of Section 9 (F3), per row, in double."""

    n = system.size
    grid = rebuilt["grid"]
    xd = np.abs(_cv_to_array(x))
    f = xd[:n]
    abs_first = np.abs(grid.first_derivative)
    abs_second = np.abs(grid.second_derivative)
    first_f = np.abs(grid.first_derivative @ _cv_to_array(x)[:n])
    interior = np.arange(1, n - 1)
    c1_scale, v_scale = _double_coefficient_scales(grid.nodes[interior], system.frequency,
                                                   rebuilt["scalar"][interior])
    zeros = np.zeros(n + 1)
    assembly = zeros.copy()
    assembly[interior] = ((abs_second[interior] + np.abs(rebuilt["first_coefficient"])[:, None]
                           * abs_first[interior]) @ f + np.abs(rebuilt["potential"]) * f[interior])
    assembly[0] = f[0] + abs(rebuilt["transfer"].field_current) * xd[n]
    assembly[n - 1] = abs_first[-1] @ f + abs(rebuilt["horizon"]) * f[n - 1]
    assembly[n] = abs_first[0] @ f + abs(rebuilt["transfer"].derivative_current) * xd[n]
    coefficient = zeros.copy()
    # Correction 1 to F3 (reported): rounding of F = 1 - u^3 is amplified by
    # 1/F near the horizon, which the frozen bound omitted.
    conditioning = 1.0 + 1.0 / (1.0 - grid.nodes[interior] ** 3)
    coefficient[interior] = conditioning * (c1_scale * first_f[interior] + v_scale * f[interior])
    product = zeros.copy()
    product[interior] = (abs_first @ (abs_first @ f))[interior]
    scale = system.row_scale(x)
    floor = OPTICAL_OC_HP_FLOOR * scale
    return {
        "equilibration": 4.0 * EPS * scale + floor,
        "assembly": 8.0 * EPS * assembly + floor,
        "coefficients": 64.0 * EPS * coefficient + floor,
        "D@D-product": rounding_gamma(n) * product + floor,
    }


def optical_oc_decomposition(system: "_OCSystem", rebuilt, x) -> Dict[str, Any]:
    """Measurement 1 and the F3 consistency checks for one solution vector."""

    with localcontext() as context:
        context.prec = HIGH_PRECISION_DIGITS
        residuals = {variant: system.apply(variant, x) for variant in OPTICAL_OC_CHAIN}
        contributions = {}
        for step, (left, right) in zip(OPTICAL_OC_STEPS, zip(OPTICAL_OC_CHAIN, OPTICAL_OC_CHAIN[1:])):
            contributions[step] = ([a - b for a, b in zip(residuals[left][0], residuals[right][0])],
                                   [a - b for a, b in zip(residuals[left][1], residuals[right][1])])
        contributions["solve"] = residuals["eq"]
        total = residuals["exact"]
        summed_re = [sum(values) for values in zip(*(c[0] for c in contributions.values()))]
        summed_im = [sum(values) for values in zip(*(c[1] for c in contributions.values()))]
        scale = system.row_scale(x)
        identity = max(float(_cabs((a - b, c - d))) / s
                       for a, b, c, d, s in zip(total[0], summed_re, total[1], summed_im, scale))
        magnitudes = {name: np.array([float(_cabs((r, i))) for r, i in zip(*vector)])
                      for name, vector in contributions.items()}
        total_abs = np.array([float(_cabs((r, i))) for r, i in zip(*total)])
    bounds = _oc_bounds(system, rebuilt, x)
    checks = {step: bool(np.all(magnitudes[step] <= bounds[step])) for step in bounds}
    worst = {step: float(np.max(magnitudes[step] / bounds[step])) for step in bounds}
    n = system.size
    rows = [0, 1, 2, 3, n - 1, n]
    report_rows = []
    for row in rows:
        report_rows.append({
            "row": int(row),
            "row_scale": float(scale[row]),
            "total": _cfloat((total[0][row], total[1][row])),
            "contributions": {name: _cfloat((vector[0][row], vector[1][row]))
                              for name, vector in contributions.items()},
        })
    maxima = {name: {"max_over_row_scale": float(np.max(values / scale)),
                     "row": int(np.argmax(values / scale))} for name, values in magnitudes.items()}
    maxima["total"] = {"max_over_row_scale": float(np.max(total_abs / scale)),
                       "row": int(np.argmax(total_abs / scale))}
    return {
        "rows": report_rows,
        "maxima": maxima,
        "sum_identity_max_relative": identity,
        "bound_checks": {"passed": all(checks.values()) and identity <= 1.0e-40,
                         "per_step": checks, "worst_ratio_to_bound": worst},
    }


def optical_oc_case(frequency_over_temperature: float, degree: int, background, matrix_cache,
                    *, label: str, artifact_dir: Optional[Path], cross_check: bool = False) -> Dict[str, Any]:
    from scipy.linalg import lu_factor

    response, captured = optical_oc_capture(frequency_over_temperature, degree, background)
    args = captured["residual_args"]
    frequency = float(args[3])
    rebuilt = optical_oc_reconstruct(frequency, degree, background)
    solves = captured["solves"]
    record: Dict[str, Any] = {
        "omega_over_temperature": float(frequency_over_temperature),
        "degree": int(degree),
        "dimensionless_omega": frequency,
    }
    if len(solves) != 1:
        record.update({"identity_check": {"exact_match": False, "solve_calls": len(solves)},
                       "classification": "technical-stop",
                       "stopped": "expected exactly one production solve"})
        return record
    a, b, solution = solves[0]
    stored_regular = np.asarray(args[1], dtype=complex)
    identity = {
        "equilibrated_operator": rebuilt["equilibrated"].tobytes() == a.tobytes(),
        "equilibrated_rhs": rebuilt["equilibrated_rhs"].tobytes() == b.tobytes(),
        "stored_regular": solution[: degree + 1].tobytes() == stored_regular.tobytes(),
        "nodes": rebuilt["grid"].nodes.tobytes() == np.asarray(args[0], dtype=float).tobytes(),
    }
    identity["exact_match"] = all(identity.values())
    record["identity_check"] = identity
    if not identity["exact_match"]:
        record.update({"classification": "technical-stop",
                       "stopped": "production operator not reconstructed bit for bit"})
        return record

    wide = optical_residual_profiles(*args, first_index=1)
    check = {"coordinate": wide["check_coordinate"],
             "scalar": np.concatenate([[np.nan], wide["scalar"]])}
    arrays = {
        "stored_solution": solution, "nodes": rebuilt["grid"].nodes, "local_nodes": wide["local_nodes"],
        "scalar_nodes": rebuilt["scalar"], "check_coordinate": wide["check_coordinate"],
        "check_scalar": wide["scalar"], "first_coefficient": rebuilt["first_coefficient"],
        "potential": rebuilt["potential"],
        "fixed_inputs": np.array([rebuilt["transfer"].field_source, rebuilt["transfer"].field_current,
                                  rebuilt["transfer"].derivative_source,
                                  rebuilt["transfer"].derivative_current, rebuilt["horizon"]]),
        "rhs": rebuilt["rhs"], "row_norms": rebuilt["row_norms"], "equilibrated_rhs": b,
        "first_derivative": rebuilt["grid"].first_derivative,
        "second_derivative": rebuilt["grid"].second_derivative,
        "assembled_operator": rebuilt["operator"], "equilibrated_operator": a,
    }
    record["array_sha256"] = {name: _array_sha256(value) for name, value in arrays.items()}
    if artifact_dir is not None:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        name = f"{label}-omega{frequency_over_temperature:g}-degree{degree}.npz"
        path = artifact_dir / name
        np.savez_compressed(path, **arrays)
        record["artifact"] = {"relative_path": (OPTICAL_OC_ARTIFACT_DIR / name).as_posix(),
                              "bytes": path.stat().st_size, "sha256": _file_sha256(path)}

    with localcontext() as context:
        context.prec = HIGH_PRECISION_DIGITS
        system = _OCSystem(rebuilt, frequency, solution, matrix_cache)
        stored = _cv_from_array(solution)
        record["row_decomposition"] = optical_oc_decomposition(system, rebuilt, stored)

        def spike(vector):
            return optical_oc_spike(system, check, vector, OPTICAL_OC_SPIKE_INDEX)

        stored_spike = spike(stored)
        lu = lu_factor(a)
        approximations = {}
        for variant in OPTICAL_OC_CHAIN:
            approximations[variant] = optical_oc_refine(system, variant, stored, lu, spike)
        stored_abs = float(_cabs(stored_spike))
        for item in approximations.values():
            item["qualified"] = bool(item["converged"] and
                                     item["last_spike_change"] <= OPTICAL_OC_UNCERTAINTY_LIMIT * stored_abs)
        eq, exact = approximations["eq"], approximations["exact"]
        solve_part = _csub(stored_spike, eq["spike"])
        operator_part = _csub(eq["spike"], exact["spike"])
        qualified = bool(eq["qualified"] and exact["qualified"]
                         and record["row_decomposition"]["bound_checks"]["passed"])
        magnitudes = (stored_abs, float(_cabs(solve_part)), float(_cabs(operator_part)),
                      float(_cabs(exact["spike"])))
        classification = optical_oc_classification(*magnitudes, qualified)
        all_qualified = all(item["qualified"] for item in approximations.values())
        # Step k between chain[k] (closer to exact) and chain[k+1] contributes
        # R(x~_chain[k+1]) - R(x~_chain[k]); the steps sum to Delta_op.
        step_values = {step: _csub(approximations[right]["spike"], approximations[left]["spike"])
                       for step, (left, right) in zip(OPTICAL_OC_STEPS,
                                                       zip(OPTICAL_OC_CHAIN, OPTICAL_OC_CHAIN[1:]))}
        step_magnitudes = {step: float(_cabs(value)) for step, value in step_values.items()}
        named = optical_oc_named_step(step_magnitudes, magnitudes[2], all_qualified)
        context_values = {}
        for index in OPTICAL_OC_CONTEXT_INDICES:
            context_values[str(index)] = {
                "coordinate": float(check["coordinate"][index]),
                "stored": _cfloat(optical_oc_spike(system, check, stored, index)),
                "eq": _cfloat(optical_oc_spike(system, check, eq["x"], index)),
                "exact": _cfloat(optical_oc_spike(system, check, exact["x"], index)),
            }
        ob_local = _decimal_node_evaluation(wide, solution[: degree + 1], frequency, OPTICAL_OC_SPIKE_INDEX,
                                            HIGH_PRECISION_DIGITS, {})
        width = Decimal(float(wide["width"]))
        ob_physical = _cscale(ob_local["residual"], 1 / (width * width))
        convention = float(_cabs(_csub(ob_physical, stored_spike)) / _cabs(stored_spike))
        cross = None
        if cross_check:
            cache: Dict[Any, Any] = {}
            high_stored = optical_oc_spike(system, check, stored, OPTICAL_OC_SPIKE_INDEX,
                                           OPTICAL_OC_CROSS_CHECK_DIGITS, cache)
            high_exact = optical_oc_spike(system, check, exact["x"], OPTICAL_OC_SPIKE_INDEX,
                                          OPTICAL_OC_CROSS_CHECK_DIGITS, cache)
            with localcontext() as wider:
                wider.prec = OPTICAL_OC_CROSS_CHECK_DIGITS
                cross = {
                    "digits": OPTICAL_OC_CROSS_CHECK_DIGITS,
                    "stored_relative_difference": float(_cabs(_csub(high_stored, stored_spike))
                                                        / _cabs(high_stored)),
                    "exact_relative_difference": float(_cabs(_csub(high_exact, exact["spike"]))
                                                       / _cabs(high_exact)),
                }
        sum_check = _csub(stored_spike, _cadd(_cadd(solve_part, operator_part), exact["spike"]))
    record.update({
        "spike_check_index": OPTICAL_OC_SPIKE_INDEX,
        "spike_coordinate": float(check["coordinate"][OPTICAL_OC_SPIKE_INDEX]),
        "production_equation_residual": float(response.equation_residual),
        "condition_number": float(response.condition_number),
        "approximations": {
            variant: {key: value for key, value in item.items() if key not in ("x",)}
            | {"spike": _cfloat(item["spike"])}
            for variant, item in approximations.items()
        },
        "spike_attribution": {
            "stored": _cfloat(stored_spike),
            "stored_abs": stored_abs,
            "solve": _cfloat(solve_part),
            "operator_rounding": _cfloat(operator_part),
            "discretization": _cfloat(exact["spike"]),
            "shares": {"solve": magnitudes[1] / stored_abs, "operator_rounding": magnitudes[2] / stored_abs,
                       "discretization": magnitudes[3] / stored_abs},
            "uncertainty_share": (eq["last_spike_change"] + exact["last_spike_change"]) / stored_abs,
            "sum_identity_abs": float(_cabs(sum_check)),
            "steps": {step: _cfloat(value) for step, value in step_values.items()},
            "step_shares_of_operator": ({step: value / magnitudes[2] for step, value in step_magnitudes.items()}
                                        if magnitudes[2] > 0 else None),
        },
        "classification": classification,
        "named_step": named,
        "context_nodes": context_values,
        "ob_convention_relative_difference": convention,
        "cross_check": cross,
    })
    return record


def optical_oc_identity_fixture(matrix_cache) -> Dict[str, Any]:
    """F1-F5 of the plan (Section 9), before any production case."""

    from holoforge.benchmarks import holographic_superconductor_optical as optical
    from scipy.linalg import lu_factor

    checks: Dict[str, Any] = {}
    with localcontext() as context:
        context.prec = HIGH_PRECISION_DIGITS
        grid = chebyshev_lobatto_grid(640, optical.ENDPOINT_SPLIT_COORDINATE, 1.0)
        nodes = [Decimal(float(u)) for u in grid.nodes]
        key = (HIGH_PRECISION_DIGITS, grid.nodes.tobytes())
        if key not in matrix_cache:
            matrix_cache[key] = decimal_differentiation_matrices(nodes)
        first, second, weights = matrix_cache[key]
        coefficients = [(Decimal(c), Decimal(d)) for c, d in
                        ((1, 0), (2, -1), (-3, 0.5), (0.25, 4), (5, 0), (0, -2), (1.5, 1))]

        def polynomial(x):
            powers = [Decimal(1)]
            for _ in coefficients[1:]:
                powers.append(powers[-1] * x)
            value = d1 = d2 = (Decimal(0), Decimal(0))
            for power, coefficient in enumerate(coefficients):
                value = _cadd(value, _cscale(coefficient, powers[power]))
                if power >= 1:
                    d1 = _cadd(d1, _cscale(coefficient, power * powers[power - 1]))
                if power >= 2:
                    d2 = _cadd(d2, _cscale(coefficient, power * (power - 1) * powers[power - 2]))
            return value, d1, d2

        exact = [polynomial(u) for u in nodes]
        values = ([e[0][0] for e in exact], [e[0][1] for e in exact])
        got1 = _real_matvec(first, values)
        got2 = _real_matvec(second, values)
        worst = Decimal(0)
        for order, got in ((1, got1), (2, got2)):
            want = [e[order] for e in exact]
            largest = max(_cabs(w) for w in want)
            error = max(_cabs(_csub((got[0][k], got[1][k]), want[k])) for k in range(len(want)))
            worst = max(worst, error / largest)
        point = Decimal(float(chebyshev_lobatto_grid(1280, optical.ENDPOINT_SPLIT_COORDINATE, 1.0).nodes[3]))
        evaluated = decimal_interpolant_derivatives(nodes, weights, [e[0] for e in exact], point)
        for got, want in zip(evaluated, polynomial(point)):
            worst = max(worst, _cabs(_csub(got, want)) / _cabs(want))
    checks["F1_exact_polynomial_degree_640"] = {"max_relative_error": float(worst), "limit": 1.0e-30,
                                                "passed": bool(worst <= Decimal("1e-30"))}

    background = type("NormalState", (), {"scalar_profile": staticmethod(optical.zero_scalar_profile),
                                          "scalar_response": 0.0, "horizon_scalar": 0.0})
    frequency_over_temperature, degree = OPTICAL_OC_FIXTURE_CASE
    record = optical_oc_case(frequency_over_temperature, degree, background, matrix_cache,
                             label="fixture", artifact_dir=None)
    checks["F2_reconstruction"] = {"passed": bool(record["identity_check"]["exact_match"]),
                                   "detail": record["identity_check"]}
    if record["identity_check"]["exact_match"]:
        bound = record["row_decomposition"]["bound_checks"]
        checks["F3_rounding_bounds"] = {"passed": bool(bound["passed"]),
                                        "worst_ratio_to_bound": bound["worst_ratio_to_bound"],
                                        "sum_identity": record["row_decomposition"]["sum_identity_max_relative"]}
        checks["F4_refinement"] = {
            "passed": all(item["qualified"] for item in record["approximations"].values()),
            "iterations": {k: v["iterations"] for k, v in record["approximations"].items()},
            "final_backward_error": {k: v["backward_errors"][-1] for k, v in record["approximations"].items()},
        }
        _, captured = optical_oc_capture(frequency_over_temperature, degree, background)
        rebuilt = optical_oc_reconstruct(float(captured["residual_args"][3]), degree, background)
        solution = captured["solves"][0][2]
        with localcontext() as context:
            context.prec = HIGH_PRECISION_DIGITS
            system = _OCSystem(rebuilt, float(captured["residual_args"][3]), solution, matrix_cache)
            known = _cv_from_array(solution)
            product = system.apply("coef", known)
            rhs = ([p for p in product[0]], [p for p in product[1]])  # T x - b, so b' - b = T x - b

            def target(vector):
                residual = system.apply("coef", vector)
                return ([r - c for r, c in zip(residual[0], rhs[0])],
                        [r - c for r, c in zip(residual[1], rhs[1])])

            rng = np.random.default_rng(20260930)
            noise = 1.0 + 1.0e-8 * (rng.standard_normal(solution.size) + 1j * rng.standard_normal(solution.size))
            start = _cv_from_array(solution * noise)
            refined = optical_oc_refine(system, "coef", start, lu_factor(captured["solves"][0][0]),
                                        lambda vector: (Decimal(0), Decimal(0)), target=target)
            difference = max(float(_cabs((a - b, c - d)))
                             for a, b, c, d in zip(refined["x"][0], known[0], refined["x"][1], known[1]))
            relative = difference / float(np.max(np.abs(solution)))
        checks["F5_known_solution"] = {"normwise_relative_error": relative, "limit": 1.0e-25,
                                       "iterations": refined["iterations"], "passed": bool(relative <= 1.0e-25)}
    return {"checks": checks, "passed": all(item["passed"] for item in checks.values())}


def optical_oc_run(case_set: str, adverse: bool, *, build_label: Optional[str] = None,
                   artifact_dir: Optional[Path] = None) -> Dict[str, Any]:
    if case_set != "calibration":
        return {"stopped": "O-C uses only previously examined cases; reserved cases stay unused"}
    if adverse:
        return {"stopped": "the O-C plan defines no adverse controls"}
    if build_label not in OPTICAL_OC_CASES:
        return {"stopped": f"--build-label must be one of {sorted(OPTICAL_OC_CASES)}"}
    matrix_cache: Dict[Any, Any] = {}
    started = time.perf_counter()
    fixture = optical_oc_identity_fixture(matrix_cache)
    fixture["wall_seconds"] = time.perf_counter() - started
    if not fixture["passed"]:
        return {"identity_fixture": fixture, "stopped": "identity fixture failed"}
    background = optical_background()
    directory = artifact_dir or Path(__file__).resolve().parents[1] / OPTICAL_OC_ARTIFACT_DIR
    records = []
    for frequency, degree in OPTICAL_OC_CASES[build_label]:
        case_started = time.perf_counter()
        record = optical_oc_case(
            frequency, degree, background, matrix_cache, label=build_label, artifact_dir=directory,
            cross_check=(build_label, frequency, degree) == OPTICAL_OC_CROSS_CHECK,
        )
        record["wall_seconds"] = time.perf_counter() - case_started
        records.append(record)
    return {"identity_fixture": fixture, "build_label": build_label, "records": records}


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

RUNNERS: Dict[str, Callable[[str, bool], Dict[str, Any]]] = {
    "soft-wall": soft_wall_run,
    "soft-wall-sa": soft_wall_sa_run,
    "gn": gn_run,
    "optical": optical_run,
    "optical-ob": optical_ob_run,
    "optical-oc": optical_oc_run,
}


def _jsonable(value: Any) -> Any:
    """Return a strict-JSON form; non-finite numbers become strings.

    Complex numbers become ``[real, imaginary]``, each part converted the
    same way, so a non-finite part never reaches the output as a bare token.
    """

    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return _jsonable(value.tolist())
    if isinstance(value, np.bool_):
        return bool(value)
    # Explicit conversions: ``item()`` keeps ``longdouble`` as a NumPy scalar.
    # Extended values are rounded to double, which is what JSON holds.
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return _jsonable(float(value))
    if isinstance(value, np.complexfloating):
        return _jsonable(complex(value))
    if isinstance(value, Decimal):
        return _jsonable(float(value))
    if isinstance(value, complex):
        return [_jsonable(value.real), _jsonable(value.imag)]
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


PLAN = Path("docs/numerics/gate-calibration-2026-09-plan.md")
GATE_PLANS = {"optical-ob": OPTICAL_OB_PLAN, "optical-oc": OPTICAL_OC_PLAN}
THREAD_VARIABLES = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
)


def diagnostic_errors(result: Any, location: str = "result") -> List[str]:
    """Return tool-integrity failures found in a diagnostic result.

    A failed identity fixture, a reconstruction that does not reproduce its
    production value, or a non-finite diagnostic number is an execution
    error. Large residuals or controls that exceed a production limit are
    scientific data, not errors.
    """

    errors: List[str] = []
    if isinstance(result, Mapping):
        if "stopped" in result:
            errors.append(f"{location}: stopped: {result['stopped']}")
        fixture = result.get("identity_fixture")
        if isinstance(fixture, Mapping) and fixture.get("passed") is not True:
            errors.append(f"{location}.identity_fixture did not pass")
        check = result.get("identity_check")
        if isinstance(check, Mapping) and check.get("exact_match") is not True:
            errors.append(f"{location}.identity_check does not reproduce production")
        for key, value in result.items():
            if key in ("identity_fixture", "identity_check"):
                continue
            errors.extend(diagnostic_errors(value, f"{location}.{key}"))
    elif isinstance(result, np.ndarray) and result.ndim == 0:
        errors.extend(diagnostic_errors(result[()], location))
    elif isinstance(result, (list, tuple, np.ndarray)):
        for index, value in enumerate(result):
            errors.extend(diagnostic_errors(value, f"{location}[{index}]"))
    elif isinstance(result, (np.floating, np.complexfloating)):
        # np.isfinite handles longdouble without first rounding to double.
        if not bool(np.isfinite(result)):
            errors.append(f"{location} is not finite")
    elif isinstance(result, complex):
        if not (math.isfinite(result.real) and math.isfinite(result.imag)):
            errors.append(f"{location} is not finite")
    elif isinstance(result, float) and not math.isfinite(result):
        errors.append(f"{location} is not finite")
    return errors


def _file_sha256(path: Path) -> str:
    import hashlib

    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return "unknown"


def _installed_wheel_tags(name: str) -> List[str]:
    """Return the wheel tags recorded in an installed distribution, if any."""

    import importlib.metadata

    try:
        wheel = importlib.metadata.distribution(name).read_text("WHEEL") or ""
    except importlib.metadata.PackageNotFoundError:
        return []
    return [line.split(":", 1)[1].strip() for line in wheel.splitlines() if line.startswith("Tag:")]


def execution_metadata(plan: Path = PLAN) -> Dict[str, Any]:
    """Record the diagnostic's own identity and execution settings (path-free)."""

    import os

    root = Path(__file__).resolve().parents[1]
    threads = {}
    for variable in THREAD_VARIABLES:
        value = os.environ.get(variable)
        if value is not None:
            threads[variable] = value.strip() if value.strip().isdigit() else "set"
    return {
        "tool_sha256": _file_sha256(Path(__file__).resolve()),
        "plan_sha256": _file_sha256(root / plan),
        "thread_environment": threads,
        "installed_wheel_tags": {
            name: _installed_wheel_tags(name) for name in ("numpy", "scipy")
        },
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Print the diagnostic JSON; exit 2 on a tool-integrity failure.

    Exit 0 means every identity check and fixture passed and all diagnostic
    numbers are finite, whatever the scientific values. Exit 2 means the
    output, which is still printed for inspection, must not be used as
    calibration evidence.
    """

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("gate", choices=sorted(RUNNERS))
    parser.add_argument("--case-set", choices=("calibration", "confirmation"), default="calibration")
    parser.add_argument("--adverse", action="store_true", help="Also run adverse controls.")
    parser.add_argument("--build-label", help="optical-oc only: B1 or B3 (selects cases).")
    parser.add_argument("--artifact-dir", type=Path,
                        help="optical-oc only: where local arrays go (default output/optical-oc-artifacts).")
    args = parser.parse_args(argv)
    started = time.perf_counter()
    runner = RUNNERS[args.gate]
    if args.gate == "optical-oc":
        result = runner(args.case_set, args.adverse, build_label=args.build_label,
                        artifact_dir=args.artifact_dir)
    else:
        result = runner(args.case_set, args.adverse)
    errors = diagnostic_errors(result)
    plan = GATE_PLANS.get(args.gate, PLAN)
    payload = {
        "tool": "gate-calibration",
        "plan": plan.as_posix(),
        "gate": args.gate,
        "case_set": args.case_set,
        "adverse": bool(args.adverse),
        "status": "ok" if not errors else "diagnostic-error",
        "diagnostic_errors": errors,
        "identity_scope": "maximum value of each reconstructed residual, not every node",
        "execution": execution_metadata(plan),
        "runtime": runtime_versions(),
        "wall_seconds": time.perf_counter() - started,
        "result": result,
    }
    print(json.dumps(_jsonable(payload), indent=2, sort_keys=True, allow_nan=False))
    if errors:
        print("gate calibration diagnostic error: " + "; ".join(errors), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
