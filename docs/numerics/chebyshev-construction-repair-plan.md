# Chebyshev differentiation-matrix construction repair: proposed plan

- **Status: PROPOSED.** Batch 3, item 1. Not approved, not frozen, not
  executed. AI-assisted (Claude).
  - The owner approved the Batch 3 order on 1 October 2026.
  - This exact plan needs Codex review, then an owner-approved freeze
    commit, before any production code changes.
- **Scope:** one shared numerical routine, `chebyshev_lobatto_grid`, used by
  eight benchmark modules. Under the
  [compatibility policy](../version-0.5-compatibility-policy.md), numerical
  results may change only through an explicit scientific review; this plan
  is that review. No gate, threshold, tolerance, model physics or release
  changes.

## 1. Why

- **O-C finding.** The [O-C diagnosis](optical-oc-diagnosis-report.md) found
  that the double-precision construction of the differentiation matrix
  causes about 59% of the optical spike residual at degree 640. It also
  causes essentially all of the UV-end collocation-node defect.
- **Same routine elsewhere.** It builds the matrices for Gubser--Nellore,
  Gubser--Rocha, both DeWolfe--Gubser--Rosen modules, hard-wall chiral,
  hard-wall vector, soft-wall and the optical benchmark.
- **GN may be affected too.** GN's platform-sensitive collocation gate may
  share part of this cause. That is untested.

**Current construction** (`src/holoforge/numerics/chebyshev.py`):
1. Nodes `x_k = cos(pi k/N)` in double.
2. `D_ij = (c_i/c_j)(-1)^(i+j) / (x_i - x_j)`, with the differences formed
   by subtracting rounded cosines. These cancel badly near `±1`.
3. The diagonal is the negative row sum.
4. Physical nodes `midpoint + half_width * x` are rounded separately from
   the differences used in D, so D is not exactly the matrix for the stored
   nodes.
5. `D2 = D @ D` is computed through BLAS, so it depends on the build.

## 2. Candidate construction (prospectively defined)

Write `theta_k = pi k / N`. Each candidate below is a variant of the
trigonometric construction C-T; all use steps 1–3.

1. **Physical nodes.** Compute them from half-angles, accurate at both ends:
   - `u_k = lower + width sin^2(theta_k/2)` for `k <= N/2`;
   - `u_k = upper - width sin^2((pi - theta_k)/2)` for `k > N/2`;
   - endpoints exact.
2. **Node differences.** Use the identity
   `u_i - u_j = width sin((theta_i+theta_j)/2) sin((theta_i-theta_j)/2)`.
   The only cancellation left is in the rounding of the stored nodes
   themselves.
3. **First derivative.** `D_ij = (w_j/w_i)/(u_i - u_j)`, with the
   Chebyshev--Lobatto weights `w_j = (-1)^j delta_j`. The diagonal is the
   negative row sum.

| Variant | Second derivative | Extra step |
| --- | --- | --- |
| **C-T1** | `D @ D` | — |
| **C-T2** | explicit elementwise formula `D2_ij = 2 D_ij (D_ii - 1/(u_i - u_j))` for `i != j`, negative-sum diagonal; no BLAS, so deterministic across builds | — |
| **C-T3** | as C-T2 | the "flipping" antisymmetry `D_(N-i)(N-j) = -D_ij` (and symmetry for D2), to halve independent rounding |

This follows Baltensperger and Trummer, *SIAM J. Sci. Comput.* 24, 1465
(2003). The public API, argument checks, node ordering and read-only arrays
are unchanged.

## 3. Stages, measurements and prospective rules

### S0: calibration (development allowance)

Measure the current construction and C-T1–C-T3 against 50-digit exact
matrices, using the O-C `decimal_differentiation_matrices` for the stored
nodes of each construction.
- **Degrees:** 16, 40, 64, 80, 96, 150, 256, 512, 640 and 1024.
- **Intervals:** `[-1,1]`, `[1e-5,1]` (optical), `[0,1]` and `[2,5]`.

Metrics:
- **(a) entrywise error:** the maximum relative error of D and D2 over rows
  0–3 and `N-3..N`;
- **(b) row-scaled derivative error:** `|(D2_exact - D2) f|_i / (|D2||f|)_i`,
  and likewise for D1, for smooth test functions;
