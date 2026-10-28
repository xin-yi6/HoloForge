# Chebyshev differentiation-matrix construction repair: plan, frozen before execution

- **Status: FROZEN** before any P0, S0–S3 code or run. Batch 3, item 1.
  AI-assisted (Claude).
  - This is revision 3 (`0d4442d`), which Codex reviewed with no blocking
    finding. The owner approved the complete bounded milestone on 1 October
    2026. Only this status block and the title changed at freeze.
  - **Baseline (pre-change) commit:** `main` at `5846975`, merged into this
    branch before the freeze.
  - One approval covers the whole bounded milestone (P0, S0–S3). No routine
    step needs separate approval unless it hits a stop.
- **Scope:** one shared routine, `chebyshev_lobatto_grid`, used by eight
  benchmark modules. Under the
  [compatibility policy](../version-0.5-compatibility-policy.md), numerical
  results change only through explicit scientific review; this plan is that
  review.
- **Closed** (none of these is changed or done):
  - gates, thresholds, tolerances and model physics;
  - solver polish and refits;
  - paid compute;
  - installations;
  - CI-dispatched scientific runs beyond ordinary PR CI and the existing PR
    gate telemetry;
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
- **Consumers and call sites** (read from source at `5846975`):

  | Module | Functions that call the routine |
  | --- | --- |
  | soft-wall vector | `_spectral_spectrum`, `_spectral_level_diagnostics` (spectral route only) |
  | hard-wall vector | `_spectral_dimensionless_masses` (spectral route only) |
  | hard-wall chiral | `solve_spectral_mode`, `_mode_diagnostics` |
  | Gubser--Nellore | `solve_coupled_profile`, `coupled_equation_diagnostics` |
  | Gubser--Rocha | `solve_emd_profile`, `equation_diagnostics` |
  | DGR neutral | `einstein_constraint_residual`, and Gubser--Nellore's solver, which it imports |
  | DGR finite density / critical point | `_solve_charged_once`, `_solve_explicit_maxwell_once`, `charged_equation_diagnostics`, `explicit_maxwell_diagnostics` |
  | HHH optical | `solve_spectral_response`, `solve_endpoint_split_spectral_response`, `solve_series_transferred_spectral_response`, and the two independent residual checks |

**Current construction** (`src/holoforge/numerics/chebyshev.py`):
1. Nodes `x_k = cos(pi k/N)` in double.
2. `D = (c_i/c_j)(-1)^(i+j)/(x_i - x_j)`, with differences of rounded
   cosines, which cancel near `±1`.
3. Negative-sum diagonal.
4. Physical nodes `midpoint + half_width x`, rounded separately from the
   differences used in D.
5. `D2 = D @ D` through BLAS.

## 2. Reference operators

Both are evaluated in 50-digit Decimal arithmetic.

- **`R_ideal(N, interval)`** — the exact differentiation matrices of the
  polynomial interpolant on the *ideal* Chebyshev--Lobatto nodes.
  - Nodes: `u_k = lower + width sin^2(pi k/(2N))`, in 50 digits.
  - Weights: `w_j = (-1)^j delta_j`, with `delta_0 = delta_N = 1/2`.
- **`R_stored(nodes)`** — the exact differentiation matrices of the
  polynomial interpolant through the *returned double nodes*, with
  barycentric weights recomputed from those nodes (the O-C oracle).

**Two distinct effects are kept apart:**
- **Node-set difference.** The returned double nodes are a valid node set.
  They define their own well-posed interpolation problem, whose exact
  matrices are `R_stored`. That they differ from the ideal nodes is not an
  error in any matrix. It shows up as `R_stored - R_ideal`.
- **Matrix rounding.** The computed double matrix differs from its target
  reference because of floating-point arithmetic in its construction.

**Intended production operator (frozen here).** The grid returns nodes and
matrices together, and its consumers interpolate through the returned nodes.
The primary target is therefore `R_stored` for the returned nodes. Agreement
with `R_ideal` is reported separately. A C-T candidate builds its matrix from
ideal-grid differences, so its distance from `R_stored` includes the node-set
difference. That is why the stored-node candidate C-S1 is declared in
advance.

