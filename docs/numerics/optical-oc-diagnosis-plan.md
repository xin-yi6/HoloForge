# Optical discrete-system diagnosis (O-C): plan, frozen before execution

- **Status:** frozen before any O-C run. AI-assisted (Claude).
  - Owner approval (30 September 2026, relayed with Codex's review) covers
    one bounded execution. This revision addresses Codex's comments on the
    proposal (`d393993`).
- **Scope:** diagnosis only. No production solver, gate, threshold, record
  or verdict changes. The reserved cases stay unused.
- **Ceilings:**
  - at most 4 hours of active implementation, testing and reporting;
  - at most 30 cumulative minutes of local diagnostic execution, including
    fixtures, retries and refinement;
  - no paid compute, installations, or CI-dispatched scientific runs.
- **On failure:** if qualification fails or a budget is exhausted, the
  evidence is preserved and an unresolved or technical outcome is returned.
  The investigation is not expanded.

## 1. Question

O-B ([report](optical-ob-diagnosis-report.md)) found that the stored
degree-640 solution's interpolating polynomial misses the equation:
- by about `1e-4` at the first checked UV node (the "spike");
- by `2e-5`–`3e-4` on UV-end collocation nodes, where an exactly solved exact
  discrete system would not.

Which part of the discrete computation produces the spike residual?
- **Solve:** the linear solve's backward error.
- **Operator rounding:** rounding in the operator actually solved, relative
  to the exact discrete operator for the stored nodes. Its steps are:
  - differentiation-matrix construction, including consistency with the
    stored node positions;
  - the `D @ D` product;
  - coefficient evaluation;
  - assembly;
  - row equilibration.
- **Discretization:** what remains for a high-precision solution of the
  exact discrete system, such as under-resolution or the C¹ spline
  background.

**Prior hypothesis from code inspection (not a result).**
- `chebyshev_lobatto_grid` builds D from differences of double cosines near
  `±1`. It takes the diagonal by negative row sum, and forms D² as `D @ D`.
- The physical nodes come from a separately rounded affine map.
- Differences of cosines near the endpoints are a known roundoff source in
  Chebyshev differentiation (Baltensperger and Trummer, *SIAM J. Sci.
  Comput.* 24, 1465 (2003)).

O-C tests this hypothesis; it does not assume it.

## 2. Cases and builds (unchanged from the proposal)

- **B1 (Accelerate):**
  - ω/T = 60, 59, 50 and 70 at degree 640;
  - ω/T = 60 at degree 512.
- **B3 (OpenBLAS wheels):**
  - ω/T = 60 and 59 at degree 640;
  - ω/T = 60 at degree 512.
- **Reserved and not run:** ω/T = 55, 65, 75 and degree 576.

## 3. The complete discrete system

- **Unknowns.** `x = (f_0, ..., f_N, J)`: the regular factor at the stored
  physical nodes `u_0 = 1e-5 < ... < u_N = 1`, and the current `J`.
- **Production rows**, each with its right-hand side `b`:

  | Row | Equation | Right-hand side |
  | --- | --- | --- |
  | 0 (UV-transfer field) | `f_0 - c_F J` | `s_F` |
  | `1..N-1` (interior) | `sum_j (D2_ij + c1_i D1_ij) f_j + V_i f_i` | `0` |
  | `N` (horizon) | `sum_j D1_Nj f_j + h f_N` | `0` |
  | `N+1` (UV-transfer derivative) | `sum_j D1_0j f_j - c_D J` | `s_D` |

  Here `c1 = F'/F - 2s/(1-u)` and
  `V = s(s-1)/(1-u)^2 - s F'/((1-u) F) + omega^2/F^2 - 2 psi^2/(u^2 F)`, with
  `s = -i omega/3`.
- **Fixed inputs.** The transfer coefficients `c_F, s_F, c_D, s_D` and the
  horizon coefficient `h` are the production double values. They are treated
  as fixed inputs of the discrete problem; rounding inside their own
  computation is out of scope.

**Operator chain.** Each is a complete `(N+2) × (N+2)` operator, all rows
included, with its right-hand side.

| Operator | D1 | Second derivative | `c1`, `V` | Arithmetic | Right-hand side |
| --- | --- | --- | --- | --- | --- |
| `T_exact` | exact D1 of the polynomial through the stored `u_j` | exact D2 | 50-digit, from the double inputs `u_i`, `psi_i`, `omega` | exact | production `b` |
| `T_D` | production double `first_derivative` | its exact square | as `T_exact` | exact | production `b` |
| `T_D2` | as `T_D` | production double `second_derivative` | as `T_exact` | exact | production `b` |
| `T_coef` | as `T_D` | as `T_D2` | production double arrays | exact | production `b` |
| `T_asm` | the production assembled double operator, entries taken exactly | | | | production `b` |
| `T_eq` | `n_i Â_ij`: production row norms times the equilibrated operator, exact products | | | | `n_i b̂_i` |

The boundary rows use the variant's D1, and their fixed inputs are the same
in every operator. `T_eq` is the system production actually solved.

## 4. Conventions

- Every high-precision quantity uses:
  - the stored **physical** nodes `u_j`;
  - derivatives in `u`;
  - the production regular-factor equation;
  - double inputs converted exactly;
  - 50-digit Decimal arithmetic.
- **Spike residual `R(y)`** of a regular-factor vector `y`:
  - Construct the polynomial through `(u_j, y_j)`, using barycentric
    weights from the stored `u_j`.
  - Evaluate it at the production check coordinate `u*` (check index 3 of
    the degree-`2N` check grid), and at indices 1–5 for context.
  - Form `R = p'' + c1(u*) p' + V(u*) p`, with the coefficients taken in 50
    digits from double `u*`, `psi(u*)` and `omega`.
- **Comparison with O-B.** O-B's local-node value `R_a / w^2` (with `w` the
  element width) is recomputed. Its complex difference from `R` for the
  stored solution is reported. A 70-digit repetition of `R` is made for one
  case (60/640, B1).

