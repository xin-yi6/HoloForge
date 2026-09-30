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
spectral route records degrees 24, 32, and 40 and requires the maximum analytic
error to decrease at every level and finish below `1e-8`. At degree 40 the
development result is about `2.7e-13`; this is numerical verification of the
finite-domain eigenproblem, not phenomenological precision.

Run either route with:

```bash
holoforge verify soft-wall-vector
holoforge verify soft-wall-vector --method spectral --json
```

Machine-readable output records the complete numerical configuration, method,
boundary conditions, convergence levels, and runtime provenance.

**Known issue: spectral degrees of 56 or more.** The spectral refinement
check compares degrees `N-16`, `N-8` and `N` and requires strictly decreasing
error. From `--spectral-degree 56` upward, all three errors are already at the
rounding floor (about `1e-14`). Their order is then arbitrary, so the check can
report FAIL even though the analytic-spectrum error passes by ten orders of
magnitude. The human-readable summary names each gate separately, so this case
reads `PASS: max relative error ...` followed by
`FAIL: spectral-degree-refinement ...`. The default degree 40 is unaffected. A
floor-aware refinement rule needs its own justification and adverse
under-resolution tests; until then, the rule is unchanged.

This checks the equation, scale restoration, discretization, and eigenvalue
ordering. It does **not** test decay constants, experimental fits, chiral
physics, backreaction, or the phenomenological adequacy of the soft-wall model.