## 3. Declared candidates (the entire development space)

**Common to every candidate:**
- **Nodes** come from half-angles, using integer-index angles only:
  - `u_k = lower + width sin^2(pi k/(2N))` for `2k <= N`;
  - `u_k = upper - width sin^2(pi (N-k)/(2N))` otherwise.
- **Endpoints are exact**, ascending order, read-only arrays; API and argument
  checks are unchanged.

| Candidate | First derivative | Second derivative |
| --- | --- | --- |
| **C-T1** (ideal-grid) | `D_ij = (w_j/w_i)/(u_i - u_j)` with `u_i - u_j = width sin(pi(i+j)/(2N)) sin(pi(i-j)/(2N))`, both sines from integer arguments; negative-sum diagonal | `D @ D` |
| **C-T2** | as C-T1 | explicit `D2_ij = 2 D_ij (D_ii - 1/(u_i - u_j))` for `i != j`, same differences; negative-sum diagonal |
| **C-T3** | as C-T2 on the stable half-grid: compute only rows `i <= floor(N/2)` (the midpoint row directly when N is even), then reflect `D_(N-i)(N-j) = -D_ij` | reflect `D2_(N-i)(N-j) = +D2_ij` |
| **C-S1** (stored-node) | differences `u_i - u_j` of the returned doubles; weights recomputed from the returned nodes by log-magnitude products with explicit signs; negative-sum diagonal | as C-T2, with these differences |

C-T3 follows Weideman and Reddy's `chebdif` reflection. It never evaluates
near-pi sines, and it never symmetrizes two independently computed halves.

In S0 the candidates may receive implementation fixes within these
definitions. No candidate is added after results are seen.

## 4. Metrics

**Node sets** — this list bounds all unit coverage:
- **Degrees:** 2 (the minimum), 3, 16, 17, 40, 41, 64, 80, 96, 120, 128,
  150, 160, 192, 256, 320, 384, 512, 640, 1024 and 1280.
- **Intervals:** `[-1,1]`, `[1e-5,1]`, `[0,1]` and `[2,5]`.

**Row sets** — defined for every `N >= 2`, never empty:
- all rows: `0..N`;
- interior rows: `1..N-1`;
- UV set: `1..min(3, N-1)`;
- IR set: `max(1, N-3)..N-1`.

At `N = 2` both end sets are `{1}`; at `N = 3` both are `{1, 2}`. Endpoint
rows `0` and `N` belong to "all rows" only.

**Required-metric rule.** A metric that this plan requires and that turns
out undefined (for example, a zero denominator) is a failure of that
requirement. It is never dropped: a fixture fails, or a candidate is
disqualified at that grid, and the event is reported.

### 4.1 Operator-agreement metrics (no analytic derivative is used)

- **Sample vectors.** With `xi` the affine map of `u` to `[-1,1]`:
  - `v1 = exp(3 xi)`;
  - `v2 = sin(8 xi + 0.3)`;
  - `v3 = 1/(1 + 4 xi^2)`.
- **Evaluation.** Each is evaluated in 50 digits at the candidate's returned
  nodes and rounded to double.
- **Same vector on both sides.** The candidate and the reference act on the
  *same double vector* by index, so sample rounding cancels exactly. These
  vectors are used only as test vectors; their true derivatives play no role.
- **Common denominators.** For each row `i`,
  `S_i = (|R_ideal| |v(ideal nodes)|)_i`, which does not depend on the
  construction. `S_i > 0` is required.

Metrics:
- **(a) row-scaled entrywise error:**
  `max_j |R_ij - D_ij| / max_j |R_ij|` for each row, for D1 and D2. It is
  reported against `R_stored` (primary) and `R_ideal`.
