"""Command adapter for the Gubser--Nellore Einstein--dilaton benchmark."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from holoforge.benchmarks.gubser_nellore_ed import (
    save_gubser_nellore_artifacts,
    verify_gubser_nellore_ed,
)
from holoforge.core.registry import (
    BenchmarkAdapter,
    BenchmarkExecution,
    BenchmarkExecutionError,
    ModelCardReference,
)


GUBSER_NELLORE_MODEL_CARD = ModelCardReference(
    identifier="qcd.gubser-nellore-einstein-dilaton",
    schema_version="0.1",
    repository_path="domains/qcd/gubser_nellore_ed/model-card.json",
    sha256="293cdd10f4f53885eac77a56bc3248117caa075ccb6829863e8cc85aa9620879",
)


def _configure_gubser_nellore(parser: Any) -> None:
    parser.add_argument(
        "--residual-backend",
        choices=("numpy", "rust"),
        default="numpy",
        help="Evaluate collocation residuals with NumPy (default) or the optional Rust extension.",
    )
    parser.add_argument(
        "--profile",
        choices=("anchor", "figure"),
        default="anchor",
        help=(
            "Run the bounded anchor scan or the denser Figure 2 scan "
            "(default: anchor)."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        metavar="PATH",
        help="Save the JSON record, curve CSV, and reproduction plot under PATH.",
    )


def _execute_gubser_nellore(args: Any) -> BenchmarkExecution:
    try:
        result = verify_gubser_nellore_ed(
            profile=args.profile, residual_backend=args.residual_backend
        )
        artifacts = {}
        if args.output_dir is not None:
            artifacts = save_gubser_nellore_artifacts(result, args.output_dir)
    except (OSError, RuntimeError, ValueError) as exc:
        raise BenchmarkExecutionError(str(exc)) from exc
    return BenchmarkExecution(
        payload=result.to_dict(),
        passed=result.passed,
        artifacts=artifacts,
    )


def _render_gubser_nellore(execution: BenchmarkExecution) -> Sequence[str]:
    payload = execution.payload
    presets = payload["results"]["presets"]
    lines = [
        "Gubser--Nellore Einstein--dilaton benchmark",
        "Ensemble: zero chemical potential; no Maxwell field",
        "preset             horizons  max equation residual  max figure error",
    ]
    for identifier in ("cosh-calibration", "qcd-like"):
        result = presets[identifier]
        lines.append(
            f"{identifier:18s}  {result['horizon_count']:8d}  "
            f"{result['maximum_equation_residual']:21.6e}  "
            f"{result['figure']['maximum_anchor_error']:16.6e}"
        )
    for check in payload["acceptance_checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        value = "" if "value" not in check else f"; value = {check['value']:.6e}"
        lines.append(f"{status}: {check['description']}{value}")
    for role, path in execution.artifacts.items():
        lines.append(f"Artifact ({role}): {path}")
    overall = "PASS" if execution.passed else "FAIL"
    lines.extend((f"{overall}: all declared acceptance gates", payload["scope"]))
    return lines


def _gubser_nellore_state(result: Mapping[str, Any]) -> Mapping[str, Any]:
    configuration = result["configuration"]
    return {
        "model_identifier": GUBSER_NELLORE_MODEL_CARD.identifier,
        "ensemble": configuration["ensemble"],
        "fixed_variables": {
            "bulk_dimension": configuration["bulk_dimension"],
            "units": configuration["units"],
            "potentials": configuration["potentials"],
        },
        "approximation": (
            "classical two-derivative bottom-up Einstein gravity with one scalar"
        ),
        "phase_branch": "single zero-density black-hole branch per potential",
        "parameters": {
            "profile": configuration["profile"],
            "T_c_plot_registration": configuration["T_c_plot_registration"],
            "dop853_target_phi_h": configuration["dop853_target_phi_h"],
        },
        "declared_controls": ["profile"],
        "boundary_source_conditions": {
            "scalar": "unit leading UV coefficient in phi = x + ...",
            "metric": "asymptotically AdS with f(0) = 1 and f(1) = 0",
            "gauge": "no Maxwell field and zero chemical potential",
        },
        "conventions": {
            "primary_coordinate": "u = x/x_H, x = z^(4-Delta)",
            "thermodynamics": "L = 1 and kappa_5^2 = 1",
            "figure_3_scale": "T_c_plot is plot registration, not a prediction",
        },
        "source_record_versions": {
            "model_card_schema": GUBSER_NELLORE_MODEL_CARD.schema_version,
            "model_card_sha256": GUBSER_NELLORE_MODEL_CARD.sha256,
            "primary_source_pdf_sha256": result["primary_source"]["pdf_sha256"],
            "primary_source_archive_sha256": result["primary_source"][
                "source_archive_sha256"
            ],
        },
    }


GUBSER_NELLORE_ADAPTER = BenchmarkAdapter(
    identifier="gubser-nellore-ed",
    description=(
        "Reproduce the zero-density Gubser--Nellore Einstein--dilaton "
        "thermodynamic curves."
    ),
    configure_parser=_configure_gubser_nellore,
    execute=_execute_gubser_nellore,
    render_human=_render_gubser_nellore,
    scientific_state=_gubser_nellore_state,
    model_cards=(GUBSER_NELLORE_MODEL_CARD,),
)


__all__ = ["GUBSER_NELLORE_ADAPTER", "GUBSER_NELLORE_MODEL_CARD"]
