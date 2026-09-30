# Gate calibration plan (Batch 2a), September 2026

- **Status:** frozen before execution. AI-assisted (Claude); owner-approved scope
  (Batch 2a); independent review by Codex after completion.
- **Scope:** diagnostics, calibration, adverse controls, tests and a report for
  three platform-sensitive acceptance gates. **No production solver, gate,
  threshold, record or scientific outcome changes.** Any amendment (Batch 2b)
  returns separately, with exact criteria, for owner approval.
- **Outcome is open.** The evidence may support improving how a residual is
  evaluated, amending a gate, or keeping it unchanged. Loosening is not
  presumed.

## 1. Gates and prior observations

| Gate | Definition | Prior observation (calibration data, already seen) |
| --- | --- | --- |
| G: Gubser--Nellore `collocation-residual` | Max over all solved profiles of `max_i |R_i|`, where each equation is already normalized as `sum(terms) / (1 + sum |terms|)`. The limit is `1e-9`, the same constant that triggers the least-squares polish. | Accelerate fails on one profile: `qcd-like`, degree 150, `x_h = 1.23`, which was polished and ended at `1.716e-9`. On all builds, about 10 to 15 profiles lie between `5e-10` and `1e-9`. |
| O: HHH optical `optical-response-numerics` | Max over normal, near-critical and provenance-only Figure 2 responses of a normalized gate ratio. It is driven by the independent A-form equation residual on the `2N` check grid. The target limit is `1e-5`. | Only the Figure 2 response at `omega/T = 60` (degree 640) is near the limit, at `9.4e-6` to `1.0e-5` on every build. Its neighbours at 50 and 70 are `8.7e-7` and `6.5e-7`. The spike is reproducible, and builds move it by a few percent. |
| S: soft-wall `spectral-degree-refinement` | Strictly decreasing analytic error across degrees `N-16`, `N-8`, `N`, with a final error `<= 1e-8`. | It fails for `N >= 56`, where all errors are about `1e-14`. |

## 2. Builds (calibration)

| ID | Build |
| --- | --- |
| B1 | macOS arm64, NumPy 2.4.6 / SciPy 1.17.1, `macosx_14_0` wheels (Accelerate), default threads |
| B2 | B1 with `VECLIB_MAXIMUM_THREADS=1` |
| B3 | macOS arm64, same versions, `macosx_11_0` / `macosx_12_0` wheels (OpenBLAS), default threads |
| B4 | B3 with `OPENBLAS_NUM_THREADS=1` |
| B5 | Linux x86_64, CI `ubuntu-latest`, same versions (OpenBLAS), via manual workflow dispatch |

Every output records the provenance fields added in Version 0.7 maintenance:
source digest, commit, backends, `long double` epsilon and thread variables.

## 3. Case matrix (calibration)

### G: Gubser--Nellore

- **Profiles:** reproduce the production verification continuation branches.
  These are `qcd-like` on `linspace(0.20, 1.25, 106)` at degrees `(80, 120, 150)`
  and `cosh-calibration` on `geomspace(0.10, 35.5, 100)` at `(40, 60, 80)`.
- **Detailed cases:** G1 `qcd-like`/150/`x_h=1.23`; G2 `qcd-like`/80/`x_h=1.04`;
  G3 `qcd-like`/150/`x_h=1.10`; G4 the worst `cosh-calibration` profile.
- **Measured per case and build:**
  1. the final residual, polish applied/success/evaluations, and root residual
     before polish;
  2. the per-node residual `R_i` with equation and `u_i`;
  3. an a-priori rounding bound for evaluating `R_i`. It uses the standard
     dot-product bound `gamma_n |D| |x|` for every derivative product, plus the
     term magnitudes, with the same normalization as the production residual;
  4. a 50-digit re-evaluation `R_i^hp` of the same stored double solution. It
     uses the same double derivative matrices converted exactly, so it isolates
     the evaluation error `R_i - R_i^hp` from the residual of the stored vector
     itself;
  5. the root-residual distribution of all profiles, from existing records.

  Items 3 and 4 are diagnostics. Neither alone proves the residual is rounding
  limited.

