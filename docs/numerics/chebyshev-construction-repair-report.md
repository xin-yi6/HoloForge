# Chebyshev differentiation-matrix construction repair: report (stopped at S2)

- **Status: STOPPED at S2, a declared stop.** AI-assisted (Claude); awaiting
  review and an owner decision. Nothing is merged.
  - **Under the frozen plan** ([plan](chebyshev-construction-repair-plan.md),
    freeze commit `0cd24dd`, SHA-256 `7d26e662…`), S1 stopped: no candidate
    qualifies. That result stands.
  - **Under post-observation
    [amendment 1](chebyshev-construction-repair-amendment-1.md)**, which the
    owner approved for one bounded continuation, the stored-node candidate
    C-S1 qualified and was selected. It was frozen into
    `chebyshev_lobatto_grid` on this unmerged branch (`bea799b`).
  - **S2, the cross-benchmark regression, then stopped** on the plan's own
    criteria: one gate that passed at baseline fails (A1), and 13 table
    leaves exceed their allowances (A2). Section 9 has the details.
- **Completed:** P0; S0 and S1 on B1 and B3; the continuation stages C0, C1
  and C2; the implementation freeze; R0; the S2 runs and comparison.
- **Not run:** S3 (post-selection revalidation), and the full unit suite on
  the local builds. Both come after the stop.
- **State of this branch.** It contains the new construction in production
  code. `main` is unchanged. **The branch must not be merged as it is.**
- **Unchanged:** every gate, threshold, tolerance and model card, the
  historical evidence, and the BTZ pin. No reserved optical case was used.
- **Baseline commit:** `main` at `5846975`.
- **Scientific boundary:** a statement about the numerics of one shared
  routine. It is not a physical result.

## Answer

- **The new construction does what it was designed for.**
  - On the preserved O-C stored solutions, the construction error at UV-end
    collocation rows falls by **97×** (C-S1).
  - With it in production, the two gates that fail today on the Accelerate
    build both pass: the Gubser--Nellore collocation residual
    (`1.72e-9` to `9.3e-10`, limit `1e-9`) and the optical numerical gate
    ratio (`1.001` to `0.42`, limit 1).
  - Every control route is bit for bit unchanged, on both builds.
- **It does not pass the frozen regression criteria, so the work stops.**
  - **A1.** The Gubser--Rocha `spectral-refinement` gate passes at baseline
    and fails afterwards on the Accelerate build, and in Linux CI. It still
    passes on the OpenBLAS build.
  - **A2.** 13 of 4,132 leaf comparisons exceed their allowance: 12 in DGR
    neutral and 1 in the soft-wall spectrum. The changes are between `2e-14`
    and `5e-12` relative, up to 4.4 times the allowance.
  - Under the plan each is a stop to be reported. It is not, by itself, a
    physics failure, and no criterion was changed.
- **How C-S1 came to be selected.**
  - Under the frozen rule no candidate qualifies (Section 4). That is
    unchanged.
  - Under amendment 1, written after the results were seen, C-S1 qualifies
    on the 84 observed grids and on 20 fresh ones, on both builds. Its label
    is "qualified under post-observation amendment 1".
- **What is decided next is the owner's** (Section 9.8).

**Reading order.** Sections 1–8 record the work up to the S1 stop and the
two review rounds, as written at the time. Section 9 records the
continuation and supersedes Section 6.

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
| **Total charged before the continuation** | **about `1,299 s` (21.7 min)** | |

The continuation's execution is in Section 9.7. The cumulative total is
about 60.7 of the 90 minutes the owner then allowed.

- **Untimed runs** covered by the allowance: three tool-test runs, the
  soft-wall verifier, the reproduction of eight schema tests on `main`, and
  two helper checks. Each took a few seconds at most.
- **Remaining at that point:** at most about 38.3 of the 60 minutes. Nothing was reset or
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

## 6. Decisions for the owner (with Codex), as they stood at the S1 stop

**Superseded by Section 9.** The owner chose option A with conditions; the
text below is kept as the record of what was offered.

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

## 9. Continuation under amendment 1 (1 October 2026): stopped at S2

The owner approved one bounded continuation on Codex's five conditions,
after Codex's review of `335331c`. The frozen plan's stages, gates,
thresholds, A1 and A2 requirements and control checks were kept. The
cumulative execution ceiling became 90 minutes, including what was already
charged.

### 9.1 C0: what was frozen first

- **CI at `335331c`.** The test job had failed on one test added in the
  previous step. It pinned an entry error of `14.17u`. That number depends
  on the platform's sine through the stored nodes, and Linux gives `14.03u`.
  The test now checks only the portable claim. Nothing else failed.
