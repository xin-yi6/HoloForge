# Chebyshev differentiation-matrix construction repair: report (stopped at S1)

- **Status: STOPPED at S1, a declared stop.** Under the frozen qualification
  rule no candidate qualifies, so the
  [frozen plan](chebyshev-construction-repair-plan.md) (freeze commit
  `0cd24dd`, SHA-256 `7d26e662…`) requires that no production change is made.
  AI-assisted (Claude); awaiting Codex review and an owner decision.
- **Completed:** P0, and S0 on B1 and B3.
- **Not run (incomplete):**
  - the implementation freeze;
  - R0 (numerical baseline);
  - S2 (cross-benchmark regression);
  - S3 (post-selection revalidation).
- **Unchanged:** `chebyshev_lobatto_grid`, every gate, threshold and record,
  the historical evidence and the BTZ pin. No reserved case was used.
- **Baseline commit:** `main` at `5846975`.
- **Scientific boundary:** a statement about the numerics of one shared
  routine. It is not a physical result.

## Answer

- **The repair works on the measure it was designed for.**
  - On the preserved O-C stored solutions, the construction error at UV-end
    collocation rows falls by **135×** (C-T2, C-T3) and **97×** (C-S1).
  - The explicit-D2 candidates are bit-identical between Accelerate and
    OpenBLAS at every tested grid.
  - Polynomial exactness holds with a margin of more than three orders of
    magnitude.
- **No candidate passes the frozen qualification rule.**
  - The rule requires every operator-agreement component to be within 2× of
    the current construction's value. It has no rounding floor.
  - Many of the compared values are below one machine epsilon. There, the
    current construction's value is itself rounding noise, and a ratio of
    two such values says nothing.
  - **C-S1 (stored-node candidate):** 26 of 1,680 comparisons fail per
    build. Every failing value is below 8 epsilons, and 20 are below one.
  - **C-T family:** the same kind of failures, plus 10–11 above 64 epsilons
    that are real. They come from the difference between the stored nodes
    and the ideal nodes.
- **The stop is correct under the plan.** Adding a floor after seeing the
  results would weaken a frozen criterion, so it was not done. Whether to
  amend the rule is an owner decision (Section 6).

## 1. Execution and resource use

**Builds.** Both were re-established for this milestone; the earlier
temporary environments no longer existed.
- **B1:** the owner's existing `holoforge` conda environment — NumPy 2.4.6
  and SciPy 1.17.1 `macosx_14_0` wheels (Accelerate), Python 3.11.15.
- **B3:** a temporary virtual environment with the `macosx_11_0` /
  `macosx_12_0` wheels of the same versions (OpenBLAS), Python 3.11.15. The
  owner approved this installation on 1 October 2026.

**Local diagnostic execution** (ceiling 60 min):

| Run | Wall time |
| --- | ---: |
| P0 static check; tool tests; selection | about `2 s` |
| S0 development subset (degrees 2, 3, 16, 17), B1 | `5 s` |
| S0 full, B1, development run 1 | `236 s` |
| S0 development subset (2, 3, 16, 17, 64, 256), B1 | `11 s` |
| S0 full, B1, final implementations | `241 s` |
| S0 full, B3, final implementations | `242 s` |
| Build agreement | `1 s` |
| **Total** | **about `738 s` (12.3 min)** |

- **Active work:** about 35 minutes of the 6-hour ceiling when S1 stopped.
- **Not used:** paid compute, CI-dispatched scientific runs, reserved cases.
- **Provenance.** Each evidence file records plan SHA-256 `7d26e662…`, tool
  SHA-256 `6d0eff7c…` (the committed tool), commit `474a6c2` with `src/`
  unmodified, and the build.

## 2. P0: structural preflight

Passed for all eight consumers (`p0-preflight.json`):
- the call sites equal the table's;
- no control route reaches the routine through the call graph;
- every record key exists in the source;
- every pointer resolves against the committed records.

## 3. S0: fixtures and measurements

**Fixtures** (identical on both builds):

| Fixture | Result | Limit |
| --- | --- | --- |
| F1 oracle arithmetic | `2.9e-49` | `1e-45` |
| F2 recurrence versus exact product | `2.8e-49` | `1e-40` |
| F3 oracle polynomial exactness | `2.3e-40` | `1e-30` |
| F4 artifact hashes and continuity with O-C | `8.2e-14` | `1e-6` |
| F5 candidate API at all 84 grids | pass | — |

