# Chebyshev differentiation-matrix construction repair: proposed plan (revision 2)

- **Status: PROPOSED, revision 2.** Batch 3, item 1. Not approved, not
  frozen, not executed. AI-assisted (Claude).
  - Revision 1 (`2a50de5`) was reviewed by Codex on 1 October 2026. This
    revision addresses review items C1–C6 and the answers to revision 1's
    Section 6.
  - On owner approval of this exact text, a freeze commit precedes any code.
  - One approval covers the whole bounded milestone (S0–S3). No step needs
    separate approval unless it hits a stop.
- **Scope:** one shared routine, `chebyshev_lobatto_grid`, used by eight
  benchmark modules. Under the
  [compatibility policy](../version-0.5-compatibility-policy.md), numerical
  results change only through explicit scientific review; this plan is that
  review.
- **Closed** (none of these is changed or done):
  - gates, thresholds, tolerances and model physics;
  - solver polish and refits;
  - releases and branch deletion;
  - the BTZ framework pin (`668db63`) and its records;
  - private programs;
  - reserved cases;
  - historical evidence.

## 1. Why, and the current construction

- **O-C finding.** The [O-C diagnosis](optical-oc-diagnosis-report.md)
  attributed about 59% of the optical spike residual at degree 640 to the
  double-precision differentiation-matrix construction. It also accounts for
  essentially all of the UV-end collocation-node defect.
- **Consumers.** The same routine serves eight modules:
  - Gubser--Nellore;
  - Gubser--Rocha;
  - DeWolfe--Gubser--Rosen (DGR) neutral;
  - DGR finite density and critical point;
  - hard-wall chiral;
  - hard-wall vector (spectral route);
  - soft-wall (spectral route);
  - the optical benchmark.

**Current construction** (`src/holoforge/numerics/chebyshev.py`):
1. Nodes `x_k = cos(pi k/N)` in double.
2. `D = (c_i/c_j)(-1)^(i+j)/(x_i - x_j)`, with differences of rounded
   cosines, which cancel near `±1`.
3. Negative-sum diagonal.
4. Physical nodes `midpoint + half_width x`, rounded separately from the
   differences used in D.
5. `D2 = D @ D` through BLAS.

## 2. Reference operators (C1)

Two different exact reference problems are defined, both evaluated in
50-digit Decimal arithmetic:

- **`R_ideal(N, interval)`** — the exact differentiation matrices of the
  polynomial interpolant on the *ideal* Chebyshev--Lobatto nodes.
  - Nodes: `u_k = lower + width sin^2(pi k/(2N))`, computed in 50 digits.
  - Weights: `w_j = (-1)^j delta_j`, with `delta_0 = delta_N = 1/2`.
- **`R_stored(nodes)`** — the exact differentiation matrices of the
  polynomial interpolant through the *returned double nodes*. Its barycentric
  weights are recomputed from those nodes, as in the O-C oracle
  (`decimal_differentiation_matrices`).

**Intended production operator (frozen here).**
- The grid returns nodes and matrices together, and its consumers
  interpolate through the returned nodes. The operationally relevant target
  is therefore **`R_stored` for the returned nodes**.
- `R_ideal` accuracy is reported separately.
- **Irreducible inconsistency.** Near `u = 1` a returned node carries an
  absolute rounding of about `1e-16`, against a spacing of about `6e-6` at
  degree 640. No construction that returns double nodes is therefore exactly
  consistent with them. The plan measures stored-node consistency and does
  not claim it from the formula.
- **Why the stored-node candidate is predeclared.** The tension between the
  two targets is resolved by predeclaring C-S1 below, not by switching to it
  after seeing results.

**Oracle checks** (fixtures, Section 7):
- The 50-digit sine and pi used for `R_ideal` are checked against known
  values.
- `R_D2` from the recurrence is checked against the exact product
  `R_D1 · R_D1` at degrees at most 64, so that a shared recurrence mistake
  cannot validate itself (C3).

