"""Runtime provenance helpers."""

from __future__ import annotations

from contextlib import redirect_stdout
from functools import lru_cache
import hashlib
import io
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple
import warnings

import numpy as np
import scipy

from holoforge import __version__
from holoforge.numerics.chebyshev import CHEBYSHEV_CONSTRUCTION


UNKNOWN = "unknown"
_PACKAGE_DIRECTORY = Path(__file__).resolve().parents[1]
_SOURCE_SUFFIXES = (".py", ".json")
_COMMIT = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")
_GIT_TIMEOUT_SECONDS = 10.0


def runtime_versions() -> Dict[str, str]:
    """Return privacy-safe runtime and numerical-build provenance.

    Besides interpreter and library versions, the record fingerprints the
    HoloForge package as it is on disk when the record is made, gives the Git
    commit when the package runs from a HoloForge checkout, and reports the
    BLAS/LAPACK backends of NumPy and SciPy, the ``long double`` machine
    epsilon and the identifier of the shared Chebyshev matrix construction.
    The source fingerprint and Git state are recomputed on every
    call, so a long-lived interpreter does not report a stale snapshot.  They
    describe files on disk, not which bytes an already running interpreter
    imported earlier.  Unavailable facts are recorded as ``"unknown"`` rather
    than guessed.  No field contains a filesystem path.
    """

    versions = {
        "holoforge": __version__,
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "byteorder": sys.byteorder,
        "platform_system": platform.system() or UNKNOWN,
        "platform_machine": platform.machine() or UNKNOWN,
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "numerical_build_sha256": _numerical_build_digest(),
        "longdouble_epsilon": repr(float(np.finfo(np.longdouble).eps)),
        "chebyshev_construction": CHEBYSHEV_CONSTRUCTION,
    }
    versions.update(_numerical_backends())
    versions.update(_source_identity())
    return versions


