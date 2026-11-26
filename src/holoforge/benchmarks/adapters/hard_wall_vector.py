"""Command adapter for the hard-wall vector benchmark."""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from holoforge.benchmarks.hard_wall_vector import (
    DEFAULT_NUM_MODES,
    DEFAULT_RATIO_TOLERANCE,
    DEFAULT_SPECTRAL_DEGREE,
    HardWallConfig,
    solve_hard_wall_spectrum,
)
from holoforge.core.registry import (
    BenchmarkAdapter,
    BenchmarkExecution,
    BenchmarkExecutionError,
    ModelCardReference,
)


HARD_WALL_MODEL_CARD = ModelCardReference(
    identifier="qcd.hard-wall-vector.ekss",
    schema_version="0.1",
    repository_path="domains/qcd/hard_wall_vector/model-card.json",
    sha256="d2df67b80f203613655a5107625238229f6e99fce81395689f281eb6149b02c4",
)


def _configure_hard_wall(parser: Any) -> None:
    parser.add_argument(
        "--z-m",
        type=float,
        default=1.0,
        help="Positive hard-wall position in GeV^-1 (default: 1.0).",
    )
    parser.add_argument(
        "--epsilon-fraction",
        type=float,
        default=1.0e-4,
        help="UV cutoff as a fraction of z_m (default: 1e-4).",
    )
    parser.add_argument(
        "--modes",
        type=int,
        default=DEFAULT_NUM_MODES,
        help=f"Number of lowest modes (default: {DEFAULT_NUM_MODES}).",
    )
    parser.add_argument(
        "--method",
        choices=("shooting", "shooting-rust", "collocation", "spectral"),
        default="shooting",
        help="Numerical formulation (default: shooting).",
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
        "--tolerance",
        type=float,
        default=DEFAULT_RATIO_TOLERANCE,
        help=(
            "Maximum accepted relative ratio error "
            f"(default: {DEFAULT_RATIO_TOLERANCE:g})."
        ),
    )


def _execute_hard_wall(args: Any) -> BenchmarkExecution:
    if not math.isfinite(args.tolerance) or args.tolerance < 0.0:
        raise BenchmarkExecutionError(
            "tolerance must be finite and non-negative"
        )
    try:
        config = HardWallConfig(
            z_m_gev_inverse=args.z_m,
            epsilon_fraction=args.epsilon_fraction,
            spectral_degree=args.spectral_degree,
        )
        result = solve_hard_wall_spectrum(
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


def _render_hard_wall(execution: BenchmarkExecution) -> Sequence[str]:
    payload = execution.payload
    configuration = payload["configuration"]
    lines = [
        "Hard-wall vector benchmark",
        (
            f"method = {payload['numerical_method']['route']}, "
            f"z_m = {configuration['z_m_gev_inverse']:g} GeV^-1, "
            f"epsilon/z_m = {configuration['epsilon_fraction']:g}"
        ),
        " n    numerical m*z_m    analytic m*z_m    numerical ratio    error",
    ]
    for record in payload["results"]:
        lines.append(
            f"{record['n']:2d}    {record['numerical_m_z_m']:15.9f}    "
            f"{record['analytic_m_z_m']:14.9f}    "
            f"{record['numerical_ratio']:15.9f}    "
            f"{record['ratio_relative_error']:10.3e}"
        )
    status = "PASS" if execution.passed else "FAIL"
    lines.extend(
        (
            (
                f"{status}: max ratio relative error = "
                f"{payload['max_ratio_relative_error']:.6e}; "
                f"tolerance = {payload['tolerance']:.6e}"
            ),
            (
                "Scope: numerical reproduction of the published model equation, "
                "not precision validation."
            ),
        )
    )
    return lines


def _hard_wall_state(result: Mapping[str, Any]) -> Mapping[str, Any]:
    configuration = result["configuration"]
    return {
        "model_identifier": HARD_WALL_MODEL_CARD.identifier,
        "ensemble": "zero-density vacuum spectral problem",
        "fixed_variables": {
            "background": "fixed AdS_5 slice with an IR wall",
            "sector": "transverse vector",
        },
        "approximation": "bottom-up fixed-background hard-wall model",
        "phase_branch": "normalizable transverse-vector tower",
        "parameters": {
            "z_m_gev_inverse": configuration["z_m_gev_inverse"]
        },
        "declared_controls": ["z_m_gev_inverse"],
        "boundary_source_conditions": {
            "uv": "finite-cutoff Dirichlet condition",
            "ir": "Neumann condition at the IR wall",
        },
        "conventions": {
            "coordinate": "z",
            "units": "z_m in GeV^-1 and masses in GeV",
            "observable": "masses normalized to the lowest mode",
        },
        "source_record_versions": {
            "model_card_schema": HARD_WALL_MODEL_CARD.schema_version,
            "model_card_sha256": HARD_WALL_MODEL_CARD.sha256,
        },
    }


HARD_WALL_ADAPTER = BenchmarkAdapter(
    identifier="hard-wall-vector",
    description="Reproduce the hard-wall vector spectrum and Bessel-zero ratios.",
    configure_parser=_configure_hard_wall,
    execute=_execute_hard_wall,
    render_human=_render_hard_wall,
    scientific_state=_hard_wall_state,
    model_cards=(HARD_WALL_MODEL_CARD,),
)


__all__ = ["HARD_WALL_ADAPTER", "HARD_WALL_MODEL_CARD"]
