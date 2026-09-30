# Gate calibration report (Batch 2a), September 2026

- **Status:** Batch 2a evidence for owner and Codex review. It is AI-generated
  (Claude) and not yet reviewed. **No production solver, gate, threshold, record or
  verdict was changed.**
- **Plan:** [`gate-calibration-2026-09-plan.md`](gate-calibration-2026-09-plan.md),
  frozen at commit `ace2971` before execution.
- **Tool:** `tools/gate_calibration.py` at commit `c4a15a2`; its SHA-256
  begins `eea8d743c0dc8292`. It ran unchanged for every build.
- **Evidence:** [`docs/generated/gate-calibration/`](../generated/gate-calibration/),
  one JSON file per build and gate. Each file includes the runtime provenance
  fields.
- **Reserved confirmation cases:** not run.

## Builds and budget

| ID | Build | Source |
| --- | --- | --- |
| B1 | macOS arm64, Accelerate wheels, default threads | local |
| B2 | B1 with `VECLIB_MAXIMUM_THREADS=1` | local |
| B3 | macOS arm64, OpenBLAS wheels (same NumPy 2.4.6 / SciPy 1.17.1) | local |
| B4 | B3 with `OPENBLAS_NUM_THREADS=1` | local |
| B5 | Linux x86_64, OpenBLAS, same versions | CI dispatch [36679954944](https://github.com/xin-yi6/HoloForge/actions/runs/36679954944) |
| B6 | GitHub `macos-latest` arm64, Accelerate | same dispatch (not in the plan; see deviations) |

Budget use was about 14 minutes of local wall time out of 90, and one CI
dispatch out of three.

Identity checks passed on every build and every case:
- each reconstructed production residual matches production bit for bit;
- the 50-digit GN evaluator agrees with double evaluation off-solution to
  `<= 2.8e-14`;
- the fixture tests confirm that the actual evaluation error lies inside the
  a-priori rounding bound.

## 1. Gubser--Nellore collocation gate

The failing profile and two neighbours, on each build:

| Profile (qcd-like) | B1/B2/B6 (Accelerate) | B3/B4 (OpenBLAS, Mac) | B5 (OpenBLAS, Linux) |
| --- | --- | --- | --- |
| deg 150, `x_h = 1.23` | root `8.79e-9`, then polish (6 evaluations, `xtol` stop), final **`1.716e-9`**; stored-vector residual `1.359e-9`; evaluation error `3.6e-10` | root `1.01e-10`, no polish | root `3.71e-11`, no polish |
| deg 150, `x_h = 1.10` | root `9.72e-10`, no polish | root `8.79e-10`, no polish | root `1.65e-9`, then polish (9 evaluations), final `5.96e-11` |
| deg 80, `x_h = 1.04` | `9.83e-10` | `9.96e-10` | `9.85e-10` |

| Whole-branch statistic | B1/B2/B6 | B3/B4 | B5 |
| --- | ---: | ---: | ---: |
| Worst final residual | `1.716e-9` | `9.96e-10` | `9.85e-10` |
| qcd-like profiles above `5e-10` (of 318) | 19 | 11 | 14 |
| Profiles polished | 9 | 7 | 8 |

Findings:
- **The residual is set by where the nonlinear solve stops**, not by
  evaluation rounding. The 50-digit residual of the stored Accelerate vector
  is itself `1.36e-9`. Evaluation rounding contributes at most `3.6e-10` on
  any build.
- **Which profile needs the polish, and whether it gets below `1e-9`, depends
  on the build.** The iterate path of the finite-difference `hybr` solve
  differs between builds, and the polish can stop on its step-size criterion
  above `1e-9` (Accelerate) or reach `6e-11` (Linux).
- **The `1e-9` constant is both the polish trigger and the acceptance limit.**
  Only profiles whose root residual exceeds it are polished. Profiles that end
  just below it are never polished. The polish itself may stop far below it
  (Linux, `6e-11`) or above it (Accelerate, `1.7e-9`). The gate therefore
  tests the same boundary that decides whether the solver works harder, and
  roughly 11 to 19 profiles per build sit between `5e-10` and `1e-9`.
- **The physical checks are unaffected.** For the failing profile the
  oversampled equation residual is `2.1e-8` (Accelerate) against `2.9e-8`
  (OpenBLAS); the gate is `1e-7`.

Adverse controls on B1 and B3 (base: qcd-like deg 80, `x_h = 1.04`):

| Control | Collocation residual | Oversampled equation residual | Detected by |
| --- | ---: | ---: | --- |
| Reference | `9.8e-10` | `2.9e-7`* | — |
| Bump `1e-6` in `f` | `9.7e-4` | `9.8e-4` | both |
| Bump `1e-8` | `9.7e-6` | `9.8e-6` | both |
| Bump `1e-10` (supplementary) | `9.7e-8` | `2.9e-7`* | collocation only |
| Bump `1e-11` (supplementary) | `9.7e-9` | `2.9e-7`* | collocation at `1e-9` only |
| Horizon condition violated by `1e-6` | `2.0e-4` | `8.6e-4` (boundary `1e-6`) | both |
| Potential `b` times 1.01 | `0.156` | `0.156` | both |
| Degree 24 (under-resolved) | `4e-11` / `1e-11` | **`0.98`** | **oversampled only** |

\*The production oversampled gate applies only to the finest degree. At
degree 80 its baseline is already `2.9e-7`, so this adverse base under-states
what that check can detect. A degree-150 base should be used in any Batch 2b
confirmation.

The collocation residual alone detects perturbations of amplitude about
`1e-12` to `1e-10`, far below the scale that can move the thermodynamic
observables (refinement `2e-4`, figure anchors `1.5e-3` and `5e-3`). Only the
oversampled check detects under-resolution.

## 2. HHH optical equation gate

A-form production residual and regular-factor residual, at degree 640 unless
stated:

| `omega/T` | A-form, B1 / B3 / B5 | Regular form, B1 / B5 |
| --- | --- | --- |
| 50 | `8.7e-7` / `8.6e-7` / `9.4e-7` | `6.5e-8` / `7.9e-8` |
| 58 | `5.5e-6` / `5.3e-6` / `5.7e-6` | `6.5e-8` / `7.8e-8` |
| **59** | **`2.0e-5` / `2.1e-5` / `2.1e-5`** | `6.5e-8` / `7.9e-8` |
| **60** | **`1.0011e-5` / `9.8e-6` / `9.96e-6`** | `6.5e-8` / `7.9e-8` |
| 61 | `4.2e-6` / `3.8e-6` / `4.4e-6` | `6.5e-8` / `8.0e-8` |
| 62 | `2.8e-6` / `2.6e-6` / `2.8e-6` | `6.5e-8` / `7.9e-8` |
| 70 | `6.5e-7` / `6.2e-7` / `6.7e-7` | `6.5e-8` / `8.0e-8` |
| 60, degree 512 | `2.1e-7` | `1.3e-7` |
| 60, degree 384 | `3.9e-6`, in the bulk | `3.9e-6` |

Findings:
- **The value near `1e-5` is a reproducible, single-node feature, not a
  build-dependent floor.**
  - At every degree-640 frequency the A-form maximum sits at the same check
    node, `u = 2.355e-5`. This is the first node checked after the three
    excluded nodes at the UV end of the bulk element `[1e-5, 1]`.
  - There the two dominant terms, about `4.73` each, cancel.
  - Elsewhere the A-form residual is at most about `6.5e-8`.
  - The value at that node varies non-monotonically with frequency, peaking
    near `omega/T = 59`. At 59 it exceeds the `1e-5` limit **on every
    build**.
  - Builds move the node value by only a few percent; B4, with one OpenBLAS
    thread, gives `9.40e-6`.
- **Pathological sensitivity at that node.** Relative `eps`-level
  perturbations of the stored regular solution change the maximum by up to
  `2.8e-7` at 60 and `7e-7` at 59, about `10^9` times the perturbation. This
  is consistent with the few-percent build scatter.
- **The regular-factor equation, evaluated independently on the same `2N`
  grid, is satisfied to `6.5e-8` (Mac) and `8.0e-8` (Linux) everywhere**,
  including `1.3e-8` at the spike node. It agrees with the A-form wherever the
  error is genuine (degree 384: both `3.9e-6`; degree 192: both `0.23`).
- The mechanism behind the single-node cancellation is **not established** in
  this batch.

Adverse controls (B1; B3 agrees to about 1e-10):

| Control | A-form | Regular form |
| --- | ---: | ---: |
| Reference (60/640) | `1.0e-5` | `6.5e-8` |
| Conjugated ingoing exponent | `0.999` | `0.997` |
| Frequency squared times 1.01 | `0.163` | `2.5e-4` |
| Degree 192 | `0.226` | `0.226` |
| Absolute `1e-6` bump in the bulk | `0.29` | `0.29` |
| Relative `1e-6` bump near the UV end (`u ~ 0.02`) | `3.7e-4` at the spike node; **`8.8e-6` elsewhere** | `4.7e-7` |
| Relative `1e-4` bump near the UV end | `3.4e-2` at the spike node; `8.9e-4` elsewhere | `4.6e-5` |

**Caution: simply switching to the regular form at the same `1e-5` ceiling
would weaken the check.** Away from the spike node, the A-form is about 19
times more sensitive to genuine near-UV perturbations. Any regular-form
ceiling would have to be sensitivity-matched rather than kept at `1e-5`.

In the bulk the field is about `1e-16` on this low-temperature background. A
relative perturbation there is therefore invisible to both forms. (The plan's
mid-element relative bump was replaced by the two near-UV and bulk controls
above; see deviations.)

This benchmark's headline results are not near the limit. The exact normal
conductivity and the near-critical `C_2 = 24` responses have ratios of at
most `0.11`. The failing response belongs to the provenance-only Figure 2
set.

## 3. Soft-wall spectral refinement

- Eigenvalue condition numbers are `kappa = 1.04` on every degree and build.
- `||H||_2` grows from `1.0e3` (degree 24) to `6.4e5` (degree 120).
- Floor estimate: `eps ||H||_2 kappa / |lambda|` rises from `5.8e-14` to
  `3.6e-11`.

| Degree | Max relative error (range over B1 to B6) | Error / floor (range) |
| ---: | --- | --- |
| 24 | `2.1e-5` | `1.4e9` |
| 32 | `1.7e-9` | `3.6e4` |
| 40 | `2.7e-13` to `2.8e-13` | `2.3` to `2.4` |
| 48 to 120 | `5.6e-15` to `1.7e-13` | **`0.001` to `0.036`** |

| Adverse control | Error / floor |
| --- | --- |
| Coarse degrees 24 and 32 | `1.4e9` and `3.6e4` |
| `z_max = 4/kappa` (degrees 48 to 64) | `1.2e10` to `3.8e10` (error `5.2e-2`) |
| `z_max = 6/kappa` | `2.0e5` to `6.3e5` (error `4.1e-7`) |
| Swapped eigenvalues | error `1.0`, fails the spectrum tolerance |
| Non-finite eigenvalue | flagged |

Findings:
- From degree 48 the errors form a plateau at 0.1% to 3.6% of the
  first-order floor estimate on every build. The estimate is conservative by
  one to three orders of magnitude.
- Every adverse control lies at least **`2e5`** times above it, a separation of
  about seven orders of magnitude.
- Degree 40 is still converging (ratio about 2.3), where the existing
  strictly-decreasing criterion applies.

## 4. What is and is not established

**Established on these builds:**
- **GN:** the collocation failure is where the nonlinear solve stops, and it
  depends on the build. It is not evaluation rounding. The `1e-9` constant
  both triggers the polish and sets the acceptance limit.
- **Optical:** the failure is a reproducible single-node A-form cancellation.
  ω/T = 59 would fail everywhere. The independently evaluated regular-factor
  equation holds to about `8e-8`.
- **Soft-wall:** the refinement failures are an error plateau at the rounding
  floor, cleanly separated from all adverse cases.

**Not established:**
- the mechanism of the optical single-node cancellation;
- whether an amended rule holds on the reserved confirmation cases;
- behaviour on other NumPy/SciPy versions or other platforms.

## 5. Candidate Batch 2b directions (for owner decision; none approved)

The exact criteria below are candidates for Codex review and owner approval.
Each would be frozen before running the reserved confirmation cases.

- **Soft-wall (candidate S-A).** Pass if either:
  - (i) the current strictly decreasing error, with final error `<= 1e-8`; or
  - (ii) all three errors are `<=` their floor estimates
    `eps ||H||_2 kappa_j / |lambda_j|` and the final error is `<= 1e-8`.

  The default spectrum tolerance is unchanged. Evidence: plateau ratio at most
  `0.036`; adverse ratios at least `2e5`.
- **GN (candidate G-A).**
  - Keep the polish trigger at `1e-9`, so the solver route and results are
    unchanged.
  - Set collocation acceptance to `1e-8`, one tenth of the `1e-7` oversampled
    continuum limit, so the algebraic solve stays an order below the checked
    discretization error.
  - The worst observed value, `1.716e-9`, would then pass with a 5.8x margin.
  - Every plan adverse control stays detected. Collocation-only detection
    moves from about `1e-12` to about `1e-11` bump amplitude.

  **Alternative G-B:** make the polish stop on the residual rather than on the
  step size. This changes solver output on every build, needs full
  requalification, and its success is not demonstrated.
- **Optical (candidate O-A).** Evaluate the independent equation in the
  regular-factor form with a **sensitivity-matched** ceiling. `1e-6` on the
  target set would give a 12x margin over the observed maximum of `8.0e-8`.
  Its detection of near-UV relative perturbations (about `2e-6`) would then be
  within 2x of the A-form's away from the spike node (about `1.1e-6`).

  **Alternatives:** O-B, investigate the single-node mechanism first; O-C,
  retain the current check and record the ω/T = 59 fragility.

  Given the unexplained mechanism, **Claude's recommendation for optical is
  O-B before any amendment**. For soft-wall and GN, S-A and G-A are
  recommended for confirmation.

## 6. Deviations from the frozen plan (disclosed)

1. **Optical adverse control, correction 1 of 3.** The mid-element relative
   bump was invisible because `|a|` is about `1e-16` there. It was replaced by
   a relative bump near the UV end and an absolute bump in the bulk.
2. **GN supplementary controls.** Bumps of `1e-10` and `1e-11` were added after
   the first run to probe the band between the two limits. They are labelled
   in the evidence.
3. **GN adverse base profile.** The base is degree 80, where production does
   not apply the oversampled gate. This is noted above.
4. **Extra build.** B6, the GitHub macOS runner, came from the planned
   dispatch. It was not in the plan.
5. **Small soft-wall differences between B1 and B6** (for example `1.9e-14`
   against `3.4e-14` at degree 48). Both are Accelerate on arm64 and differ by
   CPU generation. They do not change any conclusion.

No stopping condition was triggered.
