# Optical single-node diagnosis (O-B): report

- **Status:** completed under the [frozen plan](optical-ob-diagnosis-plan.md)
  (commit `18d02f5`, SHA-256 `a158b07a…d7118`). AI-assisted (Claude); revised
  after Codex review (Section 6). **Diagnosis only.** No production solver,
  gate, threshold, record or verdict changed. On Accelerate the optical
  verifier's FAIL remains the recorded result.
- **Evidence:** [`B1-optical-ob.json`](../generated/optical-ob/B1-optical-ob.json)
  (Accelerate) and [`B3-optical-ob.json`](../generated/optical-ob/B3-optical-ob.json)
  (OpenBLAS wheels), from `python tools/gate_calibration.py optical-ob`.
  - Both runs record plan commit `18d02f5` with `src/` unmodified, the plan
    hash above, and tool SHA-256 `8ee96206…34f78`.
  - That tool version is commit `a651a51`, byte-identical to the file that
    ran. Later tool corrections (Section 6) postdate the evidence, which is
    preserved unchanged.
- **Scientific boundary:** a statement about the numerics of one benchmark
  check. It is not a physical result. O-B does not reassess the accuracy of
  the conductivity.

## Answer

In every sampled case on both builds (16 case-build pairs), the result falls
in category **(b), a genuine polynomial defect**, under the plan's
prospective rules:
- The exact interpolating polynomial through the stored solution does not
  satisfy the equation at the spike node. A 50-digit evaluation of it gives a
  raw residual of about `1e-4`.
- Double-precision evaluation changes that by only 1–5%.
- The value is therefore **not an evaluation artifact**. More precise
  evaluation of the residual would not change the verdict.

Two further observations, from the same evidence:
- **In the sampled frequencies, the frequency dependence is a denominator
  effect.** The raw defect is nearly the same at every sampled frequency,
  while the normalizing scale varies more than 30-fold.
- **The defect is already present at collocation nodes near the UV end,**
  where an exactly solved discrete system would have none (with the caveat
  in Section 4, item 1).

Its origin within the discrete system is not established (Section 4).

## 1. Execution

- **Cases:** `omega/T = 50, 58, 59, 60, 61, 62, 70` at degree 640, and 60 at
  degree 512, on the conditioned Figure 2 background. The reserved cases
  `omega/T = 55, 65, 75` and degree 576 were not run.
- **Builds:** B1 and B3, as defined in the
  [Batch 2a plan](gate-calibration-2026-09-plan.md). Local wall time was
  `9.9 s` on B1 and `93.8 s` on B3, against a `20 min` budget. No CI dispatch.
- **Identity checks:**
  - **Reconstruction.** On every case and build, the reconstructed A-form
    maximum equals production's `equation_residual` exactly. It also
    reproduces the Batch 2a values.
  - **Fixture.** The fixture passed before any production case was examined:
    - agreement with the double interpolant at a well-separated point:
      `1.2e-14`, against a limit of `1e-10`;
    - reproduction of a known degree-6 polynomial on degree-640 nodes,
      off-node near the UV end, at an exact node, and mid-element:
      `8.4e-40`, against `1e-30`.
  - **Correction.** The fixture needed one correction, in its own test
    polynomial rather than the evaluator: Decimal leaves `0 ** 0` undefined.
- **Precision cross-check.** Repeating the spike evaluation at 70 digits
  changes `p`, `p'`, `p''` and `R_a` by at most `2.5e-34` relative.
- **Stop conditions:** none reached.

### Implementation choices and deviations

Choices made before any plan case was run:
- **Neighbours.** The spike's four neighbours are check indices 1, 2, 4 and
  5. Indices 1 and 2 lie in the three excluded endpoint nodes and are
  reported for diagnosis only.
- **"Accounts for".** This rule (Section 4 of the plan) is taken to mean
  that the residual change implied by the derivative differences alone is
  within a factor of 2 of the double-minus-50-digit residual difference.
- **Identity defect.** The plan's relative identity defect
  `|R_A - (1-u)^s R_a| / |R_A|` is large wherever `|R_A|` itself is at
  rounding level. The defect under the common A-form denominator is
  therefore also reported.