- **Freeze (`0ca7a8d`),** before any continuation run:
  - the amendment, revised to the approved conditions: rule 2 for C-S1
    only; an entry requirement for C-S1; the bound described as first order
    and not as an exact certificate;
  - the evaluator stages `c1` (measurements) and `c2` (qualification and
    selection), with tests;
  - the four adverse controls, defined in the evaluator with unchanged
    perturbations.
- **CI at `0ca7a8d`:** passed.

### 9.2 C1 and C2: qualification and selection under amendment 1

Evidence: `B1-c1.json`, `B3-c1.json`, `c2-selection-amendment-1.json`. The
oracle fixtures passed on both builds. The two builds agree in every count
and, to the digits shown, in every ratio.

**C-S1:**

| Set | Components failing rule 1, all excused by rule 2 | Other failures | Largest bound ratio | Largest entry ratio, D1 / D2 |
| --- | ---: | ---: | ---: | --- |
| Retrospective (84 grids, `v1`–`v3`) | 26 | 0 | `0.74` | `0.95` / `0.52` |
| Confirmation (20 grids, `w1`–`w3`, first use) | 8 | 0 | `0.37` | `0.87` / `0.47` |

- **Entrywise rule and exactness** (unchanged rules): no failure. On the
  confirmation set C-S1's largest entrywise error is `8.1e-14`, against
  `5.2e-11` for the current construction, and its polynomial-exactness
  defect is at most `4.7e-16`.
- **The margin of the entry requirement is thin at large degrees.** The
  largest D1 entry ratio rises with the degree:

  | Degrees | Largest D1 entry ratio |
  | --- | ---: |
  | 2, 3 | `0.36`, `0.46` |
  | 16 to 640 | `0.72` to `0.86` |
  | 1024 | `0.95` |
  | 1280 | `0.92` |

  So the worst entry's actual error grows about as fast as the bound. This
  answers the open question of the previous step: the linear growth of the
  bound is not slack. The bound held everywhere it was tested, with 5% to
  spare at degree 1024. Nothing is known above degree 1280.

**C-T1, C-T2 and C-T3** keep the frozen rule and do not qualify:
126 / 112 / 112 failures on B1 and 125 / 111 / 111 on B3 on the
retrospective set, and 16 / 11 / 11 and 16 / 12 / 12 on the confirmation
set.

**Adverse controls** at degree 1280 on `[1e-5, 1]` (identical on both
builds):

| Operator | Rejected | By which checks | Largest entry ratio, D1 / D2 | Largest bound ratio |
| --- | --- | --- | --- | ---: |
| undamaged C-S1 | no | — | `0.85` / `0.35` | `0.12` |
| `one_D1_entry` | **yes** | action rule 2, entry | `154` / `0.35` | `8.7e3` |
| `all_D1_entries` | **yes** | action rule 2, entry | `349` / `0.35` | `5.4` |
| `shifted_nodes` | **yes** | entrywise, action, entry, exactness | `4.8e9` / `9.7e8` | `1.7e6` |
| `one_D2_entry` | **yes** | action rule 2, entry | `0.85` / `244` | `8.6e3` |

- **All four are rejected,** as required.
- **A limit worth knowing.** The unchanged entrywise 2× rule did not reject
  three of the four at this grid. The current construction's own entrywise
  error is larger there than those damages. The action rule and the entry
  requirement rejected them.

**Selection.** C-S1 is the only qualified candidate. Its improvement on
metric (c) is `97×`, against the required `10×`. It is recorded as "C-S1
qualified under post-observation amendment 1".

### 9.3 Implementation freeze (`bea799b`)

- **Change.** `chebyshev_lobatto_grid` now builds C-S1: half-angle nodes,
  weights recomputed from the returned nodes by double-double products,
  compensated negative-sum diagonals, and the explicit second-derivative
  recurrence. Signatures, defaults, ordering, dtype and read-only arrays are
  unchanged.
- **Identity.** The production matrices are bit for bit those of the
  qualified diagnostic construction on all 84 grids of the plan, on both
  builds.
- **Provenance.** Every record's `software_versions` gains one string,
  `chebyshev_construction: "c-s1-r1"`. No schema version changes.
- **Cost.** About `25 ms` per grid at degree 640, against `4 ms` before.
  The verifier commands of Section 8 took 434 s after the change against
  414 s before on B1, and 528 s against 622 s on B3. Each was timed once,
  so the difference is within run-to-run variation.
- **Order kept.** The freeze was committed locally, and pushed only after
  the R0 baseline was committed.

### 9.4 R0: numerical baseline (`bc6d002`)

- **What ran.** All 17 commands of the plan's Section 8, on B1 and B3,
  against an extracted copy of `main` at `5846975` (package source SHA-256
  `66d9bd28…`).