- **(b) row-scaled action error:** `|((R - D) v̂)_i| / S_i` for D1 and D2. The
  summary is the maximum over the UV set, the IR set and all rows. It is
  reported against `R_stored` (primary) and `R_ideal`.
- **(c) optical artifact action (the selection metric).**
  - Take each of the eight preserved O-C artifacts. Their file hashes are
    verified first; the artifacts are read-only and never rewritten.
  - Apply the candidate's D1 and D2 to the artifact's stored solution vector
    `x` by index.
  - Compute the complex contribution vector `c = (T_R - T_cand) x`. `T` is the
    complete (N+2)-row optical operator of the O-C plan, Section 3, with its
    exact coefficients and fixed boundary inputs. `R` is `R_stored` of the
    candidate's own returned nodes.
  - The denominator is the artifact's fixed row scale `sum_j |T_asm,ij| |x_j|
    + |b_i|`, identical for all constructions.
  - Signed complex `c_i` is retained. The summary is the maximum over rows
    1–3 and over all rows, as absolute values and as scaled ratios.
  - **This is an operator-action diagnostic on old sample vectors, not a new
    physical solution or residual.**
- **(d) build agreement:** the maximum entrywise difference of D1 and D2
  between B1 and B3, measured, not assumed zero. Also the construction's
  wall time.

### 4.2 Analytic polynomial-exactness tests (separate from 4.1)

- **Polynomial.** `P_d(xi) = sum_{k=0..d} c_k xi^k`, with the fixed
  coefficients
  `c = (1, 2 - i, -3 + i/2, 1/4 + 4i, 5, -2i, 3/2 + i)`.
  - Degree `d = min(6, N)`, so the polynomial is exactly representable at
    every listed `N` (degree 2 at `N = 2`, degree 3 at `N = 3`).
  - Derivatives in `u` follow from the chain rule with `d xi/du = 2/width`.
- **Double-precision test of a candidate.**
  - Samples `P_d` are evaluated in 50 digits at the returned nodes and
    rounded to double.
  - The double matrix is applied to them exactly (in 50 digits), and the
    result is compared with the analytic derivative at the returned nodes.
  - The metric is `|(D p̂)_i - P_d^(m)(u_i)| / (|R_stored| |p̂|)_i`, for
    `m = 1, 2`.
  - **Sample rounding is accounted for.** It contributes at most
    `eps/2 × (|D| |p̂|)_i`, about `1.1e-16` of the row scale. The
    qualification limit below is `1e-10`, far above that contribution, so
    sample rounding cannot cause a failure.

## 5. Selection, frozen before S0 results

1. **Qualification.** A candidate qualifies only if, at every listed degree
   and interval, both of the following hold:
   - the polynomial-exactness metric (Section 4.2) is at most `1e-10` for D1
     and D2 on all rows;
   - operator-agreement metrics (a) and (b) against `R_stored` are no worse
     than the current construction's by more than a factor of 2.

   A candidate that fails is excluded. The others remain eligible.
2. **Choice.** Among qualified candidates, choose the smallest worst-case
   metric (c) over rows 1–3 and all eight artifacts.
   - Proceed only if that is at least **10× smaller** than the current
     construction's. The current value is positive by the O-C evidence. If it
     were not, the required-metric rule makes this a stop.
   - Ties within a factor of 1.5 are broken by (d): first the smaller build
     difference, then the lower cost.
3. **No qualified candidate reaches 10×:** stop, make no production change,
   and report.

The `1e-10`, 10× and factor-2 figures are maintenance targets for this
repair. They are not scientific acceptance thresholds for any benchmark.

## 6. Stages and order

1. **P0 — structural preflight (no numerics).**
   - Commit the regression table of Section 8 as a machine-readable file,
     with a static checker.
   - The checker verifies each of the following against the source and the
     committed records:
     - every pointer, match key, estimator mapping and conversion;
     - the call sites of Section 1;
     - the control-route classification.
   - It runs no verifier and no candidate.
   - Stop if a pointer does not resolve, or a route cannot be classified.
2. **S0 — development.**
   - Implement the oracle and the four candidates in a diagnostic module.
   - Fixtures first (Section 7).
   - Measure the metrics of Section 4 on B1 and B3.
3. **S1 — selection** by Section 5.
4. **Freeze.** Commit the selected construction into
   `chebyshev_lobatto_grid`, with unit tests over the Section 4 node set. From
   this commit on, any code correction invalidates S2 and S3 and returns the
   work for review.
5. **R0 — numerical baseline.**
   - On the pre-change commit, run every command of Section 8 on B1 and B3.
   - Compute each limit by the Section 8 rule, and commit the baseline values
     and limits before any candidate verifier run.
6. **S2 — regression.** Run the same commands on the frozen candidate commit
   on B1 and B3; Linux comes from ordinary PR CI and the existing PR
   telemetry, reported as additional execution.
   - **A1.** No gate that passes at baseline may fail after, on the same
     build. This includes the GN and optical gates and every existing
     acceptance check. A1 takes precedence over everything else.
   - **Failing gates.** Gates that already fail are recorded individually,
     with values and build provenance. No gate, tolerance, refit or solver
     polish changes.
   - **A2.** Every table entry satisfies `|Δ| <= allowance`.
   - **A3.** The GN and optical gate values are reported on all builds.
   - **Controls** are bit for bit identical.
   - A violation of A1, A2 or a control is a stop, and is reported.
7. **S3 — post-selection revalidation** (not an untouched holdout: it
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

Every fixture compares 50-digit quantities, with no double rounding, unless
stated.
- **F1 — oracle arithmetic.**
  - The 50-digit pi matches a fixed 60-digit literal.
  - `sin(pi/6) = 1/2`, `sin(pi/2) = 1` and `sin^2 + cos^2 = 1` at 1000 sample
    angles, all to `1e-45`.
- **F2 — recurrence independence.** At degrees 2, 3, 16, 17 and 64, the
  recurrence-based `R_D2` equals the exact matrix product `R_D1 · R_D1`. The
  maximum entrywise difference is at most `1e-40` of the largest entry.
- **F3 — oracle polynomial exactness.** At degrees 2, 3, 16, 17 and 640:
  - Samples `P_d(xi(u_k))` are evaluated in 50 digits at the reference's own
    nodes, **not rounded**: the stored double nodes converted exactly for
    `R_stored`, and the 50-digit ideal nodes for `R_ideal`.
  - `R_D1` and `R_D2` applied to them must equal the analytic `P_d'` and
    `P_d''` at those nodes. The maximum error over rows is at most `1e-30` of
    the largest derivative magnitude over rows.
  - **Zero-derivative case.** If that largest magnitude is zero, the test is
    absolute, with limit `1e-30`. This occurs for no listed case, since
    `d >= 2`.
