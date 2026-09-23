# Version 0.5 compatibility, migration, support, and security policy

This policy defines the bounded public contract for the HoloForge `0.5.x`
series. Versions 0.6 and [0.7](version-0.7.md) preserve those protected
interfaces; the runtime and support guidance below applies to the current
release. This policy does not freeze undocumented internals and does not turn
a passing calculation into empirical validation.

## Supported runtime and platforms

The package declares Python 3.9 or newer as its installation range. During
pre-1.0 development, routine CI uses **Python 3.11**, matching the primary
development environment's minor version. CI installs the available 3.11 patch
and dependencies; this is not an exact reproduction of every local package
version. Other Python versions are checked explicitly rather than on every
push. An installation range is not a claim that every allowed environment was
tested on the current commit.

The default test job runs every current scientific verifier, including the
accepted Phase 4 and Phase 5 calculations, once on Python 3.11 on Ubuntu.
Superseded numerical routes and development-era ladders remain in an
explicit extended audit that runs once on Python 3.11. Scientific checks,
thresholds, and preserved historical evidence are unchanged by the smaller
routine matrix.

A built-wheel job checks installed-package identity, registry composition,
packaged reference data, and a fast verifier. A Python 3.11 wheel-portability
job on macOS exercises focused contracts, selected fast benchmarks,
evidence-bundle relocation, and integrity audit on the primary development
operating system. It does not repeat the long Phase 4 or Phase 5 scientific
calculations already required in the main test job. Ordinary pushes, pull
requests, tags, and default manual runs therefore use four jobs, all on Python
3.11.

For a wider check, open **Actions -> CI -> Run workflow** and enable
`full_compatibility`, or run:

```bash
gh workflow run ci.yml --ref BRANCH_OR_TAG -f full_compatibility=true
```

That explicit mode restores the eight-job matrix: full tests on Python 3.9,
3.11, and 3.14 on Ubuntu; one historical audit and one wheel build; and focused
Python 3.11 wheel-portability checks on Ubuntu, macOS, and Windows. It retains
the legacy 3.9 compatibility check without recommending 3.9 for a new
development environment. Run this mode on the intended release candidate
before Version 1.0 or making a broader compatibility claim, and record its exact
commit and results. A version or platform is not claimed tested on a revision
unless its checks passed there. Earlier release receipts remain historical
evidence, not proof for a newer commit.

New compatibility and security fixes target the latest release in the current
pre-1.0 minor line, now `0.7.x`. Exact older releases remain available for
reproducibility; their availability does not promise ongoing maintenance.

## Protected command behavior

Patch releases in the `0.5.x` line preserve these commands and the option
names, meanings, defaults, ordinary JSON semantics, and exit meanings exposed
by the release in which each command first appears:

- `holoforge verify soft-wall-vector`;
- `holoforge verify hard-wall-vector`;
- `holoforge verify hard-wall-chiral`;
- `holoforge verify holographic-superconductor`;
- `holoforge verify holographic-superconductor-optical`;
- `holoforge verify linear-axion-dc`;
- `holoforge verify dewolfe-gubser-rosen-emd`;
- `holoforge verify dewolfe-gubser-rosen-emd-finite-density`;
- `holoforge verify gubser-nellore-ed`;
- `holoforge verify gubser-rocha-emd`;
- `holoforge compare vector-spectrum`;
- `holoforge audit bundle`; and
- `holoforge audit compatibility` with `same-state-family`.

Exit `0` means the calculation or audit completed and all declared gates
passed. Exit `1` means a calculation completed but at least one scientific or
audit gate failed. Exit `2` means invalid input, an unsupported setup, or a
controlled execution failure. A patch may add an opt-in command, optional
field, or option only when existing invocations and meanings remain valid.
Once released in the `0.5.x` line, that new public command receives the same
compatibility protection.

Checked-in JSON records use LF line endings on every supported platform so
their reviewed raw SHA-256 digests do not change during a Windows checkout.

## Protected Python API

The following deliberately exported names are protected throughout `0.5.x`.
Their documented import paths, call signatures, and result meanings will not
change incompatibly in a patch release.

Top level:

- `holoforge.__version__`.

Core contracts and infrastructure:

- `holoforge.core.AcceptanceCheck`;
- `holoforge.core.BackgroundSpec`;
- `holoforge.core.BenchmarkAdapter`;
- `holoforge.core.BenchmarkDefinition`;
- `holoforge.core.BenchmarkExecution`;
- `holoforge.core.BenchmarkExecutionError`;
- `holoforge.core.BenchmarkRegistry`;
- `holoforge.core.BenchmarkRegistryError`;
- `holoforge.core.BoundaryConditionSpec`;
- `holoforge.core.BundleAuditResult`;
- `holoforge.core.CompatibilityAuditResult`;
- `holoforge.core.EquationSpec`;
- `holoforge.core.EvidenceBundleError`;
- `holoforge.core.ModelCardReference`;
- `holoforge.core.NormalizedSpectrum`;
- `holoforge.core.ObservableSpec`;
- `holoforge.core.SolverSpec`;
- `holoforge.core.VerificationRecord`;
- `holoforge.core.audit_evidence_bundle`;
- `holoforge.core.audit_same_state_family`;
- `holoforge.core.canonical_json_sha256`;
- `holoforge.core.normalize_spectrum`;
- `holoforge.core.runtime_versions`; and
- `holoforge.core.write_evidence_bundle`.

