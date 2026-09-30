"""Command adapter for the quadratic soft-wall vector benchmark."""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from holoforge.benchmarks.soft_wall_vector import (
    DEFAULT_GRID_POINTS,
    DEFAULT_NUM_MODES,
    DEFAULT_SPECTRAL_DEGREE,
    DEFAULT_TOLERANCE,
    SoftWallConfig,
    solve_spectrum,
)
from holoforge.core.registry import (
    BenchmarkAdapter,
    BenchmarkExecution,
    BenchmarkExecutionError,
    ModelCardReference,
)


SPECTRUM_CHECK_ID = "exact-spectrum-relative-error"


SOFT_WALL_MODEL_CARD = ModelCardReference(
    identifier="qcd.soft-wall-vector.kkss",
    schema_version="0.1",
    repository_path="domains/qcd/soft_wall_vector/model-card.json",
    sha256="feac63ac24daa4f8fefaf5ddfffaeb161911a3b999966000e132a59c8d84426e",
)


def _configure_soft_wall(parser: Any) -> None:
    parser.add_argument(
        "--kappa",
        type=float,
        default=1.0,
        help="Positive soft-wall scale in GeV (default: 1.0).",
    )
    parser.add_argument(
        "--modes",
        type=int,
        default=DEFAULT_NUM_MODES,
        help=f"Number of lowest modes (default: {DEFAULT_NUM_MODES}).",
    )
    parser.add_argument(
        "--method",
        choices=("finite-difference", "spectral"),
        default="finite-difference",
        help="Numerical formulation (default: finite-difference).",
    )
    parser.add_argument(
        "--grid-points",
        type=int,
        default=DEFAULT_GRID_POINTS,
        help=(
            "Number of interior finite-difference points "
            f"(default: {DEFAULT_GRID_POINTS})."
        ),
    )
    parser.add_argument(
        "--spectral-degree",
        type=int,
        default=DEFAULT_SPECTRAL_DEGREE,
        help=(
            "Chebyshev polynomial degree for --method spectral "
            f"(default: {DEFAULT_SPECTRAL_DEGREE})."
        ),
    )
    parser.add_argument(
        "--z-max",
        type=float,
        default=None,
        help="IR boundary in GeV^-1 (default: 10/kappa).",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=DEFAULT_TOLERANCE,
        help=f"Maximum accepted relative error (default: {DEFAULT_TOLERANCE:g}).",
    )


def _execute_soft_wall(args: Any) -> BenchmarkExecution:
    if not math.isfinite(args.tolerance) or args.tolerance < 0.0:
        raise BenchmarkExecutionError(
            "tolerance must be finite and non-negative"
        )
    try:
        config = SoftWallConfig(
            kappa_gev=args.kappa,
            grid_points=args.grid_points,
            z_max_gev_inverse=args.z_max,
            spectral_degree=args.spectral_degree,
        )
        result = solve_spectrum(
            config=config,
            num_modes=args.modes,
            method=args.method,
        )
    except (RuntimeError, ValueError) as exc:
        raise BenchmarkExecutionError(str(exc)) from exc
    payload = result.to_dict(args.tolerance)
    return BenchmarkExecution(
        payload=payload,
        passed=bool(payload["passed"]),
    )


def _render_soft_wall(execution: BenchmarkExecution) -> Sequence[str]:
    payload = execution.payload
    configuration = payload["configuration"]
    if payload["numerical_method"].get("route") == "spectral":
        resolution = (
            f"spectral degree = {configuration['spectral_degree']}"
        )
    else:
        resolution = f"grid points = {configuration['grid_points']}"
    lines = [
        "Quadratic soft-wall vector benchmark",
        (
            f"kappa = {configuration['kappa_gev']:g} GeV, "
            f"{resolution}, "
            f"z_max = {configuration['z_max_gev_inverse']:g} GeV^-1"
        ),
        " n    numerical m^2    analytic m^2    relative error",
    ]
    for record in payload["results"]:
        lines.append(
            f"{record['n']:2d}    "
            f"{record['numerical_mass_squared_gev2']:13.8f}    "
            f"{record['analytic_mass_squared_gev2']:12.8f}    "
            f"{record['relative_error']:14.6e}"
        )
    checks = payload["acceptance_checks"]
    spectrum_checks = [
        check for check in checks if check["id"] == SPECTRUM_CHECK_ID
    ]
    spectrum_passed = (
        spectrum_checks[0]["passed"] if spectrum_checks else execution.passed
    )
    lines.append(
        f"{_status(spectrum_passed)}: max relative error = "
        f"{payload['max_relative_error']:.6e}; "
        f"tolerance = {payload['tolerance']:.6e}"
    )
    # Each remaining gate reports its own state, so a failed refinement check
    # is never attributed to the analytic-spectrum tolerance.
    for check in checks:
        if check["id"] == SPECTRUM_CHECK_ID:
            continue
        detail = f"{_status(check['passed'])}: {check['id']}"
        if "value" in check:
            detail += f"; value = {check['value']:.6e}"
        if "criterion" in check:
            detail += f"; criterion: {check['criterion']}"
        lines.append(detail)
    if len(checks) > 1:
        lines.append(f"{_status(execution.passed)}: all declared acceptance gates")
    lines.append(
        "Scope: numerical reproduction of the model equation, not "
        "empirical validation."
    )
    return lines


def _status(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def _soft_wall_state(result: Mapping[str, Any]) -> Mapping[str, Any]:
    configuration = result["configuration"]
    return {
        "model_identifier": SOFT_WALL_MODEL_CARD.identifier,
        "ensemble": "zero-density vacuum spectral problem",
        "fixed_variables": {
            "background": "fixed AdS_5 with a quadratic dilaton",
            "sector": "transverse vector",
        },
        "approximation": "bottom-up fixed-background quadratic soft-wall model",
        "phase_branch": "normalizable transverse-vector tower",
        "parameters": {"kappa_gev": configuration["kappa_gev"]},
        "declared_controls": ["kappa_gev"],
        "boundary_source_conditions": {
            "uv": "normalizable mode; numerical Dirichlet condition",
            "ir": "normalizable mode; finite-domain Dirichlet condition",
        },
        "conventions": {
            "coordinate": "z",
            "units": "kappa in GeV, z in GeV^-1, m^2 in GeV^2",
            "observable": "ordered transverse-vector squared masses",
        },
        "source_record_versions": {
            "model_card_schema": SOFT_WALL_MODEL_CARD.schema_version,
            "model_card_sha256": SOFT_WALL_MODEL_CARD.sha256,
        },
    }


SOFT_WALL_ADAPTER = BenchmarkAdapter(
    identifier="soft-wall-vector",
    description="Reproduce the exact quadratic soft-wall vector spectrum.",
    configure_parser=_configure_soft_wall,
    execute=_execute_soft_wall,
    render_human=_render_soft_wall,
    scientific_state=_soft_wall_state,
    model_cards=(SOFT_WALL_MODEL_CARD,),
)


__all__ = ["SOFT_WALL_ADAPTER", "SOFT_WALL_MODEL_CARD"]