- **F4 — artifacts and continuity.**
  - The O-C artifact hashes match the committed O-C evidence.
  - Metric (c) uses the construction's own D2. For the current construction
    it therefore equals the sum of two saved O-C contributions:
    D-construction and `D @ D` product.
  - It must reproduce that complex sum for rows 1–3 at 60/640 on B1, to
    `1e-6` relative.
- **F5 — API.** Every candidate returns ascending nodes, exact endpoints,
  read-only arrays and unchanged signatures, at every degree listed in
  Section 4.

## 8. Regression table

### 8.1 Rule

- **Comparison.** For each table leaf, `Δ` is the candidate value minus the
  baseline value on the same build, in the leaf's own units. Complex
  conductivities use `|Δ| = hypot(Δreal, Δimag)`.
- **Allowance.**
  ```text
  allowance = 10 × max(E, X, 8 eps |baseline value|)
  ```
  - **`E`** is the largest of the estimators listed for that leaf. Each is
    first converted to absolute units by the conversion stated with it. They
    are combined by maximum, not by sum or statistical combination.
  - **`X`** is the absolute B1-versus-B3 difference of the same leaf at
    baseline.
  - **`8 eps |value|`** is the double representation level. It is the only
    floor, and it applies uniformly.
- **What the allowance is.** It is a **maintenance regression allowance**,
  not a physical uncertainty.
  - `E` is the benchmark's own numerical-error indicator. It is an estimator,
    not a proved bound.
  - `X` is the build-to-build variation the platform already accepts for
    unchanged code. It is not an error estimate.
  - The factor 10 is fixed a priori. It allows a rounding-level change of the
    operator to be amplified by a conditioned nonlinear or eigenvalue solve,
    by about one order of magnitude beyond those indicators.
  - Passing A2 does not certify any observable's accuracy. Exceeding the
    allowance is a stop to be reported, not an automatic physics failure.