- **Structure.** All eight real records have the audited structure. That
  includes the five whose extraction had only been validated on synthetic
  records.
- **Allowances.** `10 × max(E, X, 8 eps |value|)` for 2,066 leaves per
  build (`r0-limits.json`), committed before any candidate verifier run.
- **Gates failing at baseline:**

  | Build | Failing gates |
  | --- | --- |
  | B1 (Accelerate) | Gubser--Nellore `collocation-residual`; optical `optical-response-numerics` |
  | B3 (OpenBLAS) | neither |
  | both | the two truncated-domain soft-wall verdict controls, as intended |

### 9.5 S2: regression — the stop

Evidence: `s2-candidate-B1.json`, `s2-candidate-B3.json`,
`s2-comparison.json`. The candidate runs report construction `c-s1-r1` and
package source SHA-256 `1c731e1b…`.

**A1 — one gate that passed at baseline fails.**

| Gate | Build | Baseline | Candidate |
| --- | --- | --- | --- |
| Gubser--Rocha `spectral-refinement` | B1 | pass, `1.63e-9` | **fail**, `4.73e-9` |
| | B3 | pass, `1.18e-9` | pass, `3.3e-10` |

- **Criterion:** "final <= 2.0e-06; zero ordering failures above 5.0e-10".
- **What failed.** The final refinement change, `4.73e-9`, is far inside
  its `2e-6` limit. The check therefore failed on its ordering clause: a
  refinement change above `5e-10` that does not decrease.
- **Also on Linux.** Ordinary PR CI fails two Gubser--Rocha tests on the
  candidate for the same reason (Section 9.6).
- **Not investigated.** Whether this is a rounding plateau near `1e-9` or a
  real loss of convergence was not examined. Examining it would be repair
  work after a stop.

**A2 — 13 of 4,132 leaf comparisons exceed their allowance.**

| Consumer | Build | Leaves over | Largest ratio to allowance | Relative size of those changes |
| --- | --- | ---: | ---: | --- |
| DGR neutral | B1 | 9 | `4.4` | `5e-13` to `5e-12` |
| DGR neutral | B3 | 3 | `2.1` | about `5e-13` |
| Soft-wall vector | B3 | 1 | `1.09` | `1.9e-14` |

- **DGR neutral.** The leaves are `chi_2/T^2` at degree 80 (positions 1 to
  6) and at degree 120 (position 3). On B1, at degree 120 and position 3,
  the entropy, the temperature and the susceptibility integral exceed too.
  Their allowances are small because the recorded refinement and build
  differences there are tiny, about `1e-13` relative for `chi_2/T^2`.
- **Soft-wall.** Spectral degree 56, mode `n = 1`. Its allowance is the
  representation floor, `10 × 8 eps`.

**Every leaf, by consumer** (largest ratio of change to allowance; largest
relative change of any leaf):

| Consumer | Leaves | B1 ratio | B3 ratio | Largest relative change |
| --- | ---: | ---: | ---: | ---: |
| Soft-wall vector | 22 | `0.37` | **`1.09`** | `3.4e-14` |
| Hard-wall vector | 7 | `5.0e-4` | `2.8e-4` | `3.3e-14` |
| Hard-wall chiral | 28 | `0.025` | `0.084` | `1.0e-12` |
| Gubser--Nellore | 1,556 | `1.9e-4` | `1.4e-4` | `1.1e-10` |
| Gubser--Rocha | 42 | `0.37` | `0.24` | `5.9e-9` |
| DGR neutral | 320 | **`4.4`** | **`2.1`** | `8.6e-11` |
| DGR finite density | 53 | `0.15` | `0.33` | `2.2e-9` |
| HHH optical | 38 | `0.0083` | `0.0083` | `1.7e-9` |

**Controls.** All 71 control values per build are bit for bit identical
between baseline and candidate. No key or configured coordinate differs.

**A3 — the two known gates, on all builds:**

| Gate (limit) | Build | Baseline | Candidate |
| --- | --- | --- | --- |
| Gubser--Nellore `collocation-residual` (`<= 1e-9`) | B1 | **fail**, `1.716e-9` | pass, `9.28e-10` |
| | B3 | pass, `9.96e-10` | pass, `9.85e-10` |
| Optical `optical-response-numerics` (ratio `<= 1`) | B1 | **fail**, `1.0011` | pass, `0.421` |
| | B3 | pass, `0.979` | pass, `0.402` |

No other acceptance check changes its verdict on either build.

**What this does and does not show.**
- It shows that the construction error was the cause of the two failing
  gates on the Accelerate build. With the new construction both pass, and
  the optical gate ratio falls by more than half on both builds.