Benchmark exports:

- `holoforge.benchmarks.BUILTIN_BENCHMARKS`;
- `holoforge.benchmarks.CondensateBranchResult`;
- `holoforge.benchmarks.CondensateConfig`;
- `holoforge.benchmarks.HardWallConfig`;
- `holoforge.benchmarks.HardWallRefinementResult`;
- `holoforge.benchmarks.HardWallSpectrumResult`;
- `holoforge.benchmarks.LinearAxionCaseResult`;
- `holoforge.benchmarks.LinearAxionFrequencyResult`;
- `holoforge.benchmarks.LinearAxionPreflightConfig`;
- `holoforge.benchmarks.LinearAxionRefinementEvidence`;
- `holoforge.benchmarks.LinearAxionVerificationResult`;
- `holoforge.benchmarks.OnsetConfig`;
- `holoforge.benchmarks.OnsetResult`;
- `holoforge.benchmarks.OpticalVerificationResult`;
- `holoforge.benchmarks.SoftWallConfig`;
- `holoforge.benchmarks.SpectrumResult`;
- `holoforge.benchmarks.SuperconductorVerificationResult`;
- `holoforge.benchmarks.analytic_dimensionless_masses`;
- `holoforge.benchmarks.analytic_mass_squared`;
- `holoforge.benchmarks.hard_wall_cutoff_refinement`;
- `holoforge.benchmarks.save_condensate_plot`;
- `holoforge.benchmarks.save_optical_diagnostic_plot`;
- `holoforge.benchmarks.schrodinger_potential`;
- `holoforge.benchmarks.solve_condensate_branch`;
- `holoforge.benchmarks.solve_hard_wall_spectrum`;
- `holoforge.benchmarks.solve_linear_axion_case`;
- `holoforge.benchmarks.solve_linear_axion_frequency`;
- `holoforge.benchmarks.solve_onset`;
- `holoforge.benchmarks.solve_spectrum`;
- `holoforge.benchmarks.verify_gubser_nellore_ed`;
- `holoforge.benchmarks.verify_dewolfe_gubser_rosen_emd`;
- `holoforge.benchmarks.verify_dewolfe_gubser_rosen_emd_finite_density`;
- `holoforge.benchmarks.verify_gubser_rocha_emd`;
- `holoforge.benchmarks.verify_hard_wall_chiral`;
- `holoforge.benchmarks.verify_holographic_superconductor_optical`;
- `holoforge.benchmarks.verify_linear_axion_dc`; and
- `holoforge.benchmarks.verify_superconductor`.

Controlled-comparison exports:

- `holoforge.comparisons.VectorSpectrumComparisonResult`;
- `holoforge.comparisons.build_vector_spectrum_comparison`;
- `holoforge.comparisons.render_vector_spectrum_table`; and
- `holoforge.comparisons.save_vector_spectrum_artifacts`.

Names inside implementation modules that are absent from these package-level
exports are not protected. Numerical results, tolerances, or scientific
contracts may change only through an explicit scientific review and cannot be
silently described as a compatibility fix.

## Supported schemas and migration

Version 0.5 ships and reads these exact schema versions:

| Record | Schema version |
| --- | --- |
| Model card | `0.1` |
| Hypothesis card | `0.1` |
| Reference dataset | `0.3` |
| Model prediction | `0.3` |
| Comparison record | `0.3` |
| Evidence bundle | `0.4` |
| Evidence compatibility report | `0.4` |

A schema change that invalidates a record valid under one of these contracts
requires a new schema version and a changelog migration note. Automatic
migration is allowed only when deterministic and when scientific meaning,
provenance, support labels, and disclosure state are preserved. Otherwise the
reader must fail closed with an actionable message. Patch releases continue to
accept every schema version listed above.

## Deprecation policy

A protected CLI or Python surface may be deprecated only with documentation,
a changelog entry, and a runtime warning where practical. It remains functional
through the rest of `0.5.x`; removal requires a later minor or major release.
Security or confidentiality fixes may fail closed immediately when retaining
old behavior would expose data, but the release notes must explain the break.

## Security and confidentiality

Use the private route in [`SECURITY.md`](../SECURITY.md) for vulnerabilities,
credentials, private paths, or unpublished research. Do not submit sensitive
details in public issues. The public-export scanner and CI are defense in
depth, not authorization to disclose private work.