- **Gates.** A1 and every existing acceptance check are independent of this
  allowance and unchanged.
- **Matching.** Matching uses the stable identifier named below. Numerically
  solved coordinates are never required to be equal.
- **Controls.** A leaf marked *control* belongs to a route that does not
  call the routine. It must be bit for bit identical.
- **Report-only leaves.** A leaf marked *report-only* has no recorded
  numerical estimator. Its delta is reported, and it is not part of A2.

### 8.2 Entries

**Soft-wall vector, spectral route.**
- **Commands.** `holoforge verify soft-wall-vector --method spectral --json`
  with:
  - `--spectral-degree` 40, 56, 64 and 100;
  - `--modes 6 --spectral-degree 64`.
- **Leaves:** `/results/*/numerical_mass_squared_gev2`. Key: command and
  `n`.
- **Estimator:** `/results/*/relative_error`, which is
  `|numerical - analytic| / analytic`. Conversion: multiply by
  `/results/*/analytic_mass_squared_gev2` of the same mode (exact inverse).
- **Verdict controls:** the truncated-domain cases `--z-max 4` and
  `--z-max 6` at degree 64. Their analytic error is cutoff bias, not
  discretization error, so no allowance is derived from it. Every
  acceptance-check outcome must be unchanged; eigenvalue deltas are
  report-only.
- **Control:** the default finite-difference route (`holoforge verify
  soft-wall-vector --json`).
- **Not recorded:** eigenvalues at the two lower refinement degrees. The
  record holds only `/spectral_convergence/levels/*/max_relative_error` and
  the rule-v2 plateau diagnostics, which are report-only.

**Hard-wall vector, spectral route.**
- **Command:** `holoforge verify hard-wall-vector --method spectral --json`
  (degree 40, default cutoff).
- **Leaves:** `/results/*/numerical_m_z_m`, and `/results/*/numerical_ratio`
  for `n >= 2`. Key: `n`. The ratio at `n = 1` is identically 1 and is a
  control.
- **Estimators:**
  - the last entry `d` of
    `/spectral_convergence/successive_max_relative_differences`. It is the
    maximum over modes of `|current - previous| / current`. Conversion:
    `d × |value|` for a mass, and `2 d × |ratio|` for a ratio;
  - the absolute spectral-versus-shooting difference of the same leaf at the
    same cutoff, from the baseline runs.
- **Controls:** `--method shooting` and `--method collocation`.
- **Not recorded:** the spectra at the two lower ladder degrees, and any
  per-mode refinement. The zero-cutoff Bessel mismatch is not used.

**Hard-wall chiral** (default verify).
- **Leaves:**
  - `/results/levels/*/observables/<name>` for the seven names `m_pi_MeV`,
    `m_rho_MeV`, `m_a1_MeV`, `f_pi_MeV`, `sqrt_F_rho_MeV`, `sqrt_F_a1_MeV` and
    `g_rho_pi_pi`. Key: `/results/levels/*/degree` (64, 80, 96) and name;
  - `/results/table/*/computed`. Key: `observable`.