- It does not show that the new construction is acceptable. By the frozen
  criteria it is not: A1 takes precedence over everything else.
- The allowances are maintenance regression allowances. Exceeding one is a
  stop to be reported, not an automatic physics failure (plan Section 8.1).
  The largest relative change of any table leaf is `5.9e-9`.

### 9.6 Not run, and CI on the candidate

- **S3 was not run.** It follows S2 in the declared order.
- **The full unit suite was not run locally,** for the same reason.
- **Ordinary PR CI on the candidate (`bc6d002`, Linux),** reported as
  additional execution:

  | Job | Result |
  | --- | --- |
  | Tests (Python 3.11) | **fail**: 2 of 535, both Gubser--Rocha (`test_amended_preflight_passes_all_declared_gates`, `test_artifacts_are_complete_and_fail_closed_on_overwrite`) |
  | Extended historical route audit | **fail**: 2 of 53, both audits of superseded optical routes (`test_figure_target_preserves_the_spectral_resolution_stop`, `test_endpoint_split_normal_state_preserves_the_w2_stop`) |
  | Gate telemetry (Ubuntu, macOS) | pass (it records verdicts and does not enforce them) |
  | Wheel build, wheel portability | pass |

  - The two historical audits assert that an old, superseded route still
    stops at a `1e-7` threshold. With the new construction its value moves
    across that threshold (`9.3e-8`, and `1.06e-7`).
- **One further local failure.** On B1 an existing unit test of the O-B
  diagnostic tool fails with the new construction
  (`test_regular_residual_matches_the_double_formula`). It asserts that the
  normal-state spike residual is at least twice its own double-precision
  evaluation error. The residual fell to that level. It did not fail in
  Linux CI. It is not a benchmark gate, and it was left unchanged.

### 9.7 Resources

**Local execution in the continuation:**

| Run | Wall time |
| --- | ---: |
| C1 on B1, on B3 | `123 s`, `131 s` |
| C2 | under `1 s` |
| Runner smoke test on the baseline tree (two cheap consumers) | `6 s` |
| R0 baseline on B1, on B3 | `414 s`, `622 s` |
| S2 candidate on B1, on B3 | `434 s`, `528 s` |
| Limits and comparison | about `1 s` |
| Unit tests of the evaluator, runners and grid (short runs) | `62 s` |
| **Logged** | **`2,321 s`** |
| **Charged** (conservative) | **`2,340 s` (39.0 min)** |

- **Cumulative execution:** about 60.7 of 90 minutes. About 29 remain.
  Nothing was reset.
- **Active work:** about 1.3 hours in the continuation, and about 2.8 of the
  6 hours in total.
- **Not used:** paid compute, installations, extra CI dispatches, reserved
  optical cases, private research.
- **Additional execution, not charged:** ordinary PR CI and the existing
  gate telemetry on the pushed commits.

### 9.8 Disclosures and the decision

**Disclosures.**
- **A diagnostic unit-test file ran on the new code before R0 was
  committed.** While checking the implementation I ran
  `tests/test_gate_calibration.py`, which exercises the O-B tool on the
  production grid. That is how the failing unit test above was found. No
  Section 8 verifier ran on the new code before the R0 commit.
- **One unit test touched a confirmation node set before the freeze.** It
  evaluated the three confirmation vectors, and no matrix, at the nodes of
  one confirmation grid. It was moved off the set before the freeze.
- **The runner was smoke-tested on the baseline tree** for two cheap
  consumers before the implementation freeze. Those runs are charged above.
- **The amendment file is frozen by hash.** The continuation evidence
  records its SHA-256, and a test checks it. Later notes belong here, not
  there.
- **No changelog entry was written.** The plan asks for one listing the
  per-consumer deltas. Writing it for a change that stopped at S2 would
  present the change as accepted.

**Nothing below is decided or done.** The stop returns the work to the
owner. No criterion was tuned, no candidate was added, and no repair was
attempted.

| Option | What it means |
| --- | --- |
| **Review the three stop items first** | Codex reviews the S2 evidence. Each item (the Gubser--Rocha ordering clause near `1e-9`, the DGR allowances, the single soft-wall leaf) gets a written disposition before anything else runs. A change to a gate or to the allowance rule would be a scientific-contract change with its own review. |
| **Accept the stop and withdraw the change** | The production change is reverted on this branch. The evidence, tool and report stay. The Gubser--Nellore and optical gates keep failing on the Accelerate build. |
| **Decide later** | The branch stays unmerged as it is. |

The first option is recommended. The evidence that the construction is the
cause of the two failing gates is strong, and the three stop items are all
at or below the `1e-8` relative level. But whether they are acceptable is a
judgement about three benchmarks' contracts, and it should not be made by
the author of the change.
