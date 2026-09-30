# Soft-wall spectral refinement: candidate rule S-A (frozen before confirmation)

- **Status:** frozen before any confirmation run. AI-assisted (Claude). This
  document authorizes the confirmation runs only. **It does not change the
  production gate.** A production change returns separately for owner
  approval, with the confirmation results.
- **Evidence basis:**
  [Batch 2a report](gate-calibration-2026-09-report.md), Section 3. The
  calibration used degrees 24 to 120 in steps of 8 at `kappa = 1 GeV`, on six
  build configurations.
- **Scope:** the opt-in `--method spectral` route of `soft-wall-vector` only.
  The default finite-difference route, the analytic-spectrum tolerance
  (`2e-4`) and the spectral accuracy requirement (`1e-8`) are unchanged.

## 1. Current rule

For spectral degree `N`, compute the relative analytic errors
`e_d = max_j |lambda_{d,j} - m_j^2| / m_j^2` at `d = N-16, N-8, N` for the
first four modes. The check passes when both hold:

- **(A)** `e_{N-16} > e_{N-8} > e_N` (strictly decreasing), and
- **(B)** `e_N <= 1e-8`.

It fails from `N = 56` upward, where all three errors are about `1e-14` and
their order is arbitrary.

## 2. Candidate rule S-A

The check passes when **(B)** holds and **either** (A) **or** (P) holds.

**(P) plateau branch.** All of the following hold at the two finest degrees
`d in {N-8, N}` and every mode `j`. The coarsest level `N-16` may still be
converging, which is exactly the situation at `N = 56`, where degree 40 is
not yet on the plateau.

1. **Finite quantities.** `lambda_{d,j}`, `e_{d,j}` and `s_{d,j}` are finite.
2. **Consistent matching.** Let `mu_{d,j}` be the eigenvalue from
   `scipy.linalg.eig(H_d, left=True, right=True)` nearest to the production
   eigenvalue `lambda_{d,j}`, with left and right eigenvectors `y` and `x`.
   The two solves must agree to first order:
   `|mu_{d,j} - lambda_{d,j}| / |lambda_{d,j}| <= s_{d,j}`.
3. **Perturbation scale.** Define
   `s_{d,j} = eps ||H_d||_2 kappa_{d,j} / |lambda_{d,j}|`, where
   `kappa_{d,j} = ||x|| ||y|| / |y^H x|`, `eps = 2^-52`, and `H_d` is the
   production collocation operator at degree `d`.
4. **Per-mode plateau.** `e_{d,j} <= s_{d,j}`.
5. **Cross-degree stability.** For every mode,
   `|lambda_{N,j} - lambda_{N-8,j}| / |lambda_{N,j}| <= s_{N,j} + s_{N-8,j}`.
   Here this is implied by item 4 through the triangle inequality, so it is
   recorded as an explicit stability statement. It is not counted as
   independent evidence.

**Terminology.** `s_{d,j}` is a first-order perturbation scale for a simple
eigenvalue, not a proved lower error floor. An error at or below it is
consistent with rounding dominance; it does not prove it. The constant in
item 4 is 1. In calibration, plateau cases had `e/s <= 0.036`. Every control
that the complete existing contract rejects on accuracy grounds had
`e/s >= 2.0e5`.

**Fixed items.** The analytic comparison is the only accuracy reference in
this benchmark. S-A does not add an independent numerical method.

**Pre-freeze correction (disclosed).** The first draft of (P) required all
three degrees to lie on the plateau. Evaluated on the already-seen Batch 2a
calibration data with the `soft-wall-sa` diagnostic (builds B1 and B3), that
draft would still fail `N = 56`, whose coarsest level (degree 40) is still
converging (`e/s` about 2.3). The rule was corrected to the two finest
degrees before any reserved case ran. On the same seen data, the constants
of 1 have margin:

- `|mu - lambda| / |lambda|` reaches at most `0.003 s`;
- plateau `e/s` reaches at most `0.034`;
- cross-degree stability reaches at most `0.023` of its allowance.

## 3. Required behaviour on calibration controls (regression, already seen)

These controls come from Batch 2a, so they are regression checks, not
confirmation.

| Case | Required S-A verdict | Reason |
| --- | --- | --- |
| `N = 24` (8/16/24) | FAIL | (B) fails: `e_N = 2.1e-5` |
| `N = 32` (16/24/32) | PASS | (A) and (B) hold, so it is accepted by the unchanged convergence branch |
| `N = 40` (24/32/40) | PASS | (A) and (B) hold |
| `N = 48` (32/40/48) | PASS | (A) and (B) hold |
| `N = 56` to `120` in steps of 8 | PASS | (B) holds, and (P) holds; (A) holds on some builds |
| `z_max = 4/kappa`, `N = 48, 56, 64` | FAIL | (B) fails, and the spectrum tolerance fails |
| `z_max = 6/kappa`, `N = 48, 56, 64` | FAIL | (B) fails: `e_N = 4.1e-7` |
| Two eigenvalues swapped (synthetic) | FAIL | (P) item 4 fails (error 1) and the spectrum tolerance fails |
| A non-finite eigenvalue (synthetic) | FAIL | (P) item 1 fails |

## 4. Reserved confirmation (not yet run)

**Cases.** `N in {60, 76, 92}` with `kappa in {0.5, 2.0} GeV` and default
`z_max = 10/kappa`. These were frozen in the Batch 2a plan. Their refinement
triples (44/52/60, 60/68/76, 76/84/92) use degrees absent from calibration.

**Amendment before any run: add `kappa = 0.7 GeV`.** `kappa = 0.5` and `2`
are powers of two, and scaling by a power of two is exact in binary64. They
therefore reproduce `kappa = 1` bit for bit and test nothing new. A
non-dyadic `kappa` does not share that property.

**Builds:**
- **R1:** macOS arm64, Accelerate wheels (NumPy 2.4.6 / SciPy 1.17.1), local.
- **R2:** macOS arm64, OpenBLAS wheels (same versions), local.
- **R3:** Linux x86_64 with NumPy 2.3.5 / SciPy 1.16.3, the newest releases
  below 2.4 and 1.17 with Python 3.11 wheels. CI dispatch.
- **R4:** Linux x86_64 with the default CI dependencies. CI dispatch.
- **R5:** a macOS x86_64 runner (`macos-15-intel`), if GitHub provides it.
  Otherwise it is omitted and reported.

**Success criteria (all required):**
1. On every reserved case and every available build, S-A passes, the
   analytic-spectrum tolerance passes, and (B) holds.
2. On every build, the Section 3 regression table is reproduced exactly.

**On failure:** the rule is **not tuned**. The failure is reported as a
confirmation failure, and the decision returns to the owner.

## 5. Budget and outputs

- **Budget:** at most 20 minutes of local wall time, and at most two CI
  dispatches.
- **Tool:** a `soft-wall-sa` subcommand of `tools/gate_calibration.py`
  evaluates the current rule and S-A side by side. It uses the production
  eigenvalues and records its own hash, the plan hash and wheel tags.
  Production code is unchanged.
- **Outputs:**
  - a confirmation report,
    `docs/numerics/soft-wall-refinement-sa-confirmation.md`, with evidence
    JSON under `docs/generated/soft-wall-sa/`;
  - if confirmation succeeds, a separate proposal for the exact production
    change, including its tests, model-card note and contract version.
