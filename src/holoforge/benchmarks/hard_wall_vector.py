"""Hard-wall transverse-vector spectrum in bottom-up AdS/QCD.

The benchmark follows Eq. (5) and the vector-mode discussion in Erlich, Katz,
Son, and Stephanov, Phys. Rev. Lett. 95, 261602 (2005),
arXiv:hep-ph/0501128.  With ``x = z / z_m`` and
``lambda = m z_m``, the dimensionless equation is

    V''(x) - V'(x) / x + lambda**2 V(x) = 0,

with a UV Dirichlet condition at a finite cutoff and an IR Neumann condition.
As the cutoff vanishes, ``lambda_n`` approaches the zeros of ``J_0``.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from functools import partial
import math
from numbers import Integral, Real
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import solve_bvp, solve_ivp
from scipy.linalg import eigvals
from scipy.optimize import root_scalar
from scipy.special import j0, j1, jn_zeros

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


DEFAULT_NUM_MODES = 4
DEFAULT_RATIO_TOLERANCE = 5.0e-4
DEFAULT_CROSS_SOLVER_TOLERANCE = 1.0e-3
DEFAULT_REFINEMENT_CUTOFFS = (1.0e-2, 3.0e-3, 1.0e-3)
DEFAULT_SPECTRAL_DEGREE = 40
DEFAULT_SPECTRAL_CONVERGENCE_TOLERANCE = 1.0e-8
SHOOTING_SOLVER = "scipy.integrate.solve_ivp + scipy.optimize.root_scalar"
COLLOCATION_SOLVER = "scipy.integrate.solve_bvp"
SPECTRAL_SOLVER = "scipy.linalg.eigvals"


RUST_SHOOTING_SPEC = SolverSpec(
    problem_type="ODE shooting eigenvalue problem",
    library_function="ivp::methods::DOP853 + scipy.optimize.root_scalar",
    method="Rust DOP853 integration with Brent root finding",
    description="Alternative implementation of the same IR Neumann shooting residual.",
)


HARD_WALL_DEFINITION = BenchmarkDefinition(
    identifier="hard-wall-vector",
    support_level="reproduced",
    background=BackgroundSpec(
        identifier="hard-wall-ads5",
        dimension=5,
        coordinate="z in [epsilon, z_m]",
        description="Fixed AdS_5 slice with a phenomenological IR wall.",
    ),
    equations=(
        EquationSpec(
            identifier="transverse-vector",
            kind="Sturm-Liouville eigenvalue problem",
            dependent_fields=("V_n",),
            expression="partial_z[(1/z) partial_z V_n] + (m_n^2/z) V_n = 0",
            source_reference="Erlich et al., arXiv:hep-ph/0501128v2, Eq. (5)",
        ),
    ),
    boundary_conditions=(
        BoundaryConditionSpec(
            field="V_n",
            location="z = epsilon",
            role="UV normalizability",
            expression="V_n(epsilon) = 0",
            interpretation=(
                "Finite-cutoff Dirichlet approximation to the normalizable mode."
            ),
        ),
        BoundaryConditionSpec(
            field="V_n",
            location="z = z_m",
            role="IR wall",
            expression="partial_z V_n(z_m) = 0",
            interpretation=(
                "Phenomenological Neumann condition used in the source model."
            ),
        ),
    ),
    solvers=(
        SolverSpec(
            problem_type="ODE shooting eigenvalue problem",
            library_function=SHOOTING_SOLVER,
            method="DOP853 integration with Brent root finding",
            description="Adaptive initial-value integration and IR residual root.",
        ),
        SolverSpec(
            problem_type="parameterized boundary-value eigenproblem",
            library_function=COLLOCATION_SOLVER,
            method="fourth-order residual-controlled collocation",
            description=(
                "Global adaptive mesh with the eigenvalue as an unknown parameter."
            ),
        ),
        SolverSpec(
            problem_type="generalized collocation eigenproblem",
            library_function=SPECTRAL_SOLVER,
            method="Chebyshev--Gauss--Lobatto pseudospectral collocation",
            description=(
                "Dense generalized eigenproblem with explicit Dirichlet and "
                "Neumann boundary rows."
            ),
        ),
    ),
    observables=(
        ObservableSpec(
            identifier="vector-mode-mass-ratios",
            symbol="R_n = m_n / m_0",
            extraction="Ordered eigenvalues normalized to the lowest mode.",
            normalization="Dimensionless; the hard-wall scale z_m cancels.",
        ),
    ),
)


@dataclass(frozen=True)
class HardWallConfig:
    """Physical and numerical settings for the hard-wall spectrum."""

    z_m_gev_inverse: float = 1.0
    epsilon_fraction: float = 1.0e-4
    integration_rtol: float = 1.0e-9
    integration_atol: float = 1.0e-11
    root_rtol: float = 1.0e-10
    collocation_mesh_points: int = 160
    collocation_tolerance: float = 1.0e-7
    collocation_max_nodes: int = 10_000
    spectral_degree: int = DEFAULT_SPECTRAL_DEGREE

    def __post_init__(self) -> None:
        _require_finite_positive(self.z_m_gev_inverse, "z_m_gev_inverse")
        _require_fraction(self.epsilon_fraction, "epsilon_fraction")
        _require_finite_positive(self.integration_rtol, "integration_rtol")
        _require_finite_positive(self.integration_atol, "integration_atol")
        _require_finite_positive(self.root_rtol, "root_rtol")
        _require_integer_at_least(
            self.collocation_mesh_points, 20, "collocation_mesh_points"
        )
        _require_finite_positive(
            self.collocation_tolerance, "collocation_tolerance"
        )
        _require_integer_at_least(
            self.collocation_max_nodes,
            self.collocation_mesh_points,
            "collocation_max_nodes",
        )
        _require_integer_at_least(
            self.spectral_degree, 24, "spectral_degree"
        )


@dataclass(frozen=True)
class HardWallSpectrumResult:
    """One numerical spectrum and its zero-cutoff analytic reference."""

    config: HardWallConfig
    method: str
    dimensionless_masses: NDArray[np.float64]
    analytic_dimensionless_masses: NDArray[np.float64]
    masses_gev: NDArray[np.float64]
    mass_ratios: NDArray[np.float64]
    analytic_mass_ratios: NDArray[np.float64]
    ratio_relative_errors: NDArray[np.float64]
    spectral_refinement_degrees: Tuple[int, ...] = ()
    spectral_refinement_differences: Tuple[float, ...] = ()
    native_version: Optional[str] = None

    @property
    def max_ratio_relative_error(self) -> float:
        """Largest relative ratio error, excluding the calibrated anchor."""

        if len(self.ratio_relative_errors) <= 1:
            return 0.0
        return float(np.max(self.ratio_relative_errors[1:]))

    def to_dict(
        self, tolerance: float = DEFAULT_RATIO_TOLERANCE
    ) -> Dict[str, Any]:
        """Return a provenance-rich, JSON-serializable verification record."""

        _require_finite_positive(tolerance, "tolerance")
        records: List[Dict[str, Any]] = []
        for index, values in enumerate(
            zip(
                self.dimensionless_masses,
                self.analytic_dimensionless_masses,
                self.masses_gev,
                self.mass_ratios,
                self.analytic_mass_ratios,
                self.ratio_relative_errors,
            )
        ):
            numerical_lambda, analytic_lambda, mass, ratio, exact_ratio, error = values
            records.append(
                {
                    "n": index,
                    "numerical_m_z_m": float(numerical_lambda),
                    "analytic_m_z_m": float(analytic_lambda),
                    "numerical_mass_gev": float(mass),
                    "numerical_ratio": float(ratio),
                    "analytic_ratio": float(exact_ratio),
                    "ratio_relative_error": float(error),
                }
            )

        checks = [AcceptanceCheck(
            identifier="analytic-ratio-relative-error",
            description=(
                "Maximum relative error of excited-state ratios against the "
                "zero-cutoff Bessel reference is within tolerance."
            ),
            value=self.max_ratio_relative_error,
            criterion=f"value <= {float(tolerance):.16g}",
            passed=self.max_ratio_relative_error <= tolerance,
        )]
        if self.method == "spectral":
            refinement_improves = bool(
                len(self.spectral_refinement_differences) >= 2
                and self.spectral_refinement_differences[-1]
                < self.spectral_refinement_differences[0]
            )
            refinement_passed = bool(
                refinement_improves
                and self.spectral_refinement_differences[-1]
                <= DEFAULT_SPECTRAL_CONVERGENCE_TOLERANCE
            )
            checks.append(
                AcceptanceCheck(
                    identifier="spectral-degree-refinement",
                    description=(
                        "Successive spectral spectra stabilize as the "
                        "polynomial degree increases."
                    ),
                    value=float(self.spectral_refinement_differences[-1]),
                    criterion=(
                        "final relative change is smaller than the preceding "
                        "change and value <= "
                        f"{DEFAULT_SPECTRAL_CONVERGENCE_TOLERANCE:.16g}"
                    ),
                    passed=refinement_passed,
                )
            )

        configuration: Dict[str, Any] = {
            "z_m_gev_inverse": float(self.config.z_m_gev_inverse),
            "epsilon_fraction": float(self.config.epsilon_fraction),
            "num_modes": len(self.dimensionless_masses),
        }
        if self.method == "spectral":
            configuration["spectral_degree"] = self.config.spectral_degree

        numerical_method: Dict[str, Any] = {
            "route": self.method,
            "uv_boundary_condition": "V(epsilon) = 0",
            "ir_boundary_condition": "partial_z V(z_m) = 0",
            "finite_cutoff_is_separate_from_solver_tolerance": True,
        }
        if self.method == "spectral":
            numerical_method.update(
                {
                    "discretization": (
                        "Chebyshev--Gauss--Lobatto pseudospectral collocation"
                    ),
                    "eigensolver": SPECTRAL_SOLVER,
                    "operator_structure": "dense generalized eigenproblem",
                    "spectral_convergence_tolerance": (
                        DEFAULT_SPECTRAL_CONVERGENCE_TOLERANCE
                    ),
                }
            )

        extra: Dict[str, Any] = {
            "tolerance": float(tolerance),
            "max_ratio_relative_error": self.max_ratio_relative_error,
        }
        if self.method == "spectral":
            extra["spectral_convergence"] = {
                "degrees": [
                    int(degree) for degree in self.spectral_refinement_degrees
                ],
                "successive_max_relative_differences": [
                    float(value)
                    for value in self.spectral_refinement_differences
                ],
                "final_difference_below_tolerance": bool(
                    self.spectral_refinement_differences[-1]
                    <= DEFAULT_SPECTRAL_CONVERGENCE_TOLERANCE
                ),
            }

        definition = HARD_WALL_DEFINITION
        versions = runtime_versions()
        if self.native_version is not None:
            definition = replace(definition, solvers=(*definition.solvers, RUST_SHOOTING_SPEC))
            versions["holoforge-native"] = self.native_version
            configuration.update(
                integration_rtol=float(self.config.integration_rtol),
                integration_atol=float(self.config.integration_atol),
                root_rtol=float(self.config.root_rtol),
            )
            numerical_method.update(
                integrator="ivp::methods::DOP853",
                root_finder="scipy.optimize.root_scalar (brentq)",
            )

        record = VerificationRecord(
            definition=definition,
            configuration=configuration,
            numerical_method=numerical_method,
            results=records,
            acceptance_checks=tuple(checks),
            software_versions=versions,
            scope=(
                "Numerical reproduction of the published hard-wall vector-mode "
                "equation; not precision validation of the model."
            ),
            extra=extra,
        )
        return record.to_dict()


@dataclass(frozen=True)
class HardWallRefinementResult:
    """Three-or-more-level study of the finite UV cutoff."""

    results: Tuple[HardWallSpectrumResult, ...]

    @property
    def cutoff_fractions(self) -> NDArray[np.float64]:
        return np.asarray(
            [result.config.epsilon_fraction for result in self.results],
            dtype=float,
        )

    @property
    def max_ratio_relative_errors(self) -> NDArray[np.float64]:
        return np.asarray(
            [result.max_ratio_relative_error for result in self.results],
            dtype=float,
        )

    @property
    def improves_at_every_level(self) -> bool:
        """Whether every smaller cutoff reduces the maximum ratio error."""

        return bool(np.all(np.diff(self.max_ratio_relative_errors) < 0.0))

    def to_dict(self) -> Dict[str, Any]:
        """Return the cutoff and error sequence without conflating tolerances."""

        return {
            "method": self.results[0].method,
            "levels": [
                {
                    "epsilon_fraction": float(result.config.epsilon_fraction),
                    "max_ratio_relative_error": result.max_ratio_relative_error,
                    "mass_ratios": result.mass_ratios.tolist(),
                }
                for result in self.results
            ],
            "improves_at_every_level": self.improves_at_every_level,
            "interpretation": (
                "This sequence estimates finite-cutoff effects; integration, "
                "root, and collocation tolerances remain separate settings."
            ),
        }


def analytic_dimensionless_masses(num_modes: int) -> NDArray[np.float64]:
    """Return the first ``num_modes`` positive zeros of ``J_0``."""

    _validate_num_modes(num_modes)
    return np.asarray(jn_zeros(0, num_modes), dtype=float)


def solve_hard_wall_spectrum(
    config: Optional[HardWallConfig] = None,
    num_modes: int = DEFAULT_NUM_MODES,
    method: str = "shooting",
) -> HardWallSpectrumResult:
    """Solve by SciPy or Rust shooting, adaptive collocation, or spectral collocation."""

    if config is None:
        config = HardWallConfig()
    _validate_num_modes(num_modes)

    refinement_degrees: Tuple[int, ...] = ()
    refinement_differences: Tuple[float, ...] = ()
    native_version = None
    if method in ("shooting", "shooting-rust"):
        if method == "shooting-rust":
            try:
                from holoforge_native import __version__, hard_wall_residual
            except ImportError as exc:
                raise RuntimeError(
                    "shooting-rust requires the optional holoforge-native extension. "
                    "Install it from the HoloForge checkout with 'python -m pip install ./native'."
                ) from exc
            residual = partial(
                hard_wall_residual, epsilon=float(config.epsilon_fraction),
                rtol=float(config.integration_rtol), atol=float(config.integration_atol),
            )
            native_version = __version__
        else:
            residual = partial(_shooting_ir_residual, config=config)
        numerical = _shooting_dimensionless_masses(config, num_modes, residual)
    elif method == "collocation":
        numerical = _collocation_dimensionless_masses(config, num_modes)
    elif method == "spectral":
        if num_modes > config.spectral_degree - 17:
            raise ValueError(
                "num_modes must not exceed spectral_degree - 17 so the "
                "three-level refinement has enough finite modes"
            )
        refinement_degrees = (
            config.spectral_degree - 16,
            config.spectral_degree - 8,
            config.spectral_degree,
        )
        refinement_values = tuple(
            _spectral_dimensionless_masses(config, num_modes, degree)
            for degree in refinement_degrees
        )
        refinement_differences = tuple(
            float(np.max(np.abs(current - previous) / current))
            for previous, current in zip(
                refinement_values[:-1], refinement_values[1:]
            )
        )
        numerical = refinement_values[-1]
    else:
        raise ValueError(
            "method must be 'shooting', 'shooting-rust', 'collocation', or 'spectral'"
        )

    analytic = analytic_dimensionless_masses(num_modes)
    numerical_ratios = numerical / numerical[0]
    analytic_ratios = analytic / analytic[0]
    relative_errors = np.abs(numerical_ratios - analytic_ratios) / analytic_ratios
    return HardWallSpectrumResult(
        config=config,
        method=method,
        native_version=native_version,
        dimensionless_masses=numerical,
        analytic_dimensionless_masses=analytic,
        masses_gev=numerical / float(config.z_m_gev_inverse),
        mass_ratios=numerical_ratios,
        analytic_mass_ratios=analytic_ratios,
        ratio_relative_errors=relative_errors,
        spectral_refinement_degrees=refinement_degrees,
        spectral_refinement_differences=refinement_differences,
    )


def hard_wall_cutoff_refinement(
    config: Optional[HardWallConfig] = None,
    num_modes: int = DEFAULT_NUM_MODES,
    method: str = "shooting",
    cutoff_fractions: Sequence[float] = DEFAULT_REFINEMENT_CUTOFFS,
) -> HardWallRefinementResult:
    """Solve at decreasing UV cutoffs and retain every numerical level."""

    if config is None:
        config = HardWallConfig()
    _validate_num_modes(num_modes)
    resolved_cutoffs = tuple(float(value) for value in cutoff_fractions)
    if len(resolved_cutoffs) < 3:
        raise ValueError("cutoff_fractions must contain at least three levels")
    for value in resolved_cutoffs:
        _require_fraction(value, "cutoff_fractions")
    if not np.all(np.diff(np.asarray(resolved_cutoffs)) < 0.0):
        raise ValueError("cutoff_fractions must be strictly decreasing")

    results = tuple(
        solve_hard_wall_spectrum(
            replace(config, epsilon_fraction=cutoff),
            num_modes=num_modes,
            method=method,
        )
        for cutoff in resolved_cutoffs
    )
    return HardWallRefinementResult(results=results)


def _shooting_dimensionless_masses(
    config: HardWallConfig, num_modes: int, residual: Callable[[float], float]
) -> NDArray[np.float64]:
    reference = analytic_dimensionless_masses(num_modes + 1)
    roots = np.empty(num_modes, dtype=float)

    for index in range(num_modes):
        if index == 0:
            lower = 0.5 * reference[0]
        else:
            lower = 0.5 * (reference[index - 1] + reference[index])
        upper = 0.5 * (reference[index] + reference[index + 1])
        solution = root_scalar(
            residual,
            bracket=(float(lower), float(upper)),
            method="brentq",
            rtol=float(config.root_rtol),
        )
        if not solution.converged:
            raise RuntimeError(f"shooting root did not converge for mode {index}")
        roots[index] = float(solution.root)

    return roots


def _shooting_ir_residual(
    dimensionless_mass: float, config: HardWallConfig
) -> float:
    epsilon = float(config.epsilon_fraction)

    def equation(x: float, fields: NDArray[np.float64]) -> NDArray[np.float64]:
        value, derivative = fields
        return np.array(
            [derivative, derivative / x - dimensionless_mass**2 * value]
        )

    solution = solve_ivp(
        equation,
        (epsilon, 1.0),
        np.array([0.0, 1.0]),
        method="DOP853",
        rtol=float(config.integration_rtol),
        atol=float(config.integration_atol),
    )
    if not solution.success:
        raise RuntimeError(f"shooting integration failed: {solution.message}")
    return float(solution.y[1, -1])


def _collocation_dimensionless_masses(
    config: HardWallConfig, num_modes: int
) -> NDArray[np.float64]:
    epsilon = float(config.epsilon_fraction)
    mesh = np.linspace(epsilon, 1.0, config.collocation_mesh_points)
    guesses = analytic_dimensionless_masses(num_modes)
    roots = np.empty(num_modes, dtype=float)

    def equation(
        x: NDArray[np.float64],
        fields: NDArray[np.float64],
        parameter: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        value, derivative = fields
        return np.vstack(
            (derivative, derivative / x - parameter[0] ** 2 * value)
        )

    def boundary_residual(
        left: NDArray[np.float64],
        right: NDArray[np.float64],
        parameter: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        del parameter
        return np.array([left[0], left[1] - 1.0, right[1]])

    for index, guess in enumerate(guesses):
        derivative_at_epsilon = guess * epsilon * j0(guess * epsilon)
        value_guess = (
            mesh * j1(guess * mesh) - epsilon * j1(guess * epsilon)
        ) / derivative_at_epsilon
        derivative_guess = (
            guess * mesh * j0(guess * mesh) / derivative_at_epsilon
        )
        initial_fields = np.vstack((value_guess, derivative_guess))
        solution = solve_bvp(
            equation,
            boundary_residual,
            mesh,
            initial_fields,
            p=np.array([guess]),
            tol=float(config.collocation_tolerance),
            max_nodes=config.collocation_max_nodes,
        )
        if not solution.success:
            raise RuntimeError(
                f"collocation solve did not converge for mode {index}: "
                f"{solution.message}"
            )
        root = float(solution.p[0])
        if not math.isfinite(root) or root <= 0.0:
            raise RuntimeError(f"collocation returned an invalid mode {index}")
        roots[index] = root

    if np.any(np.diff(roots) <= 0.0):
        raise RuntimeError("collocation modes are not strictly ordered")
    return roots


def _spectral_dimensionless_masses(
    config: HardWallConfig, num_modes: int, degree: int
) -> NDArray[np.float64]:
    """Solve the finite-cutoff equation as a generalized eigenproblem."""

    grid = chebyshev_lobatto_grid(
        degree, float(config.epsilon_fraction), 1.0
    )
    coordinate = grid.nodes
    operator = (
        -grid.second_derivative
        + np.diag(1.0 / coordinate) @ grid.first_derivative
    ).copy()
    weight = np.eye(grid.size)

    # UV Dirichlet row: V(epsilon) = 0.
    operator[0, :] = 0.0
    operator[0, 0] = 1.0
    weight[0, :] = 0.0
    # IR Neumann row: V'(1) = 0.
    operator[-1, :] = grid.first_derivative[-1, :]
    weight[-1, :] = 0.0

    squared_masses = eigvals(
        operator, weight, check_finite=True
    )
    real = squared_masses.real
    admissible = (
        np.isfinite(real)
        & np.isfinite(squared_masses.imag)
        & (real > 0.0)
        & (np.abs(squared_masses.imag) <= 1.0e-8 * np.maximum(real, 1.0))
    )
    ordered = np.sort(real[admissible])
    if len(ordered) < num_modes:
        raise RuntimeError(
            "spectral eigensolver returned too few finite positive real modes"
        )
    masses = np.sqrt(ordered[:num_modes])
    if np.any(np.diff(masses) <= 0.0):
        raise RuntimeError("spectral modes are not strictly ordered")
    return np.asarray(masses, dtype=float)


def _validate_num_modes(num_modes: int) -> None:
    _require_integer_at_least(num_modes, 1, "num_modes")


def _require_finite_positive(value: Real, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite positive number")
    if not math.isfinite(float(value)) or float(value) <= 0.0:
        raise ValueError(f"{name} must be a finite positive number")


def _require_fraction(value: Real, name: str) -> None:
    _require_finite_positive(value, name)
    if float(value) >= 1.0:
        raise ValueError(f"{name} must be less than one")


def _require_integer_at_least(value: int, minimum: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{name} must be an integer")
    if int(value) < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