@lru_cache(maxsize=1)
def _numerical_build_digest() -> str:
    """Hash NumPy/SciPy build reports without exposing their local paths."""

    sections = []
    for label, show in (
        ("numpy", np.__config__.show),
        ("scipy", scipy.__config__.show),
    ):
        buffer = io.StringIO()
        with warnings.catch_warnings(), redirect_stdout(buffer):
            warnings.simplefilter("ignore")
            show()
        sections.append(f"[{label}]\n{buffer.getvalue().strip()}\n")
    return hashlib.sha256("".join(sections).encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def _numerical_backends() -> Tuple[Tuple[str, str], ...]:
    """Return readable BLAS/LAPACK names for NumPy and SciPy."""

    fields: Dict[str, str] = {}
    for label, show in (
        ("numpy", np.__config__.show),
        ("scipy", scipy.__config__.show),
    ):
        fields.update(backend_fields(label, _structured_build_report(show)))
    return tuple(fields.items())


def _structured_build_report(show: Callable[..., Any]) -> Any:
    """Return a structured build report, or ``None`` for older builds."""

    try:
        with warnings.catch_warnings(), redirect_stdout(io.StringIO()):
            warnings.simplefilter("ignore")
            return show(mode="dicts")
    except (TypeError, ValueError):
        return None


def backend_fields(label: str, report: Any) -> Dict[str, str]:
    """Extract allowlisted BLAS and LAPACK labels from a build report.

    Only each library's name and version are read.  Directories, compiler
    arguments, and other build details never enter the result.
    """

    dependencies = (
        report.get("Build Dependencies") if isinstance(report, Mapping) else None
    )
    fields = {}
    for library in ("blas", "lapack"):
        entry = (
            dependencies.get(library) if isinstance(dependencies, Mapping) else None
        )
        fields[f"{label}_{library}"] = _library_label(entry)
    return fields


def _library_label(entry: Any) -> str:
    if not isinstance(entry, Mapping):
        return UNKNOWN
    name = _safe_token(entry.get("name"))
    if name == UNKNOWN:
        return UNKNOWN
    version = _safe_token(entry.get("version"))
    return name if version == UNKNOWN else f"{name} {version}"


def _safe_token(value: Any) -> str:
    if not isinstance(value, str):
        return UNKNOWN
    token = value.strip().lower()
    if (
        not token
        or token == UNKNOWN
        or any(character in token for character in "/\\~:")
        or any(character.isspace() for character in token)
    ):
        return UNKNOWN
    return token


def _source_identity() -> Tuple[Tuple[str, str], ...]:
    """Fingerprint the on-disk package and its checkout state, uncached."""

    commit, modified = git_source_state(_PACKAGE_DIRECTORY)
    return (
        ("holoforge_source_sha256", package_source_digest(_PACKAGE_DIRECTORY)),
        ("holoforge_git_commit", commit),
        ("holoforge_git_src_modified", modified),
    )


def package_source_files(package_directory: Path) -> List[str]:
    """Return the sorted package-relative paths covered by the source digest.

    These are the ``.py`` sources and bundled ``.json`` data; bytecode caches
    and every other file type are excluded.
    """

    return sorted(
        path.relative_to(package_directory).as_posix()
        for path in package_directory.rglob("*")
        if path.suffix in _SOURCE_SUFFIXES
        and path.is_file()
        and "__pycache__" not in path.relative_to(package_directory).parts
    )


def package_source_digest(package_directory: Path) -> str:
    """Hash Python sources and bundled JSON data by package-relative path.

    This fingerprints the package files as they are on disk now. Identical
    files give the same digest from a checkout, a source distribution, or a
    wheel.  It cannot prove which bytes an already running interpreter
    imported, because modules loaded before a file changed stay in memory.
    """

    try:
        files = package_source_files(package_directory)
        if not files:
            return UNKNOWN
        digest = hashlib.sha256()
        for relative in files:
            content = (package_directory / relative).read_bytes()
            digest.update(relative.encode("utf-8") + b"\0")
            digest.update(hashlib.sha256(content).hexdigest().encode("ascii") + b"\n")
    except OSError:
        return UNKNOWN
    return digest.hexdigest()


def git_source_state(package_directory: Path) -> Tuple[str, str]:
    """Return the checkout commit and whether ``src/`` differs from it.

    Only a Git checkout whose top level tracks this package as
    ``src/holoforge`` qualifies.  An installed copy inside some other
    repository therefore reports ``"unknown"`` instead of that repository's
    commit.  The modification flag covers tracked and untracked changes under
    ``src/``, the code and data that determine numerical results.
    """

    unknown = (UNKNOWN, UNKNOWN)
    source_root = package_directory.parent
    if package_directory.name != "holoforge" or source_root.name != "src":
        return unknown
    checkout = source_root.parent
    toplevel = _run_git(checkout, "rev-parse", "--show-toplevel")
    if toplevel is None or Path(toplevel).resolve() != checkout.resolve():
        return unknown
    tracked = _run_git(
        checkout, "ls-files", "--error-unmatch", "src/holoforge/__init__.py"
    )
    if tracked is None:
        return unknown
    # One status query reports both the HEAD commit and any change under src/.
    status = _run_git(checkout, "status", "--porcelain=v2", "--branch", "--", "src")
    if status is None:
        return unknown
    commit = UNKNOWN
    modified = False
    for line in status.splitlines():
        if line.startswith("# branch.oid "):
            candidate = line[len("# branch.oid "):].strip()
            commit = candidate if _COMMIT.fullmatch(candidate) else UNKNOWN
        elif line and not line.startswith("#"):
            modified = True
    if commit == UNKNOWN:
        return unknown
    return commit, "true" if modified else "false"


def _run_git(checkout: Path, *arguments: str) -> Optional[str]:
    """Run one read-only Git query, returning ``None`` on any failure."""

    environment = dict(os.environ)
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        completed = subprocess.run(
            ("git", "-c", "core.fsmonitor=false", "-C", str(checkout), *arguments),
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
            env=environment,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()