### O: HHH optical

- **Case:** reproduce the production Figure 2 provenance responses on the
  conditioned low-temperature background at degree 640. O1 is
  `omega/T = 60`; O2 is `omega/T = 50` and `70` as contrasts. A diagnostic fine
  scan uses `omega/T = 58, 59, 61, 62` at degree 640.
- **Degree dependence:** `omega/T = 60` at degrees 384, 512 and 640.
- **Measured:**
  1. the production residual and its location, captured with a pass-through
     wrapper around the production residual function (production behaviour
     unchanged);
  2. the term decomposition at the maximum;
  3. an independently evaluated **regular-factor** equation residual on the
     same `2N` grid, with analytically combined coefficients, from the
     interpolated `a(u)`;
  4. an empirical evaluation-rounding level, from relative `eps` perturbations
     of the stored `a` values (8 random draws, fixed seed);
  5. the existing Riccati/DOP853 route as a cross-check only.

### S: soft-wall

- **Case:** degrees 24 to 120 in steps of 8, `kappa = 1 GeV`, default `z_max`,
  four modes.
- **Measured:** relative errors; the eigenvalue condition numbers
  `kappa_j = ||y_j|| ||x_j|| / |y_j^H x_j|`, from separate left and right
  eigenvectors; `||H||_2`; and the first-order relative floor estimate
  `eps ||H||_2 kappa_j / |lambda_j|`.

## 4. Adverse controls (run on B1 and B3)

For each control, record which existing checks and which candidate
diagnostics detect it.

- **G:** degree 24 (under-resolved); the stored `f` plus a localized bump of
  amplitude `1e-6` and `1e-8`; the horizon condition violated by `1e-6`; the
  `qcd-like` quadratic potential coefficient scaled by 1.01 in the residual.
- **O:** conjugated ingoing exponent in the field reconstruction; frequency
  squared scaled by 1.01; under-resolution (degree 192 at `omega/T = 60`); a
  localized `1e-6` perturbation of the stored `a` values.
- **S:** degrees 24 and 32; `z_max = 4/kappa` and `6/kappa`; two eigenvalues
  swapped; a non-finite eigenvalue.

## 5. Reserved confirmation cases (not run in Batch 2a)

These are frozen now and held out for confirming any Batch 2b rule.

- **G:** `qcd-like` degrees 100 and 140 and `cosh-calibration` degree 70, along
  the verification grids.
- **O:** `omega/T = 55, 65, 75` at degree 640, and degree 576 at `omega/T = 60`.
- **S:** degrees 60, 76 and 92; `kappa = 0.5` and `2 GeV`.
- **Builds:**
  - Linux with the newest NumPy/SciPy release older than 2.4/1.17 that
    supports Python 3.11, pinned exactly at dispatch;
  - a macOS x86_64 runner if GitHub offers one, otherwise omitted and
    reported.
- **Commands:** the calibration tool's subcommands, with the case flags above,
  run by manual dispatch.

## 6. Budget and stopping conditions

- **Local compute:** at most 90 minutes of wall time in total. **CI:** at most
  three manual dispatches.
- **Development:** at most three correction attempts per diagnostic before
  returning.
- **Stop and return early if:**
  - a diagnostic would require changing production code;
  - the high-precision GN evaluator fails its formula-identity fixture
    (agreement with production evaluation for non-solution inputs) after three
    corrections;
  - any production record, test outcome or verdict changes;
  - the budget is exhausted. Partial evidence is then returned, labelled as
    partial.

Evidence contradicting the rounding hypothesis is an outcome to report, not a
stop.

## 7. Deliverables

- `tools/gate_calibration.py`: read-only diagnostics with JSON output.
- `tests/test_gate_calibration.py`: fast fixture tests only.
- An optional `calibration` input on the Gate telemetry workflow's manual
  dispatch for B5.
- `docs/numerics/gate-calibration-2026-09-report.md`, with evidence JSON under
  `docs/generated/gate-calibration/`.
- A corrected known-issue note if the evidence changes its interpretation. For
  example, the optical spike at `omega/T = 60` is not a generic floor.
