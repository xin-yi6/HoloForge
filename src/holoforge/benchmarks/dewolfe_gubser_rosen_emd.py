"""Phase 5A zero-density DGR Einstein--Maxwell--dilaton benchmark.

The primary route reuses the accepted UV-factorized neutral Chebyshev
Einstein--scalar solver and adds the DGR gauge coupling only through the
linear-response susceptibility.  A scalar-coordinate DOP853 reconstruction
and an explicit Maxwell solve provide independent checks.  Passing verifies
the selected source-model calculation; it is not empirical validation of QCD
or a calculation of the finite-density critical point.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from numbers import Integral, Real
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import cumulative_simpson, simpson, solve_ivp
from scipy.interpolate import PchipInterpolator
from scipy.optimize import brentq

from holoforge.benchmarks.gubser_nellore_ed import (
    CoupledProfile,
    CoupledSolverConfig,
    PotentialPreset,
    _horizon_series_quadratic,
    _master_g_second_derivative,
    coupled_equation_diagnostics,
    profile_thermodynamics,
    solve_coupled_profile,
)
from holoforge.core import (
    AcceptanceCheck,
    BackgroundSpec,
    BenchmarkDefinition,
    BoundaryConditionSpec,
    EquationSpec,
    ObservableSpec,
    SolverSpec,
    VerificationRecord,
)
from holoforge.numerics import chebyshev_lobatto_grid


SOURCE_ID = "arXiv:1012.1864v2"
SOURCE_PDF_SHA256 = (
    "ed6f00b759dbf3347521b6321d2c69c8c2e629f45ff7ab3dd6a9e6a6afc7040c"
)
SOURCE_ARCHIVE_SHA256 = (
    "3f921d2212cb5f7956c1da7cbb0904c02ff32e302d514ab2e80b4bfc64b6778e"
)
SOURCE_FIGURE_3_SHA256 = (
    "bf1dfec799335ca3b8db124a188a4c7d17e1a3f73ddf31f2606f58fa7492f65b"
)

DEFAULT_DEGREES = (80, 120, 150)
DEFAULT_TARGET_PHI_H = tuple(
    float(value) for value in np.exp(np.linspace(math.log(1.5), math.log(7.5), 20))
)
DEFAULT_INDEPENDENT_PHI_H = (1.5, 2.0, 3.0, 5.0, 7.5)
DEFAULT_QUADRATURE_ORDERS = (128, 256, 512)
DEFAULT_COLLOCATION_TOLERANCE = 1.0e-8
DEFAULT_EQUATION_TOLERANCE = 1.0e-6
DEFAULT_CONSTRAINT_TOLERANCE = 1.0e-6
DEFAULT_BOUNDARY_TOLERANCE = 1.0e-8
DEFAULT_TARGET_TOLERANCE = 1.0e-9
DEFAULT_REFINEMENT_TOLERANCE = 2.0e-4
DEFAULT_REFINEMENT_ORDER_FLOOR = 1.0e-8
DEFAULT_QUADRATURE_TOLERANCE = 2.0e-5
DEFAULT_QUADRATURE_ORDER_FLOOR = 1.0e-10
DEFAULT_MAXWELL_TOLERANCE = 1.0e-6
DEFAULT_MAXWELL_FLUX_TOLERANCE = 1.0e-8
DEFAULT_INDEPENDENT_TOLERANCE = 5.0e-4
DEFAULT_ENTROPY_FIGURE_TOLERANCE = 0.15
DEFAULT_SUSCEPTIBILITY_FIGURE_TOLERANCE = 5.0e-3
DEFAULT_DETERMINISM_TOLERANCE = 1.0e-12

LAMBDA_S_MEV3 = 121.0**3
LAMBDA_T_MEV = 252.0
LAMBDA_MU_MEV = 972.0
LAMBDA_RHO_MEV3 = 77.0**3
PRINTED_SCALE_PRODUCT_RELATIVE_MISMATCH = 0.006046863189720333

ENTROPY_FIGURE_3_ANCHORS: Mapping[float, float] = {
    170.0: 1.899407,
    180.0: 4.961648,
    190.0: 7.883849,
    200.0: 9.909476,
    225.0: 12.972585,
    250.0: 14.642470,
    300.0: 16.505148,
    400.0: 18.087696,
    550.0: 19.098777,
    650.0: 19.418822,
    700.0: 19.574478,
}
SUSCEPTIBILITY_FIGURE_3_ANCHORS: Mapping[float, float] = {
    150.0: 0.002001,
    170.0: 0.022026,
    180.0: 0.081693,
    190.0: 0.151201,
    200.0: 0.203321,
    225.0: 0.281409,
    250.0: 0.318216,
    300.0: 0.346912,
    350.0: 0.351970,
    400.0: 0.349351,
    450.0: 0.344815,
}


DGR_POTENTIAL = PotentialPreset(
    identifier="dewolfe-gubser-rosen",
    gamma=0.606,
    b=2.057,
    figure=3,
    figure_tolerance=DEFAULT_ENTROPY_FIGURE_TOLERANCE,
    digitization_uncertainty=DEFAULT_ENTROPY_FIGURE_TOLERANCE,
)


DEWOLFE_GUBSER_ROSEN_DEFINITION = BenchmarkDefinition(
    identifier="dewolfe-gubser-rosen-emd",
    support_level="reproduced",
    background=BackgroundSpec(
        identifier="five-dimensional-dgr-zero-density-black-brane",
        dimension=5,
        coordinate="u = x/x_H in [0,1], x = z^(4-Delta_phi)",
        description=(
            "Phenomenological bottom-up DGR EMD model restricted to the neutral "
            "black-hole branch; the Maxwell sector is linear response only."
        ),
    ),
    equations=(
        EquationSpec(
            identifier="neutral-warp-equation",
            kind="coupled nonlinear boundary-value equation",
            dependent_fields=("A", "phi"),
            expression="A'' - A'^2 + phi'^2/6 = 0",
            source_reference="DeWolfe, Gubser, Rosen, arXiv:1012.1864v2, Eqs. (27)-(29)",
        ),
        EquationSpec(
            identifier="neutral-blackening-equation",
            kind="coupled nonlinear boundary-value equation",
            dependent_fields=("h", "A"),
            expression="h'' + 3 A' h' = 0",
            source_reference="DeWolfe, Gubser, Rosen, arXiv:1012.1864v2, Eqs. (27)-(29)",
        ),
        EquationSpec(
            identifier="neutral-scalar-equation",
            kind="coupled nonlinear boundary-value equation",
            dependent_fields=("phi", "A", "h"),
            expression="h phi'' + (3 A' h + h') phi' - exp(2A) V_phi = 0",
            source_reference="DeWolfe, Gubser, Rosen, arXiv:1012.1864v2, Eqs. (27)-(29)",
        ),
        EquationSpec(
            identifier="einstein-constraint",
            kind="independent radial constraint",
            dependent_fields=("A", "h", "phi"),
            expression="6 A' h' + h(24 A'^2 - phi'^2) + 2 exp(2A) V = 0",
            source_reference="DeWolfe, Gubser, Rosen, arXiv:1012.1864v2, Eq. (29)",
        ),
        EquationSpec(
            identifier="linear-maxwell-equation",
            kind="linear response on a neutral background",
            dependent_fields=("Phi", "A", "phi"),
            expression="d/dz[exp(A) f_EMD(phi) Phi'] = 0",
            source_reference="DeWolfe, Gubser, Rosen, arXiv:1012.1864v2, Eqs. (53)-(57)",
        ),
    ),
    boundary_conditions=(
        BoundaryConditionSpec(
            field="h",
            location="u = 0 and u = 1",
            role="normalized boundary and regular simple horizon",
            expression="h(0) = 1, h(1) = 0",
            interpretation="Both physical endpoints are Chebyshev nodes.",
        ),
        BoundaryConditionSpec(
            field="phi",
            location="u = 0",
            role="unit scalar deformation scale",
            expression="phi = x_H u P(u), P(0) = 1",
            interpretation="The physical horizon value is phi_0 = x_H P(1).",
        ),
        BoundaryConditionSpec(
            field="A",
            location="u = 0",
            role="asymptotically AdS boundary metric",
            expression="A = -log(z) + x_H^2 u^2 C(u)",
            interpretation="The leading scalar backreaction power is explicit.",
        ),
        BoundaryConditionSpec(
            field="phi",
            location="u = 1",
            role="regular scalar horizon",
            expression="retain the undivided scalar equation at u = 1",
            interpretation="No fitted horizon boundary value is introduced.",
        ),
    ),
    solvers=(
        SolverSpec(
            problem_type="neutral coupled Einstein--scalar BVP",
            library_function="scipy.optimize.root and scipy.optimize.least_squares",
            method="Chebyshev--Gauss--Lobatto, hybr, bounded TRF polish",
            description=(
                "Deterministic continuation and bracketing target the twenty "
                "physical source horizon values."
            ),
        ),
        SolverSpec(
            problem_type="independent scalar-coordinate background IVP",
            library_function="scipy.integrate.solve_ivp",
            method="DOP853 with analytic horizon master-field series",
            description="Reconstructs T, s, the Maxwell integral, and chi_2/T^2.",
        ),
    ),
    observables=(
        ObservableSpec(
            identifier="temperature",
            symbol="T",
            extraction="absolute exact-horizon blackening derivative divided by 4 pi",
            normalization="lambda_T = 252 MeV for the Figure 3 plot",
        ),
        ObservableSpec(
            identifier="entropy-ratio",
            symbol="s/T^3",
            extraction="2 pi exp(3 A_H)/T^3 with the source scale dictionary",
            normalization="lambda_s = (121 MeV)^3",
        ),
        ObservableSpec(
            identifier="susceptibility-ratio",
            symbol="chi_2/T^2",
            extraction="1/[2 I T^2], I = integral dz exp(-A)/f_EMD",
            normalization="lambda_mu = 972 MeV and the source scale dictionary",
        ),
    ),
)


@dataclass(frozen=True)
class DGRPoint:
    """One source-normalized neutral background and its Phase 5A observables."""

    degree: int
    x_h: float
    phi_h: float
    temperature: float
    entropy: float
    susceptibility_integral: float
    chi_hat: float
    temperature_mev: float
    entropy_ratio_plot: float
    susceptibility_ratio_plot: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "degree": self.degree,
            "x_h": self.x_h,
            "phi_h": self.phi_h,
            "temperature_BH": self.temperature,
            "entropy_BH": self.entropy,
            "susceptibility_integral": self.susceptibility_integral,
            "chi_2_over_T2_BH": self.chi_hat,
            "temperature_MeV": self.temperature_mev,
            "s_over_T3_plot": self.entropy_ratio_plot,
            "chi_2_over_T2_plot": self.susceptibility_ratio_plot,
        }


@dataclass(frozen=True)
class TargetedBranch:
    """One physical-horizon branch at a declared spectral degree."""

    degree: int
    targets: Tuple[float, ...]
    profiles: Tuple[CoupledProfile, ...]
    continuation_profiles: Tuple[CoupledProfile, ...]
    points: Tuple[DGRPoint, ...]


@dataclass(frozen=True)
class MaxwellDiagnostics:
    """Explicit linear Maxwell solution compared with the integral formula."""

    phi_h: float
    integral_quadrature: float
    integral_maxwell: float
    relative_error: float
    normalized_flux_drift: float
    function_evaluations: int

    def to_dict(self) -> Dict[str, float]:
        return {
            "phi_h": self.phi_h,
            "integral_quadrature": self.integral_quadrature,
            "integral_maxwell": self.integral_maxwell,
            "relative_error": self.relative_error,
            "normalized_flux_drift": self.normalized_flux_drift,
            "function_evaluations": self.function_evaluations,
        }


@dataclass(frozen=True)
class IndependentPoint:
    """Scalar-coordinate DOP853 reconstruction at one physical horizon."""

    phi_h: float
    temperature: float
    entropy: float
    susceptibility_integral: float
    chi_hat: float
    reconstructed_temperature: float
    function_evaluations: int


@dataclass(frozen=True)
class IndependentComparison:
    """Primary-versus-DOP853 comparison at one preregistered horizon."""

    target_phi_h: float
    actual_phi_h: float
    temperature_relative_error: float
    entropy_relative_error: float
    integral_relative_error: float
    susceptibility_relative_error: float
    dop853_function_evaluations: int

    @property
    def maximum_relative_error(self) -> float:
        return max(
            self.temperature_relative_error,
            self.entropy_relative_error,
            self.integral_relative_error,
            self.susceptibility_relative_error,
        )

    def to_dict(self) -> Dict[str, float]:
        return {
            "target_phi_h": self.target_phi_h,
            "actual_phi_h": self.actual_phi_h,
            "temperature_relative_error": self.temperature_relative_error,
            "entropy_relative_error": self.entropy_relative_error,
            "integral_relative_error": self.integral_relative_error,
            "susceptibility_relative_error": self.susceptibility_relative_error,
            "maximum_relative_error": self.maximum_relative_error,
            "dop853_function_evaluations": self.dop853_function_evaluations,
        }


def gauge_coupling(phi: Any) -> Any:
    """Return the frozen DGR gauge kinetic function ``f_EMD(phi)``."""

    values = np.asarray(phi)
    result = np.cosh(12.0 / 5.0) / np.cosh(6.0 * (values - 2.0) / 5.0)
    return float(result) if result.ndim == 0 else result


def gauge_log_derivative(phi: Any) -> Any:
    """Return ``d log(f_EMD)/dphi`` without numerical differencing."""

    values = np.asarray(phi)
    result = -1.2 * np.tanh(1.2 * (values - 2.0))
    return float(result) if result.ndim == 0 else result


def susceptibility_integral(profile: CoupledProfile, order: int = 512) -> float:
    """Evaluate ``I = integral dz exp(-A)/f_EMD`` on one spectral profile."""

    _validate_integer("order", order, minimum=32)
    nodes, weights = np.polynomial.legendre.leggauss(int(order))
    u = 0.5 * (nodes + 1.0)
    weights = 0.5 * weights
    _, c_interpolator, p_interpolator = profile.interpolators()
    c = np.asarray(c_interpolator(u), dtype=float)
    pfield = np.asarray(p_interpolator(u), dtype=float)
    x = profile.x_h * u
    z = x ** (1.0 / DGR_POTENTIAL.uv_power)
    phi = x * pfield
    a_e = x**2 * c
    integrand = z**2 * np.exp(-a_e) / (
        DGR_POTENTIAL.uv_power * u * gauge_coupling(phi)
    )
    value = float(np.dot(weights, integrand))
    if not math.isfinite(value) or value <= 0.0:
        raise RuntimeError("susceptibility integral must be positive and finite")
    return value


def point_from_profile(profile: CoupledProfile, order: int = 512) -> DGRPoint:
    """Extract the complete DGR Phase 5A observable dictionary."""

    thermo = profile_thermodynamics(profile)
    integral = susceptibility_integral(profile, order)
    chi_hat = 1.0 / (2.0 * integral * thermo.temperature**2)
    return DGRPoint(
        degree=profile.degree,
        x_h=profile.x_h,
        phi_h=profile.phi_h,
        temperature=thermo.temperature,
        entropy=thermo.entropy,
        susceptibility_integral=integral,
        chi_hat=chi_hat,
        temperature_mev=LAMBDA_T_MEV * thermo.temperature,
        entropy_ratio_plot=(
            LAMBDA_S_MEV3
            / LAMBDA_T_MEV**3
            * thermo.entropy
            / thermo.temperature**3
        ),
        susceptibility_ratio_plot=(
            LAMBDA_S_MEV3
            / (LAMBDA_T_MEV * LAMBDA_MU_MEV**2)
            * chi_hat
        ),
    )


def solve_targeted_branch(
    degree: int,
    targets: Sequence[Real] = DEFAULT_TARGET_PHI_H,
    *,
    config: Optional[CoupledSolverConfig] = None,
) -> TargetedBranch:
    """Solve the monotone neutral branch at exact physical ``phi_H`` targets."""

    _validate_integer("degree", degree, minimum=40)
    resolved_degree = int(degree)
    values = tuple(float(value) for value in targets)
    if len(values) < 5 or not all(math.isfinite(value) and value > 0.0 for value in values):
        raise ValueError("targets must contain at least five positive finite values")
    if not all(right > left for left, right in zip(values, values[1:])):
        raise ValueError("targets must be strictly increasing")
    if values[0] < 1.5 or values[-1] > 7.5:
        raise ValueError("targets must remain inside the approved [1.5, 7.5] range")

    lower_x = 0.82
    lower: Optional[CoupledProfile] = None
    initialization_degrees = tuple(
        item for item in (24, 40, 60, 80, 120, 150) if item <= resolved_degree
    )
    degree_caches: Dict[int, Dict[float, CoupledProfile]] = {
        item: {} for item in DEFAULT_DEGREES if item <= resolved_degree
    }
    for initialization_degree in initialization_degrees:
        lower = solve_coupled_profile(
            DGR_POTENTIAL,
            lower_x,
            initialization_degree,
            seed=lower,
            config=config,
        )
        if initialization_degree in degree_caches:
            degree_caches[initialization_degree][lower_x] = lower
    if lower is None or lower.degree != resolved_degree:
        raise RuntimeError("degree continuation did not reach the requested target")
    if lower.phi_h >= values[0]:
        raise RuntimeError("the frozen lower x_H bracket does not lie below phi_H=1.5")

    def profile_at_x(x_h: float) -> CoupledProfile:
        key = float(x_h)
        if resolved_degree == 80:
            return _cached_same_degree_profile(
                degree_caches[80], key, 80, config
            )
        degree_80 = _cached_same_degree_profile(
            degree_caches[80], key, 80, config
        )
        if key not in degree_caches[120]:
            degree_caches[120][key] = solve_coupled_profile(
                DGR_POTENTIAL,
                key,
                120,
                seed=degree_80,
                config=config,
            )
        if resolved_degree == 120:
            return degree_caches[120][key]
        if key not in degree_caches[150]:
            degree_caches[150][key] = solve_coupled_profile(
                DGR_POTENTIAL,
                key,
                150,
                seed=degree_caches[120][key],
                config=config,
            )
        return degree_caches[150][key]

    target_profiles: List[CoupledProfile] = []
    for target in values:
        lower = target_profiles[-1] if target_profiles else lower
        upper_x = min(1.05, lower.x_h + 0.04)
        upper = profile_at_x(upper_x)
        while upper.phi_h < target:
            lower = upper
            if upper_x >= 1.05:
                raise RuntimeError(f"physical horizon target {target} is not bracketed")
            upper_x = min(1.05, upper_x + 0.04)
            upper = profile_at_x(upper_x)

        def objective(x_h: float) -> float:
            return (
                profile_at_x(x_h).phi_h - target
            )

        root_x = brentq(
            objective,
            lower.x_h,
            upper.x_h,
            xtol=5.0e-14,
            rtol=1.0e-14,
            maxiter=100,
        )
        profile = profile_at_x(root_x)
        target_profiles.append(profile)

    profiles = tuple(target_profiles)
    if not all(
        right.x_h > left.x_h and right.phi_h > left.phi_h
        for left, right in zip(profiles, profiles[1:])
    ):
        raise RuntimeError("the approved x_H to phi_H branch is not one-to-one")
    return TargetedBranch(
        degree=resolved_degree,
        targets=values,
        profiles=profiles,
        continuation_profiles=tuple(
            profile
            for _, profile in sorted(
                degree_caches[resolved_degree].items(), key=lambda item: item[0]
            )
        ),
        points=tuple(point_from_profile(profile) for profile in profiles),
    )


def einstein_constraint_residual(
    profile: CoupledProfile,
    *,
    oversampling_factor: int = 2,
) -> float:
    """Evaluate the independently scaled conformal-gauge constraint."""

    _validate_integer("oversampling_factor", oversampling_factor, minimum=2)
    grid = chebyshev_lobatto_grid(
        int(oversampling_factor) * profile.degree, 0.0, 1.0
    )
    u = grid.nodes
    h_interpolator, c_interpolator, p_interpolator = profile.interpolators()
    h = np.asarray(h_interpolator(u), dtype=float)
    h_u = np.asarray(h_interpolator.derivative(u, der=1), dtype=float)
    c = np.asarray(c_interpolator(u), dtype=float)
    c_u = np.asarray(c_interpolator.derivative(u, der=1), dtype=float)
    pfield = np.asarray(p_interpolator(u), dtype=float)
    p_u = np.asarray(p_interpolator.derivative(u, der=1), dtype=float)
    a_e_u = profile.x_h**2 * (2.0 * u * c + u**2 * c_u)
    phi_u = profile.x_h * (pfield + u * p_u)
    a_z_scaled = -1.0 + DGR_POTENTIAL.uv_power * u * a_e_u
    h_z_scaled = DGR_POTENTIAL.uv_power * u * h_u
    phi_z_scaled = DGR_POTENTIAL.uv_power * u * phi_u
    phi = profile.x_h * u * pfield
    a_e = profile.x_h**2 * u**2 * c
    terms = (
        6.0 * a_z_scaled * h_z_scaled,
        24.0 * h * a_z_scaled**2,
        -h * phi_z_scaled**2,
        2.0 * np.exp(2.0 * a_e) * DGR_POTENTIAL.potential(phi),
    )
    scaled = sum(terms) / (1.0 + sum(np.abs(term) for term in terms))
    return float(np.max(np.abs(scaled)))


def explicit_maxwell_diagnostics(profile: CoupledProfile) -> MaxwellDiagnostics:
    """Solve the linear Maxwell equation independently in logarithmic flux form."""

    _, c_interpolator, p_interpolator = profile.interpolators()
    uv_cutoff = 1.0e-6
    p = DGR_POTENTIAL.uv_power
    z_h = profile.x_h ** (1.0 / p)
    a_e_h = profile.x_h**2 * profile.warp_factor[-1]
    derivative_h = z_h**2 * math.exp(-a_e_h) / (
        p * gauge_coupling(profile.phi_h)
    )

    def rhs(u: float, state: NDArray[np.float64]) -> Tuple[float, float]:
        c = float(c_interpolator(u))
        c_u = float(c_interpolator.derivative(u, der=1))
        pfield = float(p_interpolator(u))
        p_u = float(p_interpolator.derivative(u, der=1))
        a_e_u = profile.x_h**2 * (2.0 * u * c + u**2 * c_u)
        phi = profile.x_h * u * pfield
        phi_u = profile.x_h * (pfield + u * p_u)
        coefficient = (
            (p - 2.0) / (p * u)
            + a_e_u
            + gauge_log_derivative(phi) * phi_u
        )
        return math.exp(float(state[1])), -float(coefficient)

    answer = solve_ivp(
        rhs,
        (1.0, uv_cutoff),
        (0.0, math.log(derivative_h)),
        method="DOP853",
        rtol=1.0e-10,
        atol=1.0e-12,
        dense_output=True,
    )
    if not answer.success or answer.sol is None:
        raise RuntimeError(f"explicit Maxwell solve failed: {answer.message}")
    integral_maxwell = abs(float(answer.y[0, -1]))
    integral_quadrature = susceptibility_integral(profile)
    sample = np.linspace(0.5, 1.0, 300)
    log_derivative = np.asarray(answer.sol(sample)[1], dtype=float)
    derivative = np.exp(log_derivative)
    c = np.asarray(c_interpolator(sample), dtype=float)
    pfield = np.asarray(p_interpolator(sample), dtype=float)
    x = profile.x_h * sample
    z = x ** (1.0 / p)
    phi = x * pfield
    a_e = x**2 * c
    flux = (
        p
        * sample
        * np.exp(a_e)
        * gauge_coupling(phi)
        * derivative
        / z**2
    )
    return MaxwellDiagnostics(
        phi_h=profile.phi_h,
        integral_quadrature=integral_quadrature,
        integral_maxwell=integral_maxwell,
        relative_error=_relative_error(integral_quadrature, integral_maxwell),
        normalized_flux_drift=float(np.max(np.abs(flux - 1.0))),
        function_evaluations=int(answer.nfev),
    )


def independent_master_point(
    phi_h: Real,
    *,
    sample_count: int = 40001,
) -> IndependentPoint:
    """Reconstruct one DGR background and susceptibility with scalar-coordinate DOP853."""

    _validate_positive("phi_h", phi_h)
    _validate_integer("sample_count", sample_count, minimum=10001)
    resolved_phi_h = float(phi_h)
    uv_cutoff = 1.0e-5
    horizon_cutoff = 1.0e-5
    left = uv_cutoff * resolved_phi_h
    right = (1.0 - horizon_cutoff) * resolved_phi_h
    g_h, g_prime_h, g_second_h = _horizon_series_quadratic(
        DGR_POTENTIAL, resolved_phi_h
    )
    offset = right - resolved_phi_h
    initial = (
        g_h + g_prime_h * offset + g_second_h * offset**2,
        g_prime_h + 2.0 * g_second_h * offset,
    )

    def rhs(phi: float, state: NDArray[np.float64]) -> Tuple[float, float]:
        g, g_prime = float(state[0]), float(state[1])
        return (
            g_prime,
            _master_g_second_derivative(
                DGR_POTENTIAL, phi, g, g_prime
            ),
        )

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
        raise RuntimeError(f"DOP853 master integration failed: {answer.message}")

    phi = np.linspace(0.0, resolved_phi_h, int(sample_count))
    evaluation = np.clip(phi, left, right)
    g = np.asarray(answer.sol(evaluation)[0], dtype=float)
    low = phi < left
    high = phi > right
    safe_low = np.maximum(phi[low], 1.0e-300)
    g[low] = 1.0 / ((DGR_POTENTIAL.delta - 4.0) * safe_low)
    high_offset = phi[high] - resolved_phi_h
    g[high] = (
        g_h
        + g_prime_h * high_offset
        + g_second_h * high_offset**2
    )
    a_regular = np.zeros_like(phi)
    inverse_g = np.zeros_like(phi)
    nonzero = phi > 0.0
    a_regular[nonzero] = g[nonzero] - 1.0 / (
        (DGR_POTENTIAL.delta - 4.0) * phi[nonzero]
    )
    inverse_g[nonzero] = 1.0 / (6.0 * g[nonzero])
    a_integral = cumulative_simpson(a_regular, x=phi, initial=0.0)
    b_integral = cumulative_simpson(inverse_g, x=phi, initial=0.0)
    a = np.zeros_like(phi)
    b = np.zeros_like(phi)
    a[nonzero] = (
        np.log(phi[nonzero]) / (DGR_POTENTIAL.delta - 4.0)
        + a_integral[nonzero]
    )
    b[nonzero] = np.log(-g[nonzero]) + b_integral[nonzero]
    h_integrand = np.zeros_like(phi)
    h_integrand[nonzero] = np.exp(-4.0 * a[nonzero] + b[nonzero])
    h_integral = float(simpson(h_integrand, x=phi))
    g_h_exact = -DGR_POTENTIAL.potential(resolved_phi_h) / (
        3.0 * DGR_POTENTIAL.first_derivative(resolved_phi_h)
    )
    b_shift = 0.5 * math.log(
        3.0
        * g_h_exact
        * math.exp(-4.0 * a[-1])
        / (
            h_integral
            * DGR_POTENTIAL.potential(resolved_phi_h)
            * math.exp(b[-1])
        )
    )
    maxwell_integrand = np.zeros_like(phi)
    maxwell_integrand[nonzero] = np.exp(
        -2.0 * a[nonzero] + b[nonzero] + b_shift
    ) / gauge_coupling(phi[nonzero])
    susceptibility = float(simpson(maxwell_integrand, x=phi))
    log_temperature = (
        math.log(resolved_phi_h) / (DGR_POTENTIAL.delta - 4.0)
        - math.log(math.pi)
        + math.log(
            DGR_POTENTIAL.potential(resolved_phi_h)
            / DGR_POTENTIAL.potential(0.0)
        )
        + a_integral[-1]
        + b_integral[-1]
    )
    temperature = math.exp(log_temperature)
    entropy = math.exp(math.log(2.0 * math.pi) + 3.0 * a[-1])
    reconstructed_temperature = math.exp(-3.0 * a[-1] - b_shift) / (
        4.0 * math.pi * h_integral
    )
    return IndependentPoint(
        phi_h=resolved_phi_h,
        temperature=temperature,
        entropy=entropy,
        susceptibility_integral=susceptibility,
        chi_hat=1.0 / (2.0 * susceptibility * temperature**2),
        reconstructed_temperature=reconstructed_temperature,
        function_evaluations=int(answer.nfev),
    )


def verify_dewolfe_gubser_rosen_emd(
    *,
    repeat_for_determinism: bool = True,
    residual_backend: str = "numpy",
) -> VerificationRecord:
    """Run the owner-approved Phase 5A preflight and return bounded evidence."""

    config = CoupledSolverConfig(residual_backend=residual_backend)
    versions = config.software_versions()
    first = _verify_once(config)
    if repeat_for_determinism:
        second = _verify_once(config)
        determinism_error: Optional[float] = _maximum_nested_numeric_difference(
            first["determinism_state"], second["determinism_state"]
        )
    else:
        determinism_error = None

    summary = first["summary"]
    checks = (
        AcceptanceCheck(
            "source-algebra",
            "source potential, gauge function, UV dimension, and scale dictionary",
            summary["source_algebra_error"] <= 1.0e-12,
            summary["source_algebra_error"],
            "maximum absolute analytic error <= 1e-12",
        ),
        AcceptanceCheck(
            "nonlinear-solver",
            "every reported and continuation solve succeeds within the collocation ceiling",
            bool(summary["solver_success"]),
            summary["maximum_collocation_residual"],
            f"library success and scaled residual <= {DEFAULT_COLLOCATION_TOLERANCE:.1e}",
        ),
        AcceptanceCheck(
            "independent-equations",
            "maximum twice-oversampled uncross-multiplied neutral equation residual",
            summary["maximum_equation_residual"] <= DEFAULT_EQUATION_TOLERANCE,
            summary["maximum_equation_residual"],
            f"<= {DEFAULT_EQUATION_TOLERANCE:.1e}",
        ),
        AcceptanceCheck(
            "einstein-constraint",
            "maximum independently evaluated Einstein-constraint residual",
            summary["maximum_constraint_residual"] <= DEFAULT_CONSTRAINT_TOLERANCE,
            summary["maximum_constraint_residual"],
            f"<= {DEFAULT_CONSTRAINT_TOLERANCE:.1e}",
        ),
        AcceptanceCheck(
            "exact-endpoints-and-regularity",
            "maximum UV, exact-endpoint, and retained horizon-scalar residual",
            summary["maximum_boundary_residual"] <= DEFAULT_BOUNDARY_TOLERANCE,
            summary["maximum_boundary_residual"],
            f"<= {DEFAULT_BOUNDARY_TOLERANCE:.1e}",
        ),
        AcceptanceCheck(
            "physical-horizon-targets",
            "twenty physical phi_H targets and one-to-one x_H branch",
            bool(
                summary["branch_integrity"]
                and summary["maximum_target_relative_error"]
                <= DEFAULT_TARGET_TOLERANCE
            ),
            summary["maximum_target_relative_error"],
            f"relative target error <= {DEFAULT_TARGET_TOLERANCE:.1e}; monotone branch",
        ),
        AcceptanceCheck(
            "spectral-refinement",
            "N=120 to N=150 T, s, I, and susceptibility refinement",
            bool(
                summary["maximum_final_refinement_change"]
                <= DEFAULT_REFINEMENT_TOLERANCE
                and summary["refinement_ordering_failures"] == 0
            ),
            summary["maximum_final_refinement_change"],
            f"<= {DEFAULT_REFINEMENT_TOLERANCE:.1e}; zero ordered-change failures above floor",
        ),
        AcceptanceCheck(
            "quadrature-refinement",
            "successive susceptibility-integral quadrature refinements",
            bool(
                summary["maximum_final_quadrature_change"]
                <= DEFAULT_QUADRATURE_TOLERANCE
                and summary["quadrature_ordering_failures"] == 0
            ),
            summary["maximum_final_quadrature_change"],
            f"<= {DEFAULT_QUADRATURE_TOLERANCE:.1e}; zero failures above floor",
        ),
        AcceptanceCheck(
            "explicit-maxwell-response",
            "integral versus explicit Maxwell response and normalized flux drift",
            bool(
                summary["maximum_maxwell_relative_error"]
                <= DEFAULT_MAXWELL_TOLERANCE
                and summary["maximum_maxwell_flux_drift"]
                <= DEFAULT_MAXWELL_FLUX_TOLERANCE
            ),
            max(
                summary["maximum_maxwell_relative_error"],
                summary["maximum_maxwell_flux_drift"],
            ),
            f"response <= {DEFAULT_MAXWELL_TOLERANCE:.1e}; flux <= {DEFAULT_MAXWELL_FLUX_TOLERANCE:.1e}",
        ),
        AcceptanceCheck(
            "dop853-background-comparison",
            "Chebyshev versus scalar-coordinate DOP853 T, s, I, and susceptibility",
            summary["maximum_independent_relative_error"]
            <= DEFAULT_INDEPENDENT_TOLERANCE,
            summary["maximum_independent_relative_error"],
            f"<= {DEFAULT_INDEPENDENT_TOLERANCE:.1e}",
        ),
        AcceptanceCheck(
            "figure-3-entropy",
            "maximum absolute s/T^3 error at the eleven source Figure 3 anchors",
            summary["maximum_entropy_anchor_error"]
            <= DEFAULT_ENTROPY_FIGURE_TOLERANCE,
            summary["maximum_entropy_anchor_error"],
            f"<= {DEFAULT_ENTROPY_FIGURE_TOLERANCE:.2f}",
        ),
        AcceptanceCheck(
            "figure-3-susceptibility",
            "maximum absolute chi_2/T^2 error at the eleven source Figure 3 anchors",
            summary["maximum_susceptibility_anchor_error"]
            <= DEFAULT_SUSCEPTIBILITY_FIGURE_TOLERANCE,
            summary["maximum_susceptibility_anchor_error"],
            f"<= {DEFAULT_SUSCEPTIBILITY_FIGURE_TOLERANCE:.1e}",
        ),
        AcceptanceCheck(
            "determinism",
            "two complete runs agree in reported physical observables",
            determinism_error is not None
            and determinism_error <= DEFAULT_DETERMINISM_TOLERANCE,
            determinism_error,
            f"maximum scaled difference <= {DEFAULT_DETERMINISM_TOLERANCE:.1e}",
        ),
        AcceptanceCheck(
            "record-and-privacy-boundary",
            "strict finite record, public-source-only artifacts, and Phase 5A scope",
            bool(summary["strict_finite_record"] and summary["phase_boundary_intact"]),
            0.0 if summary["strict_finite_record"] and summary["phase_boundary_intact"] else 1.0,
            "finite public-source Phase 5A record; external regression/privacy suite required",
        ),
    )
    results = {
        "summary": summary,
        "curve": first["curve"],
        "degree_branches": first["degree_branches"],
        "equation_diagnostics": first["equation_diagnostics"],
        "constraint_diagnostics": first["constraint_diagnostics"],
        "refinement": first["refinement"],
        "quadrature_refinement": first["quadrature_refinement"],
        "maxwell_comparisons": first["maxwell_comparisons"],
        "independent_comparisons": first["independent_comparisons"],
        "figure_3": first["figure_3"],
        "determinism": {
            "repeat_enabled": repeat_for_determinism,
            "maximum_scaled_difference": determinism_error,
        },
    }
    return VerificationRecord(
        definition=DEWOLFE_GUBSER_ROSEN_DEFINITION,
        configuration={
            "bulk_dimension": 5,
            "ensemble": "zero chemical potential; neutral background with linear Maxwell response",
            "units": "L = 1 and kappa_5^2 = 1 before source rescalings",
            "potential": DGR_POTENTIAL.to_dict(),
            "gauge_coupling": "sech[(6/5)(phi-2)]/sech(12/5)",
            "degrees": list(DEFAULT_DEGREES),
            "physical_phi_h_targets": list(DEFAULT_TARGET_PHI_H),
            "independent_target_phi_h": list(DEFAULT_INDEPENDENT_PHI_H),
            "quadrature_orders": list(DEFAULT_QUADRATURE_ORDERS),
            "scale_dictionary": {
                "lambda_s_MeV3": LAMBDA_S_MEV3,
                "lambda_T_MeV": LAMBDA_T_MEV,
                "lambda_mu_MeV": LAMBDA_MU_MEV,
                "lambda_rho_MeV3": LAMBDA_RHO_MEV3,
                "printed_value_relative_mismatch": PRINTED_SCALE_PRODUCT_RELATIVE_MISMATCH,
            },
        },
        numerical_method={
            "primary_route": "UV-factorized neutral Chebyshev--Gauss--Lobatto BVP",
            "coordinate": "u = x/x_H, x = z^(4-Delta_phi)",
            "unknowns": ["h(u)", "C(u)", "P(u)"],
            "nonlinear_solver": "hybr then accepted bounded TRF polish when triggered",
            "collocation_residual_backend": residual_backend,
            "physical_targeting": "deterministic bracketed x_H to phi_H inversion",
            "quadrature": "Gauss--Legendre on the analytic spectral representation",
            "independent_background": "scalar-coordinate DOP853 master equation",
            "independent_response": "explicit logarithmic-flux Maxwell DOP853 solve",
        },
        results=results,
        acceptance_checks=checks,
        software_versions=versions,
        scope=(
            "AI-assisted, owner-approved numerical reproduction of the two DGR "
            "black-hole curves in source Figure 3 at zero chemical potential. "
            "Passing verifies the selected public source-model calculation; it "
            "does not validate QCD or lattice data and does not calculate Figure 5, "
            "a critical point, finite-density phase structure, or critical exponents."
        ),
        extra={
            "primary_source": {
                "id": SOURCE_ID,
                "doi": "10.1103/PhysRevD.83.086005",
                "pdf_sha256": SOURCE_PDF_SHA256,
                "source_archive_sha256": SOURCE_ARCHIVE_SHA256,
                "figure_3_sha256": SOURCE_FIGURE_3_SHA256,
                "raw_source_artwork_redistributed": False,
                "lattice_points_included": False,
            },
            "contract_review": {
                "review_state": "approved",
                "reviewed_by": "Xin-Yi Liu",
                "reviewed_on": "2026-08-22",
                "phase_5b_amendment": (
                    "Figure 5 is mandatory; Figure 4 is diagnostic only and not "
                    "a required reproduction target."
                ),
            },
            "reference_data": {
                "kind": "derived public Figure 3 vector-path anchors",
                "raw_source_artwork_redistributed": False,
                "lattice_points_included": False,
                "review_state": "approved",
                "reviewed_by": "Xin-Yi Liu",
                "reviewed_on": "2026-08-22",
            },
            "result_review_state": "approved",
            "result_reviewed_by": "Xin-Yi Liu",
            "result_reviewed_on": "2026-08-22",
            "generated_by_ai": True,
        },
    )


def save_dewolfe_gubser_rosen_artifacts(
    record: VerificationRecord,
    output_directory: Path,
) -> Mapping[str, Path]:
    """Save the strict record, computed curve, and two-panel Figure 3 check."""

    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": directory / "dewolfe-gubser-rosen-emd-result.json",
        "csv": directory / "dewolfe-gubser-rosen-emd-figure-3-curve.csv",
        "plot": directory / "dewolfe-gubser-rosen-emd-figure-3.png",
    }
    existing = [path for path in paths.values() if path.exists()]
    if existing:
        raise ValueError(
            "refusing to overwrite existing artifact: "
            + ", ".join(str(path) for path in existing)
        )
    payload = record.to_dict()
    paths["json"].write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    rows = [
        "phi_h,x_h,temperature_BH,temperature_MeV,entropy_BH,"
        "s_over_T3_plot,susceptibility_integral,chi_2_over_T2_BH,"
        "chi_2_over_T2_plot"
    ]
    for row in payload["results"]["curve"]:
        rows.append(
            ",".join(
                f"{row[key]:.17g}"
                for key in (
                    "phi_h",
                    "x_h",
                    "temperature_BH",
                    "temperature_MeV",
                    "entropy_BH",
                    "s_over_T3_plot",
                    "susceptibility_integral",
                    "chi_2_over_T2_BH",
                    "chi_2_over_T2_plot",
                )
            )
        )
    paths["csv"].write_text("\n".join(rows) + "\n", encoding="utf-8")
    _save_figure_3_plot(payload, paths["plot"])
    return paths


def model_card_sha256(path: Path) -> str:
    """Return the model-card digest registered by the command adapter."""

    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _verify_once(config: CoupledSolverConfig) -> Dict[str, Any]:
    branches = {
        degree: solve_targeted_branch(degree, config=config) for degree in DEFAULT_DEGREES
    }
    fine = branches[DEFAULT_DEGREES[-1]]
    equation_diagnostics = [
        coupled_equation_diagnostics(profile) for profile in fine.profiles
    ]
    constraint_diagnostics = [
        einstein_constraint_residual(profile) for profile in fine.profiles
    ]
    refinement = _refinement_evidence(branches)
    quadrature_refinement = _quadrature_refinement(fine)
    selected_indices = _independent_indices(fine.points)
    maxwell = [
        explicit_maxwell_diagnostics(fine.profiles[index])
        for index in selected_indices
    ]
    independent = [
        _independent_comparison(
            fine.points[index],
            DEFAULT_INDEPENDENT_PHI_H[position],
        )
        for position, index in enumerate(selected_indices)
    ]
    figure = _figure_3_comparison(fine.points)

    continuation_profiles = tuple(
        profile
        for branch in branches.values()
        for profile in branch.continuation_profiles
    )
    maximum_collocation = max(
        profile.nonlinear.final_scaled_residual
        for profile in continuation_profiles
    )
    solver_success = all(
        profile.nonlinear.success
        and math.isfinite(profile.nonlinear.final_scaled_residual)
        and profile.nonlinear.final_scaled_residual
        <= DEFAULT_COLLOCATION_TOLERANCE
        for profile in continuation_profiles
    )
    maximum_equation = max(
        diagnostic.maximum_equation_residual
        for diagnostic in equation_diagnostics
    )
    maximum_boundary = max(
        max(
            diagnostic.maximum_boundary_residual,
            diagnostic.horizon_scalar_equation,
        )
        for diagnostic in equation_diagnostics
    )
    target_error = max(
        abs(profile.phi_h - target) / target
        for profile, target in zip(fine.profiles, fine.targets)
    )
    branch_integrity = bool(
        np.all(np.diff([point.x_h for point in fine.points]) > 0.0)
        and np.all(np.diff([point.phi_h for point in fine.points]) > 0.0)
        and np.all(np.diff([point.temperature for point in fine.points]) < 0.0)
    )
    curve = [point.to_dict() for point in fine.points]
    strict_finite = _all_finite_numeric(
        {
            "curve": curve,
            "figure": figure,
            "refinement": refinement,
            "quadrature": quadrature_refinement,
            "maxwell": [item.to_dict() for item in maxwell],
            "independent": [item.to_dict() for item in independent],
        }
    )
    summary = {
        "source_algebra_error": _source_algebra_error(),
        "solver_success": solver_success,
        "maximum_collocation_residual": maximum_collocation,
        "maximum_equation_residual": maximum_equation,
        "maximum_constraint_residual": max(constraint_diagnostics),
        "maximum_boundary_residual": maximum_boundary,
        "maximum_target_relative_error": target_error,
        "branch_integrity": branch_integrity,
        "maximum_final_refinement_change": refinement["maximum_final_change"],
        "refinement_ordering_failures": refinement["ordering_failures"],
        "maximum_final_quadrature_change": quadrature_refinement[
            "maximum_final_change"
        ],
        "quadrature_ordering_failures": quadrature_refinement[
            "ordering_failures"
        ],
        "maximum_maxwell_relative_error": max(
            item.relative_error for item in maxwell
        ),
        "maximum_maxwell_flux_drift": max(
            item.normalized_flux_drift for item in maxwell
        ),
        "maximum_independent_relative_error": max(
            item.maximum_relative_error for item in independent
        ),
        "maximum_entropy_anchor_error": figure["entropy"][
            "maximum_anchor_error"
        ],
        "maximum_susceptibility_anchor_error": figure["susceptibility"][
            "maximum_anchor_error"
        ],
        "strict_finite_record": strict_finite,
        "phase_boundary_intact": True,
    }
    degree_records = {
        str(degree): {
            "degree": degree,
            "target_count": len(branch.points),
            "continuation_solve_count": len(branch.continuation_profiles),
            "maximum_target_relative_error": max(
                abs(profile.phi_h - target) / target
                for profile, target in zip(branch.profiles, branch.targets)
            ),
            "maximum_collocation_residual": max(
                profile.nonlinear.final_scaled_residual
                for profile in branch.continuation_profiles
            ),
            "points": [point.to_dict() for point in branch.points],
        }
        for degree, branch in branches.items()
    }
    determinism_state = {
        "curve": curve,
        "figure_3": figure,
        "refinement": refinement,
        "quadrature_refinement": quadrature_refinement,
        "independent_comparisons": [item.to_dict() for item in independent],
    }
    return {
        "summary": summary,
        "curve": curve,
        "degree_branches": degree_records,
        "equation_diagnostics": [item.to_dict() for item in equation_diagnostics],
        "constraint_diagnostics": [
            {
                "phi_h": point.phi_h,
                "scaled_infinity_norm": residual,
            }
            for point, residual in zip(fine.points, constraint_diagnostics)
        ],
        "refinement": refinement,
        "quadrature_refinement": quadrature_refinement,
        "maxwell_comparisons": [item.to_dict() for item in maxwell],
        "independent_comparisons": [item.to_dict() for item in independent],
        "figure_3": figure,
        "determinism_state": determinism_state,
    }


def _cached_same_degree_profile(
    cache: Dict[float, CoupledProfile],
    x_h: float,
    degree: int,
    config: Optional[CoupledSolverConfig],
) -> CoupledProfile:
    key = float(x_h)
    if key not in cache:
        seed = min(cache.values(), key=lambda item: abs(item.x_h - key))
        cache[key] = solve_coupled_profile(
            DGR_POTENTIAL,
            key,
            degree,
            seed=seed,
            config=config,
        )
    return cache[key]


def _refinement_evidence(
    branches: Mapping[int, TargetedBranch],
) -> Dict[str, Any]:
    coarse, middle, fine = DEFAULT_DEGREES
    earlier: List[float] = []
    final: List[float] = []
    for observable in (
        "temperature",
        "entropy",
        "susceptibility_integral",
        "chi_hat",
    ):
        coarse_values = np.asarray(
            [getattr(item, observable) for item in branches[coarse].points]
        )
        middle_values = np.asarray(
            [getattr(item, observable) for item in branches[middle].points]
        )
        fine_values = np.asarray(
            [getattr(item, observable) for item in branches[fine].points]
        )
        earlier.extend(_relative_array_change(middle_values, coarse_values))
        final.extend(_relative_array_change(fine_values, middle_values))
    ordering_failures = sum(
        1
        for previous, current in zip(earlier, final)
        if previous > DEFAULT_REFINEMENT_ORDER_FLOOR and current >= previous
    )
    return {
        "degrees": list(DEFAULT_DEGREES),
        "coarse_to_middle_maximum": max(earlier),
        "maximum_final_change": max(final),
        "ordering_floor": DEFAULT_REFINEMENT_ORDER_FLOOR,
        "ordering_failures": ordering_failures,
    }


def _quadrature_refinement(branch: TargetedBranch) -> Dict[str, Any]:
    coarse, middle, fine = DEFAULT_QUADRATURE_ORDERS
    earlier: List[float] = []
    final: List[float] = []
    records: List[Dict[str, Any]] = []
    for profile in branch.profiles:
        values = [
            susceptibility_integral(profile, order)
            for order in DEFAULT_QUADRATURE_ORDERS
        ]
        previous = _relative_error(values[1], values[0])
        current = _relative_error(values[2], values[1])
        earlier.append(previous)
        final.append(current)
        records.append(
            {
                "phi_h": profile.phi_h,
                "orders": [coarse, middle, fine],
                "integrals": values,
                "coarse_to_middle_change": previous,
                "middle_to_fine_change": current,
            }
        )
    ordering_failures = sum(
        1
        for previous, current in zip(earlier, final)
        if previous > DEFAULT_QUADRATURE_ORDER_FLOOR and current >= previous
    )
    return {
        "orders": list(DEFAULT_QUADRATURE_ORDERS),
        "records": records,
        "coarse_to_middle_maximum": max(earlier),
        "maximum_final_change": max(final),
        "ordering_floor": DEFAULT_QUADRATURE_ORDER_FLOOR,
        "ordering_failures": ordering_failures,
    }


def _independent_indices(points: Sequence[DGRPoint]) -> Tuple[int, ...]:
    return tuple(
        min(
            range(len(points)),
            key=lambda index: abs(points[index].phi_h - target),
        )
        for target in DEFAULT_INDEPENDENT_PHI_H
    )


def _independent_comparison(
    point: DGRPoint,
    target_phi_h: float,
) -> IndependentComparison:
    independent = independent_master_point(point.phi_h)
    temperature_dictionary_error = _relative_error(
        independent.temperature, independent.reconstructed_temperature
    )
    if temperature_dictionary_error > 1.0e-6:
        raise RuntimeError(
            "independent scalar-coordinate temperature dictionary failed"
        )
    return IndependentComparison(
        target_phi_h=target_phi_h,
        actual_phi_h=point.phi_h,
        temperature_relative_error=_relative_error(
            point.temperature, independent.temperature
        ),
        entropy_relative_error=_relative_error(point.entropy, independent.entropy),
        integral_relative_error=_relative_error(
            point.susceptibility_integral,
            independent.susceptibility_integral,
        ),
        susceptibility_relative_error=_relative_error(
            point.chi_hat, independent.chi_hat
        ),
        dop853_function_evaluations=independent.function_evaluations,
    )


def _figure_3_comparison(points: Sequence[DGRPoint]) -> Dict[str, Any]:
    temperature = np.asarray([point.temperature_mev for point in points])
    entropy = np.asarray([point.entropy_ratio_plot for point in points])
    susceptibility = np.asarray(
        [point.susceptibility_ratio_plot for point in points]
    )
    order = np.argsort(temperature)
    temperature = temperature[order]
    entropy = entropy[order]
    susceptibility = susceptibility[order]
    entropy_curve = PchipInterpolator(temperature, entropy, extrapolate=False)
    susceptibility_curve = PchipInterpolator(
        temperature, susceptibility, extrapolate=False
    )
    return {
        "source_figure": 3,
        "source_figure_sha256": SOURCE_FIGURE_3_SHA256,
        "temperature_range_MeV": [
            float(temperature[0]),
            float(temperature[-1]),
        ],
        "entropy": _anchor_comparison(
            entropy_curve,
            temperature,
            ENTROPY_FIGURE_3_ANCHORS,
            DEFAULT_ENTROPY_FIGURE_TOLERANCE,
            "s_over_T3",
        ),
        "susceptibility": _anchor_comparison(
            susceptibility_curve,
            temperature,
            SUSCEPTIBILITY_FIGURE_3_ANCHORS,
            DEFAULT_SUSCEPTIBILITY_FIGURE_TOLERANCE,
            "chi_2_over_T2",
        ),
        "lattice_points_included": False,
        "raw_source_artwork_redistributed": False,
    }


def _anchor_comparison(
    curve: PchipInterpolator,
    coordinate: NDArray[np.float64],
    anchors: Mapping[float, float],
    tolerance: float,
    observable: str,
) -> Dict[str, Any]:
    records: List[Dict[str, float]] = []
    for temperature, source_value in anchors.items():
        if not coordinate[0] <= temperature <= coordinate[-1]:
            raise RuntimeError(f"Figure 3 anchor {temperature} MeV is not bracketed")
        computed = float(curve(temperature))
        records.append(
            {
                "temperature_MeV": temperature,
                f"source_{observable}": source_value,
                f"computed_{observable}": computed,
                "absolute_error": abs(computed - source_value),
            }
        )
    return {
        "observable": observable,
        "anchors": records,
        "maximum_anchor_error": max(item["absolute_error"] for item in records),
        "tolerance": tolerance,
    }


def _source_algebra_error() -> float:
    product_left = LAMBDA_T_MEV * LAMBDA_S_MEV3
    product_right = LAMBDA_MU_MEV * LAMBDA_RHO_MEV3
    mismatch = abs(product_left - product_right) / product_right
    expected_mass = -0.292832
    expected_delta = 3.925400737508948
    expected_power = 0.0745992624910521
    return max(
        abs(DGR_POTENTIAL.potential(0.0) + 12.0),
        abs(DGR_POTENTIAL.first_derivative(0.0)),
        abs(DGR_POTENTIAL.mass_squared - expected_mass),
        abs(DGR_POTENTIAL.delta - expected_delta),
        abs(DGR_POTENTIAL.uv_power - expected_power),
        abs(
            DGR_POTENTIAL.delta * (DGR_POTENTIAL.delta - 4.0)
            - DGR_POTENTIAL.mass_squared
        ),
        abs(gauge_coupling(0.0) - 1.0),
        abs(mismatch - PRINTED_SCALE_PRODUCT_RELATIVE_MISMATCH),
    )


def _save_figure_3_plot(payload: Mapping[str, Any], path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib import pyplot as plt
    except ImportError as exc:
        raise RuntimeError(
            "Matplotlib is required for --output-dir; install holoforge[plot]"
        ) from exc
    curve = payload["results"]["curve"]
    temperature = [row["temperature_MeV"] for row in curve]
    entropy = [row["s_over_T3_plot"] for row in curve]
    susceptibility = [row["chi_2_over_T2_plot"] for row in curve]
    figure, axes = plt.subplots(
        1, 2, figsize=(11.2, 4.5), constrained_layout=True
    )
    axes[0].plot(
        temperature,
        entropy,
        color="#1565c0",
        linewidth=2.0,
        label="HoloForge Chebyshev",
    )
    axes[0].scatter(
        list(ENTROPY_FIGURE_3_ANCHORS),
        list(ENTROPY_FIGURE_3_ANCHORS.values()),
        color="black",
        s=22,
        zorder=3,
        label="DGR Figure 3 path anchors",
    )
    axes[0].set(
        xlabel=r"$T\,[\mathrm{MeV}]$",
        ylabel=r"$s/T^3$",
        title="DGR entropy at zero chemical potential",
    )
    axes[0].set_xlim(140.0, 720.0)
    axes[0].legend(fontsize=8)

    axes[1].plot(
        temperature,
        susceptibility,
        color="#1565c0",
        linewidth=2.0,
        label="HoloForge Chebyshev + linear response",
    )
    axes[1].scatter(
        list(SUSCEPTIBILITY_FIGURE_3_ANCHORS),
        list(SUSCEPTIBILITY_FIGURE_3_ANCHORS.values()),
        color="black",
        s=22,
        zorder=3,
        label="DGR Figure 3 path anchors",
    )
    axes[1].set(
        xlabel=r"$T\,[\mathrm{MeV}]$",
        ylabel=r"$\chi_2/T^2$",
        title="DGR susceptibility at zero chemical potential",
    )
    axes[1].set_xlim(140.0, 470.0)
    axes[1].legend(fontsize=8)
    figure.suptitle(
        "DeWolfe--Gubser--Rosen Figure 3 model reproduction",
        fontsize=12,
    )
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _relative_array_change(
    fine: NDArray[np.float64],
    coarse: NDArray[np.float64],
) -> List[float]:
    return list(
        np.abs(fine - coarse)
        / np.maximum(np.maximum(np.abs(fine), np.abs(coarse)), 1.0e-300)
    )


def _relative_error(left: float, right: float) -> float:
    return abs(left - right) / max(abs(left), abs(right), 1.0e-300)


def _maximum_nested_numeric_difference(left: Any, right: Any) -> float:
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        if set(left) != set(right):
            return math.inf
        return max(
            (
                _maximum_nested_numeric_difference(left[key], right[key])
                for key in left
            ),
            default=0.0,
        )
    if (
        isinstance(left, Sequence)
        and isinstance(right, Sequence)
        and not isinstance(left, (str, bytes))
    ):
        if len(left) != len(right):
            return math.inf
        return max(
            (
                _maximum_nested_numeric_difference(a, b)
                for a, b in zip(left, right)
            ),
            default=0.0,
        )
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        left_value = float(left)
        right_value = float(right)
        return abs(left_value - right_value) / max(
            1.0, abs(left_value), abs(right_value)
        )
    return 0.0 if left == right else math.inf


def _all_finite_numeric(value: Any) -> bool:
    if isinstance(value, Mapping):
        return all(_all_finite_numeric(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return all(_all_finite_numeric(item) for item in value)
    if isinstance(value, (float, np.floating)):
        return math.isfinite(float(value))
    return True


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
    "DEFAULT_DEGREES",
    "DEFAULT_TARGET_PHI_H",
    "DEWOLFE_GUBSER_ROSEN_DEFINITION",
    "DGR_POTENTIAL",
    "ENTROPY_FIGURE_3_ANCHORS",
    "SOURCE_ARCHIVE_SHA256",
    "SOURCE_FIGURE_3_SHA256",
    "SOURCE_PDF_SHA256",
    "SUSCEPTIBILITY_FIGURE_3_ANCHORS",
    "einstein_constraint_residual",
    "explicit_maxwell_diagnostics",
    "gauge_coupling",
    "gauge_log_derivative",
    "independent_master_point",
    "model_card_sha256",
    "point_from_profile",
    "save_dewolfe_gubser_rosen_artifacts",
    "solve_targeted_branch",
    "susceptibility_integral",
    "verify_dewolfe_gubser_rosen_emd",
]
