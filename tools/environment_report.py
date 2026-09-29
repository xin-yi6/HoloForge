"""Read-only report of the local HoloForge numerical and test environment.

Use it when a verifier or test behaves differently on another machine. It
reports the provenance fields recorded in verification records plus the
test dependencies, installed-package metadata, and BLAS threading variables
of the current interpreter. It installs, repairs, and uploads nothing, and it
prints no filesystem paths.

Usage:  python tools/environment_report.py
"""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import os
import sys
from typing import Any, Dict, List, Mapping, Optional


REPORT_VERSION = "1"
TEST_EXTRAS = ("jsonschema", "rfc3339_validator", "matplotlib")
THREAD_VARIABLES = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
)


def build_report(environment: Optional[Mapping[str, str]] = None) -> Dict[str, Any]:
    """Return the environment report as a JSON-serializable mapping."""

    from holoforge.core.provenance import runtime_versions

    if environment is None:
        environment = os.environ
    runtime = runtime_versions()
    installed = _installed_distribution_version("holoforge")
    extras = {name: _module_available(name) for name in TEST_EXTRAS}
    report: Dict[str, Any] = {
        "report": "holoforge-environment",
        "report_version": REPORT_VERSION,
        "runtime": runtime,
        "installed_distribution_version": installed or "not-installed",
        "installed_metadata_matches_source": (
            None if installed is None else installed == runtime["holoforge"]
        ),
        "test_extras_available": extras,
        "thread_environment": _thread_environment(environment),
    }
    report["warnings"] = _warnings(runtime, installed, extras)
    return report


def _installed_distribution_version(name: str) -> Optional[str]:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _thread_environment(environment: Mapping[str, str]) -> Dict[str, str]:
    """Report BLAS/OpenMP thread variables; non-numeric values are masked."""

    result = {}
    for name in THREAD_VARIABLES:
        value = environment.get(name)
        if value is None:
            continue
        stripped = value.strip()
        result[name] = stripped if stripped.isdigit() else "set"
    return result


def _warnings(
    runtime: Mapping[str, str],
    installed: Optional[str],
    extras: Mapping[str, bool],
) -> List[str]:
    warnings = []
    if installed is not None and installed != runtime["holoforge"]:
        warnings.append(
            f"installed holoforge metadata reports {installed}, but the imported "
            f"source is {runtime['holoforge']}; the installation is stale. "
            "Create a fresh environment rather than trusting the metadata."
        )
    missing = [name for name, available in extras.items() if not available]
    if missing:
        warnings.append(
            "missing test dependencies: " + ", ".join(missing)
            + "; the full test suite will report failures. Install the "
            "'test' extra in an isolated environment."
        )
    if runtime.get("holoforge_git_src_modified") == "true":
        warnings.append(
            "src/ differs from commit "
            f"{runtime.get('holoforge_git_commit', 'unknown')[:12]}; results "
            "come from uncommitted source."
        )
    return warnings


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.parse_args(argv)
    try:
        report = build_report()
    except ImportError as exc:
        # The message of an ImportError can contain paths; report the module only.
        print(
            json.dumps(
                {
                    "report": "holoforge-environment",
                    "error": "import failed",
                    "module": exc.name or "unknown",
                }
            ),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
