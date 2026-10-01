# Chebyshev differentiation-matrix construction repair: report (stopped at S1)

- **Status: STOPPED at S1, a declared stop.** Under the frozen qualification
  rule no candidate qualifies, so the
  [frozen plan](chebyshev-construction-repair-plan.md) (freeze commit
  `0cd24dd`, SHA-256 `7d26e662…`) requires that no production change is made.
  AI-assisted (Claude); revised after Codex's review of `f01da66`
  (Section 7) and its re-review of `d5eb95a` (Section 8); awaiting targeted
  review and an owner decision.
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
  - Many of the compared values are below one machine epsilon. They are
    measured against 50-digit references, so they are real construction
    rounding, not measurement noise. The rule compares the rounding of two
    different constructions and counts any factor of 2 as a regression.
  - **C-S1 (stored-node candidate):** 26 of 1,680 comparisons fail per
    build. Every failing value is below 8 epsilons, and 20 are below one.
  - **C-T family:** the same kind of failures, plus 10–11 at 64 epsilons or
    more. Those come from the difference between the stored nodes and the
    ideal nodes.
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

**Local execution** (ceiling 60 min), reconciled from the existing logs.
The first version of this table omitted the full test suite and the untimed
runs (Section 7, R55-4).

| Run | Wall time | Source |
| --- | ---: | --- |
| P0 static check | `0.15 s` | tool record |
| S0 development subset (degrees 2, 3, 16, 17), B1 | `5 s` | log |
| S0 full, B1, development run 1 | `236 s` | log |
| S0 development subset (2, 3, 16, 17, 64, 256), B1 | `11 s` | log |
| S0 full, B1, final implementations | `241 s` | log |
| S0 full, B3, final implementations | `242 s` | log |
| Build agreement | `1 s` | log |
| Selection | `0.07 s` | tool record |
| Full unit suite (integration validation), B1 | `458 s` | log |
| Short runs that were not timed | `60 s` | conservative allowance |
| Amendment-preparation step | `15 s` | log gives `8 s`; charged conservatively |
| Correction step after the re-review (Section 8) | `30 s` | log gives about `15 s`; charged conservatively |
| **Total charged** | **about `1,299 s` (21.7 min)** | |

- **Untimed runs** covered by the allowance: three tool-test runs, the
  soft-wall verifier, the reproduction of eight schema tests on `main`, and
  two helper checks. Each took a few seconds at most.
- **Remaining:** at most about 38.3 of the 60 minutes. Nothing was reset or
  extended.
- **Not charged:**
  - recreating the two environments (an installation the owner approved,
    not timed);
  - Codex's own review runs.
- **Active work**, reported separately: about 45 minutes up to the S1
  handoff, about 20 more for the amendment-preparation step, and about 25
  more for the correction step after the re-review (its own limit was one
  hour). That is about 1.5 of the 6 hours.
- **Not used:** paid compute, CI-dispatched scientific runs, reserved cases.
- **Provenance.** Each original evidence file records plan SHA-256
  `7d26e662…`, tool SHA-256 `6d0eff7c…` (the tool committed at that time),
  commit `474a6c2` with `src/` unmodified, and the build. The appended
  replays record the tool version that produced them: `ded34a52…`
  (Section 7) and `9e339930…` (Section 8).

## 2. P0: structural preflight

**Original P0** (`p0-preflight.json`) passed for all eight consumers. It
checked less than this report first claimed (Section 7, R55-2). What it did
check:
- the call-site names against the table;
- control routes by a module-local call graph, which is not a cross-module
  proof;
- that each record key occurs as a string somewhere in the module, without
  its parent path;
- only the separately listed pointers, against the three committed records,
  and without cardinality.

**Revalidation** (`p0-revalidation.json`, appended; the original is kept)
passes for all eight and adds:
- strict resolution of every table pointer, counting wildcard elements that
  lack the path;
- the extraction itself, with unique stable keys, matched states and the
  estimator conversions.

Its record sources differ, and the output says which:
- **Committed verifier records:** hard-wall chiral, Gubser--Nellore and DGR
  neutral. Here the conversions are checked against the data. For example,
  the DGR per-position difference between degrees 150 and 120 reproduces the
  recorded `maximum_final_change` exactly (`5.55e-11`).
- **Synthetic records:** the other five. These are hand-built from a manual
  source audit and are not verifier output. They validate the extraction
  code against the audited structure only. The real records are first seen
  at R0, where a mismatch is a stop.

Manual source review, not executable: the five structures and their
normalizations, and whether a control route depends on spectral outputs
through its data.

