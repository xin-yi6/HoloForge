# Gate calibration report (Batch 2a), September 2026

- **Status:** Batch 2a evidence. AI-generated (Claude), revised after Codex
  review R49 on 30 September 2026; the original text is in commit `53a4da1`.
  Section 7 lists the revisions. **No production solver, gate, threshold,
  record or verdict was changed.**
- **Plan:** [`gate-calibration-2026-09-plan.md`](gate-calibration-2026-09-plan.md),
  frozen at `ace2971` before execution (SHA-256 `3d20c42a…`).
- **Evidence:** [`docs/generated/gate-calibration/`](../generated/gate-calibration/),
  one JSON file per build and gate. These files are unchanged by the revision.
- **Reserved confirmation cases:** not run.

## Provenance: recorded facts and executor-reported facts

**Recorded in every evidence file:**
- HoloForge version, source digest and commit;
- platform and machine;
- Python, NumPy and SciPy versions;
- the NumPy/SciPy BLAS and LAPACK names;
- `long double` epsilon and wall time.

All 18 files carry the same HoloForge source digest.

**Executor-reported only, not recorded in those files:**
- **Tool identity.** Runs used `tools/gate_calibration.py`, committed unchanged
  as `c4a15a2` (SHA-256 `eea8d743…`). The B1 runs and the B2 soft-wall run
  executed the identical uncommitted working copy, which is why their commit
  field is `ace2971`. The source digest excludes `tools/` and cannot confirm
  this.
- **Threads.** The B2 and B4 single-thread settings were set on the command
  line.
- **Wheels.** The B3 and B4 OpenBLAS wheels were installed from the
  `macosx_11_0` NumPy and `macosx_12_0` SciPy variants. The recorded backend
  names distinguish Accelerate from OpenBLAS, but not the wheel files.
- **Cost.** About 14 minutes of local wall time, with the B1–B4 batch taking
  537 s.

From this revision onward, the tool also records `tool_sha256`,
`plan_sha256`, allowlisted thread variables and installed NumPy/SciPy wheel
tags. Existing files were not backfilled.