- **Estimators.** Each is `|value - reference| / |reference|`.
  - `/results/refinement/<name>/N80_to_N96` for degree-96 and table leaves.
    Conversion: multiply by the degree-80 level value.
  - `/results/refinement/<name>/N64_to_N80` for degree-80 and degree-64
    leaves. Conversion: multiply by the degree-64 value.
  - Where the name is present (`m_pi_MeV`, `m_a1_MeV`, `sqrt_F_a1_MeV`,
    `g_rho_pi_pi`): `/results/cutoff_changes/<name>`, converted by the
    second-finest `/results/independent/*/<name>`; and
    `/results/cross_route_differences/<name>`, converted by the degree-96
    value.
  - For `f_pi_MeV`: `/results/independent/*/f_pi_route_relative_difference`,
    converted by `f_pi_dop853_MeV` of the same entry.
- **Controls:** `/results/independent/*` (`solve_bvp` and DOP853), keyed by
  `epsilon`.
- **Report-only:** `/results/gmor/*/{m_pi_MeV, f_pi_MeV, R_GMOR}` (key
  `m_q_factor`). No numerical estimator is recorded for the scaled-mass
  runs.
- **Not used:** the 1% source-table allowance.

**Gubser--Nellore** (default verify; `/results/presets` is a mapping with
keys `cosh-calibration` and `qcd-like`).
- **Leaves:** `/results/presets/<preset>/curve/*/temperature_L` and
  `.../sound_speed_squared`.
- **Key:** preset and list position. `x_h` is the configured coordinate and
  must agree to `4 eps`, or the entry stops.
- **Estimators:**
  - `/results/presets/<preset>/refinement/maximum_final_change`. This is one
    number per preset: the maximum over all points, and over temperature,
    entropy and `c_s^2`, of `|fine - middle| / |fine|`. Conversion: multiply
    by the leaf's own magnitude. It is an upper indicator for an individual
    leaf.
  - For `sound_speed_squared`, also
    `/results/presets/<preset>/maximum_derivative_disagreement`. It is
    already absolute: the maximum of `|barycentric - PCHIP|`.
- **Report-only:**
  - `.../curve/*/phi_h`, a solved coordinate with no estimator;
  - `/results/presets/<preset>/independent_comparisons/*`, keyed by
    `target_phi_h` (not `x_h`).
- **Not recorded:** entropy is not a curve leaf. It enters only the
  preset-level estimator and the independent comparisons.

**Gubser--Rocha** (default verify).
- **Leaves:** `/results/cases/*/thermodynamics/<field>` for `mu_bh`,
  `hat_epsilon`, `hat_s`, `hat_rho`, `temperature` and `Omega`. Key: `xi`, a
  configured value.
- **Estimators:**
  - `/results/refinement/cases/*/observables/<name>/middle_to_fine`, matched
    by `xi`.

    | Estimator name | Leaf field |
    | --- | --- |
    | `mu_bh` | `mu_bh` |
    | `energy_density` | `hat_epsilon` |
    | `entropy_density` | `hat_s` |
    | `charge_density` | `hat_rho` |
    | `temperature` | `temperature` |
    | `chemical_potential` | `Omega` |

    Its normalization is `|fine - middle| / max(1, |fine|, |middle|)`.
    Conversion: multiply by `max(1, |fine value|)`. The middle value is not
    recorded, so this conversion is exact only up to a relative error of the
    estimator's own size.
  - The absolute difference between the leaf and
    `/results/cases/*/source_exact_thermodynamics/<field>`, the closed-form
    solution. No normalization is involved.
- **Report-only:** `.../thermodynamics/maxwell_flux`.

**DGR neutral** (default verify; `/results/degree_branches` is a mapping with
keys `80`, `120` and `150`).
- **Leaves:**
  - `/results/curve/*/<field>` for `temperature_BH`, `entropy_BH`,
    `susceptibility_integral` and `chi_2_over_T2_BH`;
  - `/results/degree_branches/<degree>/points/*/<field>`, for the same
    fields.