- **Coverage.** B3 ran all four measurements (the plan required 1 and 2).
  The 70-digit cross-check was added.
- **Smoke test.** A normal-state case (`omega/T = 40`, degree 64) served as
  a development smoke test. It is not a plan case, and its values are not
  used here.

**Deviation: per-node arrays were not saved.**
- Measurement 1 of the plan asks for the raw numerators to be recorded at
  every check node. They were computed at every node, but the evidence saves
  only:
  - their maxima and argmaxima;
  - the spike's full values;
  - the first 12 checked nodes (under measurement 4).
- The all-node arrays are not in the evidence. Recovering them requires a
  rerun, which this revision does not perform.

## 2. Measurements

Terminology:
- The spike is check index 3 in every case: the first checked node at the
  UV end. It is `u = 2.355e-5` at degree 640 and `u = 3.118e-5` at degree 512.
- `R_A` is the production A-form numerator, and `R_a` the regular-factor
  numerator.
- "50-digit" means a 50-digit evaluation of the exact interpolating
  polynomial through the stored double nodes and values. Its coefficient
  inputs are the same doubles, converted exactly. The nodes and coordinates
  follow the production check's convention (Section 4, item 1).

| Case (`omega/T`) | Raw `\|R_A\|`, B1 / B3 | A-form scale, B1 | Production normalized, B1 / B3 | 50-digit `\|R_a\|`, B1 / B3 | 50-digit / double, B1 / B3 |
| --- | --- | ---: | --- | --- | --- |
| 50 | `1.010e-4` / `9.91e-5` | `116` | `8.73e-7` / `8.57e-7` | `1.038e-4` / `1.033e-4` | `1.029` / `1.042` |
| 58 | `9.90e-5` / `9.63e-5` | `18.2` | `5.45e-6` / `5.30e-6` | `1.021e-4` / `1.006e-4` | `1.031` / `1.045` |
| **59** | `9.98e-5` / `1.033e-4` | `4.96` | **`2.01e-5` / `2.08e-5`** | `1.019e-4` / `1.039e-4` | `1.020` / `1.006` |
| **60** | `1.048e-4` / `1.024e-4` | `10.5` | **`1.001e-5`** / `9.79e-6` | `1.059e-4` / `1.034e-4` | `1.011` / `1.010` |
| 61 | `1.023e-4` / `9.24e-5` | `24.1` | `4.24e-6` / `3.83e-6` | `1.034e-4` / `9.54e-5` | `1.011` / `1.033` |
| 62 | `1.050e-4` / `9.76e-5` | `38.0` | `2.76e-6` / `2.57e-6` | `1.074e-4` / `1.008e-4` | `1.024` / `1.033` |
| 70 | `1.015e-4` / `9.77e-5` | `157` | `6.46e-7` / `6.22e-7` | `1.053e-4` / `1.025e-4` | `1.037` / `1.049` |
| 60, degree 512 | `5.96e-5` / `5.91e-5` | `289` | `2.06e-7` / `2.05e-7` | `6.21e-5` / `6.11e-5` | `1.041` / `1.034` |

**Measurement 1: raw numerators and a common normalization.**
- At the spike, `|R_A|` and `|R_a|` agree to within `1.4e-8` relative, and
  under the common denominator they agree at every node to `1.3e-13`. Both
  forms' common-denominator maxima lie at check index 3 and agree to
  `3.5e-10` relative.
- The regular form's own denominator at the spike is `6.9e3`–`9.5e3`. Its
  first two terms, about `3.4e3`–`4.7e3` each, nearly cancel, whereas the
  A-form scale is `4.96`–`289`. This fully explains the smaller "normalized
  regular form" values in the Batch 2a report. That report's open question
  is closed: the two forms describe the same defect.

**Measurement 2: the interpolating polynomial at the spike.**
- The 50-digit residual is 0.6–4.9% larger than the double one.
- The residual change implied by the derivative differences equals the
  double-minus-50-digit difference to six digits (ratio `1.000000`). The
  whole evaluation error is therefore in the interpolant's derivatives,
  chiefly `a''`, whose relative error is `1.5e-10`–`1.2e-9` at a magnitude of
  `3.4e3`–`4.7e3`. Coefficient rounding is negligible.

