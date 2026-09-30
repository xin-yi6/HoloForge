# Quadratic Soft-Wall Vector Benchmark

## Scientific source

The benchmark follows A. Karch, E. Katz, D. T. Son, and M. A. Stephanov,
“Linear Confinement and AdS/QCD,” *Physical Review D* **74**, 015005 (2006),
[arXiv:hep-ph/0602229](https://arxiv.org/abs/hep-ph/0602229), especially
Eqs. (8)–(15).

## Conventions and derivation

Use the conformally flat five-dimensional metric

```text
ds^2 = exp(2 A(z)) (dz^2 + eta_{mu nu} dx^mu dx^nu),
A(z) = -log(z/R),
Phi(z) = kappa^2 z^2,
B(z) = Phi(z) - A(z).
```

For a transverse vector mode, the field redefinition
`v_n = exp(B/2) psi_n` turns the Sturm–Liouville equation into

```text
-psi_n''(z) + V(z) psi_n(z) = m_n^2 psi_n(z),
V(z) = B'(z)^2 / 4 - B''(z) / 2
     = kappa^4 z^2 + 3 / (4 z^2).
```

Normalizability gives the exact spectrum

```text
m_n^2 = 4 kappa^2 (n + 1),  n = 0, 1, 2, ... .
```

Natural units are used. In the implementation, `kappa` is measured in GeV,
`z` in GeV^-1, and eigenvalues in GeV^2. The AdS radius cancels from this mode
equation.

## Numerical methods

The implementation truncates the half-line to `0 < z < z_max` and imposes
Dirichlet conditions on the Schrödinger wavefunction at both ends. It exposes
two numerical formulations without changing the protected default:

1. `finite-difference` uses a second-order centered stencil on a uniform
   interior grid. Only the lowest requested eigenvalues of the symmetric
   tridiagonal Hamiltonian are computed with SciPy's eigenvalue-only
   `eigvalsh_tridiagonal` routine.
2. `spectral` uses Chebyshev--Gauss--Lobatto nodes. Removing both endpoint rows
   and columns enforces the Dirichlet conditions, and SciPy's dense `eigvals`
   routine solves the resulting nonsymmetric collocation eigenproblem. Only
   finite, positive eigenvalues with negligible imaginary parts are retained.

The UV potential is never evaluated at `z = 0`; the first point is one grid
point inside the domain. The default `z_max = 10 / kappa` suppresses the
normalizable wavefunctions well before the artificial IR boundary for the
first few modes.

## Verification and limits

The default verification requires the first four eigenvalues to agree with the
analytic result within a maximum relative error of `2e-4`. Finite-difference
tests require the expected approximately second-order convergence. The
spectral route records degrees `N-16`, `N-8` and `N` (24, 32 and 40 by
default). Its refinement check, rule `soft-wall-spectral-refinement-v2`,
requires the final maximum analytic error to be below `1e-8` and, in addition,
one of two branches:

- **convergence:** the maximum error decreases strictly across the three
  degrees (the version 1 rule, unchanged); or
- **plateau:** for every requested mode at the two finest degrees, the
  analytic error and the eigenvector-solve mismatch lie within the mode's
  first-order perturbation scale `eps ||H||_2 kappa / |lambda|`, and the two
  degrees agree within the sum of their scales.

The record states which branch passed and keeps every per-mode quantity for
audit. At degree 40 the development result is about `2.7e-13`; this is
numerical verification of the finite-domain eigenproblem, not
phenomenological precision.

Run either route with:

```bash
holoforge verify soft-wall-vector
holoforge verify soft-wall-vector --method spectral --json
```

Machine-readable output records the complete numerical configuration, method,
boundary conditions, convergence levels, and runtime provenance.

**Why version 2.** From `--spectral-degree 56` upward, all three errors are
already at the rounding level (about `1e-14`), so their order is arbitrary.
The version 1 rule could then report FAIL although the analytic-spectrum error
passes by ten orders of magnitude.

The plateau branch was calibrated on seen data and frozen before
confirmation. It was then confirmed on nine reserved cases across five builds,
covering macOS arm64 and x86_64, Linux, Accelerate and OpenBLAS, and an older
NumPy/SciPy release:
[contract](../numerics/soft-wall-refinement-sa-contract.md),
[confirmation](../numerics/soft-wall-refinement-sa-confirmation.md).
Under-resolved degrees and truncated domains still fail. The perturbation
scale is not a proved error floor, and the analytic spectrum remains the only
accuracy reference.

This checks the equation, scale restoration, discretization, and eigenvalue
ordering. It does **not** test decay constants, experimental fits, chiral
physics, backreaction, or the phenomenological adequacy of the soft-wall model.
