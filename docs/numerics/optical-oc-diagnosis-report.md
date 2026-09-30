# Optical discrete-system diagnosis (O-C): report

- **Status:** completed under the [frozen plan](optical-oc-diagnosis-plan.md)
  (commit `ffcaedb`, SHA-256 `243428fc…6b7b`). AI-assisted (Claude);
  awaiting Codex review. **Diagnosis only.** No production solver, gate,
  threshold, record or verdict changed. On Accelerate the optical verifier's
  FAIL remains the recorded result.
- **Evidence:** [`B1-optical-oc.json`](../generated/optical-oc/B1-optical-oc.json)
  (Accelerate) and [`B3-optical-oc.json`](../generated/optical-oc/B3-optical-oc.json)
  (OpenBLAS wheels), from `python tools/gate_calibration.py optical-oc
  --build-label B1|B3`.
  - Both runs record plan commit `ffcaedb` with `src/` unmodified, the plan
    hash above, and tool SHA-256 `d93ea131…`. That is the committed tool in
    this change.
- **Local arrays (outside Git).** Eight `.npz` files, 131 MB in total, are in
  `output/optical-oc-artifacts/` in the checkout, which Git ignores. They were
  neither uploaded nor deleted.
  - The evidence JSON records each file's name, size and SHA-256, and the
    SHA-256, dtype and shape of every array inside.
  - Each file holds the complete system of one case: the stored solution,
    nodes, coefficient inputs, fixed boundary inputs, right-hand sides, D1,
    D2, the assembled and equilibrated operators, and the row norms.
- **Scientific boundary:** a statement about the numerics of one benchmark
  check in the sampled cases. It is not a physical result, and it does not
  reassess the conductivity.

## Answer

At degree 640 the spike residual is **`mixed`** under the plan's rules, on
all four sampled frequencies and both builds. Its three parts are:

| Part | Share of the spike residual |
| --- | --- |
| **Operator rounding** | **57.5–59.4%**. The named step is **differentiation-matrix construction**. |
| **Discretization** (high-precision solution of the exact discrete system) | 38.9–40.5% |
| **Linear solve** | 0.07–3.0% |

At degree 512 the spike is **`discretization-dominated`** (95.6–97.1%).

**Established:**
- The collocation-node defects found by O-B come from the double-precision
  construction of the differentiation matrix.
- The solve's backward error is negligible.

**Unresolved:**
- the origin of the discretization part, which is independent of frequency
  to four digits;
- the mechanism inside the matrix construction.

## 1. Execution and resource use

**Fixtures.** Every run first executes F1–F5 of the plan. Run 1 on B1
stopped at the fixture, as designed, before any production case. Two
fixtures had failed, and each received one correction (Section 5, items 1
and 2). The rerun and the B3 run passed every fixture:

| Fixture | Result |
| --- | --- |
| F1 | exact-polynomial derivatives at degree 640 to `9.8e-40` |
| F2 | bit-for-bit reconstruction |
| F3 | worst ratio to bound `0.048`; sum identity `2e-66` |
| F4 | all six approximations qualified in 2 iterations |
| F5 | known solution recovered to `1.7e-35` |

**Every production case:**
- The reconstructed equilibrated operator, right-hand side, stored solution
  and nodes equal production's bit for bit.
- The F3 rounding bounds hold, with a worst ratio of `0.055`.
- All six high-precision approximations qualify within 2 iterations:
  backward error at most `4e-34`, and attribution uncertainty at most
  `4.9e-12` of `|R_s|`.

**Diagnostic execution** (ceiling 30 min):

| Run | Wall time |
| --- | ---: |
| O-C unit tests, two runs | `1 s` |
| B1 run 1 (stopped at the fixture) | `2 s` |
| F3 failure localization (fixture case) | `1 s` |
| B1 run 2 | `55 s` |
| B3 | `43 s` |
| **Total** | **`102 s`** |

- **Other resources:** no paid compute, installations or CI-dispatched
  scientific runs. Reserved cases were not run.