50-digit `|R_a|` at the neighbours (ranges over both builds and the seven
degree-640 frequencies):

| Check index | Position | 50-digit `\|R_a\|` |
| --- | --- | --- |
| 1 (excluded) | between collocation nodes 0 and 1 | `3.5e-4`–`4.6e-4` |
| 2 (excluded) | on collocation node 1 | `2.5e-4`–`3.0e-4` |
| **3 (spike)** | between collocation nodes 1 and 2 | `9.5e-5`–`1.07e-4` |
| 4 | on collocation node 2 | `2.1e-5`–`2.7e-5` |
| 5 | between collocation nodes 2 and 3 | `4.1e-5`–`4.6e-5` |

At degree 512 the values on collocation nodes 1 and 2 are `5.8e-5`–`5.9e-5`
and `2.3e-5`–`2.5e-5`.

**Measurement 3: input sensitivity versus evaluation error.** Both are
small compared with the defect:
- **Input sensitivity.** Eight random relative `eps` perturbations of the
  stored values move the spike numerator by `1.3e-6`–`1.1e-5`. On the
  normalized maximum they reproduce the Batch 2a figures, for example
  `2.8e-7` at ω/T = 60 on B1.
- **Evaluation error.** At fixed inputs it is `6.1e-7`–`4.8e-6`.

**Measurement 4: local structure** over the first 12 checked nodes (check
indices 3–14):
- **Alternation.** Checked nodes that coincide with collocation nodes have
  raw `|R_A|` of `3.7e-7`–`3.3e-5` at degree 640, the largest on collocation
  node 2 in every case. Nodes between collocation nodes, at 0.52–0.63 of the
  local spacing, have `1.3e-5`–`1.0e-4`, the largest at the spike in every
  case.
- **Normalized values.** These fall quickly inward because the scale grows.
  At ω/T = 60 they are `1.0e-5`, `5.8e-8` and `3.4e-8` at check indices 3–5,
  and at most `5e-9` beyond.

## 3. Findings

- **Ruled out: evaluation artifact, category (a).** The 50-digit residual is
  never smaller than the double one by more than a few percent, let alone
  10-fold.
- **Established by the prospective rule: polynomial defect, category (b).**
  This holds for all 16 sampled case-build pairs.
- **In the sampled cases, the frequency dependence is a denominator effect.**
  - The raw defect at the spike is `9.2e-5`–`1.05e-4` (50-digit:
    `9.5e-5`–`1.07e-4`) at the seven sampled frequencies from ω/T = 50 to 70,
    on both builds.
  - The production scale varies from `4.96` to `157`, so the normalized value
    varies about 30-fold.
  - Among the sampled frequencies, the scale is smallest at ω/T = 59. From
    the saved Batch 2a terms, the near-UV potential
    `omega^2/F^2 - 2 psi^2/(u^2 F)` at the spike changes sign between
    ω/T = 59 and 60. There the two cancelling terms, `|A''|` and the
    potential term, are smallest: about `2.0` at 59 and `4.7` at 60. This is
    inferred from the saved term magnitudes and `omega^2`; it was not
    measured separately.
  - The unused frequency ω/T = 59 therefore fails because its local scale is
    the smallest of the sampled set, not because its defect is the largest.
    Frequencies between the sampled ones were not examined.
- **Input sensitivity (c): small within the tested perturbations.**
  - The eight random `eps` perturbations and the B1-versus-B3 difference each
    change the defect by at most about 10%, and most of the defect is common
    to both builds.
  - This is not a worst-case bound. It does not test the backward error of
    the linear solve, which could perturb the stored values by much more
    than `eps`.

## 4. What the evidence suggests but does not establish