| ID | Build | Source |
| --- | --- | --- |
| B1 | macOS arm64, NumPy 2.4.6 / SciPy 1.17.1 Accelerate wheels, default threads | local |
| B2 | B1 with `VECLIB_MAXIMUM_THREADS=1` (executor-reported) | local |
| B3 | macOS arm64, same versions, OpenBLAS wheels (executor-reported variant) | local |
| B4 | B3 with `OPENBLAS_NUM_THREADS=1` (executor-reported) | local |
| B5 | Linux x86_64, OpenBLAS, same versions | CI dispatch [36679954944](https://github.com/xin-yi6/HoloForge/actions/runs/36679954944) at `c4a15a2` |
| B6 | GitHub `macos-latest` arm64, Accelerate | same dispatch; supplementary, not in the plan |

**Identity checks.** Every saved case records that the maximum of its
reconstructed residual equals the production value bit for bit. This is a
**maximum-value** identity, not a per-node comparison. The 50-digit GN
evaluator agrees with double evaluation off-solution to at most `2.8e-14`.

## 1. Gubser--Nellore collocation gate

| Profile (qcd-like) | B1/B2/B6 (Accelerate) | B3/B4 (OpenBLAS, Mac) | B5 (OpenBLAS, Linux) |
| --- | --- | --- | --- |
| deg 150, `x_h = 1.23` | root `8.79e-9`, then polish (6 evaluations, `xtol` stop), final **`1.716e-9`**; stored-vector residual at 50 digits `1.359e-9`; evaluation error `3.6e-10` | root `1.01e-10`, no polish | root `3.71e-11`, no polish |
| deg 150, `x_h = 1.10` | root `9.72e-10`, no polish | root `8.79e-10`, no polish | root `1.65e-9`, then polish (9 evaluations), final `5.96e-11` |
| deg 80, `x_h = 1.04` | `9.83e-10` | `9.96e-10` | `9.85e-10` |

| Whole-branch statistic | B1/B2/B6 | B3/B4 | B5 |
| --- | ---: | ---: | ---: |
| Worst final residual | `1.716e-9` | `9.96e-10` | `9.85e-10` |
| qcd-like profiles above `5e-10` (of 318) | 19 | 11 | 14 |
| Profiles polished (qcd-like; none for cosh) | 9 | 7 | 8 |

Findings:
- **Evaluation rounding does not explain the violation.** The stored
  Accelerate solution itself has a 50-digit residual of `1.36e-9`, above
  `1e-9`. Evaluation rounding contributed at most `3.6e-10` in any saved case.
  The 50-digit calculation keeps the binary64 derivative matrices fixed. It
  therefore does not bound discretization or matrix-construction error.
- **The root residuals differ between builds for the same profile.** Which
  profile needs the least-squares polish, and whether the polish ends below
  `1e-9`, differ with them. On Accelerate the polish stopped on its `xtol`
  criterion at `1.7e-9`; on Linux the polish of another profile reached
  `6e-11`.
- **The `1e-9` constant is both the polish trigger and the acceptance limit.**
  Profiles ending just below it are never polished.
- **Physical-check values are recorded, not interpreted.** For the failing
  profile, the oversampled equation residual is `2.1e-8` on Accelerate and
  `2.9e-8` on OpenBLAS; the production limit is `1e-7`.
- The `gamma_n |D| |x|` expression is a conservative diagnostic. It is not a
  certified universal bound: nonlinear operations, normalization and special
  functions would need a derivation first. The fixture test shows only that
  one degree-24 profile's evaluation error lies inside it.
- **Partial deliverable:** plan item 2 asked for per-node residual arrays.
  Only each case's maximum, its location and the bound there were saved.

Adverse controls (the six evidence files; B1 and B3 values shown; base:
qcd-like degree 80, `x_h = 1.04`):

| Control | Collocation residual | Oversampled equation residual at degree 80 |
| --- | ---: | ---: |
| Reference | `9.8e-10` | `2.9e-7` |
| Bump `1e-6` in `f` | `9.7e-4` | `9.8e-4` |
| Bump `1e-8` | `9.7e-6` | `9.8e-6` |
| Bump `1e-10` (supplementary) | `9.7e-8` | `2.9e-7` |
| Bump `1e-11` (supplementary) | `9.7e-9` | `2.9e-7` |
| Horizon condition violated by `1e-6` | `2.0e-4` | `8.6e-4` (boundary `1e-6`) |
| Potential `b` times 1.01 | `0.156` | `0.156` |
| Degree 24 | `4e-11` / `1e-11` | `0.98` |

The limitation matters. Production applies the oversampled gate only at the
finest degree, and at degree 80 this base already exceeds that gate's `1e-7`
ceiling. These controls therefore do not establish the rejection sensitivity
of the finest-degree contract.

The diagnostic did not measure how any perturbation changes the
thermodynamic observables. No observable-level conclusion is drawn from the
field-perturbation amplitudes.

## 2. HHH optical equation gate

A-form production residual (normalized as in production) and normalized
regular-factor residual, degree 640 unless stated:

| `omega/T` | A-form, B1 / B3 / B5 | Normalized regular form, B1 / B5 |
| --- | --- | --- |
| 50 | `8.7e-7` / `8.6e-7` / `9.4e-7` | `6.5e-8` / `7.9e-8` |
| 58 | `5.5e-6` / `5.3e-6` / `5.7e-6` | `6.5e-8` / `7.8e-8` |
| **59** | **`2.0e-5` / `2.1e-5` / `2.1e-5`** | `6.5e-8` / `7.9e-8` |
| **60** | **`1.0011e-5` / `9.8e-6` / `9.96e-6`** | `6.5e-8` / `7.9e-8` |
| 61 | `4.2e-6` / `3.8e-6` / `4.4e-6` | `6.5e-8` / `8.0e-8` |
| 62 | `2.8e-6` / `2.6e-6` / `2.8e-6` | `6.5e-8` / `7.9e-8` |
| 70 | `6.5e-7` / `6.2e-7` / `6.7e-7` | `6.5e-8` / `8.0e-8` |
| 60, degree 512 | `2.1e-7` | `1.3e-7` |
| 60, degree 384 | `3.9e-6` | `3.9e-6` |

Findings supported by the saved evidence:
- **One node, every build.** At every degree-640 frequency, the A-form
  maximum is at the same check node, `u = 2.355e-5`. By the grid
  construction this is the first checked node at the UV end of the bulk
  element `[1e-5, 1]`, after three excluded endpoint nodes. There the two
  saved dominant term magnitudes are both about `4.73`.
- **ω/T = 59 fails everywhere.** The maximum varies non-monotonically with
  frequency and exceeds the `1e-5` limit at 59 on all six configurations.
  Builds move it by only a few percent.
- **Sensitivity to input perturbation.** Relative `eps`-sized perturbations
  of the stored regular solution change the maximum by up to `2.8e-7` at
  ω/T = 60 and `7.0e-7` at ω/T = 59. This measures sensitivity to the inputs,
  not arithmetic evaluation error at fixed inputs.

The normalized regular-factor values are not evidence of a smaller defect:
- For real frequency, `A = (1-u)^s a` with `|(1-u)^s| = 1`, and the two
  numerators obey `R_A = (1-u)^s R_a` exactly. The raw defects have the same
  magnitude in exact arithmetic.
- The tool divides them by different sums of term magnitudes. A smaller
  normalized regular residual therefore does **not** show that the equation
  is better satisfied, nor that evaluation was repaired.
- At the B1 spike the normalized ratio is about 780. If the numerators agree
  numerically, this is a denominator effect. The derived raw A-form defect
  there is about `1.05e-4` (saved scale times saved normalized value).
- The saved evidence does not contain the raw complex numerators or the
  regular denominator needed to verify the split numerically.

**Withdrawn as unverified.** The following came from interactive exploratory
runs whose outputs were not saved:
- the claim that the A-form residual is at most about `6.5e-8` away from the
  spike node;
- the off-spike A-form maxima under perturbation (`8.8e-6`, `8.9e-4`) and a
  relative `1e-4` UV bump (a supplementary control);
- the resulting "about 19x" sensitivity comparison, and the O-A threshold
  estimate built on it.

**Not performed.** Plan item 5, the Riccati cross-check, was not run by the
tool. The production verifier's own spectral-versus-Riccati difference for
this response is `1.434e-6` (Linux) and `1.435e-6` (GitHub macOS). It is
recorded in the Gate telemetry artifacts of run 36679954944, which are
subject to GitHub's artifact retention.

The mechanism of the single-node value is not established.

*Follow-up, 30 September 2026:* the
[O-B diagnosis](optical-ob-diagnosis-report.md) addresses the open questions
of this section. This section is otherwise unchanged.

Adverse controls (saved; B1, with B3 agreeing to about `1e-10`):

| Control | A-form maximum | Normalized regular form |
| --- | ---: | ---: |
| Reference (60/640) | `1.0e-5` | `6.5e-8` |
| Conjugated ingoing exponent | `0.999` | `0.997` |
| Frequency squared times 1.01 | `0.163` | `2.5e-4` |
| Degree 192 | `0.226` | `0.226` |
| Absolute `1e-6` bump in the bulk (post-observation replacement) | `0.29` | `0.29` |
| Relative `1e-6` bump near the UV end (post-observation replacement) | `3.7e-4` | `4.7e-7` |

The two replacement controls were designed after the planned mid-element
relative bump proved ineffective. On this low-temperature background `|a|`
is about `1e-16` in the bulk, and that ineffective trial left both maxima
unchanged. Its output file was overwritten by the rerun, so its result is
executor-reported only.

The failing response belongs to the provenance-only Figure 2 set. The
normal-state and near-critical `C_2` responses have gate ratios of at most
`0.113` in the production record.

## 3. Soft-wall spectral refinement

- Eigenvalue condition numbers by mode are `1.015` to `1.041` on every degree
  and build.
- `||H||_2` grows from `1.0e3` (degree 24) to `6.4e5` (degree 120).
- The first-order perturbation scale `eps ||H||_2 kappa_j / |lambda_j|`
  rises from `5.8e-14` to `3.6e-11`. It assumes a simple eigenvalue,
  first-order perturbation theory, the 2-norm, binary64 `eps`, and matching
  each analytic mode to the nearest computed eigenvalue. It is an
  order-of-magnitude reference, not a proved error floor. Errors well below
  it are consistent with rounding dominance but do not prove it.

| Degree | Max relative error (B1 to B6) | Error / perturbation scale |
| ---: | --- | --- |
| 24 | `2.1e-5` | `1.4e9` |
| 32 | `1.7e-9` | `3.6e4` |
| 40 | `2.7e-13` to `2.8e-13` | `2.3` to `2.4` |
| 48 to 120 | `5.6e-15` to `1.7e-13` | `0.001` to `0.036` |

Controls, classified by what they test:

| Control | Complete existing contract | Error / scale | Role |
| --- | --- | --- | --- |
| Degree 24 | FAIL (final error `2.1e-5` > `1e-8`) | `1.4e9` | must reject |
| Degree 32 | **PASS**: 16/24/32 improve and final `1.7e-9` ≤ `1e-8` | `3.6e4` | non-plateau calibration example, not a negative control |
| `z_max = 4/kappa`, degrees 48–64 | FAIL (spectrum error `5.2e-2` > `2e-4`) | `1.2e10` to `3.8e10` | must reject |
| `z_max = 6/kappa`, degrees 48–64 | FAIL (error `4.1e-7` > `1e-8` refinement requirement) | `2.0e5` to `6.3e5` | must reject |
| Swapped eigenvalues | fails the spectrum tolerance (error `1.0`) | not computed | synthetic |
| Non-finite eigenvalue | local finite-value flag only | not computed | synthetic; no production rejection test executed |

Among the controls the complete contract rejects on accuracy grounds, the
smallest ratio is `2.0e5`. The largest plateau ratio (degrees 48–120, all
builds) is `0.036`. Degree 32 lies between them and passes through the
convergence criterion.

## 4. What is and is not established

**Established on these builds:**
- **GN:** the collocation violation on Accelerate is carried by the stored
  solution, not by evaluation rounding. Root and polish outcomes differ by
  build. One constant is both trigger and limit.
- **Optical:** the A-form maximum is at one fixed node on every build and
  varies strongly with frequency. ω/T = 59 exceeds the limit everywhere.
- **Soft-wall:** from degree 48 the refinement failures coincide with errors
  far below the first-order perturbation scale.

**Not established:**
- the mechanism of the optical single-node value;
- any comparison of raw defects between the two optical forms;
- the observable-level effect of the GN collocation residual;
- rejection sensitivity of the finest-degree GN contract;
- any amended rule on reserved cases, or on other versions and platforms.

## 5. Batch 2b directions (candidates for owner decision; none approved)

- **Soft-wall, S-A (promising).** A roundoff-aware alternative to the
  strictly-decreasing criterion, keeping analytic accuracy:
  - pass by (i) the current convergence rule, or (ii) a plateau branch whose
    errors are at most their first-order perturbation scales;
  - add explicit cross-degree eigenvalue stability;
  - do not count the same analytic comparison as an independent method.

  The complete rule must reject the cutoff, ordering and non-finite examples,
  and must still accept converged degree-32 results. Freeze the exact
  contract before the reserved confirmation cases.
- **GN, G-A (candidate, deferred).** Keep the `1e-9` polish trigger, so the
  route and results are unchanged, and set collocation acceptance to `1e-8`.
  - Making one ceiling one tenth of another is a policy heuristic, not proof
    that the algebraic error is an order below the discretization or
    observable error.
  - Before selection it needs a bounded residual-to-observable sensitivity
    test on the finest-degree reference, with the independent, boundary and
    thermodynamic gates unchanged.

  **Alternative G-B:** make the polish stop on the residual. It would directly
  change the polished profiles: 9, 7 and 8 of 318 qcd-like on
  Accelerate, OpenBLAS Mac and Linux, and none for cosh-calibration. Through
  continuation seeding, it could also change later profiles on the same
  branch. Both possibilities stay open until that evidence exists.
- **Optical, O-B (recommended; O-A withdrawn).** On existing saved solutions:
  1. compare raw complex numerators and both scales under a common
     normalization;
  2. check the transformation identity;
  3. if needed, independently re-evaluate interpolation and derivatives at
     the spike node;
  4. keep input sensitivity separate from evaluation error.

  Do not discard the node or widen the threshold.

## 6. Deviations from the frozen plan

1. **Optical adverse control.** The planned mid-element relative bump was
   ineffective and was replaced after observation by two new controls. The
   ineffective trial's output is executor-reported only.
2. **GN supplementary bumps** of `1e-10` and `1e-11` were added after the
   first run. They are labelled in the evidence and are calibration, not
   confirmation.
3. **GN adverse base** at degree 80, where the oversampled gate does not
   apply and is already exceeded. This limits G-A inference (Section 1).
4. **Coverage.** B6 is supplementary. Adverse controls ran on all six builds,
   although the plan specified B1 and B3.
5. **Exploratory runs.** Interactive exploratory runs informed the narrative,
   but their outputs were not saved. Claims depending only on them are
   withdrawn (Section 2).
6. **Partial deliverables:** GN per-node arrays, and the optical Riccati
   cross-check, which was not performed (Section 2 cites the existing
   production record).
7. **Soft-wall differences between B1 and B6**, for example `1.9e-14` against
   `3.4e-14` at degree 48, are an observed configuration difference. No
   mechanism is attributed.

No stopping condition was triggered.

## 7. Revision after Codex review R49 (30 September 2026)

- **R49-1.** The tool now exits 2 on a failed fixture, an identity mismatch
  or a non-finite diagnostic value. Scientific values never trigger it.
  Identities are described as maximum-value checks.
- **R49-2.** Unsaved optical and adverse claims are withdrawn. The
  normalization identity is added, and plan items not performed are
  disclosed.
- **R49-3.** Recorded facts are separated from executor-reported ones.
  Tool/plan digests, thread variables and wheel tags are now recorded
  prospectively.
- **R49-4.** Soft-wall controls are reclassified. Degree 32 passes the
  existing contract, and the separation claims are corrected.
- **R49-5.** Observable-level inferences from GN field perturbations are
  removed. G-A is a candidate requiring observable justification, and G-B's
  scope is stated precisely.
