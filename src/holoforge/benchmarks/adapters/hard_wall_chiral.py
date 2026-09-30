"""Command adapter for the hard-wall chiral Model A benchmark."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from holoforge.benchmarks.hard_wall_chiral import (
    save_hard_wall_chiral_artifacts,
    verify_hard_wall_chiral,
)
from holoforge.core.registry import (
    BenchmarkAdapter,
    BenchmarkExecution,
    BenchmarkExecutionError,
    ModelCardReference,
)


HARD_WALL_CHIRAL_MODEL_CARD = ModelCardReference(
    identifier="qcd.hard-wall-chiral.ekss-model-a",
    schema_version="0.1",
    repository_path="domains/qcd/hard_wall_chiral/model-card.json",
    sha256="9deaa54d3a474543b67aa2c68fbd4a52f5736b13ae354c0fcb4fdad5b7eefe88",
)


def _configure_hard_wall_chiral(parser: Any) -> None:
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        metavar="PATH",
        help="Save the strict JSON, combined evidence CSV, and verification plot.",
    )


def _execute_hard_wall_chiral(args: Any) -> BenchmarkExecution:
    try:
        result = verify_hard_wall_chiral()
        artifacts = {}
        if args.output_dir is not None:
            artifacts = save_hard_wall_chiral_artifacts(result, args.output_dir)
    except (OSError, RuntimeError, ValueError) as exc:
        raise BenchmarkExecutionError(str(exc)) from exc
    return BenchmarkExecution(
        payload=result.to_dict(), passed=result.passed, artifacts=artifacts
    )


def _render_hard_wall_chiral(execution: BenchmarkExecution) -> Sequence[str]:
    payload = execution.payload
    lines = [
        "Hard-wall chiral Model A benchmark",
        "observable             HoloForge       source       relative error   role",
    ]
    for row in payload["results"]["table"]:
        lines.append(
            f"{row['observable']:21s} {row['computed']:12.6f} "
            f"{row['target']:12.6f} {row['relative_error']:16.6e}   "
            f"{row['source_role']}"
        )
    for check in payload["acceptance_checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        value = "" if "value" not in check else f"; value = {check['value']:.6e}"
        lines.append(f"{status}: {check['description']}{value}")
    for role, path in execution.artifacts.items():
        lines.append(f"Artifact ({role}): {path}")
    overall = "PASS" if execution.passed else "FAIL"
    lines.extend(
        (
            f"{overall}: all declared acceptance gates",
            "Review state: owner-approved by Xin-Yi Liu on 2026-08-20; "
            "passing remains bounded by the recorded scope.",
            payload["scope"],
        )
    )
    return lines


def _hard_wall_chiral_state(result: Mapping[str, Any]) -> Mapping[str, Any]:
    configuration = result["configuration"]
    return {
        "model_identifier": HARD_WALL_CHIRAL_MODEL_CARD.identifier,
        "ensemble": "two-flavor zero-temperature zero-density vacuum spectrum",
        "fixed_variables": {
            "background": "fixed AdS5 slice with a phenomenological IR wall",
            "flavor_symmetry": "SU(2)_L x SU(2)_R",
            "source_model": "Erlich-Katz-Son-Stephanov Model A",
        },
        "approximation": "classical truncated bottom-up hard-wall effective model",
        "phase_branch": "lowest normalizable rho, transverse-a1, and pion modes",
        "parameters": {
            "z_m_inverse_MeV": configuration["z_m_inverse_MeV"],
            "m_q_MeV": configuration["m_q_MeV"],
            "sigma_cube_root_MeV": configuration["sigma_cube_root_MeV"],
            "g5": configuration["g5"],
        },
        "declared_controls": [],
        "boundary_source_conditions": {
            "normalizable_uv": "quadratic UV factors with exact endpoint",
            "hard_wall_ir": "Neumann conditions at u=1",
            "axial_zero_uv": "explicit public-source regulator",
        },
        "conventions": {
            "coordinate": "u=z/z_m",
            "units": "masses and decay constants in MeV",
            "fit_performed": False,
        },
        "source_record_versions": {
            "model_card_schema": HARD_WALL_CHIRAL_MODEL_CARD.schema_version,
            "model_card_sha256": HARD_WALL_CHIRAL_MODEL_CARD.sha256,
            "primary_source_pdf_sha256": result["primary_source"]["pdf_sha256"],
            "primary_source_archive_sha256": result["primary_source"]["source_archive_sha256"],
        },
    }


HARD_WALL_CHIRAL_ADAPTER = BenchmarkAdapter(
    identifier="hard-wall-chiral",
    description="Reproduce all seven hard-wall chiral Model A entries and GMOR.",
    configure_parser=_configure_hard_wall_chiral,
    execute=_execute_hard_wall_chiral,
    render_human=_render_hard_wall_chiral,
    scientific_state=_hard_wall_chiral_state,
    model_cards=(HARD_WALL_CHIRAL_MODEL_CARD,),
)


__all__ = ["HARD_WALL_CHIRAL_ADAPTER", "HARD_WALL_CHIRAL_MODEL_CARD"]