1. **The defect belongs to the discrete system near the UV end.**
   - Suppose the collocation system were solved exactly with exact
     differentiation matrices. Its interpolating polynomial would satisfy
     the equation exactly at every interior collocation node.
   - The 50-digit residuals on collocation nodes 1 and 2 (`2.5e-4`–`3.0e-4`
     and `2.1e-5`–`2.7e-5`) therefore reflect how the discrete system was
     built and solved in double precision.
   - **Caveat on conventions.** O-B follows the production check's
     convention: local nodes `fl((u_j - lower)/width)` and a width-scaled
     local derivative. The collocation itself uses the physical nodes `u_j`
     and derivatives in `u`. The two polynomials differ only through
     node-position rounding. That difference is expected to be negligible
     here but was not measured; O-C would use one consistent convention.
   - The spike lies between these two nodes, and its value lies between
     theirs. This points to a UV-end boundary layer of defect in the stored
     solution, mostly inside the three excluded check nodes. The first
     included node catches its tail.
2. **At ω/T = 60 the defect is larger at degree 640 than at 512:**
   - spike `1.05e-4` against `6.0e-5`;
   - collocation node 1: `2.9e-4` against `5.9e-5`.

   If both degrees were in the convergent regime, a truncation-dominated
   defect would be expected to shrink with degree, and growth would point to
   rounding amplified by the degree-N differentiation operators near the
   endpoint. Two degrees at different node positions do not establish that
   regime, so under-resolution is not ruled out and no scaling law is
   claimed.
3. **Candidate mechanisms not distinguished by O-B:**
   - rounding in the double-precision differentiation matrices;
   - rounding in operator assembly and row equilibration;
   - the backward error of the linear solve;
   - under-resolution.

   The largely build-independent value favours a deterministic contribution
   but does not decide among them.

   The background scalar profile is a `solve_bvp` cubic spline, which is only
   C¹. It enters the potential through `2 psi^2/(u^2 F)`, about `200` at the
   spike (inferred from the saved terms and `omega^2`). It cannot produce
   residuals *on* collocation nodes, where the same values are collocated,
   but it could contribute between them.

O-B does not reassess the conductivity. For context only, the existing
records report a resolution change of about `1.2e-12` and a
spectral-versus-Riccati difference of `1.46e-6` against `5e-4`. Neither was
re-examined here.

## 5. Consequences and next decision (for owner and Codex review)

- **Retire as remedies:** changing only the residual evaluation (for
  example extended precision), and reading the regular-form normalization
  as evidence of a smaller defect.
- **Not supported:**
  - Widening the `1e-5` threshold. In the sampled cases the normalized value
    is governed by the local scale at one node. A fixed threshold would
    therefore pass or fail according to how close the frequencies in use
    come to the potential's sign change, not according to the defect.
  - Excluding more nodes is not supported by this evidence alone.
- **Candidates for a separate, prospectively calibrated proposal:**
  - **Separate the contributions.** A bounded follow-up diagnosis (O-C)
    would separate operator construction, assembly and equilibration, and
    the solve, using consistent conventions and complex residual
    differences. This bears on whether the principled response is a solver
    improvement, a construction repair or an independently justified gate
    redesign. It can therefore change the decision, which is why it is
    recommended before any gate change.
  - **Revise the normalization.** A gate normalization that does not
    collapse where the local potential changes sign, with its own adverse
    controls.

Nothing here authorizes a gate, threshold, solver or record change.

## 6. Post-review corrections (30 September 2026)

After Codex's review of `a651a51`, the tool was corrected. The evidence and
the frozen plan are unchanged.
- **Non-finite guard.** The diagnostic now treats a complex value with a
  non-finite real or imaginary part as a non-finite diagnostic number, as it
  already did for real values. Such a result gives `diagnostic-error` and
  exit status 2.
- **Strict JSON.** Output is strict JSON: non-finite parts are written as
  strings, including NumPy scalars and arrays.
- **Interpretation rule.**
  - It returns `zero-residual`, not a defect, when both residuals are
    exactly zero.
  - It rejects non-finite, negative or non-real magnitudes. The case record
    then stops with a diagnostic error.
- **Scope of the gap.** This was a gap in a helper that predates O-B. The
  saved O-B evidence contains no non-finite values.
- **Classifications preserved.** A regression test reapplies the corrected
  rule to the saved spike values and recovers the saved classification in
  all 16 cases.
- **Reproduction check (executor-reported, output not saved).** On B1, the
  corrected tool's `optical-ob` result section reproduces the saved B1
  evidence exactly, apart from the added description of the zero-residual
  rule.
