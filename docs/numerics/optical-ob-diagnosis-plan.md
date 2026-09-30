# Optical single-node diagnosis (O-B): plan, frozen before execution

- **Status:** frozen before any O-B run. AI-assisted (Claude); owner-approved
  as O-B; Codex review after completion. **Diagnosis only: no production
  solver, gate, threshold, record or verdict changes.**
- **Background:** [Batch 2a report](gate-calibration-2026-09-report.md),
  Section 2. On every build, the A-form independent equation residual of the
  HHH optical benchmark peaks at one check node, `u = 2.355e-5`. This is the
  first checked node at the UV end of the bulk element `[1e-5, 1]` at degree
  640. The peak varies sharply with frequency; `omega/T = 59` exceeds the
  `1e-5` limit on every build. For real frequency `R_A = (1-u)^s R_a` with
  `|(1-u)^s| = 1`, so the two forms' raw residuals have equal magnitude.

## 1. Question

Is the value at that node:
- **(a)** an artifact of evaluating the interpolant's derivatives or the
  residual in binary64;
- **(b)** a genuine property of the stored discrete solution, meaning its
  interpolating polynomial does not satisfy the equation there; or
- **(c)** sensitivity to the stored values, that is, to the solve?

## 2. Cases (all previously examined; no reserved case is used)

- `omega/T = 50, 58, 59, 60, 61, 62, 70` at degree 640, and `omega/T = 60` at
  degree 512, on the conditioned low-temperature background of the Figure 2
  set.
- **Builds:** B1 (macOS arm64, Accelerate) for all measurements; B3 (macOS
  arm64, OpenBLAS wheels) for measurements 1 and 2.
- **Still reserved and not run:** `omega/T = 55, 65, 75` and degree 576.

## 3. Measurements

1. **Raw numerators and common normalization.** At every check node, record
   the complex numerators `R_A` and `R_a`, both production-style
   denominators, and the numerical identity defect
   `|R_A - (1-u)^s R_a| / |R_A|`. Compare both forms under one common
   denominator, the A-form's.
2. **Exact polynomial at the spike.** Take the stored double nodes and values
   of the regular factor, converted exactly. Compute the interpolating
   polynomial's value and first and second derivatives at the spike node and
   its four neighbours, in 50-digit Decimal arithmetic.
   - Use barycentric weights recomputed from the stored nodes, and the
     derivative identities
     `p' = -sum w_j (f_j - p)/(x - x_j)^2 / D` and
     `p'' = 2 sum w_j [p'/(x - x_j)^2 + (f_j - p)/(x - x_j)^3] / D`, with
     `D = sum w_j/(x - x_j)`.
   - Evaluate `|R_a|` there at 50 digits, with the same double coefficient
     inputs (background scalar, frequency, coordinates) converted exactly.
   - Compare with the double values: interpolant value and derivatives, and
     the residual.
3. **Input sensitivity versus evaluation error.** Report the existing
   `eps`-perturbation change (input sensitivity) separately from measurement
   2's difference between 50-digit and double evaluation at fixed inputs
   (evaluation error).
4. **Local structure.** Report the normalized A-form residual at the first 12
   checked nodes for each frequency, and the positions of the nearest
   collocation nodes.

## 4. Prospective interpretation rules

- **Evaluation artifact, (a):** the 50-digit `|R_a|` at the spike is at least
  10x smaller than the double value, and the double derivatives differ from
  the 50-digit ones by enough to account for the difference.
- **Genuine polynomial defect, (b):** the 50-digit `|R_a|` agrees with the
  double value to within a factor of 2.
- **Unresolved:** anything between these, reported as such.

Evidence for (c) is reported separately. No outcome changes a gate. Any
amendment, or any change to evaluation or resolution, is a separate proposal
for owner approval.

## 5. Budget, stopping and outputs

- **Budget:** at most 20 minutes of local wall time; no CI dispatch.
- **Stop and return if:**
  - production code would need to change;
  - the 50-digit evaluator fails its identity fixture (it must reproduce the
    double interpolant value and derivatives to `1e-10` relative at a
    well-separated point) after three corrections;
  - the budget is exhausted.
- **Outputs:**
  - a new `optical-ob` subcommand of `tools/gate_calibration.py`, with tests;
  - `docs/numerics/optical-ob-diagnosis-report.md`;
  - evidence JSON under `docs/generated/optical-ob/`.
