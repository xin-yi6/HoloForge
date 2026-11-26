"""Command adapter for the zero-density DeWolfe--Gubser--Rosen benchmark."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from holoforge.benchmarks.dewolfe_gubser_rosen_emd import (
    save_dewolfe_gubser_rosen_artifacts,
    verify_dewolfe_gubser_rosen_emd,
)
from holoforge.core.registry import (
    BenchmarkAdapter,
    BenchmarkExecution,
    BenchmarkExecutionError,
    ModelCardReference,
)


DEWOLFE_GUBSER_ROSEN_MODEL_CARD = ModelCardReference(
    identifier="qcd.dewolfe-gubser-rosen-emd",
    schema_version="0.1",
    repository_path="domains/qcd/dewolfe_gubser_rosen_emd/model-card.json",
    sha256="0267628ee299aacc46358e5157ff3171cb072198266ca752cef82f9ecab29ec1",
)


def _configure_dewolfe_gubser_rosen(parser: Any) -> None:
    parser.add_argument(
        "--residual-backend",
        choices=("numpy", "rust"),
        default="numpy",
        help="Evaluate neutral background collocation residuals with NumPy (default) or Rust.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        metavar="PATH",
        help="Save the strict JSON record, curve CSV, and Figure 3 plot under PATH.",
    )


def _execute_dewolfe_gubser_rosen(args: Any) -> BenchmarkExecution:
    try:
        result = verify_dewolfe_gubser_rosen_emd(residual_backend=args.residual_backend)
        artifacts = {}
        if args.output_dir is not None:
            artifacts = save_dewolfe_gubser_rosen_artifacts(
                result,
                args.output_dir,
            )
    except (OSError, RuntimeError, ValueError) as exc:
        raise BenchmarkExecutionError(str(exc)) from exc
    return BenchmarkExecution(
        payload=result.to_dict(),
        passed=result.passed,
        artifacts=artifacts,
    )


def _render_dewolfe_gubser_rosen(
    execution: BenchmarkExecution,
) -> Sequence[str]:
    payload = execution.payload
    summary = payload["results"]["summary"]
    lines = [
        "DeWolfe--Gubser--Rosen EMD Phase 5A benchmark",
        "Ensemble: zero chemical potential; Maxwell sector in linear response",
        "Result review: owner-approved by Xin-Yi Liu on 2026-08-22",
        (
            "Figure 3 maximum errors: "
            f"s/T^3 = {summary['maximum_entropy_anchor_error']:.6e}; "
            f"chi_2/T^2 = {summary['maximum_susceptibility_anchor_error']:.6e}"
        ),
    ]
    for check in payload["acceptance_checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        value = "" if check.get("value") is None else f"; value = {check['value']:.6e}"
        lines.append(f"{status}: {check['description']}{value}")
    for role, path in execution.artifacts.items():
        lines.append(f"Artifact ({role}): {path}")
    overall = "PASS" if execution.passed else "FAIL"
    lines.extend(
        (
            f"{overall}: all declared numerical reproduction gates",
            "Support level: reproduced; bounded by the recorded scope.",
            payload["scope"],
        )
    )
    return lines


def _dewolfe_gubser_rosen_state(result: Mapping[str, Any]) -> Mapping[str, Any]:
    configuration = result["configuration"]
    return {
        "model_identifier": DEWOLFE_GUBSER_ROSEN_MODEL_CARD.identifier,
        "ensemble": configuration["ensemble"],
        "fixed_variables": {
            "bulk_dimension": configuration["bulk_dimension"],
            "units": configuration["units"],
            "potential": configuration["potential"],
            "gauge_coupling": configuration["gauge_coupling"],
            "scale_dictionary": configuration["scale_dictionary"],
        },
        "approximation": (
            "classical two-derivative phenomenological bottom-up EMD; "
            "neutral background and linear Maxwell response"
        ),
        "phase_branch": "single zero-density black-hole branch",
        "parameters": {
            "degrees": configuration["degrees"],
            "physical_phi_h_targets": configuration["physical_phi_h_targets"],
            "independent_target_phi_h": configuration[
                "independent_target_phi_h"
            ],
            "quadrature_orders": configuration["quadrature_orders"],
        },
        "declared_controls": [],
        "boundary_source_conditions": {
            "scalar": "unit leading UV coefficient in phi = x + ...",
            "metric": "asymptotically AdS with h(0) = 1 and h(1) = 0",
            "gauge": "zero chemical potential with infinitesimal Maxwell response",
        },
        "conventions": {
            "primary_coordinate": "u = x/x_H, x = z^(4-Delta_phi)",
            "result_review_state": result["result_review_state"],
            "phase_5b_boundary": result["contract_review"][
                "phase_5b_amendment"
            ],
        },
        "source_record_versions": {
            "model_card_schema": DEWOLFE_GUBSER_ROSEN_MODEL_CARD.schema_version,
            "model_card_sha256": DEWOLFE_GUBSER_ROSEN_MODEL_CARD.sha256,
            "primary_source_pdf_sha256": result["primary_source"]["pdf_sha256"],
            "primary_source_archive_sha256": result["primary_source"][
                "source_archive_sha256"
            ],
            "source_figure_3_sha256": result["primary_source"][
                "figure_3_sha256"
            ],
        },
    }


DEWOLFE_GUBSER_ROSEN_ADAPTER = BenchmarkAdapter(
    identifier="dewolfe-gubser-rosen-emd",
    description=(
        "Reproduce the zero-density DGR EMD Figure 3 thermodynamic and "
        "susceptibility curves."
    ),
    configure_parser=_configure_dewolfe_gubser_rosen,
    execute=_execute_dewolfe_gubser_rosen,
    render_human=_render_dewolfe_gubser_rosen,
    scientific_state=_dewolfe_gubser_rosen_state,
    model_cards=(DEWOLFE_GUBSER_ROSEN_MODEL_CARD,),
)


__all__ = [
    "DEWOLFE_GUBSER_ROSEN_ADAPTER",
    "DEWOLFE_GUBSER_ROSEN_MODEL_CARD",
]