## 5. Capture and preservation

- **Capture.** The production solve runs unmodified. Spies capture:
  - the residual-function inputs;
  - the arguments and result of `scipy.linalg.solve`.
- **Identity requirement.** The tool reconstructs, in production's
  operation order:
  - the assembled operator, right-hand side, row norms and equilibrated
    operator;
  - the physical nodes and D matrices, from `chebyshev_lobatto_grid`;
  - the coefficient arrays.

  The equilibrated operator and right-hand side must equal the captured ones
  bit for bit, and the stored solution must equal production's. Otherwise
  that case stops.
- **Local artifacts (outside Git).** For each case and build, all arrays are
  saved to `output/optical-oc-artifacts/` in the checkout, which Git
  ignores. They are neither uploaded nor deleted. The arrays are:
  - the stored solution;
  - the physical and local nodes;
  - the scalar values at the nodes and check coordinates;
  - the coefficient arrays and fixed inputs;
  - the right-hand sides;
  - D1 and D2;
  - the assembled operator, row norms and equilibrated operator.
- **Committed evidence.** The evidence JSON records:
  - the SHA-256 of every array's bytes (with dtype and shape);
  - each artifact file's name, size and SHA-256;
  - the scalar inputs;
  - all results.

## 6. Measurements

1. **Row decomposition** of the stored solution's 50-digit residual
   `r_k = T_k x - b_k`.
   - The contributions are `c_k = r_k - r_{k+1}` along the chain
     `T_exact → T_D → T_D2 → T_coef → T_asm → T_eq`, and `r_eq` is the solve
     residual. Together they sum to `r_exact`.
   - Reported as complex values and magnitudes, normalized by the row scale
     `sum_j |T_ij||x_j| + |b_i|`.
   - Rows covered: 0, 1, 2, 3, `N` and `N+1`, plus the maximum and argmax
     over all rows.
   - Supporting evidence only; it does not enter the classification.
2. **High-precision approximations** `x̃_T` of the exact solution of each
   operator in the chain (Section 7).
3. **Spike attribution:**
   - `R_s = R(x_stored)`;
   - `Δ_solve = R_s - R(x̃_eq)`;
   - `Δ_op = R(x̃_eq) - R(x̃_exact)`;
   - `R_disc = R(x̃_exact)`, so that `R_s = Δ_solve + Δ_op + R_disc`;
   - step differences `Δ_step = R(x̃_k) - R(x̃_{k+1})` along the chain, with
     `sum Δ_step = Δ_op`.

   All are complex. Shares are `σ = |component| / |R_s|`.

## 7. High-precision approximations and their error

Each `x̃_T` is a **high-precision approximation**, not an exact solution. It
comes from iterative refinement:
- **Start:** `x^(0) = x_stored`.
- **Residual:** `rho = b_T - T x^(k)`, computed in 50 digits.
- **Correction:** `delta` from the production LU factorization of `Â`
  applied to `fl(rho_i / n_i)`, in double.
- **Update:** `x^(k+1) = x^(k) + delta`, accumulated in 50 digits.

Qualification of each `x̃_T`:
- **Backward error.** The componentwise backward error
  `beta = max_i |rho_i| / (sum_j |T_ij| |x_j| + |b_i|)` must be at most
  `1e-28` within 10 iterations. The denominator is evaluated in double from
  `|T_asm|` as a scale.