- **(c) O-C artifact metric:** the same row-scaled D-construction
  contribution evaluated on the eight preserved O-C stored solutions. These
  are read from `output/optical-oc-artifacts/` and never modified;
- **(d) determinism:** bit-for-bit equality of D and D2 between B1
  (Accelerate) and B3 (OpenBLAS).

S0 fixes no threshold. It may change implementation details of C-T1–C-T3,
but not the rules of S1.

### S1: selection rule, frozen before S0 results are seen

- The candidate is the C-T variant with the smallest worst-case metric (c).
  Ties within a factor of 1.5 go to C-T2 (deterministic).
- **Proceed only if** the selected candidate:
  - improves metric (c) by at least 10× over the current construction, in
    the worst case over rows 1–3;
  - is no worse than the current construction on metric (b) at every degree
    and interval, within a factor of 2.
- **Otherwise stop:** no production change, and report.

### S2: production change and cross-benchmark regression

- **Replace the construction** and add unit tests: exact polynomials,
  agreement with the 50-digit reference at a fixed bound, node accuracy,
  determinism, and the existing API tests.
- **Before and after**, on B1, B3 and Linux CI, run:
  - all eight benchmark verifiers, default configurations;
  - the full test suite;
  - `tools/gate_margins.py`.

Prospective acceptance:

| # | Criterion |
| --- | --- |
| A1 | **No verdict regression.** Any gate that passes before and fails after on the same build is a stop. |
| A2 | **Changes within each benchmark's own numerical uncertainty.** Every reported observable changes by at most its benchmark's documented numerical-error measure (its resolution change, independent-route difference or cutoff change, as recorded in its guide). Any larger change is a stop and is reported. |
| A3 | **Platform-sensitive gates reported, not required to pass:** the optical equation gate and the GN collocation gate, on all three builds. An improvement is expected but is not an acceptance criterion; a worsening is reported. |
| A4 | **Soft-wall** rule v2 and the default finite-difference output behave as before, up to rounding-level eigenvalue changes. |

### S3: confirmation

- Rerun the O-C decomposition at ω/T = 60 and 59, degree 640, on B1 and B3
  with the new construction.
- Prospective expectation: the D-construction step share of the spike is at
  most 10% of its O-C value. Either outcome is reported.
- The discretization part (about 40%) is **not** expected to change. It
  belongs to Batch 3 item 2.

## 4. Records, versioning and compatibility

- **Changelog.** A "Changed" entry states that spectral results in eight
  benchmarks shift at rounding level, and lists the observed maximum change
  per benchmark.
- **Model cards.** They change only if their text describes the
  construction; any pinned hashes are then updated.
- **Historical evidence stays unchanged.** That includes the committed O-B
  and O-C evidence, earlier calibration evidence and the private research
  pins. It is reproducible from its recorded commits. No "legacy
  construction" option is kept, to avoid a second public surface. Codex
  should say if one is wanted.
- **No release** is part of this plan.

## 5. Budget, stopping and outputs

- **Budget:**
  - at most 6 hours of active work;
  - at most 60 cumulative minutes of local execution, including fixtures,
    retries and verifier runs;
  - no paid compute or installations;
  - PR CI and the existing gate telemetry only, with no dispatched
    scientific runs.
- **Stop and return if:**
  - the S1 selection fails;
  - A1 or A2 fails;
  - a fixture fails after three corrections;
  - a budget is exhausted.

  Nothing is merged without Codex review and owner approval.
- **Outputs:**
  - one PR with the frozen plan, the implementation, tests, S0–S3 evidence
    (JSON under `docs/generated/chebyshev-repair/`) and a report;
  - a handoff stating what changed, per-benchmark deltas, the gate
    outcomes, deviations and resource use.

## 6. Questions for Codex review

1. Is C-T2's explicit D2 preferable to `D @ D`, given that it removes a BLAS
   dependence? Or should S1 decide on metric (c) alone, as proposed?
2. Is A2's per-benchmark numerical-uncertainty measure the right acceptance
   scale? For each benchmark, which recorded quantity should it be?
3. Should a legacy construction be kept for reproducing historical records,
   or is the commit pin sufficient?
4. Is anything else in the public or private workspaces sensitive to node
   positions at the ulp level (frozen hashes of outputs, for example)?
