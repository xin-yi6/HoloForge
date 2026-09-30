# Optical discrete-system diagnosis (O-C): proposed plan

- **Status: PROPOSED.** Not approved, not frozen, not executed.
  AI-assisted (Claude), drafted at Codex's request after review of the
  [O-B report](optical-ob-diagnosis-report.md).
  - On approval this file is frozen in its own commit before any O-C run.
  - Until then no O-C code or run exists.
- **Diagnosis only.** No production solver, gate, threshold, record or
  verdict changes. The reserved cases stay unused.

## 1. Question

O-B showed that the stored degree-640 solution's interpolating polynomial
misses the equation by about `1e-4` at the first checked UV node. It also
misses by `2e-5`–`3e-4` on UV-end collocation nodes, where an exactly solved
exact discrete system would not.

Which part of the discrete computation produces this?
1. **Construction:** the double-precision differentiation matrices, including
   the node positions they imply.
2. **Coefficients, assembly and equilibration rounding.**
3. **The linear solve's backward error.**
4. **The discretization itself:** under-resolution or the C¹ background, which
   remain after an exact solve of the exact discrete system.

**Prior hypothesis from code inspection (not a result).**
`chebyshev_lobatto_grid` builds D from differences of double cosines near
`±1`. It takes the diagonal by negative row sum, and forms D² as `D @ D`.
Separately, the physical nodes come from an affine map with its own
rounding. Differences of cosines near the endpoints are a known roundoff
source in Chebyshev differentiation (Baltensperger and Trummer, *SIAM J. Sci.
Comput.* 24, 1465 (2003)). Such errors would be amplified by `|a'| ≈ 4e2` and
by `D²` entries of order `N^4` near the UV end. O-C tests this; it does not
assume it.

## 2. Cases and builds

- **Cases:** all previously examined, with no reserved case.
  - ω/T = 60 (production failure), 59 (smallest sampled scale), 50 and 70 at
    degree 640;
  - ω/T = 60 at degree 512.
- **Builds:** B1 (Accelerate) for all cases. B3 (OpenBLAS) for ω/T = 60 at
  both degrees and 59 at 640, to test build dependence of the solve and
  `D @ D`.
- **Still reserved:** ω/T = 55, 65, 75 and degree 576.

## 3. Capture and preservation

For each case and build, the production solve runs unmodified. Spies capture
the residual-function inputs (as in O-B) and the arguments and result of the
`scipy.linalg.solve` call.
- **Identity requirement.** The tool reconstructs, in production's operation
  order, the assembled operator, row norms, equilibrated operator and
  right-hand side. The reconstructed equilibrated operator and right-hand side
  must equal the captured ones bit for bit, and the stored solution must equal
  production's. Otherwise O-C stops for that case.
- **Hashed.** A SHA-256 of the array bytes is taken for each of:
  - the stored solution (regular values and current);
  - the physical nodes `u_j` and the local nodes;
  - the scalar values at the nodes;
  - the coefficient arrays (`first_coefficient`, `potential`) and the
    transfer coefficients;
  - the right-hand side;
  - `first_derivative` and `second_derivative`;
  - the assembled operator, row norms and equilibrated operator.
- **Saved in the committed evidence JSON:** all hashes, plus the full small
  arrays: solution, nodes, scalar values, coefficients, right-hand side and
  row norms.
- **Large arrays.** The operators and differentiation matrices are about
  6.6 MB each per case. They are saved as local compressed `.npz` artifacts,
  outside the repository and with their hashes recorded. They can be
  regenerated from the committed inputs and verified by hash.
  - **Owner decision:** keep them outside the repository (recommended), or
    attach them to a release or CI artifact.

## 4. Conventions

Every high-precision quantity uses one consistent convention:
- the **physical** stored nodes `u_j`, as collocated;
- derivatives in `u`;
- the production's regular-factor equation and coefficient definitions;
- double inputs converted exactly;
- 50-digit Decimal arithmetic, with a 70-digit cross-check on one case.

The O-B local-node value at the spike is recomputed under this convention.
The complex difference between the two is reported, which measures O-B's
convention caveat.