No fixture needed a correction.

**Metric (c), the selection metric.** This is the D-dependent operator action
on the eight preserved O-C stored solutions, at rows 1–3, in the worst case
over the artifacts. It is identical on both builds for the explicit-D2
candidates.

| Construction | Scaled | Absolute | Improvement |
| --- | ---: | ---: | ---: |
| current | `4.25e-15` | `2.81e-4` | 1× |
| C-T1 (`D @ D`) | `8.78e-16` | `1.45e-5` | 4.8× |
| **C-T2** | `3.15e-17` | `1.09e-6` | **135×** |
| **C-T3** | `3.15e-17` | `1.09e-6` | **135×** |
| **C-S1** | `4.38e-17` | `1.18e-6` | **97×** |

This is an operator-action diagnostic on old sample vectors, not a new
physical solution.

**Polynomial exactness** (limit `1e-10`), worst over all 84 grids:
- C-S1: `1.1e-15`;
- C-T family: at most `1.7e-14`;
- current: `2.3e-14`.

**Build agreement, metric (d):**

| Construction | Grids differing between B1 and B3 | Largest difference | Time at degree 640 |
| --- | ---: | ---: | ---: |
| current | 28 of 84 | `5.5e-15` | `4.0 ms` |
| C-T1 | 28 of 84 | `5.5e-15` | `12.7 ms` |
| C-T2 | 0 | — | `15.8 ms` |
| C-T3 | 0 | — | `9.0 ms` |
| C-S1 | 0 | — | `24.9 ms` |

On B3, 364 of 420 construction-grid entries were bit-identical to B1 and
inherit its metrics. The other 56 were measured again.

**Entrywise agreement at degree 640 on `[1e-5, 1]`** (metric (a), D1 / D2):

| Construction | Against the stored-node reference | Against the ideal-node reference |
| --- | --- | --- |
| current | `1.4e-11` / `8.8e-12` | `2.3e-12` / `4.0e-12` |
| C-T2 | `1.7e-11` / `1.1e-11` | `5.4e-16` / `5.8e-16` |
| C-S1 | `5.0e-14` / `7.8e-14` | `1.7e-11` / `1.1e-11` |

Each candidate family is accurate for its own target. The roughly `1e-11`
gap between the two references is the node-set difference. It comes from the
stored nodes near `u = 1`, which carry about `1e-16` of rounding against a
spacing of about `6e-6`.

## 4. S1: the frozen rule applied

**Qualification** (identical conclusions on B1 and B3):

| Candidate | Failing comparisons (B1 / B3, of 1,680) | Worst ratio | Failures by candidate value |
| --- | --- | ---: | --- |
| C-T1 | 126 / 125 | 10.6 | 33 below 1 eps; 62 in 1–4; 8 in 4–8; 13 in 8–64; **10 at 64 or more** |
| C-T2 | 112 / 111 | 9.4 | 25 below 1 eps; 56 in 1–4; 7 in 4–8; 14 in 8–64; **10 at 64 or more** |
| C-T3 | 112 / 111 | 9.4 | as C-T2 |
| C-S1 | 26 / 26 | 5.3 | **20 below 1 eps; 3 in 1–4; 3 in 4–8; none above** |

The failure-size counts are from B1.

**Outcome:** `no candidate qualifies`. The selection therefore fails, and the
plan's stop applies. The 10× improvement requirement is met by three
candidates but is not reached in the rule's order.

**What the failures are:**
- **C-S1.**
  - 15 of the 26 are first-derivative action errors on the UV rows, where the
    current construction's own value is `8e-18`–`2e-17`.
  - The largest failing value is `1.55e-15` (7 epsilons). It is the
    first-derivative action over all rows at degree 1024, against `5.7e-16`
    for the current construction.
- **C-T family.**
  - 7 failures are entrywise first-derivative errors against the stored-node
    reference on `[-1, 1]`, up to `3.6e-11` against `1.7e-11`.
  - The others above 8 epsilons are second-derivative actions, up to `2.0e-14`
    against `8.9e-15`.
  - These are real and small. They arise because C-T targets the ideal
    nodes, not the stored ones.