- **Key:** list position, identified with
  `/configuration/physical_phi_h_targets[position]`. The solved `phi_h` and
  `x_h` are report-only. In the committed record only 1 of 20 solved `phi_h`
  values equals its target exactly.
- **Estimators:**
  - the absolute difference between the same position's values at the two
    finest degrees, read from `/results/degree_branches`: 150 against 120
    for curve and degree-150 leaves, and 120 against 80 for degree-120 and
    degree-80 leaves;
  - for the two susceptibility fields,
    `/results/quadrature_refinement/records/*/middle_to_fine_change` at the
    same position. Its normalization is `|a - b| / max(|a|, |b|)`.
    Conversion: multiply by the leaf's magnitude.
- **Report-only:**
  - the plot-unit copies `temperature_MeV`, `s_over_T3_plot` and
    `chi_2_over_T2_plot`;
  - `/results/refinement/maximum_final_change`, a record-level maximum;
  - `/results/independent_comparisons/*`, keyed by `target_phi_h`.
- **Not used:** the Figure 3 source mismatch.

**DGR finite density / critical point** (default verify).
- **Leaves** — `<field>` is `temperature_BH`, `mu_BH`, `entropy_BH` or
  `rho_canonical_BH`:
  - `/results/refinement/states/*/primary/point/<field>` and
    `.../explicit/point/<field>`. Key: `degree`; the label is the constant
    `located-critical-state`.
  - `/results/controls/*/primary/point/<field>` and
    `.../explicit/point/<field>`. Key: `label` (`neutral`, `charged`,
    `high-charge`).
- **Estimators:**
  - `/results/refinement/changes/*/changes/<field>`, keyed by
    `(coarse_degree, fine_degree)`. Its normalization is
    `|a - b| / max(1, |a|, |b|)`. Conversion: multiply by
    `max(1, |coarse value|, |fine value|)`. Both values are recorded, so the
    inverse is exact.
  - the absolute primary-versus-explicit difference of the same leaf, taken
    directly from the two recorded points.
- **Single-degree states.** The control states exist at one degree only. For
  them the route difference is the only estimator.
- **Critical coordinates, compared separately:**
  - Leaves: the last entry of `/results/critical/step_roots`, with fields
    `phi_H`, `eta`, `T_BH`, `mu_BH` and `rho_canonical_BH`.
  - Estimator: the last entry of `/results/critical/scaled_step_changes` for
    the same field. Its normalization is `|a - b| / max(1, |a|, |b|)`.
    Conversion: multiply by the two last roots, as above.
- **Not opened:** the Figure 5 absolute-density comparison.

**HHH optical** (default verify).
- **Leaves:**
  - `spectral_conductivity/{real, imag}`, compared as one complex value, in
    `/results/normal_responses/*`, `/results/figure_2_provenance/responses/*`
    and `/results/near_critical_pole/points/*/responses/*`;
  - `/results/near_critical_pole/points/*/pole_intercept`.
- **Keys:** `omega_over_temperature`, a configured value; near-critical
  points by list position, with `temperature_over_tc` report-only.
- **Estimators for a response.** Each is taken from the same response.
  - `resolution_change`, `series_truncation_change`, and
    `background_cutoff_change` where present. Each is
    `|Δσ| / (1 + |σ_spectral|)`. Conversion: multiply by
    `1 + spectral_conductivity/magnitude`.
  - `route_relative_difference`, which is `|Δσ| / (1 + |σ_independent|)`.
    Conversion: multiply by `1 + independent_conductivity/magnitude`.
- **Estimators for `pole_intercept`:**
  - `intercept_stability`, which is `|reduced - intercept| / |intercept|`.
    Conversion: multiply by `|pole_intercept|`.
  - `static_pole_relative_difference`, which is
    `|rho_s - intercept| / |rho_s|`. Conversion: multiply by
    `|static_london/superfluid_density_over_tc|`.
- **Controls, to be confirmed by the P0 call graph:**
  `independent_conductivity` and `static_london/*` (DOP853 routes). If either
  reaches the routine, it moves into the table with the estimators above.