- **Active work:** well under the 4-hour ceiling. It covered implementation,
  testing and this report, and is stated in the handoff.

## 2. Spike attribution

**Terminology:**
- `R_s` is the stored solution's physical-node residual at check index 3
  (`u = 2.355e-5` at degree 640 and `3.118e-5` at degree 512).
- The shares are `|component| / |R_s|`. The three components are complex
  and sum to `R_s` exactly: the computed sum identity is `0` to 50 digits.

| Case, build | `\|R_s\|` | Solve | Operator rounding | Discretization | Outcome | Named step |
| --- | --- | ---: | ---: | ---: | --- | --- |
| 60/640, B1 | `1.059e-4` | 3.0% | 58.1% | 38.9% | mixed | D-construction |
| 59/640, B1 | `1.019e-4` | 0.07% | 59.4% | 40.5% | mixed | D-construction |
| 50/640, B1 | `1.038e-4` | 1.1% | 59.2% | 39.7% | mixed | D-construction |
| 70/640, B1 | `1.053e-4` | 1.8% | 59.0% | 39.2% | mixed | D-construction |
| 60/640, B3 | `1.034e-4` | 1.8% | 58.3% | 39.9% | mixed | D-construction |
| 59/640, B3 | `1.039e-4` | 2.8% | 57.5% | 39.7% | mixed | D-construction |
| 60/512, B1 | `6.20e-5` | 0.17% | 4.2% | 95.6% | discretization-dominated | cancellation among steps |
| 60/512, B3 | `6.11e-5` | 0.12% | 2.8% | 97.1% | discretization-dominated | cancellation among steps |

**Within the operator rounding at degree 640** (fractions of the operator
part):
- D-construction: `1.04`–`1.09`;
- `D @ D` product: `0.066`–`0.080`;
- assembly: `0.006`–`0.020`;
- equilibration: `0.0004`–`0.015`;
- coefficients: below `1e-4`.

These are complex parts, so fractions above one are offset by others. At
degree 512 the steps largely cancel, and no step is named.

**Why the outcome is `mixed`, not `operator-rounding-dominated`.** The
operator share is below `0.8`, and the discretization share exceeds `0.25`.

**Discretization component at the spike** (the exact discrete system's
residual): `4.1250e-5`–`4.1254e-5` at every degree-640 case on both builds,
and `5.9300e-5` at degree 512.
- On collocation nodes the same solution's residual is below `2e-26`, as it
  must be.
- Between nodes, at check indices 1, 3 and 5, it is `1.169e-4`, `4.125e-5`
  and `2.604e-5`, again at every frequency.

**Conventions and precision.**
- The O-B local-node value differs from the physical-node `R_s` by
  `9e-5`–`1.6e-4` relative, confirming O-B's caveat that the difference is
  negligible.
- The 70-digit repetition (60/640, B1) changes `R_s` by `9e-37` and the
  discretization residual by `1e-34` relative.

## 3. Collocation-row decomposition (supporting evidence)

The stored solution's 50-digit residual in row 1 (collocation node 1) is
`2.68e-4`–`2.91e-4` at degree 640 on both builds, and in row 2 it is
`2.18e-5`–`2.60e-5`.
- **D-construction** accounts for `0.98`–`1.06` of row 1 and `0.95`–`1.13`
  of row 2 (complex parts).
- **The solve residual** is at most `1.2e-5` in those rows.

The O-B collocation-node defects are therefore D-construction rounding.

Over all rows, normalized by the row scale:
- D-construction reaches `1.5e-12`–`2.0e-12` at degree 640 (`7.8e-13` at
  512);
- the solve reaches `1.4e-16`–`2.5e-16` (backward-stable);
- the total reaches at most `2.2e-12`.

## 4. Findings

**Established in the sampled cases:**
1. **The solve is not the cause.** Refining to the exact solution of the
   production system removes at most 3% of the spike residual. A solver
   improvement alone would not address it.
