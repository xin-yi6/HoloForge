# HHH optical conductivity and superfluid density

## Scope and review state

This Forge/Verify benchmark extends the released dimension-two HHH
holographic-superconductor example using the transverse Maxwell response in
Sean A. Hartnoll, Christopher P. Herzog, and Gary T. Horowitz, “Building an
AdS/CFT superconductor,” *Phys. Rev. Lett.* 101, 031601 (2008),
[arXiv:0803.3295v1](https://arxiv.org/abs/0803.3295).

Xin-Yi Liu approved the corrected equations, numerical contract, result, and
bounded public promotion on 2026-08-21. The benchmark is AI-assisted and
records that provenance explicitly.

It reproduces the exact normal conductivity and the source's near-critical
dimension-two coefficient `C_2 = 24`. The existing
[`holographic-superconductor`](holographic-superconductor.md) benchmark remains
the protected background and source Figure 1 right-panel reproduction.

The source Figure 2 rightmost curve is **not reproduced**. Its public caption,
vector path, and condensate-rescaled counterpart cannot be reconciled from the
public artifacts. That disagreement remains provenance-only and is not an
acceptance gate, a claimed paper correction, or a physical negative result.

## Equations and conventions

Use `u=r_h/r`, `F=1-u^3`, and `L=r_h=1` during the dimensionless solve. The
protected background has `m^2 L^2=-2`, `q=1`, and the dimension-two scalar
condition `psi_-=0`.

For a zero-momentum transverse perturbation with time dependence
`exp(-i omega t)`, the optical equation is

```text
A_x'' + (F'/F) A_x'
      + [Omega^2/F^2 - 2 psi^2/(u^2 F)] A_x = 0,

omega/T = (4 pi/3) Omega.
```

At the horizon, the retarded solution is

```text
A_x = (1-u)^(-i Omega/3) a(u),
```

with regular `a(u)`. At the UV boundary,

```text
A_x = A_0 + A_1 u + ...,
sigma(omega) = -i A_1/(Omega A_0).
```

The static London equation and regular horizon condition are

```text
(F A_x')' - 2 psi^2 A_x/u^2 = 0,
A_x'(1) + (2 psi_h^2/3) A_x(1) = 0.
```

Its UV logarithmic derivative gives

```text
n_s/T_c = -(4 pi/3)(T/T_c) A_x'(0)/A_x(0).
```

The same quantity is independently obtained from the finite-frequency pole,

```text
(n_s/T_c)(omega)
  = (omega/T)(T/T_c) Im sigma(omega),
```

followed by a linear extrapolation in `(omega/T)^2`.

## Numerical routes

The positive-frequency primary route transfers the analytic source-free UV
series to a Chebyshev--Gauss--Lobatto bulk solve. It uses maintained dense
linear algebra and evaluates the differential equation independently on a
twice-denser grid. A Riccati logarithmic-derivative DOP853 integration supplies
the independent complex conductivity.

Near the transition, the frozen temperatures and frequencies are

```text
T/T_c   = 0.990, 0.995, 0.9975, 0.999,
omega/T = 0.200, 0.100, 0.050, 0.025.
```

The spectral ladder is `N=(128,160,192)`, with `N=160` primary, `N=128`
refinement, and `N=192` audit. The independent equation-residual ceiling stays
at `1e-6`; no tolerance was relaxed to obtain the passing result.

The zero-frequency primary density uses Riccati DOP853 and two UV fit windows.
The asymptotic coefficient is extracted from

```text
n_s/T_c = C_2 delta + C_4 delta^2,
delta = 1-T/T_c.
```

This retains the first nonlinear correction required by the finite but close
temperature window. The earlier one-parameter fit over
`T/T_c=(0.900,0.940,0.970,0.985)` is preserved in the evidence record as a
superseded-contract failure, not silently discarded.

## Quantitative result

| `T/T_c` | static `n_s/T_c` | finite-frequency pole `n_s/T_c` |
| ---: | ---: | ---: |
| `0.9900` | `0.2332687444` | `0.2332686604` |
| `0.9950` | `0.1182351375` | `0.1182350909` |
| `0.9975` | `0.05952438655` | `0.05952436198` |
| `0.9990` | `0.02390827039` | `0.02390826026` |

The two frozen fits give

```text
static London:          C_2 = 23.96884335, C_4 = -64.20423952,
finite-frequency pole: C_2 = 23.96883307, C_4 = -64.20405128.
```

The static coefficient differs from `24` by `0.129819%`. The largest
static/pole density difference is `4.23721e-7`. The largest near-critical
`N=160` independent equation residual is `5.58109e-8`, and the largest `N=192`
audit residual is `1.37837e-7`.

The exact normal-state complex-conductivity error is `2.45609e-11`. The
protected condensate benchmark passes unchanged and retains
`sqrt(<O_2>)/T_c=8.4436224` on its low-temperature Figure 1 plateau.

## Run the verifier

Human-readable output:

```bash
holoforge verify holographic-superconductor-optical
```

Strict machine-readable evidence:

```bash
holoforge verify holographic-superconductor-optical --json
```

Portable evidence bundle:

```bash
holoforge verify holographic-superconductor-optical \
  --bundle-dir artifacts/hhh-optical-bundle
```

Original HoloForge near-critical diagnostic:

```bash
holoforge verify holographic-superconductor-optical \
  --plot artifacts/hhh-near-critical-optical.png
```

Plotting requires `holoforge[plot]`. The diagnostic contains no source artwork
or digitized source curve and is labelled as not being a Figure 2 reproduction.

## Known platform issue: high-frequency equation gate on macOS arm64

On macOS arm64 with NumPy 2.4.6 and SciPy 1.17.1 wheels that report Apple
Accelerate as their BLAS/LAPACK backend, the aggregate
`optical-response-numerics` gate fails with a normalized ratio of `1.0011`.
Its largest term is the independent spectral equation residual at
`omega/T = 60`, `1.0011431e-5` against its `1e-5` ceiling. At that frequency
the resolution change of the conductivity is about `1.2e-12`. The maximum
spectral-versus-Riccati conductivity difference is `1.46e-6` against `5e-4`,
and all other gates pass. Linux CI with the same NumPy and SciPy versions
passes.

The cause of the high-frequency residual is not yet identified: it may be
discretization, differentiation or normalization, or arithmetic. The equation
check is retained unchanged. On such a platform the verifier's FAIL is the
recorded result. The non-blocking gate-telemetry workflow records the values
and backend on Linux and macOS for a later, evidence-based decision.

## Interpretation limits

- The calculation is in the probe limit and is not a controlled
  zero-temperature ground state.
- The boundary U(1) is global unless weakly gauged; “charged superfluid” is the
  more precise ungauged interpretation.
- No real-part delta distribution, infinite-frequency sum rule, free energy,
  quasinormal mode, backreaction, finite momentum, or nonlinear transport is
  computed.
- Figure 2 is not reproduced, and no corrected target or caption is inferred.
- Reproduction of this model calculation is not empirical validation of a
  material or a microscopic pairing mechanism.

The [current contract](holographic-superconductor-optical-contract.md) freezes
the accepted scope. Every mandatory stop, superseded route, and the preserved
degree-320 roundoff evidence remain in the
[development history](history/holographic-superconductor-optical-development-history.md).
