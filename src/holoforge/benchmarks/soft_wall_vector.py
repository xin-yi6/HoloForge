"""Quadratic soft-wall transverse-vector spectrum.

The benchmark follows Eqs. (8)-(15) of Karch, Katz, Son, and
Stephanov, Phys. Rev. D 74, 015005 (2006), arXiv:hep-ph/0602229.
After restoring the soft-wall scale ``kappa``, the normal-mode problem is

    -psi'' + (kappa**4 * z**2 + 3 / (4 * z**2)) psi = m**2 psi,

with exact eigenvalues ``m_n**2 = 4 * kappa**2 * (n + 1)``.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.linalg import eig, eigvals, eigvalsh_tridiagonal

from holoforge.core import (
    AcceptanceCheck,
    BackgroundSpec,
    BenchmarkDefinition,
    BoundaryConditionSpec,
    EquationSpec,
    ObservableSpec,
    SolverSpec,
    VerificationRecord,
    runtime_versions,
)
from holoforge.numerics import chebyshev_lobatto_grid


DEFAULT_GRID_POINTS = 1_200
DEFAULT_NUM_MODES = 4
DEFAULT_TOLERANCE = 2.0e-4
DEFAULT_DIMENSIONLESS_Z_MAX = 10.0
DEFAULT_SPECTRAL_DEGREE = 40
DEFAULT_SPECTRAL_CONVERGENCE_TOLERANCE = 1.0e-8
EIGENSOLVER = "scipy.linalg.eigvalsh_tridiagonal"
DISCRETIZATION = "second-order centered finite difference"
SPECTRAL_EIGENSOLVER = "scipy.linalg.eigvals"
SPECTRAL_DISCRETIZATION = "Chebyshev--Gauss--Lobatto pseudospectral collocation"
# Version 2 of the spectral refinement acceptance rule (candidate S-A,
# confirmed in docs/numerics/soft-wall-refinement-sa-confirmation.md).
# Version 1 accepted only strictly decreasing errors.
SPECTRAL_REFINEMENT_RULE = "soft-wall-spectral-refinement-v2"
SPECTRAL_REFINEMENT_CONTRACT = "docs/numerics/soft-wall-refinement-sa-contract.md"
SPECTRAL_PLATEAU_FACTOR = 1.0
SPECTRAL_MATCH_FACTOR = 1.0
MACHINE_EPSILON = float(np.finfo(float).eps)


SOFT_WALL_DEFINITION = BenchmarkDefinition(
    identifier="soft-wall-vector",
    support_level="reproduced",
    background=BackgroundSpec(
        identifier="quadratic-soft-wall-ads5",
        dimension=5,
        coordinate="z in (0, infinity)",
        description=(
            "Fixed AdS_5 background with dilaton Phi(z) = kappa^2 z^2."
        ),
    ),
    equations=(
        EquationSpec(
            identifier="vector-schrodinger",
            kind="Sturm-Liouville eigenvalue problem",
            dependent_fields=("psi_n",),
            expression=(
                "-psi_n'' + (kappa^4 z^2 + 3/(4 z^2)) psi_n "
                "= m_n^2 psi_n"
            ),
            source_reference=(
                "Karch et al., arXiv:hep-ph/0602229v2, Eqs. (8)-(15)"
            ),
        ),
    ),
    boundary_conditions=(
        BoundaryConditionSpec(
            field="psi_n",
            location="z = 0",
            role="UV normalizability",
            expression="psi_n(0) = 0",
            interpretation="Dirichlet approximation to the normalizable UV mode.",
        ),
        BoundaryConditionSpec(
            field="psi_n",
            location="z = z_max",
            role="IR truncation",
            expression="psi_n(z_max) = 0",
            interpretation="Finite-domain approximation to IR normalizability.",
        ),
    ),
    solvers=(
        SolverSpec(
            problem_type="real symmetric tridiagonal eigenproblem",
            library_function=EIGENSOLVER,
            method="LAPACK driver selected by SciPy",
            description=DISCRETIZATION,
        ),
        SolverSpec(
            problem_type="dense collocation eigenproblem",
            library_function=SPECTRAL_EIGENSOLVER,
            method="dense nonsymmetric eigenvalue solve",
            description=SPECTRAL_DISCRETIZATION,
        ),
    ),
    observables=(
        ObservableSpec(
            identifier="vector-mode-masses",
            symbol="m_n^2",
            extraction="Ordered lowest eigenvalues of the discrete operator.",
            normalization="GeV^2 with the input scale kappa expressed in GeV.",
        ),
    ),
)


@dataclass(frozen=True)
class SoftWallConfig:
    """Numerical and physical inputs for the vector-spectrum benchmark.

    Args:
        kappa_gev: Positive soft-wall scale in GeV.
        grid_points: Number of uniformly spaced interior points.
        z_max_gev_inverse: Finite IR boundary in GeV^-1. If omitted, use
            ``10 / kappa``, keeping the dimensionless domain fixed.
    """

    kappa_gev: float = 1.0
    grid_points: int = DEFAULT_GRID_POINTS
    z_max_gev_inverse: Optional[float] = None
    spectral_degree: int = DEFAULT_SPECTRAL_DEGREE

    def __post_init__(self) -> None:
        if not _is_finite_positive_real(self.kappa_gev):
            raise ValueError("kappa_gev must be a finite positive number")
        if isinstance(self.grid_points, bool) or not isinstance(self.grid_points, int):
            raise ValueError("grid_points must be an integer")
        if self.grid_points < 3:
            raise ValueError("grid_points must be at least 3")
        if self.z_max_gev_inverse is not None:
            if not _is_finite_positive_real(self.z_max_gev_inverse):
                raise ValueError(
                    "z_max_gev_inverse must be a finite positive number"
                )
        if isinstance(self.spectral_degree, bool) or not isinstance(
            self.spectral_degree, int
        ):
            raise ValueError("spectral_degree must be an integer")
        if self.spectral_degree < 24:
            raise ValueError("spectral_degree must be at least 24")

    @property
    def resolved_z_max_gev_inverse(self) -> float:
        """Return the explicit IR boundary used by the solver."""

        if self.z_max_gev_inverse is not None:
            return float(self.z_max_gev_inverse)
        return DEFAULT_DIMENSIONLESS_Z_MAX / float(self.kappa_gev)


@dataclass(frozen=True)
class SpectralLevelDiagnostics:
    """Perturbation data for the requested modes at one refinement degree.

    ``eigenvalues`` are the production eigenvalues. ``matched_eigenvalues``
    come from a separate left/right eigenvector solve and are used only to
    estimate each mode's condition number and to check the match.
    """

    degree: int
    eigenvalues: Tuple[float, ...]
    matched_eigenvalues: Tuple[complex, ...]
    condition_numbers: Tuple[float, ...]
    operator_two_norm: float


@dataclass(frozen=True)
class SpectrumResult:
    """Numerical spectrum together with its exact benchmark values."""

    config: SoftWallConfig
    mode_numbers: NDArray[np.int64]
    numerical_mass_squared_gev2: NDArray[np.float64]
    analytic_mass_squared_gev2: NDArray[np.float64]
    relative_errors: NDArray[np.float64]
    grid_spacing_gev_inverse: float
    method: str = "finite-difference"
    spectral_degree: Optional[int] = None
    spectral_refinement_degrees: Tuple[int, ...] = ()
    spectral_refinement_errors: Tuple[float, ...] = ()
    spectral_plateau_diagnostics: Tuple[SpectralLevelDiagnostics, ...] = ()

    @property
    def max_relative_error(self) -> float:
        """Largest relative eigenvalue error among the requested modes."""

        return float(np.max(self.relative_errors))

    @property
    def dimensionless_z_max(self) -> float:
        """Return the scale-free IR boundary ``kappa * z_max``."""

        return float(
            self.config.kappa_gev
            * self.config.resolved_z_max_gev_inverse
        )

    def to_dict(self, tolerance: float) -> Dict[str, Any]:
        """Return a JSON-serializable verification record."""

        records: List[Dict[str, Any]] = []
        for n, numerical, analytic, error in zip(
            self.mode_numbers,
            self.numerical_mass_squared_gev2,
            self.analytic_mass_squared_gev2,
            self.relative_errors,
        ):
            records.append(
                {
                    "n": int(n),
                    "numerical_mass_squared_gev2": float(numerical),
                    "analytic_mass_squared_gev2": float(analytic),
                    "numerical_mass_gev": float(np.sqrt(numerical)),
                    "relative_error": float(error),
                }
            )

        checks = [AcceptanceCheck(
            identifier="exact-spectrum-relative-error",
            description=(
                "Maximum relative error of the requested eigenvalues is within "
                "the declared tolerance."
            ),
            value=self.max_relative_error,
            criterion=f"value <= {float(tolerance):.16g}",
            passed=self.max_relative_error <= tolerance,
        )]
        verdict: Optional[Dict[str, Any]] = None
        if self.method == "spectral":
            verdict = spectral_refinement_verdict(
                self.spectral_refinement_errors,
                self.analytic_mass_squared_gev2,
                self.spectral_plateau_diagnostics,
            )
            checks.append(
                AcceptanceCheck(
                    identifier="spectral-degree-refinement",
                    description=(
                        "The final analytic error is below the declared "
                        "spectral convergence tolerance, and either the error "
                        "decreases across three polynomial degrees or the two "
                        "finest degrees sit within their first-order "
                        f"perturbation scales ({SPECTRAL_REFINEMENT_RULE}; "
                        f"branch: {verdict['branch']})."
                    ),
                    value=float(self.spectral_refinement_errors[-1]),
                    criterion=(
                        f"{SPECTRAL_REFINEMENT_RULE}: value <= "
                        f"{DEFAULT_SPECTRAL_CONVERGENCE_TOLERANCE:.16g} and "
                        "(strictly decreasing across three degrees, or every "
                        "requested mode at the two finest degrees has error and "
                        "eigenvector-solve mismatch <= eps ||H||_2 kappa / "
                        "|lambda| with cross-degree stability)"
                    ),
                    passed=bool(verdict["passed"]),
                )
            )

        configuration: Dict[str, Any] = {
            "kappa_gev": float(self.config.kappa_gev),
            "num_modes": len(self.mode_numbers),
            "z_max_gev_inverse": self.config.resolved_z_max_gev_inverse,
            "dimensionless_z_max": self.dimensionless_z_max,
        }
        if self.method == "spectral":
            configuration["spectral_degree"] = int(self.spectral_degree)
            configuration["maximum_node_spacing_gev_inverse"] = (
                self.grid_spacing_gev_inverse
            )
        else:
            configuration["grid_points"] = self.config.grid_points
            configuration["grid_spacing_gev_inverse"] = (
                self.grid_spacing_gev_inverse
            )

        if self.method == "finite-difference":
            numerical_method: Dict[str, Any] = {
                "discretization": DISCRETIZATION,
                "operator_structure": "real symmetric tridiagonal",
                "eigensolver": EIGENSOLVER,
                "lapack_driver": "auto",
                "boundary_conditions": "psi(0) = psi(z_max) = 0",
            }
        else:
            numerical_method = {
                "route": "spectral",
                "discretization": SPECTRAL_DISCRETIZATION,
                "operator_structure": "dense real collocation operator",
                "eigensolver": SPECTRAL_EIGENSOLVER,
                "boundary_conditions": "psi(0) = psi(z_max) = 0",
                "spectral_convergence_tolerance": (
                    DEFAULT_SPECTRAL_CONVERGENCE_TOLERANCE
                ),
                "refinement_rule": SPECTRAL_REFINEMENT_RULE,
                "refinement_contract": SPECTRAL_REFINEMENT_CONTRACT,
                "conditioning_solver": "scipy.linalg.eig (left and right eigenvectors)",
            }

        extra: Dict[str, Any] = {
            "tolerance": float(tolerance),
            "max_relative_error": self.max_relative_error,
        }
        if self.method == "spectral":
            extra["spectral_convergence"] = {
                "levels": [
                    {
                        "degree": int(degree),
                        "max_relative_error": float(error),
                    }
                    for degree, error in zip(
                        self.spectral_refinement_degrees,
                        self.spectral_refinement_errors,
                    )
                ],
                "improves_at_every_level": bool(
                    np.all(np.diff(self.spectral_refinement_errors) < 0.0)
                ),
                "rule": SPECTRAL_REFINEMENT_RULE,
                "branch": verdict["branch"],
                "plateau_levels": verdict["plateau_levels"],
                "stability_ratios": verdict["stability_ratios"],
            }

        record = VerificationRecord(
            definition=SOFT_WALL_DEFINITION,
            configuration=configuration,
            numerical_method=numerical_method,
            results=records,
            acceptance_checks=tuple(checks),
            software_versions=runtime_versions(),
            scope=(
                "Numerical reproduction of the published mode equation; "
                "not empirical validation of the model."
            ),
            extra=extra,
        )
        return record.to_dict()


def schrodinger_potential(
    z_gev_inverse: ArrayLike, kappa_gev: float
) -> NDArray[np.float64]:
    """Evaluate ``kappa^4 z^2 + 3/(4 z^2)`` in GeV squared."""

    z = np.asarray(z_gev_inverse, dtype=float)
    if not np.all(np.isfinite(z)) or np.any(z <= 0.0):
        raise ValueError("z_gev_inverse must contain only finite positive values")
    if not _is_finite_positive_real(kappa_gev):
        raise ValueError("kappa_gev must be a finite positive number")
    return kappa_gev**4 * z**2 + 3.0 / (4.0 * z**2)


def analytic_mass_squared(
    num_modes: int, kappa_gev: float
) -> NDArray[np.float64]:
    """Return exact ``m_n^2 = 4 kappa^2 (n + 1)`` values in GeV squared."""

    _validate_num_modes(num_modes)
    if not _is_finite_positive_real(kappa_gev):
        raise ValueError("kappa_gev must be a finite positive number")
    n = np.arange(num_modes, dtype=float)
    return 4.0 * kappa_gev**2 * (n + 1.0)


def solve_spectrum(
    config: Optional[SoftWallConfig] = None,
    num_modes: int = DEFAULT_NUM_MODES,
    method: str = "finite-difference",
) -> SpectrumResult:
    """Solve the finite-domain soft-wall eigenvalue problem.

    The protected default is a centered finite difference on ``grid_points``
    interior sites.  The opt-in ``spectral`` route uses Lobatto collocation and
    removes both Dirichlet endpoint rows and columns.
    """

    if config is None:
        config = SoftWallConfig()
    _validate_num_modes(num_modes)
    if num_modes > config.grid_points and method == "finite-difference":
        raise ValueError("num_modes cannot exceed grid_points")

    plateau_diagnostics: Tuple[SpectralLevelDiagnostics, ...] = ()
    if method == "finite-difference":
        numerical, spacing = _finite_difference_spectrum(config, num_modes)
        refinement_degrees: Tuple[int, ...] = ()
        refinement_errors: Tuple[float, ...] = ()
        spectral_degree: Optional[int] = None
    elif method == "spectral":
        if num_modes > config.spectral_degree - 17:
            raise ValueError(
                "num_modes must not exceed spectral_degree - 17 so the "
                "three-level refinement has enough interior modes"
            )
        refinement_degrees = (
            config.spectral_degree - 16,
            config.spectral_degree - 8,
            config.spectral_degree,
        )
        analytic = analytic_mass_squared(num_modes, config.kappa_gev)
        refinement_solutions = tuple(
            _spectral_spectrum(config, num_modes, degree)
            for degree in refinement_degrees
        )
        refinement_values = tuple(
            values for values, _ in refinement_solutions
        )
        refinement_errors = tuple(
            float(np.max(np.abs(values - analytic) / analytic))
            for values in refinement_values
        )
        numerical = refinement_values[-1]
        spacing = refinement_solutions[-1][1]
        spectral_degree = config.spectral_degree
        # Perturbation data for the plateau branch at the two finest degrees.
        # The eigenvalues above are not recomputed or changed.
        plateau_diagnostics = tuple(
            _spectral_level_diagnostics(config, degree, values)
            for degree, values in zip(refinement_degrees[1:], refinement_values[1:])
        )
    else:
        raise ValueError("method must be 'finite-difference' or 'spectral'")

    analytic = analytic_mass_squared(num_modes, config.kappa_gev)
    relative_errors = np.abs(numerical - analytic) / analytic

    return SpectrumResult(
        config=config,
        mode_numbers=np.arange(num_modes, dtype=np.int64),
        numerical_mass_squared_gev2=np.asarray(numerical, dtype=float),
        analytic_mass_squared_gev2=analytic,
        relative_errors=relative_errors,
        grid_spacing_gev_inverse=float(spacing),
        method=method,
        spectral_degree=spectral_degree,
        spectral_refinement_degrees=refinement_degrees,
        spectral_refinement_errors=refinement_errors,
        spectral_plateau_diagnostics=plateau_diagnostics,
    )


def spectral_refinement_verdict(
    maximum_errors: Sequence[float],
    analytic: Sequence[float],
    plateau_levels: Sequence[SpectralLevelDiagnostics],
    accuracy: float = DEFAULT_SPECTRAL_CONVERGENCE_TOLERANCE,
) -> Dict[str, Any]:
    """Evaluate spectral refinement rule version 2 from recorded data.

    Passes when the final maximum analytic error is at most ``accuracy`` and
    either the maximum errors strictly decrease across the three degrees
    (branch ``convergence``, the version 1 rule) or the two finest degrees
    satisfy the plateau conditions (branch ``plateau``). The plateau
    conditions hold for **every requested mode**:

    - all values are finite;
    - the eigenvector-solve eigenvalue matches the production eigenvalue
      within the mode's perturbation scale
      ``s = eps ||H||_2 kappa / |lambda|``;
    - the analytic relative error is at most ``s``;
    - the two finest degrees agree within the sum of their scales.

    ``s`` is a first-order perturbation scale for a simple eigenvalue, not a
    proved error floor. The function performs no eigensolve.
    """

    maxima = [float(value) for value in maximum_errors]
    exact = np.asarray(analytic, dtype=float)
    finite = len(maxima) == 3 and all(math.isfinite(value) for value in maxima)
    convergence = finite and maxima[0] > maxima[1] > maxima[2]
    accurate = finite and maxima[-1] <= accuracy

    levels_evidence: List[Dict[str, Any]] = []
    plateau = finite and len(plateau_levels) == 2
    scales_by_level = []
    for level in plateau_levels:
        values = np.asarray(level.eigenvalues, dtype=float)
        matched = np.asarray(level.matched_eigenvalues, dtype=complex)
        conditions = np.asarray(level.condition_numbers, dtype=float)
        shapes_ok = values.shape == exact.shape == matched.shape == conditions.shape
        with np.errstate(divide="ignore", invalid="ignore"):
            errors = np.abs(values - exact) / exact if shapes_ok else np.array([np.nan])
            scales = (
                MACHINE_EPSILON * level.operator_two_norm * conditions / np.abs(values)
                if shapes_ok else np.array([np.nan])
            )
            mismatch = np.abs(matched - values) / np.abs(values) if shapes_ok else np.array([np.nan])
        level_finite = bool(
            shapes_ok
            and math.isfinite(level.operator_two_norm)
            and np.all(np.isfinite(values))
            and np.all(np.isfinite(errors))
            and np.all(np.isfinite(scales))
            and np.all(np.isfinite(mismatch))
        )
        matched_ok = level_finite and bool(np.all(mismatch <= SPECTRAL_MATCH_FACTOR * scales))
        plateau_ok = level_finite and bool(np.all(errors <= SPECTRAL_PLATEAU_FACTOR * scales))
        plateau = plateau and level_finite and matched_ok and plateau_ok
        scales_by_level.append(scales)
        levels_evidence.append({
            "degree": int(level.degree),
            "relative_errors": _finite_list(errors) if shapes_ok else [],
            "perturbation_scales": _finite_list(scales) if shapes_ok else [],
            "condition_numbers": _finite_list(conditions),
            "eigenvector_solve_mismatch": _finite_list(mismatch) if shapes_ok else [],
            "operator_two_norm": _finite_list([level.operator_two_norm])[0],
            "finite": level_finite,
            "matched": matched_ok,
            "within_scale": plateau_ok,
        })

    stability: List[float] = []
    if plateau:
        middle, fine = plateau_levels
        fine_values = np.asarray(fine.eigenvalues, dtype=float)
        middle_values = np.asarray(middle.eigenvalues, dtype=float)
        allowed = scales_by_level[0] + scales_by_level[1]
        ratios = np.abs(fine_values - middle_values) / np.abs(fine_values) / allowed
        stability = _finite_list(ratios)
        plateau = bool(np.all(np.isfinite(ratios)) and np.all(ratios <= 1.0))

    passed = bool(accurate and (convergence or plateau))
    if not passed:
        branch = "none"
    elif convergence:
        branch = "convergence"
    else:
        branch = "plateau"
    return {
        "passed": passed,
        "branch": branch,
        "convergence": bool(convergence),
        "plateau": bool(plateau),
        "accuracy": bool(accurate),
        "plateau_levels": levels_evidence,
        "stability_ratios": stability,
    }


def _finite_list(values: Any) -> List[Optional[float]]:
    """Return floats for JSON evidence, with non-finite entries as ``None``."""

    return [
        float(value) if math.isfinite(float(value)) else None
        for value in np.ravel(np.asarray(values, dtype=float))
    ]


def _spectral_level_diagnostics(
    config: SoftWallConfig, degree: int, eigenvalues: NDArray[np.float64]
) -> SpectralLevelDiagnostics:
    """Condition numbers of the given production eigenvalues at one degree."""

    grid = chebyshev_lobatto_grid(degree, 0.0, config.resolved_z_max_gev_inverse)
    interior = slice(1, -1)
    operator = -grid.second_derivative[interior, interior] + np.diag(
        schrodinger_potential(grid.nodes[interior], config.kappa_gev)
    )
    values, left, right = eig(operator, left=True, right=True, check_finite=True)
    matched: List[complex] = []
    conditions: List[float] = []
    for target in np.asarray(eigenvalues, dtype=float):
        index = int(np.argmin(np.abs(values - target)))
        x, y = right[:, index], left[:, index]
        overlap = abs(np.vdot(y, x))
        conditions.append(
            float(np.linalg.norm(x) * np.linalg.norm(y) / overlap) if overlap > 0.0 else math.inf
        )
        matched.append(complex(values[index]))
    return SpectralLevelDiagnostics(
        degree=int(degree),
        eigenvalues=tuple(float(value) for value in eigenvalues),
        matched_eigenvalues=tuple(matched),
        condition_numbers=tuple(conditions),
        operator_two_norm=float(np.linalg.norm(operator, 2)),
    )


def _finite_difference_spectrum(
    config: SoftWallConfig, num_modes: int
) -> Tuple[NDArray[np.float64], float]:
    """Return the protected finite-difference result and uniform spacing."""

    z_max = config.resolved_z_max_gev_inverse
    spacing = z_max / (config.grid_points + 1)
    z = spacing * np.arange(1, config.grid_points + 1, dtype=float)

    inverse_spacing_squared = 1.0 / spacing**2
    diagonal = (
        2.0 * inverse_spacing_squared
        + schrodinger_potential(z, config.kappa_gev)
    )
    off_diagonal = np.full(
        config.grid_points - 1, -inverse_spacing_squared, dtype=float
    )

    numerical = eigvalsh_tridiagonal(
        diagonal,
        off_diagonal,
        select="i",
        select_range=(0, num_modes - 1),
        check_finite=True,
    )
    return np.asarray(numerical, dtype=float), float(spacing)


def _spectral_spectrum(
    config: SoftWallConfig, num_modes: int, degree: int
) -> Tuple[NDArray[np.float64], float]:
    """Return a finite-domain Lobatto-collocation spectrum."""

    grid = chebyshev_lobatto_grid(
        degree, 0.0, config.resolved_z_max_gev_inverse
    )
    interior = slice(1, -1)
    nodes = grid.nodes[interior]
    operator = (
        -grid.second_derivative[interior, interior]
        + np.diag(schrodinger_potential(nodes, config.kappa_gev))
    )
    eigenvalues = eigvals(operator, check_finite=True)
    real = eigenvalues.real
    admissible = (
        np.isfinite(real)
        & np.isfinite(eigenvalues.imag)
        & (real > 0.0)
        & (np.abs(eigenvalues.imag) <= 1.0e-8 * np.maximum(real, 1.0))
    )
    ordered = np.sort(real[admissible])
    if len(ordered) < num_modes:
        raise RuntimeError(
            "spectral eigensolver returned too few finite positive real modes"
        )
    return (
        np.asarray(ordered[:num_modes], dtype=float),
        grid.maximum_spacing,
    )


def _validate_num_modes(num_modes: int) -> None:
    if isinstance(num_modes, bool) or not isinstance(num_modes, int):
        raise ValueError("num_modes must be an integer")
    if num_modes < 1:
        raise ValueError("num_modes must be at least 1")


def _is_finite_positive_real(value: object) -> bool:
    return (
        isinstance(value, Real)
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) > 0.0
    )