2. **Differentiation-matrix construction is the largest single cause at
   degree 640.** It gives about 59% of the spike and essentially all of the
   UV-end collocation-node defect. It is the matrix production builds, from
   `chebyshev_lobatto_grid`'s double cosines and negative-sum diagonal,
   compared with the exact differentiation matrix of the stored nodes.
3. **About 40% remains for the exact discrete system at degree 640.** At
   degree 512 it is almost all of the spike, so the operator-rounding
   component is small there.
4. **Build independence.** The shares agree between Accelerate and OpenBLAS
   within about 2 percentage points. The discretization residual agrees to
   five digits.

**Unresolved:**
- **Origin of the discretization part.** It is the same at ω/T = 50, 59,
  60 and 70 to `1e-4` relative. This suggests a frequency-independent source,
  such as the C¹ `solve_bvp` spline background entering `2 psi^2/(u^2 F)`,
  rather than under-resolution of the frequency-dependent field. O-C does not
  test this.
- **Mechanism within the construction step.** The step combines cosine
  differences, the negative-sum diagonal, and node-position consistency.
  O-C does not separate them.
- Frequencies and degrees beyond the sampled cases.

## 5. Deviations from the frozen plan

1. **F3 coefficient bound (fixture correction 1 of 3).**
   - The frozen bound `64 eps (C1 |D1 f| + W |f|)` omitted how rounding of
     `F = 1 - u^3` is amplified by `1/F` near the horizon.
   - Run 1 exceeded it by 5% on the row nearest the horizon. Across the last
     three rows the ratio scaled as `1/F`: `1.05`, `0.25` and `0.13` at `F =`
     `1.8e-3`, `7.2e-3` and `1.6e-2`.
   - The bound now includes the derived factor `(1 + 1/F)`, which gives a
     worst ratio of `0.0045`, in line with the other steps.
   - The correction comes from the analysis, not from tuning. It is also a
     check on the implementation only, not a scientific threshold.
2. **F4 minimum iterations (fixture correction 1 of 3).**
   - With a single refinement update, the "last change" `e_T` is the whole
     correction, not a bound on the remaining error. Three approximations had
     converged in one update and so failed the uncertainty criterion.
   - At least two updates are now made, so that `e_T` bounds the remaining
     error as the plan intends. This leaves the thresholds unchanged.
3. **Step sign convention.** Step `k` contributes `R(x̃_chain[k+1]) -
   R(x̃_chain[k])`, so that the steps sum to `Δ_op = R(x̃_eq) - R(x̃_exact)`.
4. **Exit status not captured for B1 run 1.** A shell error lost it, and its
   time comes from file timestamps. Its output (the fixture stop) is not
   part of the evidence; the saved B1 evidence is run 2.
5. **Fixture reruns.** Each run executes F1–F5 again, so B3 repeats the
   fixture.

## 6. Is a production repair justified?

**Supported as the leading candidate for a separately planned change; not
justified for adoption by this evidence alone:**
- A repair of the **differentiation-matrix construction** targets the
  largest share: about 59% of the spike and essentially all of the UV-end
  collocation-node defect.
- **Projection, not a result.** Suppose a repaired construction behaved like
  the exact matrix. The spike would fall to the discretization part,
  `4.13e-5` raw. Normalized, that is about `3.9e-6` at ω/T = 60 and `8.3e-6`
  at 59, against `1e-5`. The margin at 59 would be under 20%, and the
  remaining part is unexplained.
- **Platform-wide.** `chebyshev_lobatto_grid` is shared by eight benchmark
  modules, including this one:
  - Gubser--Nellore;
  - Gubser--Rocha;
  - both DeWolfe--Gubser--Rosen modules;
  - hard-wall chiral;
  - hard-wall vector;
  - soft-wall;
  - the optical benchmark.

  A change would need its own prospective plan, with regression and gate
  evidence across all of them.
- **Not justified:**
  - a solver improvement as the remedy, since it addresses at most 3%;
  - widening the threshold;
  - excluding nodes.

Any repair, and any follow-up on the discretization part, needs a new owner
decision.
