# Soft-wall S-A confirmation report

- **Status:** confirmation of the frozen candidate rule S-A. AI-generated
  (Claude); Codex review pending. **The production gate is unchanged.** Any
  production change returns separately for owner approval (Section 5).
- **Contract:**
  [`soft-wall-refinement-sa-contract.md`](soft-wall-refinement-sa-contract.md),
  frozen at `07ef0a0` (SHA-256 `75e921ea…`) before any reserved case ran.
  Every evidence file records this hash.
- **Tool:** `tools/gate_calibration.py soft-wall-sa`. Every evidence file
  records commit `40c99bc`, unmodified `src/`, tool SHA-256 `9366cee7…` and
  its installed NumPy/SciPy wheel tags.
- **Evidence:** [`docs/generated/soft-wall-sa/`](../generated/soft-wall-sa/),
  with regression and confirmation files for each build.
- **Budget:** 13 s of local wall time out of 20 minutes, and one CI dispatch
  out of two
  ([36689674647](https://github.com/xin-yi6/HoloForge/actions/runs/36689674647)).

## 1. Result: all success criteria met on every build

| Build | Platform | NumPy / SciPy | BLAS (NumPy / SciPy) | Wheel tag (NumPy) | Reserved cases passing S-A | Regression table |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | macOS arm64, local | 2.4.6 / 1.17.1 | accelerate / accelerate | `macosx_14_0_arm64` | 9 / 9 | reproduced |
| R2 | macOS arm64, local | 2.4.6 / 1.17.1 | scipy-openblas 0.3.31 / 0.3.30 | `macosx_11_0_arm64` | 9 / 9 | reproduced |
| R3 | Linux x86_64, CI | **2.3.5 / 1.16.3** | scipy-openblas 0.3.30 / 0.3.29.dev | `manylinux_2_27/2_28_x86_64` | 9 / 9 | reproduced |
| R4 | Linux x86_64, CI | 2.4.6 / 1.17.1 | scipy-openblas 0.3.31 / 0.3.30 | `manylinux_2_27/2_28_x86_64` | 9 / 9 | reproduced |
| R5 | **macOS x86_64** (`macos-15-intel`), CI | 2.4.6 / 1.17.1 | accelerate / accelerate | `macosx_14_0_x86_64` | 9 / 9 | reproduced |

Thread variables were at their defaults on all builds; the recorded
`thread_environment` is empty. Every identity check passed: the tool's
reconstruction of the production refinement errors and verdict matches
production exactly.

## 2. Reserved confirmation cases

Reserved cases are `N in {60, 76, 92}` with `kappa in {0.5, 0.7, 2.0} GeV`,
9 cases per build.

| Quantity over all 45 case-build pairs | Value |
| --- | --- |
| S-A verdict | PASS in all 45 |
| Analytic-spectrum tolerance (`2e-4`) and accuracy (`1e-8`) | pass in all 45 |
| Accepted through the plateau branch | 41 |
| Accepted through the unchanged convergence branch | 4 |
| Current production rule | **fails 41 of 45** |
| Largest `e/s` at the two finest degrees | `0.026` |
| Largest final error `e_N` | `9.8e-14` |

- `kappa = 0.5` and `kappa = 2.0` give **bit-identical** results to each
  other on every build, as the contract predicted: they are exact binary
  scalings. The pre-run addition of `kappa = 0.7` was therefore necessary. Its
  cases pass on every build.
- R3 and R4 give identical values, although they use different NumPy/SciPy
  releases and bundled OpenBLAS versions. That is an observation; no cause is
  attributed.

## 3. Regression controls (seen calibration data)

On every build, the contract's Section 3 table is reproduced:
- `N = 24` fails.
- `N = 32, 40, 48` pass through the convergence branch.
- `N = 56` to `120` pass. The current rule fails 6 to 9 of these 9 plateau
  cases, depending on the build.
- Both cutoff families fail at every tested `N`.
- The synthetic swapped and non-finite controls fail.

## 4. Limits of what this establishes

- The analytic spectrum is the only accuracy reference. S-A adds no
  independent numerical method, and its cross-degree stability condition is
  implied by the per-mode bounds.
- `eps ||H||_2 kappa / |lambda|` is a first-order perturbation scale. Errors
  far below it are consistent with rounding dominance but do not prove it.
- The confirmation covers 9 reserved cases on five builds of one benchmark.
  It says nothing about other benchmarks or other gates.
- The constants (factor 1 for matching and plateau) were chosen before
  confirmation from seen calibration data. That data showed margins of at
  least 29x; confirmation shows margins of at least 38x.

## 5. Proposed production change (not implemented; requires owner approval)

If the owner approves, one PR would:

1. **Implement S-A** in `SpectrumResult.to_dict` for the spectral route.
   - The check keeps the identifier `spectral-degree-refinement`.
   - Its criterion text records which branch passed: `convergence` or
     `plateau`.
   - The record gains the per-mode perturbation scales and the stability
     ratio at the two finest degrees.
   - Computing left and right eigenvectors for two matrices of size at most
     `N` adds milliseconds.
2. **Leave everything else unchanged:** the default finite-difference route,
   the analytic-spectrum tolerance, the `1e-8` accuracy requirement and all
   existing outputs for `N <= 48`.
3. **Update the records:** a model-card note, the benchmark guide (removing
   the known issue), the changelog, and a new contract version for the
   refinement check. Old outcomes stay in history.
4. **Add tests:** degrees 56, 64 and 100 now pass; degree 24 and both cutoff
   families still fail; the synthetic swapped and non-finite cases fail;
   finite-difference output is byte-identical.
5. **Validate:** the full suite, the smoke verifier and the telemetry.