**Why a 2× rule without a floor cannot be met.**
- The row-scaled action error is dominated by rounding in the negative-sum
  diagonal. That is of order one epsilon times the row's absolute sum, and it
  depends on summation order.
- Near the floor, the ratio of two constructions' values is therefore
  noise. With 1,680 comparisons per build, some ratios above 2 are expected
  for any construction that is not bit-identical to the current one.

## 5. Development history and deviations

**S0 development** (allowed by the plan; no candidate was added, and no
threshold or rule was changed):
1. **First subset run.** Trigonometric candidates missed the 2× rule at
   degree 2, because the rounded midpoint node made the stored nodes
   asymmetric. Fix: the midpoint is set to its exact value `lower + width/2`,
   for every candidate.
2. **Full run 1** (plain summation and plain weight products).
   - Failures: C-T1 222, C-T2 203, C-T3 224 and C-S1 125 of 1,680.
   - Metric (c) improvements: 5.4×, 32.5×, 32.5× and 27.4×.
   - Its summary is committed (`s0-development-run1-summary.json`); its full
     per-grid output is not.
3. **Fixes after run 1**, both within the declared definitions:
   - negative-sum diagonals of D1 and D2 are taken in compensated
     (double-double) arithmetic;
   - C-S1's weight products are accumulated in double-double arithmetic,
     with separate binary exponents.
4. **Full run 2** is the evidence reported above.

**Deviations from the frozen plan:**
1. **Builds re-established** (Section 1), with Python 3.11.15 where earlier
   evidence used 3.11.16.
2. **Evaluation route for polynomial exactness.** The plan says the double
   matrix is applied to the rounded samples exactly. It is evaluated through
   the exact identity `D p̂ - P' = -(R - D) p̂ + (R p̂ - P')`, with `R p̂`
   formed in 50 digits. The value is the same; the route avoids a second
   full-precision matrix application.
3. **Metric (c) coefficients.** The plan specifies exact coefficients. The
   artifact's stored double `first_coefficient` is used, which differs by
   rounding only. F4's `8.2e-14` agreement with the O-C evidence confirms the
   effect is negligible.
4. **Selection number.** Where the plan left it open, the scaled ratio
   (worst over rows 1–3 and artifacts) is used, and the absolute value is
   reported alongside. This choice was made before any result.
5. **Complementary sines.** C-T1 and C-T2 use the complementary integer
   index `2N - (i+j)` for the sum-angle sine, so that no near-pi sine is
   evaluated. C-T3 differs from C-T2 by the half-grid reflection only.
6. **B3 metrics.** Entries whose nodes and matrices are bit-identical to
   B1's inherit B1's metrics instead of being recomputed.
7. **Evidence format.** The S0 outputs are compact JSON (about 0.8 MB each).
8. **Incomplete stages.** The implementation freeze, R0, S2 and S3 were not
   run, because of the S1 stop.

## 6. Decisions for the owner (with Codex)

Nothing below is decided or done.

- **A. Amend the qualification rule and continue.**
  - The amendment would have to be labelled as made after the S0 results.
  - A principled form: a component counts as a regression only if it exceeds
    both 2× the current value and the standard a-priori rounding constant for
    one row, `gamma_(N+1) = (N+1) eps / (1 - (N+1) eps)`. This is the
    constant already used for the O-C rounding bounds.
  - On the saved evidence, C-S1 would then qualify on both builds: none of
    its 26 failing values exceeds `gamma`. Its largest is `1.55e-15` at
    degree 1024, where `gamma` is `2.3e-13`.
  - Each C-T candidate would still fail 7 comparisons, on entrywise errors
    of up to `3.6e-11`.
  - The remaining budget (about 47 minutes of execution) would have to cover
    R0, S2 and S3, which is tight.
- **B. Accept the stop.** No repair is made. The optical gate and every
  record stay as they are.
- **C. Decide later.** The evidence and tool are preserved either way.

**Cost.** C-S1 costs about `25 ms` per grid at degree 640, against `4 ms`
now. Several benchmarks build many grids, so their run time would rise. That
would be measured in S2 if the work continues.