- **Report-only:** the fit outputs of `/results/near_critical_pole` (slopes
  and coefficients), which have no recorded per-quantity estimator.
- **Gates.** The equation-residual and boundary-residual gates belong to A1
  and A3. They are not used as conductivity uncertainty.

### 8.3 Static validation done for this revision

No verifier, candidate or calculation was run.
- **Committed records.** Every pointer above for hard-wall chiral, GN and DGR
  neutral was resolved mechanically against the committed records under
  `docs/generated/`. All resolve to numeric leaves:
  - hard-wall chiral: 3 levels, 7 table rows;
  - GN: 696 and 522 curve points, 5 comparisons per preset;
  - DGR neutral: 20 curve points, 3 branches of 20.

  One pointer does not resolve: a GN curve entropy leaf does not exist. It is
  disclosed above.
- **Source.** The other five entries were read from the record-building
  source (`to_dict` methods and result assembly) at `5846975`, including each
  estimator's normalization.
- **P0 repeats this** as a committed checker before any numerical step.

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

- **Budget, for item 1 only** (unchanged from revision 2):
  - at most 6 hours of active work;
  - at most 60 cumulative minutes of local execution. This counts fixtures,
    failed attempts, baseline and candidate runs, regression and S3.
  - Full-suite verifier runs are reused only where they demonstrably cover
    an exact Section 8 case.
- **Not used:**
  - paid compute;
  - installations;
  - CI-dispatched scientific runs.

  Ordinary PR CI and the existing PR gate telemetry run as usual, and are
  reported as additional execution.
- **Budget exhausted:** return incomplete, without removing cases or
  extending the budget.
- **Stop and return if:**
  - the P0 checker fails;
  - a fixture fails after three corrections;
  - the S1 selection fails;
  - A1, A2 or a control fails;
  - a post-freeze code correction is needed;
  - a budget is exhausted.
- **Outputs:**
  - one PR containing the frozen plan, the P0 table and checker, the
    implementation and tests, the R0 baseline, S0–S3 evidence (under
    `docs/generated/chebyshev-repair/`) and a report;
  - a handoff covering what changed, per-consumer deltas, gate values by
    build, deviations and resource use.

Nothing is merged without Codex review and owner approval.

## 11. Disposition of Codex's second review (1 October 2026)

1. **Regression table corrected and statically validated** (Section 8).
   - Gubser--Rocha leaves are under `thermodynamics`, with an explicit name
     map to the estimator block.
   - GN presets and DGR `degree_branches` are treated as mappings.
   - GN independent comparisons are keyed by `target_phi_h`.
   - Registered states are matched by stable identifiers (position, label,
     degree, configured values), never by solved `phi_h`.
   - Numeric leaves, estimator mappings and required coverage are listed.
     Missing fields are disclosed, not invented: GN entropy, lower-degree
     spectra, and the missing GMOR and fit estimators.
   - The structural preflight is now stage P0, before S0. The numerical
     baseline (R0) stays before any candidate verifier run.
2. **Operator-agreement metrics separated from analytic exactness**
   (Sections 4.1, 4.2 and 7).
   - The polynomial coefficients are specified, with degree `min(6, N)`.
   - The oracle fixtures use unrounded 50-digit samples and derivatives.
   - The double-precision test accounts for sample rounding.
   - Row sets are defined for `N = 2` and `N = 3`.
   - An undefined required metric is a failure, never dropped.
3. **Estimator normalization and conversion stated per field** (Section 8.2).
   Estimators combine by maximum. The safety factor and the role of
   cross-build differences are explained, and the allowance is labelled a
   maintenance regression allowance (Section 8.1). A1 and all existing gates
   are preserved.
4. **"Irreducible inconsistency" corrected** (Section 2). Rounded nodes
   define a valid interpolation problem, and the node-set difference is kept
   distinct from matrix rounding. The boundaries on paid compute,
   installations and extra scientific CI dispatches are restored (header and
   Section 10).
