# Hard-Wall Vector Benchmark

## Scientific source

The benchmark follows J. Erlich, E. Katz, D. T. Son, and M. A. Stephanov,
“QCD and a Holographic Model of Hadrons,” *Physical Review Letters* **95**,
261602 (2005),
[arXiv:hep-ph/0501128](https://arxiv.org/abs/hep-ph/0501128), especially Eq.
(5) and the following vector-mode discussion.

## Equation and boundary conditions

For a transverse vector mode on the AdS5 slice, the source equation is

```text
partial_z[(1/z) partial_z V_n] + (m_n^2/z) V_n = 0.
```

The benchmark preserves the two boundary conditions and their different
physical roles:

```text
UV normalizability:  V_n(epsilon) = 0,
IR wall:             partial_z V_n(z_m) = 0.
```

In the zero-cutoff analytic limit, the spectrum is

```text
m_n z_m = j_(0,n+1),
```

where `j_(0,n+1)` is a positive zero of `J_0`. The implementation uses
`scipy.special.jn_zeros` rather than implementing a Bessel-zero routine.

## Independent numerical routes

The dimensionless coordinate `x = z/z_m` gives

```text
V''(x) - V'(x)/x + lambda^2 V(x) = 0,
lambda = m z_m.
```

HoloForge solves this problem in three genuinely different maintained-library
formulations:

1. adaptive `solve_ivp` shooting with a Brent `root_scalar` search for the IR
   Neumann residual; and
2. global `solve_bvp` collocation with `lambda` as an unknown parameter; and
3. Chebyshev--Gauss--Lobatto pseudospectral collocation, expressed as a dense
   generalized eigenproblem with explicit UV Dirichlet and IR Neumann rows and
   solved by SciPy's `eigvals`.

At the documented defaults, the first four normalized shooting and
collocation spectra differ by about `4.2e-11` or less. The shooting ratios
differ from the zero-cutoff Bessel ratios by about `7.4e-8` or less. These
numbers are development evidence, not a claim of empirical precision.

The spectral route records polynomial degrees 24, 32, and 40. At the documented
defaults, the maximum relative change between the final two spectra is about
`2.4e-12`. Its approximately `7.4e-8` disagreement with the zero-cutoff Bessel
ratios remains because `epsilon/z_m = 1e-4` is finite; this is not spectral
discretization error.

The cutoff study uses three decreasing values:

```text
epsilon/z_m = 1e-2, 3e-3, 1e-3.
```

The maximum ratio error decreases at every level. Finite-cutoff error is
reported separately from integration, root, and collocation tolerances.

## Run the verifier

```bash
holoforge verify hard-wall-vector
holoforge verify hard-wall-vector --method collocation --json
holoforge verify hard-wall-vector --method spectral --json
```

### Optional Rust shooting integrator

For repeated shooting calculations, install the native extension from a
HoloForge checkout using the same Python environment as HoloForge and a
current stable Rust toolchain (including Cargo):

```bash
python -m pip install ./native
holoforge verify hard-wall-vector --method shooting-rust --json
```

In Python, pass `method="shooting-rust"` to `solve_hard_wall_spectrum` or
`hard_wall_cutoff_refinement`. The Rust integrator evolves the same
two-component initial value problem from the UV cutoff to the wall.
HoloForge uses its existing SciPy Brent search, brackets, mode count, mass
normalization and acceptance criteria. The verification record includes
the selected route, extension version and configured tolerances. The default
`shooting` method uses SciPy and works with the base Python installation.
See the [Rust DOP853 implementation](https://docs.rs/ivp/0.6.0/ivp/methods/struct.DOP853.html).

## Interpretation limits

The hard wall and its IR boundary condition are phenomenological inputs. The
source paper itself treats the IR choice as a crude model ingredient rather
than something fixed uniquely by QCD. Passing this verifier shows that the
implemented equations and numerical routes reproduce their analytic target;
it does not establish the hard-wall construction as a precision QCD model.
