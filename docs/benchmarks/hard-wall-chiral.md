# Hard-wall chiral Model A benchmark

## Scope and review state

This Forge/Verify benchmark targets the two-flavor bottom-up hard-wall model
of J. Erlich, E. Katz, D. T. Son, and M. A. Stephanov, “QCD and a holographic
model of hadrons,” *Phys. Rev. Lett.* 95, 261602 (2005),
[arXiv:hep-ph/0501128v2](https://arxiv.org/abs/hep-ph/0501128). It recomputes
all seven rounded Model A entries in source Table II and tests the small-quark-
mass GMOR limit without refitting the three printed Model A inputs.

The owner approved the source, equations, conventions, numerical contract,
and R1--R3 UV amendment on 2026-08-20. After all frozen gates passed, Xin-Yi
Liu also accepted the AI-assisted numerical result at `reproduced`, approved
the model-card provenance, and authorized one scoped local Phase 3 commit on
2026-08-20. Push, pull request, merge, tag, release, Phase 4, and additional
model sectors remain outside that approval.

This is a truncated bottom-up effective model. A passing calculation does not
empirically validate QCD, a hard IR wall, or the omitted higher operators.

## Source record and fixed inputs

The verifier records SHA-256 digests of the inspected public v2 PDF and TeX
archive but does not redistribute either source artifact. It uses

```text
N_c = 3,             g5 = 2 pi,
z_m^{-1} = 323 MeV,  m_q = 2.29 MeV,
sigma^{1/3} = 327 MeV.
```

These printed parameters are rounded. HoloForge therefore separates the
one-percent literature-table gate from its much tighter numerical gates. They
are also EKSS-convention parameters, not QCD's quark mass and condensate; see
the normalization caveat under Limitations.
Source Table II used `m_pi`, `m_rho`, and `f_pi` as fit targets; only
`m_a1`, `sqrt(F_rho)`, `sqrt(F_a1)`, and `g_rho_pi_pi` are source
predictions. The generated artifacts preserve that distinction.

## Equations and normalizations

Set `u=z/z_m`, `lambda=q^2 z_m^2`, and

```text
v(u) = (m_q z_m) u + (sigma z_m^3) u^3.
```

The normalizable transverse equations are

```text
d_u[(1/u) V'] + (lambda/u) V = 0,
d_u[(1/u) A'] + (lambda/u) A - g5^2 v^2 A/u^3 = 0,

V(0)=A(0)=0,  V'(1)=A'(1)=0,
integral_0^1 V^2/u du = integral_0^1 A^2/u du = 1.
```

The pion and longitudinal-axial fields obey

```text
u^2 phi'' - u phi' + g5^2 v^2 (pi-phi) = 0,
-lambda phi' + g5^2 (v/u)^2 pi' = 0,

phi(0)=pi(0)=0,  phi'(1)=0,

integral_0^1 [phi'^2/(g5^2 u) + v^2(pi-phi)^2/u^3] du = 1.
```

The normalizable fields are factored as `V=u^2 Vbar`, `A=u^2 Abar`,
`phi=u^2 phibar`, and `pi=u^2 pibar`. Decay constants use the exact
factored endpoint derivatives, and `g_rho_pi_pi` is the canonically normalized
source Eq. (22) overlap.

At nonzero `m_q`, the full zero-momentum axial equation has

```text
A_0(u) = 1 + (g5^2 mhat^2/2) u^2 log(u) + O(u^2).
```

Consequently, `A_0=1+u^2 a0bar` is not regular at the exact UV endpoint. The
approved amendment retains the complete `v(u)^2` and evaluates source Eq. (20)
at the public v2 TeX numerical regulator
`epsilon_z=1e-10 MeV^-1`, or dimensionless `epsilon=3.23e-8` for Model A.
No finite unrenormalized `epsilon -> 0` limit or counterterm is claimed.

## Numerical routes

The primary normalizable-mode route uses the shared exact-endpoint
Chebyshev--Gauss--Lobatto grid at polynomial degrees `N=64,80,96`. Dense
generalized pencils are passed to `scipy.linalg.eig`. Candidate modes are
ordered by positive real eigenvalue without a source target. Each QZ candidate
receives a deterministic, local bordered refinement: one middle equation is
replaced by a fixed endpoint amplitude, `scipy.linalg.solve` reconstructs the
profile, and `scipy.optimize.root_scalar` zeros the omitted-row residual inside
a target-free local QZ bracket. The record preserves raw and filtered counts,
rejection reasons, and the fact that source values were not used for ranking.

Equations are re-evaluated on a twice-denser Chebyshev grid. The reported
scaled equation metric is the normwise operator backward error

```text
||residual||_infinity
----------------------------------------------- ,
sum_i ||linear operator_i||_infinity ||field_i||_infinity
```

which is appropriate for the ill-conditioned exact-endpoint second-derivative
matrices and is kept separate from physical endpoint, normalization,
refinement, and independent-route tests.

The axial zero mode uses backward `solve_ivp(method="DOP853")` from the IR
Neumann condition. Independent `solve_bvp` calculations use the unfactored
physical equations at `epsilon=(2e-5,1e-5,5e-6)`. They check `f_pi`, the
lowest transverse-axial mode and decay constant, the pion mode and
normalization, and `g_rho_pi_pi`. The existing hard-wall vector shooting and
adaptive-collocation routes remain protected regression anchors.

## Quantitative reproduction

The current local preflight gives:

| Observable | HoloForge | Source Model A | Relative error | Source role |
| --- | ---: | ---: | ---: | --- |
| `m_pi` [MeV] | 139.58524 | 139.6 | 0.0106% | fit target |
| `m_rho` [MeV] | 776.75866 | 775.8 | 0.1236% | fit target |
| `m_a1` [MeV] | 1358.24318 | 1363 | 0.3490% | prediction |
| `f_pi` [MeV] | 92.42728 | 92.4 | 0.0295% | fit target |
| `sqrt(F_rho)` [MeV] | 329.81203 | 329 | 0.2468% | prediction |
| `sqrt(F_a1)` [MeV] | 485.83344 | 486 | 0.0343% | prediction |
| `g_rho_pi_pi` | 4.485286 | 4.48 | 0.1180% | prediction |

The largest source-table difference is 0.3490%. The final `N=80 -> 96`
change is about `1.12e-12`; this exceptionally small number reflects the
smooth low modes and bordered refinement, not phenomenological precision.
The largest selected finite-cutoff change is `5.59e-9`, and the largest
spectral-versus-`solve_bvp` difference is `1.87e-9`.

At the three diagnostic cutoffs, DOP853 and `solve_bvp` agree on `f_pi` within
`2.45e-11` relative error. The two numerical squared-decay-constant increments
divided by `m_q^2 log(2)` are `0.999998925` and `0.999999703`, verifying the
analytic UV logarithm. At `m_q/m_q,ModelA=(1,1/2,1/4,1/8)`, the GMOR ratios
are approximately `(1.03937,1.01708,1.00789,1.00378)` and approach one
monotonically.

These numbers are passing implementation evidence, not yet an owner-accepted
scientific result.

## Commands and generated evidence

After installation:

```bash
holoforge verify hard-wall-chiral
holoforge verify hard-wall-chiral --json
holoforge verify hard-wall-chiral --output-dir OUTPUT_DIR
python3 -m unittest tests.test_hard_wall_chiral -v
```

The optional output directory receives strict JSON, one combined Table II and
GMOR CSV, and a HoloForge-generated comparison graphic. Existing artifacts are
never silently overwritten. The source paper has no plotted figure; the
generated graphic is explicitly labeled as a HoloForge verification plot, not
a source-figure reproduction.

## Limitations and non-inference boundary

- The hard wall and its Neumann conditions are phenomenological inputs.
- Model A fit-target recomputation is not an independent seven-observable fit
  or prediction.
- No Model B, strange-quark, baryon, glueball, anomaly, finite-temperature,
  finite-density, or improved-holographic-QCD sector is included.
- The source notes that omitted `F^3` terms may affect the three-meson
  coupling, and IR boundary terms can affect decay constants.
- Numerical agreement with the source calculation does not establish the
  effective model as a precision description of nature.
- **Normalization caveat for `m_q` and `sigma`.**
  - Like the source, HoloForge implicitly takes the chiral scalar's operator
    normalization `a = 1`. The printed `m_q = 2.29 MeV` and
    `sigma = (327 MeV)^3` are therefore model-convention parameters, not QCD's
    quark mass and condensate.
  - A. Cherman, T. D. Cohen and E. S. Werbos, "The chiral condensate in
    holographic models of QCD," *Phys. Rev. C* 79, 045203 (2009),
    [arXiv:0804.1096](https://arxiv.org/abs/0804.1096), match the scalar
    two-point function to large-`N_c` QCD. They find
    `a = sqrt(N_c)/(2 pi)`, which gives `m_q = 8.3 MeV` and
    `sigma = (213 MeV)^3` from the same fit.
  - The model fixes only `a m_q` and `sigma/a`. The GMOR product `m_q sigma`,
    and every observable this benchmark checks, are therefore independent of
    this choice.
  - The authors also note that neither parameter carries QCD's
    renormalization-scale dependence.

The complete prospective contract and preserved UV stop are in
[`hard-wall-chiral-contract.md`](hard-wall-chiral-contract.md).
