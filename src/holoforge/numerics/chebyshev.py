"""Chebyshev--Gauss--Lobatto differentiation on a finite interval.

The grid is the standard dense collocation grid of L. N. Trefethen,
*Spectral Methods in MATLAB*, Chapter 6.  The matrices are the exact
differentiation matrices of the polynomial interpolant through the returned
double-precision nodes, up to rounding (construction ``c-s1-r1``):

- nodes come from half-angles, ``lower + width sin^2(pi k / (2 N))`` on the
  lower half and its mirror image on the upper half, so they do not cancel
  near the endpoints;
- barycentric weights are recomputed from the returned nodes, as products
  of node differences accumulated in double-double arithmetic;
- each diagonal is the negative sum of its row, in compensated arithmetic;
- the second derivative uses the explicit recurrence
  ``D2_ij = 2 D1_ij (D1_ii - 1 / (z_i - z_j))`` instead of a matrix product.

``docs/numerics/chebyshev-construction-repair-report.md`` records why this
construction replaced differences of rounded cosines and ``D @ D``, and how
it was qualified.  The module deliberately provides only the coordinate grid
and differentiation matrices.  Equations, boundary rows, gauge choices, and
acceptance gates remain benchmark-specific.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Integral, Real

import numpy as np
from numpy.typing import NDArray


CHEBYSHEV_CONSTRUCTION = "c-s1-r1"
"""Identifier of the matrix construction, recorded in runtime provenance."""

_VELTKAMP_SPLITTER = 134217729.0  # 2^27 + 1


@dataclass(frozen=True)
class ChebyshevGrid:
    """Ascending Lobatto nodes and dense derivative matrices on ``[a, b]``."""

    degree: int
    lower_bound: float
    upper_bound: float
    nodes: NDArray[np.float64]
    first_derivative: NDArray[np.float64]
    second_derivative: NDArray[np.float64]

    @property
    def size(self) -> int:
        """Number of collocation nodes, including both endpoints."""

        return self.degree + 1

    @property
    def minimum_spacing(self) -> float:
        """Smallest adjacent-node separation."""

        return float(np.min(np.diff(self.nodes)))

    @property
    def maximum_spacing(self) -> float:
        """Largest adjacent-node separation."""

        return float(np.max(np.diff(self.nodes)))


def chebyshev_lobatto_grid(
    degree: int,
    lower_bound: Real = -1.0,
    upper_bound: Real = 1.0,
) -> ChebyshevGrid:
    """Return Chebyshev--Gauss--Lobatto nodes and ``d/dz``, ``d^2/dz^2``.

    ``degree`` is the polynomial degree, so the returned arrays contain
    ``degree + 1`` nodes.  Nodes are ordered from ``lower_bound`` to
    ``upper_bound`` to make UV/IR or boundary/horizon row placement explicit.
    The arrays are read-only; callers replacing boundary rows must first copy
    the relevant operator.
    """

    if isinstance(degree, bool) or not isinstance(degree, Integral):
        raise ValueError("degree must be an integer")
    if int(degree) < 2:
        raise ValueError("degree must be at least 2")
    if isinstance(lower_bound, bool) or not isinstance(lower_bound, Real):
        raise ValueError("lower_bound must be a finite real number")
    if isinstance(upper_bound, bool) or not isinstance(upper_bound, Real):
        raise ValueError("upper_bound must be a finite real number")

    lower = float(lower_bound)
    upper = float(upper_bound)
    if not math.isfinite(lower):
        raise ValueError("lower_bound must be a finite real number")
    if not math.isfinite(upper):
        raise ValueError("upper_bound must be a finite real number")
    if lower >= upper:
        raise ValueError("lower_bound must be less than upper_bound")

    resolved_degree = int(degree)
    nodes = _half_angle_nodes(resolved_degree, lower, upper)
    first_derivative, second_derivative = _stored_node_matrices(nodes)

    for array in (nodes, first_derivative, second_derivative):
        array.setflags(write=False)

    return ChebyshevGrid(
        degree=resolved_degree,
        lower_bound=lower,
        upper_bound=upper,
        nodes=np.asarray(nodes, dtype=float),
        first_derivative=np.asarray(first_derivative, dtype=float),
        second_derivative=np.asarray(second_derivative, dtype=float),
    )


def _half_angle_nodes(degree: int, lower: float, upper: float) -> NDArray[np.float64]:
    """Ascending Lobatto nodes from half-angles with integer-index arguments."""

    width = upper - lower
    index = np.arange(degree + 1)
    low_side = 2 * index <= degree
    nodes = np.empty(degree + 1)
    nodes[low_side] = lower + width * np.sin(np.pi * index[low_side] / (2 * degree)) ** 2
    nodes[~low_side] = upper - width * np.sin(np.pi * (degree - index[~low_side]) / (2 * degree)) ** 2
    if degree % 2 == 0:
        # sin^2(pi/4) is exactly 1/2; the rounded sine would shift the midpoint.
        nodes[degree // 2] = lower + 0.5 * width
    nodes[0], nodes[-1] = lower, upper
    return nodes


def _two_sum(a, b):
    """Error-free transformation: ``a + b = s + e`` exactly."""

    total = a + b
    shadow = total - a
    return total, (a - (total - shadow)) + (b - shadow)


def _two_product(a, b):
    """Error-free transformation: ``a b = p + e`` exactly (Dekker, Veltkamp)."""

    product = a * b
    split_a = _VELTKAMP_SPLITTER * a
    a_high = split_a - (split_a - a)
    a_low = a - a_high
    split_b = _VELTKAMP_SPLITTER * b
    b_high = split_b - (split_b - b)
    b_low = b - b_high
    return product, ((a_high * b_high - product) + a_high * b_low + a_low * b_high) + a_low * b_low


def _compensated_row_sum(matrix: NDArray[np.float64]) -> NDArray[np.float64]:
    """Row sums by pairwise double-double reduction."""

    high = np.array(matrix, dtype=float)
    low = np.zeros_like(high)
    while high.shape[1] > 1:
        if high.shape[1] % 2:
            high = np.concatenate([high, np.zeros((high.shape[0], 1))], axis=1)
            low = np.concatenate([low, np.zeros((low.shape[0], 1))], axis=1)
        total, error = _two_sum(high[:, 0::2], high[:, 1::2])
        high, low = total, low[:, 0::2] + low[:, 1::2] + error
    return (high + low)[:, 0]


def _compensated_row_product(matrix: NDArray[np.float64]):
    """Row products as ``(high + low) 2^exponent`` by pairwise double-double reduction."""

    high, exponent = np.frexp(np.array(matrix, dtype=float))
    exponent = exponent.astype(np.int64)
    low = np.zeros_like(high)
    while high.shape[1] > 1:
        if high.shape[1] % 2:
            high = np.concatenate([high, np.ones((high.shape[0], 1))], axis=1)
            low = np.concatenate([low, np.zeros((low.shape[0], 1))], axis=1)
            exponent = np.concatenate(
                [exponent, np.zeros((exponent.shape[0], 1), dtype=np.int64)], axis=1
            )
        product, error = _two_product(high[:, 0::2], high[:, 1::2])
        error = error + high[:, 0::2] * low[:, 1::2] + low[:, 0::2] * high[:, 1::2]
        product, error = _two_sum(product, error)
        mantissa, shift = np.frexp(product)
        high, low = mantissa, np.ldexp(error, -shift)
        exponent = exponent[:, 0::2] + exponent[:, 1::2] + shift
    return high[:, 0], low[:, 0], exponent[:, 0]


def _stored_node_matrices(nodes: NDArray[np.float64]):
    """First and second differentiation matrices of the interpolant through ``nodes``."""

    size = nodes.size
    index = np.arange(size)
    differences = nodes[:, np.newaxis] - nodes[np.newaxis, :]

    # Reciprocal barycentric weights 1/w_j = prod_{k != j} (z_j - z_k), up to
    # a common factor, kept as mantissas with separate binary exponents so
    # that nothing overflows.
    work = differences.copy()
    work[index, index] = 1.0
    signs = np.where(np.sum(work < 0.0, axis=1) % 2 == 0, 1.0, -1.0)
    high, low, exponent = _compensated_row_product(np.abs(work))
    shift = (exponent - exponent[size // 2]).astype(int)
    high, low = signs * np.ldexp(high, shift), signs * np.ldexp(low, shift)

    safe = differences.copy()
    safe[index, index] = 1.0
    quotient = high[:, np.newaxis] / high[np.newaxis, :]
    ratio = (
        quotient
        + quotient * (low / high)[:, np.newaxis]
        - quotient * (low / high)[np.newaxis, :]
    )
    first = ratio / safe
    first[index, index] = 0.0
    diagonal = -_compensated_row_sum(first)

    second = 2.0 * first * (diagonal[:, np.newaxis] - 1.0 / safe)
    second[index, index] = 0.0
    second[index, index] = -_compensated_row_sum(second)
    first[index, index] = diagonal
    return first, second