## 3. Declared candidates (the entire development space)

**Common to every candidate:**
- **Nodes** come from half-angles, using integer-index angles only:
  - `u_k = lower + width sin^2(pi k/(2N))` for `2k <= N`;
  - `u_k = upper - width sin^2(pi (N-k)/(2N))` otherwise.
- **Endpoints are exact**, ascending order, read-only arrays; API and argument
  checks are unchanged.

| Candidate | First derivative | Second derivative |
| --- | --- | --- |
| **C-T1** (ideal-consistent) | `D_ij = (w_j/w_i)/(u_i - u_j)` with `u_i - u_j = width sin(pi(i+j)/(2N)) sin(pi(i-j)/(2N))`, both sines from integer arguments; negative-sum diagonal | `D @ D` |
| **C-T2** | as C-T1 | explicit `D2_ij = 2 D_ij (D_ii - 1/(u_i - u_j))` for `i != j`, using the same trigonometric differences; negative-sum diagonal |
| **C-T3** | as C-T2 but stable half-grid: compute only rows `i <= floor(N/2)` directly (the midpoint row directly when N is even), then reflect `D_(N-i)(N-j) = -D_ij` | reflect `D2_(N-i)(N-j) = +D2_ij` |
| **C-S1** (stored-node-consistent) | differences `u_i - u_j` of the returned doubles (exact under Sterbenz's lemma for neighbours); weights recomputed from the returned nodes via log-magnitude products with explicit signs (no overflow); negative-sum diagonal | as C-T2, with these differences |

C-T3 follows Weideman and Reddy's `chebdif` reflection. It never evaluates
near-pi sines, and it never symmetrizes two independently computed halves.

In S0 the candidates may receive implementation fixes within their declared
definitions. No new candidate is added after results are seen.

## 4. Executable metrics (C2)

**Node sets** — this list bounds all unit coverage:
- **Degrees:** 2 (the minimum), 3, 16, 17, 40, 41, 64, 80, 96, 120, 128,
  150, 160, 192, 256, 320, 384, 512, 640, 1024 and 1280. These cover odd
  degrees, every production degree, and the optical check grid at 1280.
- **Intervals:** `[-1,1]`, `[1e-5,1]`, `[0,1]` and `[2,5]`.

**Test functions** (analytic derivatives, samples computed in 50 digits),
with `xi` the map of `u` to `[-1,1]`:
- `f1 = exp(3 xi)`;
- `f2 = sin(8 xi + 0.3)`;
- `f3 = 1/(1 + 4 xi^2)`;
- `f4`, a degree-6 polynomial with fixed exact coefficients (the exactness
  fixture).

Samples are rounded to double. Operators are then applied to the *same
double vector* by index.

**Common denominators.** Every metric uses a construction-independent
denominator, so that no apparent improvement can come from a changed
denominator.
- For each row `i`, the scale is `S_i = (|R_ideal| |f(ideal nodes)|)_i`.
- These are positive for f1–f4 at every listed grid. If one is not, it is
  reported as undefined and excluded, which is disclosed.

**Metrics:**
- **(a) row-scaled entrywise error:**
  `max_j |R_ij - D_ij| / max_j |R_ij|` for each row. It is reported against
  both `R_stored` (own nodes) and `R_ideal`, for D1 and D2 separately.
- **(b) row-scaled action error:** `|((R - D) f̂)_i| / S_i`, for D1 and D2.
  - The summary is the maximum over rows 1–3, rows `N-3`–`N-1`, and all rows.
  - It is reported against `R_stored` (primary) and `R_ideal`.
- **(c) optical artifact action (the selection metric).**
  - Take each of the eight preserved O-C artifacts. Their file hashes are
    verified first; the artifacts are read-only and never rewritten.
  - Apply the candidate's D1 and D2 to the artifact's stored solution vector
    `x` by index.
  - Compute the complex D-construction contribution vector
    `c = (T_R - T_cand) x`. `T` is the complete (N+2)-row optical operator
    with the exact coefficients and fixed boundary inputs of the O-C plan,
    Section 3. `R` is `R_stored` of the candidate's own returned nodes.
  - The denominator is the artifact's fixed row scale `sum_j |T_asm,ij| |x_j|
    + |b_i|`, identical for all constructions.
  - Signed complex `c_i` is retained. The summary is the maximum over rows
    1–3 and over all rows, as absolute values and as scaled ratios.
  - **This is an operator-action diagnostic on old sample vectors, not a new
    physical solution or residual.**
- **(d) build agreement:** the maximum entrywise difference of D1 and D2
  between B1 and B3, measured, not assumed zero. Also the construction's
  wall time.
- **Zero rule:** an improvement ratio is computed only when the baseline
  value is positive. Otherwise it is reported as undefined and does not
  count as an improvement. No numerical floor is added.

## 5. Selection (C3), frozen before S0 results

1. **Qualification.** A candidate qualifies only if, at every listed degree
   and interval, both of the following hold:
   - it is exact on f4, with metric (b) at most `1e-10` for D1 and D2 against
     `R_stored`;
   - metrics (a) and (b) are no worse than the current construction's by
     more than a factor of 2.

   A candidate failing a control is excluded. The others remain eligible.
2. **Choice.** Among qualified candidates, choose the smallest worst-case
   metric (c) over rows 1–3 and all eight artifacts.
   - Proceed only if that is at least **10× smaller** than the current
     construction's.
   - Ties within a factor of 1.5 are broken by (d): first the smaller build
     difference, then the lower cost.
3. **No qualified candidate reaches 10×:** stop, make no production change,
   and report.

The 10× and factor-2 figures are maintenance targets for this repair. They
are not new scientific acceptance thresholds for any benchmark.

## 6. Stages and order (C5, C6)

1. **S0 — development.**
   - Implement the oracle and the four candidates in a diagnostic module.
   - Fixtures first (Section 7).
   - Measure metrics (a)–(d) on B1 and B3.
2. **S1 — selection** by Section 5.
3. **Freeze.** Commit the selected construction into
   `chebyshev_lobatto_grid`, with unit tests over the Section 4 node set. From
   this commit on, any code correction invalidates S2 and S3 and returns the
   work for review.
4. **R0 — baseline.**
   - On the pre-change commit, run every command in Section 8 on B1 and B3.
   - Enumerate the observable and estimator leaves under the Section 8 paths.
   - Compute each limit by the Section 8 formula, and commit the regression
     table as a frozen file before any candidate verifier run.
   - Stop if a listed path matches no leaf, or if matching across builds or
     degrees is ambiguous.
5. **S2 — regression.** Run the same commands on the frozen candidate commit
   on B1 and B3; Linux comes from PR CI and telemetry, reported as additional
   execution.
   - **A1.** No gate that passes at baseline may fail after, on the same
     build. This includes the GN and optical gates. A1 takes precedence over
     everything else.
   - **Failing gates.** Gates that already fail are recorded individually,
     with values and build provenance.
   - **A2.** Every table entry satisfies `|Δ| <= limit`.
   - **A3.** The GN and optical gate values are reported on all builds.
   - A violation of A1 or A2 is a stop, and is reported.
6. **S3 — post-selection revalidation** (not an untouched holdout: it
   reuses the selection cases).
   - Rerun the O-C decomposition at ω/T = 60 and 59, degree 640, on B1 and
     B3, with the frozen construction.
   - Report the **absolute** D-construction contribution at a fixed
     normalization, the shares, and a freshly evaluated discretization part.
     Nothing is assumed about the former 40%.
   - Expectation (target, not acceptance): the absolute D-construction
     contribution falls to at most 10% of its O-C value.

**No reserved case is used.** Observed deltas are reported as measured.
Rounding-level changes are not promised in advance.

## 7. Fixtures (before S0 measurements; at most three corrections each)

- **F1.** The 50-digit sine and pi agree with known values to `1e-45`, and
  `R_ideal` nodes satisfy `sin^2 + cos^2 = 1` to `1e-45`.
- **F2.** The recurrence-based `R_D2` equals the exact `R_D1 · R_D1` to
  `1e-40` at degrees 2, 3, 16, 17 and 64.
- **F3.** `R_stored` and `R_ideal` reproduce f4's exact derivatives to
  `1e-30`, at degrees 16, 17 and 640.
- **F4.** The O-C artifact hashes match the committed O-C evidence. The
  current construction's metric (c) reproduces O-C's D-construction row
  contributions for rows 1–3 at 60/640 on B1, to `1e-6` relative.
- **F5.** Every candidate returns ascending nodes, exact endpoints,
  read-only arrays and an unchanged API, at every degree listed in
  Section 4.

## 8. Per-consumer regression table (C4)

**Conventions.**
- All comparisons are absolute differences of the same leaf. Relative fields
  are converted to absolute by multiplying by the baseline value's magnitude.
- Complex values are compared by modulus of the difference.
- Matching is by the named key. States must match exactly, or the entry
  stops.

**Limit formula** (frozen):
```text
limit = 10 × max(E, X, 8 eps |baseline value|)
```
- `E` is the named estimator, from the baseline record on the same build.
- `X` is the baseline B1-versus-B3 difference of the same leaf.
- `8 eps |value|` is the double representation level. It is the only floor,
  and it applies uniformly.
- An estimator is an estimator, not a proved bound. Exceeding the limit is a
  stop to be reported, not an automatic physics failure.

**Routes whose results must stay bit for bit identical** (negative
controls): the soft-wall finite-difference default, and the hard-wall vector
shooting and collocation routes, if code inspection at R0 confirms that they
do not call the routine. Otherwise they move into the table.

| Consumer and commands | Observables (JSON pointer, `*` over a list) | Match key | Estimator `E` |
| --- | --- | --- | --- |
| **Soft-wall, spectral:** `holoforge verify soft-wall-vector --method spectral --json` with `--spectral-degree` 40, 56, 64 and 100; `--modes 6 --spectral-degree 64`; the existing adverse cases `--z-max 4` and `--z-max 6` at degree 64 | `/results/*/numerical_mass_squared_gev2` | degree, mode `n` | the baseline analytic error `abs(numerical - analytic)` of the same mode |
| **Hard-wall vector, spectral:** `holoforge verify hard-wall-vector --method spectral --json` at the default and each degree in its recorded spectral refinement ladder; `--method shooting` at the same cutoff as control | `/results/*/numerical_m_z_m`, `/results/*/numerical_ratio` | degree, `n`, same `epsilon-fraction` | the final entry of the recorded spectral refinement differences for that mode, and the shooting-versus-spectral difference at the same cutoff (the zero-cutoff Bessel mismatch is not used) |
| **Hard-wall chiral:** default verify | `/results/levels/*/observables/*`, `/results/table/*/computed`, `/results/gmor/*/{m_pi_MeV,f_pi_MeV,R_GMOR}` | degree and name; row `observable`; `m_q_factor` | `/results/refinement/<name>/N80_to_N96`; `/results/cutoff_changes/<name>` and `/results/cross_route_differences/<name>`, where present; `f_pi` separately via `/results/independent/*/f_pi_route_relative_difference` (the 1% source-table allowance is not used) |
| **Gubser--Nellore:** default verify (both presets) | `/results/presets/*/curve/*/{temperature_L,sound_speed_squared}`; `/results/presets/*/independent_comparisons/*/actual_phi_h` | preset, `x_h` | `/results/presets/*/refinement/maximum_final_change` for temperature; for `sound_speed_squared`, the larger of that and `maximum_derivative_disagreement`; `independent_comparisons/*/{temperature,entropy,sound_speed}_relative_error` reported alongside |
| **Gubser--Rocha:** default verify | `/results/cases/*/observables/*` (temperature, chemical potential, black-hole parameter, energy, entropy and charge densities) | case `xi`, observable name | `/results/refinement/cases/*/observables/*/middle_to_fine` of the same observable |
| **DGR neutral:** default verify | `/results/curve/*/{temperature_BH,entropy_BH,chi_2_over_T2_BH,s_over_T3_plot}`; `/results/degree_branches/*/points/*/` (same fields) | `phi_h`, and degree for branches | `/results/refinement/maximum_final_change`; for `chi_2`, the larger of that and `/results/quadrature_refinement/records/*/middle_to_fine_change`; `independent_comparisons/*` reported (Figure 3 mismatch is not used) |
| **DGR finite density / critical point:** default verify | `/results/refinement/states/*` (T, mu, s, rho); `/results/controls/*` (same) | registered state label | `/results/refinement/changes` for the same observable, and the `route_*_relative_difference` fields. The critical coordinates `/results/critical/*` are compared separately against their own step evidence (`maximum_step_change`). The Figure 5 absolute-density comparison is not opened. |
| **HHH optical:** default verify | complex conductivities in `/results/normal_responses/*`, `/results/near_critical_pole/*` (pole residue and static pole) and `/results/figure_2_provenance/*` | state, ω/T | `resolution_change`, `series_truncation_change` and `route_relative_difference` of the same response; background cutoff change from `/results/cutoff_refined_conditioned_background`; `uv_refinement_change` (the equation-residual threshold is not used as conductivity uncertainty) |

The exact leaf lists under these pointers are enumerated at R0 and committed
before any candidate run. The pointers above were read from the code and
from the committed records of hard-wall chiral, GN and DGR neutral. A
pointer that does not resolve is an R0 stop, not an improvisation.

## 9. Records, versioning and compatibility

- **Unchanged:** signatures, defaults, ordering, dtype, read-only arrays, CLI
  semantics and exit meanings.
- **New provenance field.** New records carry a construction identifier, for
  example `chebyshev_construction: "c-t2-r1"`. This is a
  backward-compatible addition, so schema versions do not change.
- **Unchanged contracts.** Gate and contract versions stay unchanged. This is
  a numerical-method repair, not a new physical model.
- **Model cards.** A digest is updated only if a card's bytes change, and is
  then verified.
- **Historical evidence is untouched.** That covers the O-B, O-C, S-A and
  calibration evidence, source fingerprints, evidence bundles and private
  programs. Historical replay uses an isolated exact commit and its recorded
  environment. No legacy switch is added.
- **New records** carry the baseline and candidate commits, source digests,
  build and thread information, and the selected method. They go to new
  output locations. Different content hashes are expected, and no new record
  impersonates an old one.
- **Versioning.** An Unreleased changelog entry lists the measured
  per-consumer deltas. A future 0.7.1 patch is a provisional target only; no
  tag or release is part of this plan.
- **Private research.** Not rerun. The BTZ pin is unchanged.

## 10. Budget, stopping and outputs

- **Budget, for item 1 only:**
  - at most 6 hours of active work;
  - at most 60 cumulative minutes of local execution. This counts fixtures,
    failed attempts, baseline and candidate runs, regression and S3.
  - Full-suite verifier runs are reused only where they demonstrably cover
    an exact Section 8 case.
  - PR CI and telemetry are reported as additional execution.
- **Budget exhausted:** return incomplete, without removing cases or
  extending the budget.
- **Stop and return if:**
  - a fixture fails after three corrections;
  - the S1 selection fails;
  - an R0 pointer is unresolved or matching is ambiguous;
  - A1 or A2 fails;
  - a post-freeze code correction is needed;
  - a budget is exhausted.
- **Outputs:**
  - one PR containing the frozen plan, the implementation and tests, the R0
    table, S0–S3 evidence (under `docs/generated/chebyshev-repair/`) and a
    report;
  - a handoff covering what changed, per-consumer deltas, gate values by
    build, deviations and resource use.

Nothing is merged without Codex review and owner approval.
