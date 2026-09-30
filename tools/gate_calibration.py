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

``--adverse`` adds the plan's adverse controls. ``--case-set confirmation``
selects the reserved confirmation cases, which Batch 2a must not run.
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
) -> Dict[str, Any]:
    """Per-point A-form (production formula) and a-form residuals."""

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
    selected = np.arange(3, check.size - 3)
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
# Command line
# ---------------------------------------------------------------------------

RUNNERS: Dict[str, Callable[[str, bool], Dict[str, Any]]] = {
    "soft-wall": soft_wall_run,
    "gn": gn_run,
    "optical": optical_run,
}


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, complex):
        return [value.real, value.imag]
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("gate", choices=sorted(RUNNERS))
    parser.add_argument("--case-set", choices=("calibration", "confirmation"), default="calibration")
    parser.add_argument("--adverse", action="store_true", help="Also run adverse controls.")
    args = parser.parse_args(argv)
    started = time.perf_counter()
    result = RUNNERS[args.gate](args.case_set, args.adverse)
    payload = {
        "tool": "gate-calibration",
        "plan": "docs/numerics/gate-calibration-2026-09-plan.md",
        "gate": args.gate,
        "case_set": args.case_set,
        "adverse": bool(args.adverse),
        "runtime": runtime_versions(),
        "wall_seconds": time.perf_counter() - started,
        "result": result,
    }
    print(json.dumps(_jsonable(payload), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
