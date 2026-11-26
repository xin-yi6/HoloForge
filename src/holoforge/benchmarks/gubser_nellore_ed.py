"""Coupled Chebyshev benchmark for the Gubser--Nellore Einstein--dilaton model.

The primary route solves the public Einstein--scalar equations in conformal
radial gauge after analytically factoring their UV powers.  A scalar-coordinate
master ODE from the same source is integrated with DOP853 only as an
independent discretization check.  Agreement verifies this implementation of
the selected bottom-up model; it is not empirical validation of QCD.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
import hashlib
import json
import math
from numbers import Integral, Real
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import solve_ivp
from scipy.interpolate import BarycentricInterpolator, PchipInterpolator
from scipy.optimize import least_squares, minimize_scalar, root

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
from holoforge.numerics.interpolation import (
    deterministic_barycentric_interpolator as _barycentric_interpolator,
)


SOURCE_ID = "arXiv:0804.0434"
SOURCE_PDF_SHA256 = (
    "ba8f25d69881fdb0a659651258a792377b83104de12bc1e30ee09532a9434809"
)
SOURCE_ARCHIVE_SHA256 = (
    "49057620542ad6839890f8328897615f0a5272e365ea06c806073d0147803360"
)
DEFAULT_COLLOCATION_TOLERANCE = 1.0e-9
DEFAULT_EQUATION_TOLERANCE = 1.0e-7
DEFAULT_BOUNDARY_TOLERANCE = 1.0e-7
DEFAULT_REFINEMENT_TOLERANCE = 2.0e-4
DEFAULT_REFINEMENT_ORDER_FLOOR = 1.0e-8
DEFAULT_INDEPENDENT_TOLERANCE = 5.0e-4
DEFAULT_DERIVATIVE_TOLERANCE = 1.0e-3
DEFAULT_DETERMINISM_TOLERANCE = 1.0e-12
DEFAULT_DOP853_HORIZONS = (0.25, 0.5, 1.0, 2.0, 4.0)
DEFAULT_T_C_PLOT_MINIMUM = 0.9618971489


FIGURE_2_ANCHORS: Mapping[float, float] = {
    0.001: 0.250406,
    0.050: 0.283180,
    0.100: 0.300728,
    0.200: 0.315099,
    0.400: 0.324212,
    0.600: 0.327419,
    0.800: 0.329051,
    1.000: 0.329995,
    1.200: 0.330616,
}
FIGURE_3_ANCHORS: Mapping[float, float] = {
    0.100: 0.148926,
    0.250: 0.143892,
    0.500: 0.127101,
    0.750: 0.094438,
    0.900: 0.058930,
    1.000: 0.057147,
    1.250: 0.217849,
    1.500: 0.271178,
    2.000: 0.303988,
    3.000: 0.319753,
    4.000: 0.324540,
    5.000: 0.326687,
}


GUBSER_NELLORE_DEFINITION = BenchmarkDefinition(
    identifier="gubser-nellore-ed",
    support_level="reproduced",
    background=BackgroundSpec(
        identifier="five-dimensional-einstein-dilaton-black-brane",
        dimension=5,
        coordinate="u = x/x_H in [0, 1], x = z^(4-Delta)",
        description=(
            "Zero-density asymptotically AdS black brane with one canonical "
            "scalar and a phenomenological source potential."
        ),
    ),
    equations=(
        EquationSpec(
            identifier="blackening-equation",
            kind="coupled nonlinear boundary-value equation",
            dependent_fields=("f", "A_E"),
            expression="f_xx + [3 A_E,x + (1-4/p)/x] f_x = 0",
            source_reference=(
                "Gubser and Nellore, arXiv:0804.0434, Eqs. (24)-(29), "
                "transformed to conformal gauge"
            ),
        ),
        EquationSpec(
            identifier="warp-equation",
            kind="coupled nonlinear boundary-value equation",
            dependent_fields=("A_E", "phi"),
            expression=(
                "A_E,xx + (1+1/p) A_E,x/x - A_E,x^2 + phi_x^2/6 = 0"
            ),
            source_reference=(
                "Gubser and Nellore, arXiv:0804.0434, Eqs. (24)-(29), "
                "transformed to conformal gauge"
            ),
        ),
        EquationSpec(
            identifier="scalar-equation",
            kind="coupled nonlinear boundary-value equation",
            dependent_fields=("phi", "A_E", "f"),
            expression=(
                "phi_xx + [3 A_E,x + f_x/f + (1-4/p)/x] phi_x "
                "- exp(2 A_E) V'(phi)/(p^2 x^2 f) = 0"
            ),
            source_reference=(
                "Gubser and Nellore, arXiv:0804.0434, Eqs. (24)-(29), "
                "transformed to conformal gauge"
            ),
        ),
        EquationSpec(
            identifier="independent-master-equation",
            kind="horizon-seeded initial-value diagnostic",
            dependent_fields=("G = dA/dphi",),
            expression=(
                "G'/(G+V/(3V')) = d/dphi log[G'/G + 1/(6G) - 4G "
                "- G'/(G+V/(3V'))]"
            ),
            source_reference="Gubser and Nellore, arXiv:0804.0434, Eq. (34)",
        ),
    ),
    boundary_conditions=(
        BoundaryConditionSpec(
            field="f",
            location="u = 0 and u = 1",
            role="normalized conformal boundary and regular horizon",
            expression="f(0) = 1, f(1) = 0",
            interpretation="The coupled collocation domain includes both endpoints.",
        ),
        BoundaryConditionSpec(
            field="phi",
            location="u = 0",
            role="unit source-scale convention",
            expression="phi = x_H u P(u), P(0) = 1",
            interpretation=(
                "The leading UV power is factored analytically; x_H sets the "
                "source-normalized horizon scale."
            ),
        ),
        BoundaryConditionSpec(
            field="A_E",
            location="u = 0",
            role="asymptotically AdS UV behavior",
            expression="A_E = x_H^2 u^2 C(u), C finite",
            interpretation="The leading scalar backreaction power is explicit.",
        ),
        BoundaryConditionSpec(
            field="phi",
            location="u = 1",
            role="regular scalar horizon",
            expression="the transformed scalar equation is retained at u = 1",
            interpretation="No fitted horizon scalar datum is introduced.",
        ),
    ),
    solvers=(
        SolverSpec(
            problem_type="nonlinear coupled boundary-value problem",
            library_function=(
                "scipy.optimize.root and scipy.optimize.least_squares"
            ),
            method=(
                "Chebyshev--Gauss--Lobatto collocation, hybr solve, frozen "
                "TRF residual polish"
            ),
            description=(
                "UV-factorized fields use deterministic degree and same-degree "
                "horizon continuation."
            ),
        ),
        SolverSpec(
            problem_type="independent scalar-coordinate initial-value problem",
            library_function="scipy.integrate.solve_ivp",
            method="DOP853 with analytic horizon-series data",
            description=(
                "This route changes the discretization and evolution direction "
                "but uses the same physical source equations."
            ),
        ),
    ),
    observables=(
        ObservableSpec(
            identifier="temperature",
            symbol="T L",
            extraction="absolute horizon derivative of f in conformal gauge",
            normalization="AdS radius L = 1",
        ),
        ObservableSpec(
            identifier="entropy-density",
            symbol="s kappa_5^2",
            extraction="2 pi exp(3 A_E(z_H))/z_H^3",
            normalization="kappa_5^2 = 1 in reported values",
        ),
        ObservableSpec(
            identifier="speed-of-sound-squared",
            symbol="c_s^2",
            extraction="d log(T)/d log(s) along one declared horizon branch",
            normalization="dimensionless zero-density adiabatic sound speed",
        ),
    ),
)


@dataclass(frozen=True)
class PotentialPreset:
    """One public source potential and its analytic UV/IR data."""

    identifier: str
    gamma: float
    b: float
    figure: int
    figure_tolerance: float
    digitization_uncertainty: float

    @property
    def mass_squared(self) -> float:
        return 2.0 * self.b - 12.0 * self.gamma**2

    @property
    def delta(self) -> float:
        return 2.0 + math.sqrt(4.0 + self.mass_squared)

    @property
    def uv_power(self) -> float:
        return 4.0 - self.delta

    @property
    def ir_sound_speed_squared(self) -> float:
        return 1.0 / 3.0 - self.gamma**2 / 2.0

    def potential(self, phi: Any) -> Any:
        values = np.asarray(phi)
        result = -12.0 * np.cosh(self.gamma * values) + self.b * values**2
        return float(result) if result.ndim == 0 else result

    def first_derivative(self, phi: Any) -> Any:
        values = np.asarray(phi)
        result = (
            -12.0 * self.gamma * np.sinh(self.gamma * values)
            + 2.0 * self.b * values
        )
        return float(result) if result.ndim == 0 else result

    def second_derivative(self, phi: Any) -> Any:
        values = np.asarray(phi)
        result = (
            -12.0 * self.gamma**2 * np.cosh(self.gamma * values)
            + 2.0 * self.b
        )
        return float(result) if result.ndim == 0 else result

    def third_derivative(self, phi: Any) -> Any:
        values = np.asarray(phi)
        result = -12.0 * self.gamma**3 * np.sinh(self.gamma * values)
        return float(result) if result.ndim == 0 else result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.identifier,
            "gamma": self.gamma,
            "b": self.b,
            "mass_squared_L2": self.mass_squared,
            "delta": self.delta,
            "uv_power": self.uv_power,
            "ir_sound_speed_squared": self.ir_sound_speed_squared,
            "source_figure": self.figure,
            "figure_tolerance": self.figure_tolerance,
            "digitization_uncertainty": self.digitization_uncertainty,
        }


COSH_CALIBRATION = PotentialPreset(
    identifier="cosh-calibration",
    gamma=1.0 / math.sqrt(6.0),
    b=0.0,
    figure=2,
    figure_tolerance=1.5e-3,
    digitization_uncertainty=5.0e-4,
)
QCD_LIKE = PotentialPreset(
    identifier="qcd-like",
    gamma=0.606,
    b=2.06,
    figure=3,
    figure_tolerance=5.0e-3,
    digitization_uncertainty=1.5e-3,
)
PRESETS: Mapping[str, PotentialPreset] = {
    COSH_CALIBRATION.identifier: COSH_CALIBRATION,
    QCD_LIKE.identifier: QCD_LIKE,
}


@dataclass(frozen=True)
class CoupledSolverConfig:
    """Frozen maintained-library nonlinear-solver controls."""

    root_tolerance: float = 1.0e-11
    maximum_evaluations_factor: int = 500
    polish_tolerance: float = 1.0e-14
    polish_maximum_evaluations: int = 12
    oversampling_factor: int = 2
    residual_backend: str = "numpy"

    def __post_init__(self) -> None:
        if self.residual_backend not in ("numpy", "rust"):
            raise ValueError("residual_backend must be 'numpy' or 'rust'")
        _validate_positive("root_tolerance", self.root_tolerance)
        _validate_integer(
            "maximum_evaluations_factor",
            self.maximum_evaluations_factor,
            minimum=1,
        )
        _validate_positive("polish_tolerance", self.polish_tolerance)
        _validate_integer(
            "polish_maximum_evaluations",
            self.polish_maximum_evaluations,
            minimum=1,
        )
        _validate_integer(
            "oversampling_factor", self.oversampling_factor, minimum=2
        )

    def software_versions(self) -> Dict[str, str]:
        versions = runtime_versions()
        if self.residual_backend == "rust":
            versions["holoforge-native"] = _native_collocation().__version__
        return versions


@dataclass(frozen=True)
class NonlinearDiagnostics:
    """Both stages of the frozen nonlinear solve."""

    root_success: bool
    root_message: str
    root_function_evaluations: int
    root_scaled_residual: float
    polish_applied: bool
    polish_success: bool
    polish_message: str
    polish_function_evaluations: int
    final_scaled_residual: float

    @property
    def success(self) -> bool:
        return (
            (self.root_success and not self.polish_applied)
            or (self.polish_applied and self.polish_success)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root": {
                "success": self.root_success,
                "message": self.root_message,
                "function_evaluations": self.root_function_evaluations,
                "scaled_residual": self.root_scaled_residual,
            },
            "polish": {
                "applied": self.polish_applied,
                "success": self.polish_success,
                "message": self.polish_message,
                "function_evaluations": self.polish_function_evaluations,
            },
            "final_success": self.success,
            "final_scaled_residual": self.final_scaled_residual,
        }


@dataclass(frozen=True)
class CoupledProfile:
    """One source-normalized coupled collocation solution."""

    preset: PotentialPreset
    degree: int
    x_h: float
    u: NDArray[np.float64]
    blackening: NDArray[np.float64]
    warp_factor: NDArray[np.float64]
    scalar_factor: NDArray[np.float64]
    nonlinear: NonlinearDiagnostics

    @property
    def phi_h(self) -> float:
        return float(self.x_h * self.scalar_factor[-1])

    def interpolators(
        self,
    ) -> Tuple[BarycentricInterpolator, BarycentricInterpolator, BarycentricInterpolator]:
        return (
            _barycentric_interpolator(self.u, self.blackening),
            _barycentric_interpolator(self.u, self.warp_factor),
            _barycentric_interpolator(self.u, self.scalar_factor),
        )


@dataclass(frozen=True)
class EquationDiagnostics:
    """Independently oversampled physical-equation and endpoint residuals."""

    blackening_equation: float
    warp_equation: float
    scalar_equation: float
    horizon_scalar_equation: float
    f_uv: float
    f_horizon: float
    scalar_uv: float
    warp_uv: float

    @property
    def maximum_equation_residual(self) -> float:
        return max(
            self.blackening_equation,
            self.warp_equation,
            self.scalar_equation,
        )

    @property
    def maximum_boundary_residual(self) -> float:
        return max(self.f_uv, self.f_horizon, self.scalar_uv, self.warp_uv)

    def to_dict(self) -> Dict[str, float]:
        return {
            "blackening_equation": self.blackening_equation,
            "warp_equation": self.warp_equation,
            "scalar_equation": self.scalar_equation,
            "horizon_scalar_equation": self.horizon_scalar_equation,
            "f_uv": self.f_uv,
            "f_horizon": self.f_horizon,
            "scalar_uv": self.scalar_uv,
            "warp_uv": self.warp_uv,
            "maximum_equation_residual": self.maximum_equation_residual,
            "maximum_boundary_residual": self.maximum_boundary_residual,
        }


@dataclass(frozen=True)
class ThermodynamicPoint:
    """Thermodynamics at one horizon point."""

    x_h: float
    phi_h: float
    degree: int
    temperature: float
    entropy: float

    @property
    def log_temperature(self) -> float:
        return math.log(self.temperature)

    @property
    def log_entropy(self) -> float:
        return math.log(self.entropy)

    def to_dict(self) -> Dict[str, float]:
        return {
            "x_h": self.x_h,
            "phi_h": self.phi_h,
            "degree": self.degree,
            "temperature_L": self.temperature,
            "entropy_kappa5_squared": self.entropy,
        }


@dataclass(frozen=True)
class SoundSpeedPoint:
    """Two local thermodynamic derivatives at one branch point."""

    index: int
    x_h: float
    phi_h: float
    temperature: float
    barycentric: float
    pchip: float

    @property
    def disagreement(self) -> float:
        return abs(self.barycentric - self.pchip)

    def to_dict(self) -> Dict[str, float]:
        return {
            "index": self.index,
            "x_h": self.x_h,
            "phi_h": self.phi_h,
            "temperature_L": self.temperature,
            "barycentric": self.barycentric,
            "pchip": self.pchip,
            "absolute_disagreement": self.disagreement,
        }


@dataclass(frozen=True)
class IndependentComparison:
    """One coupled-versus-DOP853 comparison at a preregistered horizon."""

    target_phi_h: float
    actual_phi_h: float
    temperature_relative_error: float
    entropy_relative_error: float
    sound_speed_relative_error: float
    dop853_function_evaluations: int

    @property
    def maximum_relative_error(self) -> float:
        return max(
            self.temperature_relative_error,
            self.entropy_relative_error,
            self.sound_speed_relative_error,
        )

    def to_dict(self) -> Dict[str, float]:
        return {
            "target_phi_h": self.target_phi_h,
            "actual_phi_h": self.actual_phi_h,
            "temperature_relative_error": self.temperature_relative_error,
            "entropy_relative_error": self.entropy_relative_error,
            "sound_speed_relative_error": self.sound_speed_relative_error,
            "maximum_relative_error": self.maximum_relative_error,
            "dop853_function_evaluations": self.dop853_function_evaluations,
        }


@dataclass(frozen=True)
class BranchSolution:
    """Aligned degree sequences on one declared thermodynamic branch."""

    preset: PotentialPreset
    degrees: Tuple[int, int, int]
    x_h_values: NDArray[np.float64]
    profiles: Mapping[int, Tuple[CoupledProfile, ...]]
    thermodynamics: Mapping[int, Tuple[ThermodynamicPoint, ...]]
    sound_speeds: Mapping[int, Tuple[SoundSpeedPoint, ...]]


@dataclass(frozen=True)
class PrimaryBranchSolution:
    """Dense primary-curve branch at one declared spectral degree."""

    preset: PotentialPreset
    degree: int
    x_h_values: NDArray[np.float64]
    profiles: Tuple[CoupledProfile, ...]
    thermodynamics: Tuple[ThermodynamicPoint, ...]
    sound_speeds: Tuple[SoundSpeedPoint, ...]


def get_preset(identifier: str) -> PotentialPreset:
    """Resolve one frozen public potential preset."""

    try:
        return PRESETS[identifier]
    except KeyError as exc:
        raise ValueError(f"unknown Gubser--Nellore preset: {identifier}") from exc


def solve_coupled_profile(
    preset: PotentialPreset,
    x_h: Real,
    degree: int,
    *,
    seed: Optional[CoupledProfile] = None,
    config: Optional[CoupledSolverConfig] = None,
) -> CoupledProfile:
    """Solve one UV-factorized coupled Einstein--scalar profile."""

    _validate_positive("x_h", x_h)
    _validate_integer("degree", degree, minimum=12)
    resolved_config = CoupledSolverConfig() if config is None else config
    grid = chebyshev_lobatto_grid(int(degree), 0.0, 1.0)
    u = grid.nodes
    d1 = grid.first_derivative
    d2 = grid.second_derivative
    size = grid.size
    resolved_x_h = float(x_h)

    if seed is None:
        exponent = 4.0 / preset.uv_power
        blackening = 1.0 - u**exponent
        scalar_factor = np.ones_like(u)
        warp_factor = np.full_like(u, _analytic_warp_uv(preset))
    else:
        blackening = _interpolate_seed(seed.u, seed.blackening, u)
        warp_factor = _interpolate_seed(seed.u, seed.warp_factor, u)
        scalar_factor = _interpolate_seed(seed.u, seed.scalar_factor, u)
    initial = np.concatenate((blackening, warp_factor, scalar_factor))
    equations = (
        _rust_collocation_equations(preset, resolved_x_h, u)
        if resolved_config.residual_backend == "rust"
        else partial(_scaled_coupled_equations, preset, resolved_x_h, u)
    )

    def residual(vector: NDArray[np.float64]) -> NDArray[np.float64]:
        f, c, pfield = np.asarray(vector, dtype=float).reshape(3, size)
        scaled = equations(
            f,
            d1 @ f,
            d2 @ f,
            c,
            d1 @ c,
            d2 @ c,
            pfield,
            d1 @ pfield,
            d2 @ pfield,
        )
        f_equation, warp_equation, scalar_equation = scaled
        f_equation = f_equation.copy()
        scalar_equation = scalar_equation.copy()
        f_equation[0] = f[0] - 1.0
        f_equation[-1] = f[-1]
        scalar_equation[0] = pfield[0] - 1.0
        return np.concatenate((f_equation, warp_equation, scalar_equation))

    root_result = root(
        residual,
        initial,
        method="hybr",
        options={
            "xtol": resolved_config.root_tolerance,
            "maxfev": resolved_config.maximum_evaluations_factor * len(initial),
        },
    )
    root_vector = np.asarray(root_result.x, dtype=float)
    root_residual = float(np.max(np.abs(residual(root_vector))))
    polish_applied = bool(
        not root_result.success
        or root_residual > DEFAULT_COLLOCATION_TOLERANCE
    )
    if polish_applied:
        polish_result = least_squares(
            residual,
            root_vector,
            method="trf",
            ftol=resolved_config.polish_tolerance,
            xtol=resolved_config.polish_tolerance,
            gtol=resolved_config.polish_tolerance,
            max_nfev=resolved_config.polish_maximum_evaluations,
        )
        final_vector = np.asarray(polish_result.x, dtype=float)
        polish_success = bool(polish_result.success)
        polish_message = str(polish_result.message)
        polish_evaluations = int(polish_result.nfev)
    else:
        final_vector = root_vector
        polish_success = False
        polish_message = "not applied"
        polish_evaluations = 0
    final_residual = float(np.max(np.abs(residual(final_vector))))
    f, c, pfield = final_vector.reshape(3, size)
    return CoupledProfile(
        preset=preset,
        degree=int(degree),
        x_h=resolved_x_h,
        u=np.asarray(u, dtype=float),
        blackening=np.asarray(f, dtype=float),
        warp_factor=np.asarray(c, dtype=float),
        scalar_factor=np.asarray(pfield, dtype=float),
        nonlinear=NonlinearDiagnostics(
            root_success=bool(root_result.success),
            root_message=str(root_result.message),
            root_function_evaluations=int(root_result.nfev),
            root_scaled_residual=root_residual,
            polish_applied=polish_applied,
            polish_success=polish_success,
            polish_message=polish_message,
            polish_function_evaluations=polish_evaluations,
            final_scaled_residual=final_residual,
        ),
    )


def coupled_equation_diagnostics(
    profile: CoupledProfile,
    *,
    oversampling_factor: int = 2,
) -> EquationDiagnostics:
    """Evaluate the uncross-multiplied physical equations on a denser grid."""

    _validate_integer("oversampling_factor", oversampling_factor, minimum=2)
    over_grid = chebyshev_lobatto_grid(
        int(oversampling_factor) * profile.degree, 0.0, 1.0
    )
    u = over_grid.nodes
    evaluated: List[Tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]] = []
    for interpolator in profile.interpolators():
        values = np.asarray(interpolator(u), dtype=float)
        first = np.asarray(interpolator.derivative(u, der=1), dtype=float)
        second = np.asarray(interpolator.derivative(u, der=2), dtype=float)
        evaluated.append((values, first, second))
    f, fu, fuu = evaluated[0]
    c, cu, cuu = evaluated[1]
    pfield, pu, puu = evaluated[2]
    f_equation, warp_equation, scalar_equation = _scaled_coupled_equations(
        profile.preset,
        profile.x_h,
        u,
        f,
        fu,
        fuu,
        c,
        cu,
        cuu,
        pfield,
        pu,
        puu,
    )
    expected_warp_uv = _analytic_warp_uv(profile.preset)
    return EquationDiagnostics(
        blackening_equation=float(np.max(np.abs(f_equation[1:-1]))),
        warp_equation=float(np.max(np.abs(warp_equation))),
        scalar_equation=float(np.max(np.abs(scalar_equation[1:]))),
        horizon_scalar_equation=float(abs(scalar_equation[-1])),
        f_uv=float(abs(f[0] - 1.0)),
        f_horizon=float(abs(f[-1])),
        scalar_uv=float(abs(pfield[0] - 1.0)),
        warp_uv=float(abs(c[0] - expected_warp_uv)),
    )


def profile_thermodynamics(profile: CoupledProfile) -> ThermodynamicPoint:
    """Extract ``T`` and ``s`` directly from the exact horizon endpoint."""

    blackening_interpolator = profile.interpolators()[0]
    f_u_h = float(blackening_interpolator.derivative(1.0, der=1))
    z_h = profile.x_h ** (1.0 / profile.preset.uv_power)
    a_e_h = profile.x_h**2 * profile.warp_factor[-1]
    temperature = (
        abs(profile.preset.uv_power * f_u_h / z_h) / (4.0 * math.pi)
    )
    entropy = 2.0 * math.pi * math.exp(3.0 * a_e_h) / z_h**3
    if not all(math.isfinite(value) and value > 0.0 for value in (temperature, entropy)):
        raise RuntimeError("coupled thermodynamics must be positive and finite")
    return ThermodynamicPoint(
        x_h=profile.x_h,
        phi_h=profile.phi_h,
        degree=profile.degree,
        temperature=temperature,
        entropy=entropy,
    )


def solve_coupled_branch(
    preset: PotentialPreset,
    x_h_values: Sequence[Real],
    degrees: Tuple[int, int, int],
    *,
    config: Optional[CoupledSolverConfig] = None,
) -> BranchSolution:
    """Continue one branch at three aligned spectral degrees."""

    values = np.asarray(tuple(float(value) for value in x_h_values), dtype=float)
    if values.ndim != 1 or values.size < 7:
        raise ValueError("x_h_values must contain at least seven points")
    if not np.all(np.isfinite(values)) or np.any(values <= 0.0):
        raise ValueError("x_h_values must be positive and finite")
    if not np.all(np.diff(values) > 0.0):
        raise ValueError("x_h_values must be strictly increasing")
    resolved_degrees = tuple(int(degree) for degree in degrees)
    if len(resolved_degrees) != 3 or sorted(set(resolved_degrees)) != list(resolved_degrees):
        raise ValueError("degrees must be three strictly increasing integers")

    seed: Optional[CoupledProfile] = None
    initial: Dict[int, CoupledProfile] = {}
    initial_sequence = tuple(
        dict.fromkeys((24, 40, 60, 80) + resolved_degrees)
    )
    for degree in initial_sequence:
        seed = solve_coupled_profile(
            preset, values[0], degree, seed=seed, config=config
        )
        if degree in resolved_degrees:
            initial[degree] = seed
    profile_lists: Dict[int, List[CoupledProfile]] = {
        degree: [initial[degree]] for degree in resolved_degrees
    }
    previous = dict(initial)
    for x_h in values[1:]:
        current: Dict[int, CoupledProfile] = {}
        for index, degree in enumerate(resolved_degrees):
            if preset.identifier == QCD_LIKE.identifier and index > 0:
                seed_profile = current[resolved_degrees[index - 1]]
            else:
                seed_profile = previous[degree]
            current[degree] = solve_coupled_profile(
                preset,
                x_h,
                degree,
                seed=seed_profile,
                config=config,
            )
            profile_lists[degree].append(current[degree])
        previous = current

    profile_map = {
        degree: tuple(profile_lists[degree]) for degree in resolved_degrees
    }
    thermo_map: Dict[int, Tuple[ThermodynamicPoint, ...]] = {}
    sound_map: Dict[int, Tuple[SoundSpeedPoint, ...]] = {}
    for degree in resolved_degrees:
        thermo = tuple(profile_thermodynamics(item) for item in profile_map[degree])
        thermo_map[degree] = thermo
        sound_map[degree] = _sound_speed_curve(thermo)
    return BranchSolution(
        preset=preset,
        degrees=(resolved_degrees[0], resolved_degrees[1], resolved_degrees[2]),
        x_h_values=values,
        profiles=profile_map,
        thermodynamics=thermo_map,
        sound_speeds=sound_map,
    )


def solve_primary_branch(
    preset: PotentialPreset,
    x_h_values: Sequence[Real],
    degree: int = 80,
    *,
    config: Optional[CoupledSolverConfig] = None,
) -> PrimaryBranchSolution:
    """Continue the dense primary curve with preceding-horizon seeding."""

    values = np.asarray(tuple(float(value) for value in x_h_values), dtype=float)
    if values.ndim != 1 or values.size < 7:
        raise ValueError("x_h_values must contain at least seven points")
    if not np.all(np.isfinite(values)) or np.any(values <= 0.0):
        raise ValueError("x_h_values must be positive and finite")
    if not np.all(np.diff(values) > 0.0):
        raise ValueError("x_h_values must be strictly increasing")
    _validate_integer("degree", degree, minimum=40)

    seed: Optional[CoupledProfile] = None
    initial_sequence = tuple(
        dict.fromkeys(
            candidate
            for candidate in (24, 40, 60, 80, int(degree))
            if candidate <= int(degree)
        )
    )
    for initial_degree in initial_sequence:
        seed = solve_coupled_profile(
            preset,
            values[0],
            initial_degree,
            seed=seed,
            config=config,
        )
    if seed is None or seed.degree != int(degree):
        raise RuntimeError("primary degree continuation did not reach its target")
    profiles = [seed]
    for x_h in values[1:]:
        seed = solve_coupled_profile(
            preset,
            x_h,
            int(degree),
            seed=seed,
            config=config,
        )
        profiles.append(seed)
    profile_tuple = tuple(profiles)
    thermodynamics = tuple(profile_thermodynamics(item) for item in profile_tuple)
    return PrimaryBranchSolution(
        preset=preset,
        degree=int(degree),
        x_h_values=values,
        profiles=profile_tuple,
        thermodynamics=thermodynamics,
        sound_speeds=_sound_speed_curve(thermodynamics),
    )


def verify_gubser_nellore_ed(
    *,
    profile: str = "anchor",
    repeat_for_determinism: bool = True,
    residual_backend: str = "numpy",
) -> VerificationRecord:
    """Run the approved coupled ED reproduction and return inspectable evidence."""

    if profile not in {"anchor", "figure"}:
        raise ValueError("profile must be 'anchor' or 'figure'")
    config = CoupledSolverConfig(residual_backend=residual_backend)
    versions = config.software_versions()
    first = _verify_once(profile, config)
    if repeat_for_determinism:
        second = _verify_once(profile, config)
        determinism_error: Optional[float] = _maximum_nested_numeric_difference(
            first["determinism_state"], second["determinism_state"]
        )
    else:
        determinism_error = None

    preset_results = first["presets"]
    cosh = preset_results[COSH_CALIBRATION.identifier]
    qcd = preset_results[QCD_LIKE.identifier]
    algebra_error = max(
        float(cosh["algebra_maximum_error"]),
        float(qcd["algebra_maximum_error"]),
    )
    solver_success = bool(cosh["solver_success"] and qcd["solver_success"])
    collocation = max(
        float(cosh["maximum_collocation_residual"]),
        float(qcd["maximum_collocation_residual"]),
    )
    equation = max(
        float(cosh["maximum_equation_residual"]),
        float(qcd["maximum_equation_residual"]),
    )
    boundary = max(
        float(cosh["maximum_boundary_residual"]),
        float(qcd["maximum_boundary_residual"]),
    )
    horizon = max(
        float(cosh["maximum_horizon_scalar_residual"]),
        float(qcd["maximum_horizon_scalar_residual"]),
    )
    refinement = max(
        float(cosh["refinement"]["maximum_final_change"]),
        float(qcd["refinement"]["maximum_final_change"]),
    )
    refinement_order_failures = int(
        cosh["refinement"]["ordering_failures"]
        + qcd["refinement"]["ordering_failures"]
    )
    independent = max(
        float(cosh["maximum_independent_relative_error"]),
        float(qcd["maximum_independent_relative_error"]),
    )
    derivative = max(
        float(cosh["maximum_derivative_disagreement"]),
        float(qcd["maximum_derivative_disagreement"]),
    )
    checks = (
        AcceptanceCheck(
            "potential-algebra",
            "both source potentials and UV/IR analytic identities",
            algebra_error <= 1.0e-12,
            algebra_error,
            "maximum absolute error <= 1e-12",
        ),
        AcceptanceCheck(
            "nonlinear-solver",
            "every final nonlinear stage reports success",
            solver_success,
            0.0 if solver_success else 1.0,
            "all final solver statuses are successful",
        ),
        AcceptanceCheck(
            "collocation-residual",
            "maximum scaled coupled collocation residual",
            collocation <= DEFAULT_COLLOCATION_TOLERANCE,
            collocation,
            f"<= {DEFAULT_COLLOCATION_TOLERANCE:.1e}",
        ),
        AcceptanceCheck(
            "independent-equations",
            "maximum twice-oversampled physical-equation residual",
            equation <= DEFAULT_EQUATION_TOLERANCE,
            equation,
            f"<= {DEFAULT_EQUATION_TOLERANCE:.1e}",
        ),
        AcceptanceCheck(
            "exact-endpoints-and-uv",
            "maximum exact-endpoint and analytic UV residual",
            boundary <= DEFAULT_BOUNDARY_TOLERANCE,
            boundary,
            f"<= {DEFAULT_BOUNDARY_TOLERANCE:.1e}",
        ),
        AcceptanceCheck(
            "horizon-scalar-equation",
            "maximum retained scalar-equation residual at the horizon",
            horizon <= DEFAULT_EQUATION_TOLERANCE,
            horizon,
            f"<= {DEFAULT_EQUATION_TOLERANCE:.1e}",
        ),
        AcceptanceCheck(
            "spectral-refinement",
            "maximum final T, s, and c_s^2 refinement change",
            refinement <= DEFAULT_REFINEMENT_TOLERANCE,
            refinement,
            f"<= {DEFAULT_REFINEMENT_TOLERANCE:.1e}",
        ),
        AcceptanceCheck(
            "refinement-order",
            "successive changes decrease above the numerical floor",
            refinement_order_failures == 0,
            float(refinement_order_failures),
            "zero failures when the earlier change exceeds 1e-8",
        ),
        AcceptanceCheck(
            "dop853-comparison",
            "maximum coupled-versus-DOP853 T, s, and c_s^2 relative error",
            independent <= DEFAULT_INDEPENDENT_TOLERANCE,
            independent,
            f"<= {DEFAULT_INDEPENDENT_TOLERANCE:.1e}",
        ),
        AcceptanceCheck(
            "thermodynamic-derivative",
            "maximum barycentric-versus-PCHIP c_s^2 disagreement",
            derivative <= DEFAULT_DERIVATIVE_TOLERANCE,
            derivative,
            f"<= {DEFAULT_DERIVATIVE_TOLERANCE:.1e}",
        ),
        AcceptanceCheck(
            "figure-2-reproduction",
            "maximum absolute c_s^2 error at the nine Figure 2 anchors",
            float(cosh["figure"]["maximum_anchor_error"])
            <= COSH_CALIBRATION.figure_tolerance,
            float(cosh["figure"]["maximum_anchor_error"]),
            f"<= {COSH_CALIBRATION.figure_tolerance:.1e}",
        ),
        AcceptanceCheck(
            "figure-3-reproduction",
            "maximum absolute c_s^2 error at the twelve Figure 3 anchors",
            float(qcd["figure"]["maximum_anchor_error"])
            <= QCD_LIKE.figure_tolerance,
            float(qcd["figure"]["maximum_anchor_error"]),
            f"<= {QCD_LIKE.figure_tolerance:.1e}",
        ),
        AcceptanceCheck(
            "branch-integrity",
            "both source scans remain on one explicit monotone T-s branch",
            bool(cosh["branch_integrity"] and qcd["branch_integrity"]),
            0.0 if cosh["branch_integrity"] and qcd["branch_integrity"] else 1.0,
            "T(x_H) and s(x_H) each have one nonzero derivative sign",
        ),
        AcceptanceCheck(
            "determinism",
            "two complete verifier runs agree in reported physical observables",
            determinism_error is not None
            and determinism_error <= DEFAULT_DETERMINISM_TOLERANCE,
            determinism_error,
            f"maximum scaled difference <= {DEFAULT_DETERMINISM_TOLERANCE:.1e}",
        ),
    )
    public_results = {
        "presets": preset_results,
        "determinism": {
            "repeat_enabled": repeat_for_determinism,
            "maximum_scaled_difference": determinism_error,
        },
    }
    return VerificationRecord(
        definition=GUBSER_NELLORE_DEFINITION,
        configuration={
            "profile": profile,
            "bulk_dimension": 5,
            "ensemble": "zero chemical potential and zero Maxwell field",
            "units": "L = 1, kappa_5^2 = 1",
            "potentials": [
                COSH_CALIBRATION.to_dict(),
                QCD_LIKE.to_dict(),
            ],
            "dop853_target_phi_h": list(DEFAULT_DOP853_HORIZONS),
            "T_c_plot_registration": DEFAULT_T_C_PLOT_MINIMUM,
        },
        numerical_method={
            "route": "coupled UV-factorized Chebyshev collocation",
            "coordinate": "u = x/x_H, x = z^(4-Delta)",
            "unknowns": ["f(u)", "C(u)", "P(u)"],
            "factorization": [
                "A_E = x_H^2 u^2 C",
                "phi = x_H u P",
            ],
            "nonlinear_solver": "hybr then frozen TRF polish when required",
            "collocation_residual_backend": residual_backend,
            "independent_route": "horizon-seeded scalar-coordinate DOP853",
            "oversampling_factor": 2,
        },
        results=public_results,
        acceptance_checks=checks,
        software_versions=versions,
        scope=(
            "Numerical reproduction of two public curves in a classical, "
            "zero-density, single-scalar bottom-up model; not empirical QCD "
            "validation, a physical critical-temperature prediction, EMD, or iHQCD."
        ),
        extra={
            "primary_source": {
                "id": SOURCE_ID,
                "doi": "10.1103/PhysRevD.78.086007",
                "pdf_sha256": SOURCE_PDF_SHA256,
                "source_archive_sha256": SOURCE_ARCHIVE_SHA256,
            },
            "reference_data": {
                "kind": "derived vector-figure anchors",
                "raw_source_figures_redistributed": False,
                "review_state": "approved",
                "reviewed_by": "Xin-Yi Liu",
                "reviewed_on": "2026-08-17",
            },
            "review_state": "approved",
            "reviewed_by": "Xin-Yi Liu",
            "reviewed_on": "2026-08-17",
            "generated_by_ai": True,
        },
    )


def save_gubser_nellore_artifacts(
    record: VerificationRecord,
    output_directory: Path,
) -> Mapping[str, Path]:
    """Save JSON, CSV, and a two-panel reproduction plot."""

    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": directory / "gubser-nellore-ed-result.json",
        "csv": directory / "gubser-nellore-ed-curves.csv",
        "plot": directory / "gubser-nellore-ed-reproduction.png",
    }
    existing = [path for path in paths.values() if path.exists()]
    if existing:
        raise ValueError(
            "refusing to overwrite existing artifact: "
            + ", ".join(str(path) for path in existing)
        )
    payload = record.to_dict()
    paths["json"].write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    rows = ["preset,x_h,phi_h,temperature_L,sound_speed_squared"]
    for preset_id, result in payload["results"]["presets"].items():
        for row in result["curve"]:
            rows.append(
                f"{preset_id},{row['x_h']:.17g},{row['phi_h']:.17g},"
                f"{row['temperature_L']:.17g},{row['sound_speed_squared']:.17g}"
            )
    paths["csv"].write_text("\n".join(rows) + "\n", encoding="utf-8")
    _save_reproduction_plot(payload, paths["plot"])
    return paths


def _verify_once(profile: str, config: CoupledSolverConfig) -> Dict[str, Any]:
    cosh_count = 260 if profile == "anchor" else 700
    cosh_x = np.geomspace(0.10, 35.5, cosh_count)
    qcd_x = np.linspace(0.20, 1.25, 526)
    primary_branches = {
        COSH_CALIBRATION.identifier: solve_primary_branch(
            COSH_CALIBRATION, cosh_x, config=config
        ),
        QCD_LIKE.identifier: solve_primary_branch(QCD_LIKE, qcd_x, config=config),
    }
    branches = {
        COSH_CALIBRATION.identifier: solve_coupled_branch(
            COSH_CALIBRATION,
            np.geomspace(0.10, 35.5, 100),
            (40, 60, 80),
            config=config,
        ),
        QCD_LIKE.identifier: solve_coupled_branch(
            QCD_LIKE, np.linspace(0.20, 1.25, 106), (80, 120, 150), config=config
        ),
    }
    presets = {
        identifier: _evaluate_branch(branch, primary_branches[identifier])
        for identifier, branch in branches.items()
    }
    determinism_state = {
        identifier: {
            "curve": result["curve"],
            "figure": result["figure"],
        }
        for identifier, result in presets.items()
    }
    return {"presets": presets, "determinism_state": determinism_state}


def _evaluate_branch(
    branch: BranchSolution,
    primary: Optional[PrimaryBranchSolution] = None,
) -> Dict[str, Any]:
    coarse, middle, fine = branch.degrees
    diagnostics: List[EquationDiagnostics] = []
    profile_records: List[Dict[str, Any]] = []
    maximum_collocation = 0.0
    solver_success = True
    for degree in branch.degrees:
        for profile in branch.profiles[degree]:
            maximum_collocation = max(
                maximum_collocation, profile.nonlinear.final_scaled_residual
            )
            solver_success = solver_success and profile.nonlinear.success
            profile_records.append(
                {
                    "role": "verification",
                    "degree": degree,
                    "x_h": profile.x_h,
                    "phi_h": profile.phi_h,
                    "nonlinear": profile.nonlinear.to_dict(),
                }
            )
    primary_profiles = branch.profiles[fine] if primary is None else primary.profiles
    primary_thermodynamics = (
        branch.thermodynamics[fine] if primary is None else primary.thermodynamics
    )
    primary_sound = branch.sound_speeds[fine] if primary is None else primary.sound_speeds
    primary_x_h = branch.x_h_values if primary is None else primary.x_h_values
    primary_degree = fine if primary is None else primary.degree
    if primary is not None:
        for profile in primary.profiles:
            maximum_collocation = max(
                maximum_collocation, profile.nonlinear.final_scaled_residual
            )
            solver_success = solver_success and profile.nonlinear.success
            profile_records.append(
                {
                    "role": "primary",
                    "degree": profile.degree,
                    "x_h": profile.x_h,
                    "phi_h": profile.phi_h,
                    "nonlinear": profile.nonlinear.to_dict(),
                }
            )
    for profile in branch.profiles[fine]:
        diagnostics.append(coupled_equation_diagnostics(profile))
    maximum_equation = max(item.maximum_equation_residual for item in diagnostics)
    maximum_boundary = max(item.maximum_boundary_residual for item in diagnostics)
    maximum_horizon = max(item.horizon_scalar_equation for item in diagnostics)

    refinement = _refinement_evidence(branch, coarse, middle, fine)
    independent = _independent_comparisons(branch, fine)
    maximum_independent = max(item.maximum_relative_error for item in independent)
    derivative_disagreement = max(item.disagreement for item in primary_sound)
    branch_integrity = _branch_integrity(primary_thermodynamics)
    figure = _figure_comparison(branch.preset, primary_sound)
    curve = [
        {
            "x_h": item.x_h,
            "phi_h": item.phi_h,
            "temperature_L": item.temperature,
            "sound_speed_squared": item.pchip,
        }
        for item in primary_sound
    ]
    return {
        "potential": branch.preset.to_dict(),
        "degrees": list(branch.degrees),
        "primary_degree": primary_degree,
        "horizon_count": len(primary_x_h),
        "verification_horizon_count": len(branch.x_h_values),
        "x_h_range": [float(primary_x_h[0]), float(primary_x_h[-1])],
        "phi_h_range": [
            float(primary_thermodynamics[0].phi_h),
            float(primary_thermodynamics[-1].phi_h),
        ],
        "profiles": profile_records,
        "equation_diagnostics": [item.to_dict() for item in diagnostics],
        "solver_success": solver_success,
        "maximum_collocation_residual": maximum_collocation,
        "maximum_equation_residual": maximum_equation,
        "maximum_boundary_residual": maximum_boundary,
        "maximum_horizon_scalar_residual": maximum_horizon,
        "refinement": refinement,
        "independent_comparisons": [item.to_dict() for item in independent],
        "maximum_independent_relative_error": maximum_independent,
        "maximum_derivative_disagreement": derivative_disagreement,
        "branch_integrity": branch_integrity,
        "branch_label": "single zero-density black-hole branch",
        "figure": figure,
        "curve": curve,
        "algebra_maximum_error": _potential_algebra_error(branch.preset),
    }


def _native_collocation():
    try:
        import holoforge_native
    except ImportError as exc:
        raise RuntimeError(
            "The Rust collocation residual requires the optional native extension. "
            "From the repository root, run: python -m pip install ./native"
        ) from exc
    if not hasattr(holoforge_native, "gubser_nellore_equations"):
        raise RuntimeError(
            "The Rust collocation residual requires holoforge-native >= 0.2. "
            "Update the extension with: python -m pip install ./native"
        )
    return holoforge_native


def _rust_collocation_equations(
    preset: PotentialPreset, x_h: float, u: NDArray[np.float64]
):
    kernel = _native_collocation().gubser_nellore_equations
    uv_power = preset.uv_power
    x_h_squared = x_h**2
    scalar_scale = x_h * u
    warp_scale = x_h_squared * u**2
    denominator = uv_power**2 * x_h * u
    nonzero = u != 0.0

    def equations(f, fu, fuu, c, cu, cuu, pfield, pu, puu):
        # Use the same potential and NumPy transcendental functions as the
        # reference. Small rounding changes can alter the nonlinear iteration.
        numerator = -np.exp(2.0 * (warp_scale * c)) * preset.first_derivative(
            scalar_scale * pfield
        )
        potential_term = np.divide(numerator, denominator, out=np.zeros_like(u), where=nonzero)
        return kernel(
            x_h_squared, uv_power, u, (f, fu, fuu), (c, cu, cuu),
            (pfield, pu, puu), potential_term,
        )

    return equations


def _scaled_coupled_equations(
    preset: PotentialPreset,
    x_h: float,
    u: NDArray[np.float64],
    f: NDArray[np.float64],
    fu: NDArray[np.float64],
    fuu: NDArray[np.float64],
    c: NDArray[np.float64],
    cu: NDArray[np.float64],
    cuu: NDArray[np.float64],
    pfield: NDArray[np.float64],
    pu: NDArray[np.float64],
    puu: NDArray[np.float64],
) -> Tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    p = preset.uv_power
    a_x_scaled = 2.0 * u * c + u**2 * cu
    scalar_x = pfield + u * pu
    f_terms = (
        u * fuu,
        (3.0 * x_h**2 * u * a_x_scaled + 1.0 - 4.0 / p) * fu,
    )
    f_equation = sum(f_terms) / (1.0 + sum(np.abs(term) for term in f_terms))
    warp_terms = (
        2.0 * c + 4.0 * u * cu + u**2 * cuu,
        (1.0 + 1.0 / p) * (2.0 * c + u * cu),
        -x_h**2 * a_x_scaled**2,
        scalar_x**2 / 6.0,
    )
    warp_equation = sum(warp_terms) / (
        1.0 + sum(np.abs(term) for term in warp_terms)
    )
    scalar = x_h * u * pfield
    a_e = x_h**2 * u**2 * c
    potential_prime = np.asarray(preset.first_derivative(scalar), dtype=float)
    scalar_terms = (
        u * f * (2.0 * pu + u * puu),
        (
            3.0 * x_h**2 * u * f * a_x_scaled
            + (1.0 - 4.0 / p) * f
            + u * fu
        )
        * scalar_x,
        np.divide(
            -np.exp(2.0 * a_e) * potential_prime,
            p**2 * x_h * u,
            out=np.zeros_like(u),
            where=u != 0.0,
        ),
    )
    scalar_equation = sum(scalar_terms) / (
        1.0 + sum(np.abs(term) for term in scalar_terms)
    )
    return f_equation, warp_equation, scalar_equation


def _analytic_warp_uv(preset: PotentialPreset) -> float:
    p = preset.uv_power
    return -p / (12.0 * (2.0 * p + 1.0))


def _interpolate_seed(
    source_nodes: NDArray[np.float64],
    source_values: NDArray[np.float64],
    target_nodes: NDArray[np.float64],
) -> NDArray[np.float64]:
    return np.asarray(
        _barycentric_interpolator(source_nodes, source_values)(target_nodes),
        dtype=float,
    )


def _sound_speed_curve(
    points: Sequence[ThermodynamicPoint],
) -> Tuple[SoundSpeedPoint, ...]:
    result: List[SoundSpeedPoint] = []
    for index in range(2, len(points) - 2):
        local = points[index - 2 : index + 3]
        horizon = np.asarray([item.phi_h for item in local], dtype=float)
        log_t = np.asarray([item.log_temperature for item in local], dtype=float)
        log_s = np.asarray([item.log_entropy for item in local], dtype=float)
        center = points[index].phi_h
        bary_t = float(
            _barycentric_interpolator(horizon, log_t).derivative(center)
        )
        bary_s = float(
            _barycentric_interpolator(horizon, log_s).derivative(center)
        )
        pchip_t = float(PchipInterpolator(horizon, log_t).derivative()(center))
        pchip_s = float(PchipInterpolator(horizon, log_s).derivative()(center))
        if min(abs(bary_s), abs(pchip_s)) <= 1.0e-14:
            raise RuntimeError("entropy derivative became singular")
        result.append(
            SoundSpeedPoint(
                index=index,
                x_h=points[index].x_h,
                phi_h=points[index].phi_h,
                temperature=points[index].temperature,
                barycentric=bary_t / bary_s,
                pchip=pchip_t / pchip_s,
            )
        )
    return tuple(result)


def _refinement_evidence(
    branch: BranchSolution,
    coarse: int,
    middle: int,
    fine: int,
) -> Dict[str, Any]:
    earlier: List[float] = []
    final: List[float] = []
    for observable in ("temperature", "entropy"):
        coarse_values = np.asarray(
            [getattr(item, observable) for item in branch.thermodynamics[coarse]]
        )
        middle_values = np.asarray(
            [getattr(item, observable) for item in branch.thermodynamics[middle]]
        )
        fine_values = np.asarray(
            [getattr(item, observable) for item in branch.thermodynamics[fine]]
        )
        earlier.extend(_relative_array_change(middle_values, coarse_values))
        final.extend(_relative_array_change(fine_values, middle_values))
    coarse_sound = np.asarray([item.pchip for item in branch.sound_speeds[coarse]])
    middle_sound = np.asarray([item.pchip for item in branch.sound_speeds[middle]])
    fine_sound = np.asarray([item.pchip for item in branch.sound_speeds[fine]])
    earlier.extend(_relative_array_change(middle_sound, coarse_sound))
    final.extend(_relative_array_change(fine_sound, middle_sound))
    ordering_failures = sum(
        1
        for previous, current in zip(earlier, final)
        if previous > DEFAULT_REFINEMENT_ORDER_FLOOR and current >= previous
    )
    return {
        "coarse_to_middle_maximum": max(earlier),
        "maximum_final_change": max(final),
        "ordering_floor": DEFAULT_REFINEMENT_ORDER_FLOOR,
        "ordering_failures": ordering_failures,
    }


def _independent_comparisons(
    branch: BranchSolution,
    degree: int,
) -> Tuple[IndependentComparison, ...]:
    thermo = branch.thermodynamics[degree]
    sound_by_index = {item.index: item for item in branch.sound_speeds[degree]}
    comparisons: List[IndependentComparison] = []
    for target in DEFAULT_DOP853_HORIZONS:
        center = min(
            range(2, len(thermo) - 2),
            key=lambda index: abs(thermo[index].phi_h - target),
        )
        local = thermo[center - 2 : center + 3]
        independent_points: List[ThermodynamicPoint] = []
        evaluations = 0
        for coupled_point in local:
            independent, nfev = _dop853_thermodynamics(
                branch.preset, coupled_point.phi_h, coupled_point.x_h
            )
            independent_points.append(independent)
            evaluations += nfev
        independent_sound = _sound_speed_curve(independent_points)[0]
        coupled_sound = sound_by_index[center]
        central_independent = independent_points[2]
        central_coupled = thermo[center]
        comparisons.append(
            IndependentComparison(
                target_phi_h=target,
                actual_phi_h=central_coupled.phi_h,
                temperature_relative_error=_relative_error(
                    central_coupled.temperature,
                    central_independent.temperature,
                ),
                entropy_relative_error=_relative_error(
                    central_coupled.entropy,
                    central_independent.entropy,
                ),
                sound_speed_relative_error=_relative_error(
                    coupled_sound.pchip, independent_sound.pchip
                ),
                dop853_function_evaluations=evaluations,
            )
        )
    return tuple(comparisons)


def _dop853_thermodynamics(
    preset: PotentialPreset,
    phi_h: float,
    x_h: float,
) -> Tuple[ThermodynamicPoint, int]:
    uv_cutoff = 1.0e-5
    horizon_cutoff = 1.0e-5
    left = uv_cutoff * phi_h
    right = (1.0 - horizon_cutoff) * phi_h
    g_h, gp_h, g2_h = _horizon_series_quadratic(preset, phi_h)
    offset = right - phi_h
    initial = (g_h + gp_h * offset + g2_h * offset**2, gp_h + 2.0 * g2_h * offset)

    def rhs(phi: float, state: NDArray[np.float64]) -> Tuple[float, float]:
        g, gp = float(state[0]), float(state[1])
        return gp, _master_g_second_derivative(preset, phi, g, gp)

    answer = solve_ivp(
        rhs,
        (right, left),
        initial,
        method="DOP853",
        rtol=1.0e-10,
        atol=1.0e-12,
        dense_output=True,
    )
    if not answer.success or answer.sol is None:
        raise RuntimeError(f"DOP853 integration failed: {answer.message}")
    nodes, weights = np.polynomial.legendre.leggauss(240)
    phi = 0.5 * phi_h * (nodes + 1.0)
    weights = 0.5 * phi_h * weights
    g = np.asarray(answer.sol(phi)[0], dtype=float)
    uv_integral = float(
        np.dot(weights, g - 1.0 / ((preset.delta - 4.0) * phi))
    )
    inverse_g_integral = float(np.dot(weights, 1.0 / (6.0 * g)))
    a_h = math.log(phi_h) / (preset.delta - 4.0) + uv_integral
    log_entropy = math.log(2.0 * math.pi) + 3.0 * a_h
    potential_ratio = preset.potential(phi_h) / preset.potential(0.0)
    log_temperature = (
        math.log(phi_h) / (preset.delta - 4.0)
        - math.log(math.pi)
        + math.log(potential_ratio)
        + uv_integral
        + inverse_g_integral
    )
    return (
        ThermodynamicPoint(
            x_h=x_h,
            phi_h=phi_h,
            degree=0,
            temperature=math.exp(log_temperature),
            entropy=math.exp(log_entropy),
        ),
        int(answer.nfev),
    )


def _horizon_series_quadratic(
    preset: PotentialPreset,
    phi_h: float,
) -> Tuple[float, float, float]:
    v = preset.potential(phi_h)
    vp = preset.first_derivative(phi_h)
    vpp = preset.second_derivative(phi_h)
    vppp = preset.third_derivative(phi_h)
    if vp == 0.0:
        raise RuntimeError("V'(phi_H) vanished in the master diagnostic")
    g0 = -v / (3.0 * vp)
    g1 = (v * vpp / vp**2 - 1.0) / 6.0
    a_second = -(
        vpp / vp + v * vppp / vp**2 - 2.0 * v * vpp**2 / vp**3
    ) / 3.0
    a2 = 0.5 * a_second
    g2 = (
        12.0 * g0 * (-a2 + 2.0 * g0 * g1) - 6.0 * g1**2 - g1
    ) / (36.0 * g0)
    return float(g0), float(g1), float(g2)


def _master_g_second_derivative(
    preset: PotentialPreset,
    phi: float,
    g: float,
    g_prime: float,
) -> float:
    v = preset.potential(phi)
    vp = preset.first_derivative(phi)
    vpp = preset.second_derivative(phi)
    a = v / (3.0 * vp)
    a_prime = 1.0 / 3.0 - v * vpp / (3.0 * vp**2)
    denominator = g + a
    c = g_prime / g + 1.0 / (6.0 * g) - 4.0 * g
    remainder = (
        -denominator**2 * (g_prime + 1.0 / 6.0) * g_prime / g**2
        - 4.0 * denominator**2 * g_prime
        + g_prime * (g_prime + a_prime)
        - g_prime * denominator * c
        + g_prime**2
    )
    coefficient = a * denominator / g
    if coefficient == 0.0 or not math.isfinite(coefficient):
        raise RuntimeError("master diagnostic became singular")
    return float(-remainder / coefficient)


def _figure_comparison(
    preset: PotentialPreset,
    sound: Sequence[SoundSpeedPoint],
) -> Dict[str, Any]:
    temperature = np.asarray([item.temperature for item in sound], dtype=float)
    values = np.asarray([item.pchip for item in sound], dtype=float)
    order = np.argsort(temperature)
    temperature = temperature[order]
    values = values[order]
    if preset.figure == 2:
        coordinate = temperature
        anchors = FIGURE_2_ANCHORS
        registration = None
    else:
        curve = PchipInterpolator(temperature, values)
        minimum = minimize_scalar(
            lambda candidate: float(curve(candidate)),
            bounds=(float(temperature[0]), float(temperature[-1])),
            method="bounded",
            options={"xatol": 1.0e-13},
        )
        if not minimum.success:
            raise RuntimeError("QCD-like sound-speed minimum was not resolved")
        minimum_temperature = float(minimum.x)
        t_c_plot = minimum_temperature / DEFAULT_T_C_PLOT_MINIMUM
        coordinate = temperature / t_c_plot
        anchors = FIGURE_3_ANCHORS
        registration = {
            "T_minimum_L": minimum_temperature,
            "minimum_sound_speed_squared": float(minimum.fun),
            "T_c_plot_L": t_c_plot,
            "source_minimum_coordinate": DEFAULT_T_C_PLOT_MINIMUM,
            "interpretation": "plot registration, not a predicted critical temperature",
        }
    curve = PchipInterpolator(coordinate, values, extrapolate=False)
    records: List[Dict[str, float]] = []
    for location, target in anchors.items():
        if not coordinate[0] <= location <= coordinate[-1]:
            raise RuntimeError(
                f"Figure {preset.figure} anchor {location} is not bracketed"
            )
        predicted = float(curve(location))
        records.append(
            {
                "coordinate": location,
                "source_sound_speed_squared": target,
                "computed_sound_speed_squared": predicted,
                "absolute_error": abs(predicted - target),
                "digitization_uncertainty": preset.digitization_uncertainty,
            }
        )
    return {
        "source_figure": preset.figure,
        "coordinate_range": [float(coordinate[0]), float(coordinate[-1])],
        "registration": registration,
        "anchors": records,
        "maximum_anchor_error": max(item["absolute_error"] for item in records),
        "tolerance": preset.figure_tolerance,
    }


def _branch_integrity(points: Sequence[ThermodynamicPoint]) -> bool:
    temperature_differences = np.diff([item.temperature for item in points])
    entropy_differences = np.diff([item.entropy for item in points])
    return bool(
        np.all(temperature_differences < 0.0)
        and np.all(entropy_differences < 0.0)
    )


def _potential_algebra_error(preset: PotentialPreset) -> float:
    expected_ir = 1.0 / 3.0 - preset.gamma**2 / 2.0
    return max(
        abs(preset.potential(0.0) + 12.0),
        abs(preset.second_derivative(0.0) - preset.mass_squared),
        abs(preset.delta * (preset.delta - 4.0) - preset.mass_squared),
        abs(preset.ir_sound_speed_squared - expected_ir),
    )


def _relative_array_change(
    fine: NDArray[np.float64], coarse: NDArray[np.float64]
) -> List[float]:
    return list(
        np.abs(fine - coarse) / np.maximum(np.abs(fine), 1.0e-300)
    )


def _relative_error(left: float, right: float) -> float:
    return abs(left - right) / max(abs(left), abs(right), 1.0e-300)


def _maximum_nested_numeric_difference(left: Any, right: Any) -> float:
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        if set(left) != set(right):
            return math.inf
        return max(
            (_maximum_nested_numeric_difference(left[key], right[key]) for key in left),
            default=0.0,
        )
    if isinstance(left, Sequence) and isinstance(right, Sequence) and not isinstance(left, (str, bytes)):
        if len(left) != len(right):
            return math.inf
        return max(
            (_maximum_nested_numeric_difference(a, b) for a, b in zip(left, right)),
            default=0.0,
        )
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        left_value = float(left)
        right_value = float(right)
        return abs(left_value - right_value) / max(
            1.0, abs(left_value), abs(right_value)
        )
    return 0.0 if left == right else math.inf


def _save_reproduction_plot(payload: Mapping[str, Any], path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib import pyplot as plt
    except ImportError as exc:
        raise RuntimeError(
            "Matplotlib is required for --output-dir; install holoforge[plot]"
        ) from exc
    presets = payload["results"]["presets"]
    figure, axes = plt.subplots(1, 2, figsize=(11.0, 4.4), constrained_layout=True)
    cosh = presets[COSH_CALIBRATION.identifier]
    cosh_curve = cosh["curve"]
    axes[0].plot(
        [item["temperature_L"] for item in cosh_curve],
        [item["sound_speed_squared"] for item in cosh_curve],
        color="#1565c0",
        label="HoloForge coupled spectral",
    )
    axes[0].scatter(
        list(FIGURE_2_ANCHORS),
        list(FIGURE_2_ANCHORS.values()),
        color="black",
        s=18,
        label="source Figure 2 anchors",
        zorder=3,
    )
    axes[0].axhline(1.0 / 3.0, color="0.5", linestyle="--", linewidth=1.0)
    axes[0].set(xlabel=r"$T L$", ylabel=r"$c_s^2$", title="Pure-cosh calibration")
    axes[0].set_xscale("log")
    axes[0].legend(fontsize=8)

    qcd = presets[QCD_LIKE.identifier]
    registration = qcd["figure"]["registration"]
    t_c_plot = registration["T_c_plot_L"]
    qcd_curve = qcd["curve"]
    axes[1].plot(
        [item["temperature_L"] / t_c_plot for item in qcd_curve],
        [item["sound_speed_squared"] for item in qcd_curve],
        color="#c62828",
        label="HoloForge coupled spectral",
    )
    axes[1].scatter(
        list(FIGURE_3_ANCHORS),
        list(FIGURE_3_ANCHORS.values()),
        color="black",
        s=18,
        label="source Figure 3 red-curve anchors",
        zorder=3,
    )
    axes[1].set(
        xlabel=r"$T/T_{c,\mathrm{plot}}$",
        ylabel=r"$c_s^2$",
        title="QCD-like source potential",
    )
    axes[1].set_xlim(0.0, 1.05 * max(FIGURE_3_ANCHORS))
    axes[1].legend(fontsize=8)
    figure.savefig(path, dpi=180)
    plt.close(figure)


def model_card_sha256(path: Path) -> str:
    """Return the digest used by the command adapter and evidence bundles."""

    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _validate_positive(name: str, value: Real) -> None:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a positive finite real number")
    resolved = float(value)
    if not math.isfinite(resolved) or resolved <= 0.0:
        raise ValueError(f"{name} must be a positive finite real number")


def _validate_integer(name: str, value: Integral, *, minimum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{name} must be an integer")
    if int(value) < minimum:
        raise ValueError(f"{name} must be at least {minimum}")


__all__ = [
    "COSH_CALIBRATION",
    "CoupledProfile",
    "CoupledSolverConfig",
    "DEFAULT_BOUNDARY_TOLERANCE",
    "DEFAULT_COLLOCATION_TOLERANCE",
    "DEFAULT_DERIVATIVE_TOLERANCE",
    "DEFAULT_EQUATION_TOLERANCE",
    "DEFAULT_INDEPENDENT_TOLERANCE",
    "DEFAULT_REFINEMENT_TOLERANCE",
    "FIGURE_2_ANCHORS",
    "FIGURE_3_ANCHORS",
    "GUBSER_NELLORE_DEFINITION",
    "QCD_LIKE",
    "coupled_equation_diagnostics",
    "get_preset",
    "profile_thermodynamics",
    "save_gubser_nellore_artifacts",
    "solve_coupled_branch",
    "solve_coupled_profile",
    "verify_gubser_nellore_ed",
]