- **Effect on the spike.** The attribution uncertainty
  `e_T = |R(x^(K)) - R(x^(K-1))|` is the last iteration's change of the spike
  residual. It must be at most `0.01 |R_s|`.

Refinement contracts the error by roughly `kappa(Â) × ||T - T_eq|| / ||T||`
per iteration. The remaining error after the last iteration is therefore
expected to be far below `e_T`. `e_T` is used as a conservative bound.

Each quoted share carries uncertainty `(e_T + e_T') / |R_s|` from the two
approximations it uses. An approximation that fails qualification is a
technical stop for every quantity that uses it.

## 8. Prospective interpretation (per case and build, at the spike)

The first rule that applies decides, so the categories are mutually
exclusive and exhaustive:

| # | Outcome | Rule |
| --- | --- | --- |
| 1 | `zero-residual` | `R_s` is exactly zero; nothing is attributed |
| 2 | `technical-stop` | reconstruction failed, a Section 9 consistency check failed, or `x̃_eq` or `x̃_exact` is unqualified |
| 3 | `cancellation` | `σ_solve + σ_op + σ_disc > 1.5`: the components largely cancel, so no single attribution is meaningful |
| 4 | `solve-dominated`, `operator-rounding-dominated` or `discretization-dominated` | one share is `>= 0.8` and both others are `<= 0.25` |
| 5 | `mixed` | anything else |

Within the operator rounding, a step is named only when:
- `|Δ_op| > 0`;
- all intermediate approximations qualify;
- its `|Δ_step| >= 0.8 |Δ_op|` and `sum |Δ_step| <= 1.5 |Δ_op|`.

Otherwise the report says "several steps" or "cancellation among steps".

Possible responses, which O-C does not decide:
- **solve-dominated:** a solver improvement, such as refinement with an
  extended-precision residual;
- **operator-rounding-dominated:** a repair of the named step, such as
  trigonometric node differences and consistent nodes. A solver improvement
  against an accurately assembled operator also remains a candidate;
- **discretization-dominated:** a resolution or background treatment, or an
  independently justified gate redesign.

Any production repair needs its own prospective plan and validation. No
outcome changes a gate.

## 9. Fixtures and consistency checks

All fixtures must pass before any production case is examined. Each allows
at most three corrections.
- **F1.** 50-digit D1 and D2 for the production degree-640 physical nodes on
  `[1e-5, 1]`, and the spike evaluator off-node, reproduce a known degree-6
  polynomial's derivatives. The error is at most `1e-30` of the largest
  derivative magnitude.
- **F2.** On a normal-state case (ω/T = 40, degree 64), the reconstruction
  of Section 5 is bit for bit.
- **F3.** On the F2 case, each rounding step's row contribution lies within
  a loose a-priori rounding bound:

  | Step | Bound |
  | --- | --- |
  | equilibration | `4 eps × (sum_j |T_ij||x_j| + |b_i|)` |
  | assembly | `8 eps × sum_j (|D2_ij| + |c1_i||D1_ij| + delta_ij |V_i|) |x_j|`, with the analogous term magnitudes on boundary rows |
  | coefficients | `64 eps × (C1_i |(D1 f)_i| + W_i |f_i|)` |
  | `D @ D` | `gamma_{N+1} × (|D1|(|D1||f|))_i` |

  The bounds use term magnitudes, not `|T_ij|` or `|V|`, because terms
  cancel near the UV end. `C1 = |F'/F| + |2s/(1-u)|`, and `W` is the sum of
  the magnitudes of the four terms of `V`.

  The contributions and `r_eq` must sum to `r_exact` to `1e-40` relative.
  The same checks run on every production case; a violation is a technical
  stop for that case.
- **F4.** On the F2 case, all six approximations qualify (Section 7).
- **F5.** Take `b' = T_coef x_stored` exactly and start from `x_stored`
  perturbed by relative `1e-8`. Refinement must recover `x_stored` to `1e-25`
  normwise relative.

## 10. Budget, stopping and outputs

- **Budget:** as stated in the header. Every execution's wall time is logged
  and reported.
- **Stop and return if:**
  - production code would need to change;
  - a fixture fails after three corrections;
  - either budget is exhausted.

  Per-case technical stops are reported rather than repaired beyond these
  limits.
- **Outputs:**
  - an `optical-oc` subcommand in `tools/gate_calibration.py`, with fast
    tests;
  - `docs/numerics/optical-oc-diagnosis-report.md`;
  - evidence JSON under `docs/generated/optical-oc/`;
  - the local artifacts of Section 5;
  - one scoped PR and a consolidated handoff.