**Second revalidation** (`p0-revalidation-duplicate-rows.json`, appended;
Section 8, R55-F2). The extraction now rejects a duplicate source row before
the rows are mapped. The replay passes for all eight consumers, with the
same record sources as above.

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

**Why the frozen rule is hard to meet.**
- The row-scaled action error is dominated by rounding in the negative-sum
  diagonal. That is of order one unit roundoff times the row's absolute sum,
  and it depends on summation order.
- These values are real construction rounding. Two correct constructions
  can differ by more than a factor of 2 at that level. With 1,680 comparisons
  per build, some ratios above 2 are therefore expected for a construction
  that is not bit-identical to the current one.
- This is an expectation from the mechanism, not a proof that the rule
  cannot be met.

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

- **A. Adopt a qualification amendment and continue.**
  - The exact proposal is
    [amendment 1](chebyshev-construction-repair-amendment-1.md). It is
    labelled post-observation.
  - It changes only the action-metric rule: a component fails only if it
    exceeds both 2× the current value and the candidate's own first-order
    a-priori rounding bound. The entrywise rule, polynomial exactness and the
    10× requirement are unchanged.
  - It requires a pass on the 84 observed grids and on a fresh confirmation
    set.
  - Whether any candidate would qualify under it is not known. It cannot be
    evaluated from the saved evidence.
  - **Withdrawn:** the blanket `gamma_(N+1)` floor first suggested here. It
    is not a bound for these metrics, and its outcome depends on the
    convention: 0 C-S1 failures with `eps`, 1 with `u = eps/2`.
  - **Unresolved (Section 8, R55-F1).** The corrected C-S1 bound is derived
    and tested, but it grows about linearly with the degree. Whether rule 2
    with that bound is an acceptable regression rule at the larger degrees
    is not established.
  - **Budget:** at most about 38.3 minutes of execution remain, against an
    estimated 36–50 for a continuation. A continuation approval should state
    the budget explicitly.
- **B. Accept the stop.** No repair is made. The optical gate and every
  record stay as they are.
- **C. Decide later.** The evidence and tool are preserved either way.

**Cost.** C-S1 costs about `25 ms` per grid at degree 640, against `4 ms`
now. Several benchmarks build many grids, so their run time would rise. That
would be measured in S2 if the work continues.

## 7. Post-review corrections (1 October 2026)

After Codex's review of `f01da66`, the following was corrected in one
bounded step. The frozen plan, the S1 stop and every original evidence file
are unchanged. Only focused tests, synthetic controls and replay of saved
data were run.

- **R55-1: the selector now rejects inadmissible evidence.**
  - Before applying the rule it requires:
    - one complete, successful S0 output for each of B1 and B3;
    - no duplicate build;
    - the frozen plan's hash, and a single tool version;
    - every required fixture passed;
    - production equal to the legacy construction;
    - the plan's 84 grids and the full metric sets;
    - every metric finite and non-negative.
  - Unreadable or partial inputs are rejected with exit status 2.
  - Build agreement is derived from the matrix hashes in the evidence. The
    build-agreement stage stops if the saved matrices do not match the grids
    whose hashes differ. Equality is never inferred from an empty folder.
  - Regression tests cover Codex's three reproductions and the other cases.
  - **Replay.** The corrected selector admits the committed evidence and
    reproduces the stop with the same counts
    (`s1-selection-revalidated.json`, `build-agreement-revalidated.json`).
- **R55-2: P0 coverage corrected** (Section 2). The original artifact is
  kept, and `p0-revalidation.json` is appended. Tests cover a missing row
  under a wildcard and a wrong estimator pointer, both of which the original
  check missed.
- **R55-3: interpretation corrected and an amendment prepared.**
  - Values below machine epsilon are described as real construction
    rounding, not as noise.
  - The blanket floor is withdrawn.
  - [Amendment 1](chebyshev-construction-repair-amendment-1.md) gives the
    exact proposed rule, its roundoff convention and operation counts, and
    its adverse controls.
  - The proposed rule is implemented as `qualification_v2`. No stage uses
    it.
- **R55-4: execution time reconciled** (Section 1). The earlier statement
  that about 47 minutes remained was not supported; the reconciled figure is
  at most about 38.8.
- **Also recorded.** The 97× and 135× figures are operator-action
  diagnostics on saved vectors. They are not achieved improvements in a
  physical observable, in the optical residual, or in production.

## 8. Corrections after the re-review (1 October 2026)

Codex re-reviewed `d5eb95a` and raised three findings. They were addressed
in one correction-only step, limited to one hour of work and five minutes of
execution within the existing ceilings.
- **Unchanged:** the frozen plan, the S1 stop, every earlier evidence file,
  the candidate implementations, production code, and every gate and
  threshold.