## 5. Measurements

1. **Row decomposition on collocation rows 1–3.** The total high-precision
   residual `r = (L_exact f - b)` of the stored solution is written as an
   exact telescoping sum of complex contribution vectors.

   | Step | Operator change | Attributed to |
   | --- | --- | --- |
   | `L_exact` → `L_D` | exact D matrices for the stored nodes → production double `first_derivative`, with its square formed exactly | differentiation-matrix construction, including node-position consistency |
   | `L_D` → `L_D2` | → production double `second_derivative` (`D @ D`) | matrix-product rounding |
   | `L_D2` → `L_coef` | exact coefficients → production double coefficients | coefficient rounding |
   | `L_coef` → `L_asm` | exact assembly → the production assembled double operator | assembly rounding |
   | `L_asm` → `L_eq` | → `row_norms × equilibrated operator` (right-hand side likewise) | equilibration rounding |
   | `L_eq` | `L_eq f - b_eq` | solve residual |

   The contributions must sum to `r` to `1e-30` relative (fixture F3). Each is
   reported as a complex value and a magnitude. The same decomposition is also
   summarized over all interior rows (maximum and argmaximum).
2. **Spike attribution by exact solutions.** High-precision iterative
   refinement is used, with the residual in 50 digits and the correction from
   the production LU in double, accumulated in Decimal. It gives the exact
   solutions `f_eq`, `f_D2` and `f_exact` of `L_eq`, `L_D2` and `L_exact`.
   For `f_stored` and each exact solution, it reports:
   - the complex residual at the O-B spike and its neighbours;
   - the complex differences between successive solutions' spike residuals.
3. **Ratios.** The ratios `rho_X = |R(f_X)| / |R(f_stored)|` at the spike.

## 6. Prospective interpretation rules

| Outcome | Rule |
| --- | --- |
| **Solve-dominated** | `rho_eq <= 0.1` |
| **Construction/rounding-dominated** | `rho_eq >= 0.5` and `rho_exact <= 0.1`; the step with the largest attributed complex difference is named |
| **Discretization-dominated** | `rho_exact >= 0.5` |
| **Mixed/unresolved** | anything else |

The collocation-row decomposition is supporting evidence and must be
consistent with the named step; any inconsistency is reported.

Possible responses, which O-C does not decide:
- **solve:** a solver improvement, such as refinement with an
  extended-precision residual;
- **construction:** a construction repair, such as trigonometric node
  differences and consistent nodes, followed by prospective revalidation;
- **discretization:** a resolution or background treatment, or an
  independently justified gate redesign.

Solver improvement stays a candidate in every outcome. No outcome changes a
gate.

## 7. Fixtures (all must pass before any case is examined)

- **F1.** The 50-digit D and D² for the production degree-640 physical nodes
  on `[1e-5, 1]` reproduce a known degree-6 polynomial's first and second
  derivatives at every node to `1e-30` relative.
- **F2.** On a normal-state case (ω/T = 40, degree 64), the reconstructed
  equilibrated operator and right-hand side equal the captured ones bit for
  bit.
- **F3.** On the F2 case, the telescoping contributions sum to the total
  residual to `1e-30` relative.
- **F4.** On the F2 case, refinement reduces the 50-digit residual of each
  refined system below `1e-30` relative within 6 iterations.

## 8. Budget, stopping and outputs

- **Budget:** at most 30 minutes of local wall time in total; no CI dispatch.
- **Stop and return if:**
  - production code would need to change;
  - a fixture fails after three corrections;
  - the production operator cannot be reconstructed bit for bit;
  - refinement fails F4's criterion on a production case (a technical stop
    for that operator, reported, not a physical result);
  - the budget is exhausted.
- **Outputs:**
  - an `optical-oc` subcommand in `tools/gate_calibration.py`, with tests;
  - `docs/numerics/optical-oc-diagnosis-report.md`;
  - evidence JSON under `docs/generated/optical-oc/`;
  - the local `.npz` artifacts described in Section 3.