- **Run:** focused tests, synthetic checks and replay of saved data only.
- **Not run:** S0, R0, S2 or S3. No grid or vector of the confirmation set
  was used. Amendment 1 is not adopted.

- **R55-F1: the proposed C-S1 rounding bound was wrong at first order.**
  - **The error.** The entry model counted the rounding of the operations on
    the barycentric weight products. It omitted the rounding already inside
    the node differences that are multiplied.
  - **The counterexample.** C-S1, degree 30 on `[1e-3, 1]`, zero-based entry
    `(7, 8)`: relative error `14.17u`, against the claimed `5u`. For the
    coordinate vector `e_8` the action error was `2.83` times the claimed
    bound.
  - **The correction.** The uniform constant is withdrawn and not replaced
    by a larger one. The entry bound is now derived from the implemented
    operations: `4u` for the four rounded operations, plus the exactly
    computed subtraction errors that enter the two weight products and the
    final division
    ([amendment 1](chebyshev-construction-repair-amendment-1.md),
    Section 3).
  - **Tests.**
    - The counterexample is a regression test. It is now inside the bound.
    - The accounting is checked against exact rational arithmetic for all
      930 off-diagonal entries at that grid. After the exact input term is
      subtracted, the remainder is at most `2.45u`, against the derived
      `4u`.
    - Every entry of both matrices is inside the bound at that grid, by a
      regression test. On it and nine other small grids the largest ratio
      is `0.72` for D1 and `0.33` for D2.
    - The adverse controls of the amendment are still rejected.
  - **Unresolved derivation issue.** The corrected bound is valid where
    tested, but it grows about linearly with the degree. Its largest entry
    value is about `27u` at degree 30 and about `850u` (`9.4e-14` relative)
    at degree 1000. Whether rule 2 with a bound of that size is an
    acceptable regression rule at the larger degrees is not established.
    Whether C-S1's actual errors grow in the same way is not measured; that
    needs a pass over the S0 grids. Nothing was tuned
    (amendment Section 3.1).
  - **Also unverified.** The C-T model still assumes a library sine accurate
    to one ulp, and it is not checked against exact arithmetic. It does not
    change an outcome here: C-T2 and C-T3 fail the unchanged entrywise rule.
- **R55-F2: duplicate source rows were collapsed before the uniqueness
  checks.**
  - **The error.** Four extractors turned some source rows into mappings
    first, so a repeated row could silently overwrite the earlier one.
  - **The correction.** Rows are now mapped by one helper that rejects any
    repeated key before mapping. It is used at every such site: hard-wall
    vector modes (both routes), hard-wall chiral levels and table,
    Gubser--Rocha thermodynamic and refinement cases, and the DGR
    finite-density refinement states, changes and controls.
  - **Tests.** An exact duplicate and a conflicting duplicate are rejected
    at each of the nine sites. Codex's two reproductions are regression
    tests.
  - **Replay.** `p0-revalidation-duplicate-rows.json` (appended) passes for
    all eight consumers.
- **R55-F3: saved matrices were not bound to the S0 hashes.**
  - **The error.** The build-agreement stage checked the file names only. A
    stale or changed file with the right name could supply a statistic.
  - **The correction.** The stage now stops unless:
    - the other build is one of the two in the evidence;
    - each file holds `nodes`, `D1` and `D2` as finite double arrays of the
      expected shapes;
    - the bytes of each saved matrix hash to the other build's S0 entry;
    - each local reconstruction hashes to this build's S0 entry.

    The output records that verification, and the selector rejects a
    build-agreement record without it.
  - **Tests.** A correctly named file with other bytes, Codex's
    reproduction, a local matrix that is not the recorded one, a missing
    array, a wrong type, a wrong shape and a non-finite value each stop the
    stage.
  - **Replay.** All 56 saved B3 matrices match the B3 hashes, and all 56 B1
    reconstructions match the B1 hashes
    (`build-agreement-hash-bound.json`). The selector reproduces the stop
    with the same counts (`s1-selection-hash-bound.json`).
  - **Superseded, kept.** `build-agreement-revalidated.json` has no
    verification record, so the corrected selector now rejects it. It stays
    in the folder as the record of the earlier step.
- **Wording.** The amendment no longer says that A2 answers whether rounding
  matters to a physical observable. A2 is a maintenance regression
  allowance, not a complete physical uncertainty bound.
- **Execution.** About `15 s` by the log; `30 s` charged (Section 1).
