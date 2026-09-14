# HoloForge

[![CI](https://github.com/xin-yi6/HoloForge/actions/workflows/ci.yml/badge.svg)](https://github.com/xin-yi6/HoloForge/actions/workflows/ci.yml)

HoloForge is a verification-first platform for **bottom-up gauge/gravity
modelling**. It is intended to make scientific assumptions, conventions,
equations, numerical choices, validation evidence, and limitations inspectable
alongside executable calculations.

HoloForge has two deliberately separated modes:

- **Forge/Verify** reproduces established models and checks their analytic and
  numerical consequences.
- **Explore** records new cross-domain ideas as falsifiable hypotheses without
  presenting them as established physics.

Explore recognizes three useful research tracks: applications to a genuinely
new parent domain, applications to an unexplored subfield or phenomenon inside
an already holographic parent field, and method transfer or model improvement.
Scientific value is assessed separately from current software readiness: a
missing model, dictionary, observable, or solver can define a strategic
research campaign rather than automatically disqualifying the question. See
the [research objective](docs/research-objective.md) and
[research-gate workflow](docs/research-gate-workflow.md).

An experimental [autonomous research workflow](docs/autonomous-research-workflow.md)
can prospectively delegate candidate generation, selection, repeated frozen
gates, bounded pivots, and terminal packaging inside a private campaign. It is
designed for unattended execution, but it does not guarantee a paper or permit
the agent to modify HoloForge, relax thresholds, assign human review, or publish.

Holographic leverage may be physical or conceptual, such as a new mechanism or
relation, and it may also be computational or representational: a controlled
duality can make an otherwise inaccessible strongly coupled problem
calculable. The latter is a legitimate research-value route only when the
dictionary, approximation regime, comparison baseline, accuracy, and actual
advantage are demonstrated rather than assumed from the extra dimension.

## Framework scope

HoloForge is not organized around one physical domain, model family, or
observable. Its reusable contract is the chain from assumptions and sources
to equations, boundary conditions, numerical evidence, observables, and
explicit limitations.

The current public release contains a deliberately small reference suite,
chosen because its calculations have analytic or literature checks suitable
for testing that contract. These examples demonstrate the framework; they do
not define HoloForge's scientific scope or priority. Technical model details
belong in the linked benchmark guides and version specifications.

## Release maturity and research use

A pre-1.0 HoloForge release can be used for a bounded calculation when that
calculation's equations, conventions, solver, acceptance gates, and exact
package version or Git commit are recorded and independently checked. The
`0.x` version number means the public interfaces may still change; it does not
make a passing benchmark scientifically untrustworthy.

Private research should combine a pinned HoloForge release with
project-specific equations, code, and validation in a separate repository.
HoloForge 1.0 will denote a stable public framework contract, not the first
version capable of supporting any scientific research.

## Privacy for Explore research

HoloForge does **not** require novel work to be public while it is in progress.
Potentially publishable Explore projects should use HoloForge from a separate,
access-controlled repository. The public `incubator/` is reserved for synthetic
examples, public-literature dry runs, and work explicitly approved for
disclosure. After journal acceptance or another deliberate release decision, a
reviewed reproducibility package may be promoted into this repository. See the
[private-research workflow](docs/private-research-workflow.md).

## Quick start

Use Python 3.11 for development and routine CI, with NumPy and SciPy. Package
metadata permits Python 3.9 or newer, but wider Python and operating-system
coverage is an explicit manual CI option during pre-1.0 development. See the
[runtime and CI policy](docs/version-0.5-compatibility-policy.md#supported-runtime-and-platforms).

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python3 -m pip install -e ".[test]"
holoforge --help
python3 -m unittest discover -s tests -v
```

Conda users may replace the first two commands with
`conda create -n holoforge python=3.11` followed by
`conda activate holoforge`.

For benchmark use without schema-test dependencies, install with
`python3 -m pip install -e .`. Until the package is installed, the command can
also be run from the checkout with `PYTHONPATH=src python3 -m holoforge ...`.

## Start with an AI coding agent

Open the cloned HoloForge folder as the agent's workspace so it can see the
repository instructions, documentation, and scoped workflows. Begin with the
[agent quick-start guide](docs/agent-quickstart.md), which provides setup
commands, an inspect-only first prompt, task-specific prompts, private Explore
guidance, and a checklist for reviewing agent-generated changes.

- `AGENTS.md` is the canonical cross-agent project context and is read by
  Codex.
- `CLAUDE.md` imports that same context for Claude Code.
- Agents without automatic project-instruction or skill discovery should be
  asked explicitly to read `AGENTS.md` and the matching workflow under
  `.agents/skills/`.

An agent can help execute a workflow, but it does not replace the benchmark
acceptance gates, scientific review, or explicit authorization to disclose
private research.

Before running an expensive calculation, an agent or user can inspect one
built-in benchmark's declared public coverage without executing its solver:

```bash
holoforge inspect benchmark BENCHMARK
holoforge inspect benchmark BENCHMARK --require CAPABILITY_ID --json
```

Exact `--require` identifiers are classified as `qualified`, `known-gap`, or
`not-declared`. This is a static evidence receipt, not a natural-language
physics, novelty, scientific-value, or publication judge. A receipt informs
cost and research-horizon planning; it must not select the questions worth
pursuing. See the
[Version 0.6 capability contract](docs/version-0.6.md).

## Included reference implementations

The following are the reference calculations implemented today. Their names
identify executable examples, not a restriction on future HoloForge domains.
The owner-selected six-phase progression and its exact scope boundaries are
summarized in the [classical benchmark sequence](docs/benchmarks/classical-sequence.md).

| Capability demonstrated | Command | Documentation |
| --- | --- | --- |
| Spectral eigenvalue verification with analytic and independent numerical checks | `holoforge verify soft-wall-vector` and `holoforge verify hard-wall-vector` | [soft-wall guide](docs/benchmarks/soft-wall-vector.md) and [hard-wall guide](docs/benchmarks/hard-wall-vector.md) |
| Coupled chiral spectroscopy, decay constants, overlap, and GMOR verification | `holoforge verify hard-wall-chiral` | [hard-wall chiral guide](docs/benchmarks/hard-wall-chiral.md) |
| Linear-instability and nonlinear-condensate verification | `holoforge verify holographic-superconductor` | [condensate benchmark guide](docs/benchmarks/holographic-superconductor.md) |
| Spectral/Riccati optical response and static/finite-frequency superfluid-density verification | `holoforge verify holographic-superconductor-optical` | [HHH optical benchmark guide](docs/benchmarks/holographic-superconductor-optical.md) |
| Coupled fluctuation, radial-flux, and DC-limit verification | `holoforge verify linear-axion-dc` | [transport benchmark guide](docs/benchmarks/linear-axion-dc.md) |
| Coupled Einstein--dilaton thermodynamics with spectral, DOP853, and source-figure checks | `holoforge verify gubser-nellore-ed` | [Einstein--dilaton benchmark guide](docs/benchmarks/gubser-nellore-ed.md) |
| Reproduced zero-density bottom-up EMD thermodynamics and susceptibility with spectral and independent checks | `holoforge verify dewolfe-gubser-rosen-emd` | [DGR EMD Phase 5A guide](docs/benchmarks/dewolfe-gubser-rosen-emd.md) |
| Reproduced selected finite-density bottom-up EMD backgrounds and reported critical coordinates through two Chebyshev formulations | `holoforge verify dewolfe-gubser-rosen-emd-finite-density` | [DGR EMD Phase 5B guide](docs/benchmarks/dewolfe-gubser-rosen-emd-critical-point.md) |
| Top-down-derived charged EMD control with exact-background, flux, thermodynamic, and low-temperature checks | `holoforge verify gubser-rocha-emd` | [Gubser--Rocha EMD control guide](docs/benchmarks/gubser-rocha-emd.md) |
| Controlled model/reference comparison with uncertainty provenance | `holoforge compare vector-spectrum` | [comparison guide](docs/benchmarks/vector-spectrum-comparison.md) |
| Portable provenance and scientific-state compatibility | Add `--bundle-dir PATH` to any command, then use `holoforge audit bundle` or `holoforge audit compatibility` | [evidence-bundle guide](docs/evidence-bundles.md) |
| Solver-free inspection of declared benchmark coverage, outputs, transformations, and gaps | `holoforge inspect benchmark BENCHMARK` | [Version 0.6 capability contract](docs/version-0.6.md) |

Commands accept documented options for machine-readable records and generated
artifacts. Plot generation requires the optional dependency installed with
`python3 -m pip install -e ".[plot]"`.

## Repository map

- [`CONSTITUTION.md`](CONSTITUTION.md) defines the scientific rules of the
  project.
- [`docs/architecture.md`](docs/architecture.md) maps the benchmark-harness
  execution path, repository layers, dependency rules, and deliberate
  non-goals.
- [`docs/research-objective.md`](docs/research-objective.md) defines the
  physics-first objective, discovery/confirmation loops, conditional evidence
  profiles, and research-pulled development boundary.
- [`docs/autonomous-research-workflow.md`](docs/autonomous-research-workflow.md)
  defines the experimental campaign-level delegation contract, multi-agent
  roles, no-touch surfaces, state machine, terminal package, and AR-0--AR-5
  checkpoints.
- [`docs/version-*.md`](docs/) contains the scientific and infrastructure
  contracts for each public release.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) explains the scientific and software
  contribution workflow.
- [`docs/agent-quickstart.md`](docs/agent-quickstart.md) explains how a new
  user starts HoloForge safely with Codex, Claude Code, or another agent.
- [`docs/agent-maintenance.md`](docs/agent-maintenance.md) defines instruction
  authority, proportionate checks, private workspace navigation, execution
  receipts, and maintenance holds before resuming research.
- [`docs/physics-manuscript-writing.md`](docs/physics-manuscript-writing.md)
  guides physics-led paper writing while keeping internal review packets and
  reproducibility records separate and scientific limitations visible.
- [`docs/learning-from-results.md`](docs/learning-from-results.md) requires a
  claim-bounded, event-driven research knowledge base that learns from papers,
  derivations, methods, data, decisions, reproducibility work, and every bounded
  result, plus a closure retrospective for each completed gate.
- [`docs/research-progress-snapshots.md`](docs/research-progress-snapshots.md)
  defines the compact and grouped project-progress figures used in private
  research and owner-review packets.
- [`docs/version-0.5-compatibility-policy.md`](docs/version-0.5-compatibility-policy.md)
  defines the protected `0.5.x` commands, Python API, schemas, migrations, and
  platform support; [`SECURITY.md`](SECURITY.md) gives the private reporting
  route.
- [`CITATION.cff`](CITATION.cff) provides machine-readable citation metadata.
- [`CHANGELOG.md`](CHANGELOG.md) records release-level changes.
- [`schemas/`](schemas/) contains machine-readable model-card,
  hypothesis-card, reference-data, prediction, comparison, evidence-bundle,
  compatibility, and experimental autonomous-campaign contracts.
- [`domains/`](domains/) contains literature-anchored, testable models.
- [`incubator/`](incubator/) contains only public-safe Explore examples and
  proposals.
- [`.agents/skills/`](.agents/skills/) contains repository-scoped reusable
  workflows for research gates, benchmark development, and privacy-reviewed
  public exports. Supported agents may discover these skills automatically;
  every agent can instead read the matching `SKILL.md` directly.
- [`src/holoforge/`](src/holoforge/) contains reusable software.
- [`docs/numerics/chebyshev-collocation.md`](docs/numerics/chebyshev-collocation.md)
  documents the shared finite-interval pseudospectral primitive and its
  benchmark-level evidence boundary.
- [`tests/`](tests/) holds analytic, numerical, schema, and interface checks.

## Reusable agent skills

The checked-in skills package procedures that are specific to HoloForge:

- `$holoforge-research-gate` runs one frozen Explore gate through evidence,
  criticism, recommendations, owner review, and decision recording, with A-E
  response paths and an optional project-local research-progress map in
  Markdown/Mermaid, standalone vector, and PDF-ready forms, while updating the
  reviewed research knowledge base and preserving a closure retrospective that
  feeds bounded lessons into later gates; after a contract is frozen, an
  owner-approved bounded autonomy window can carry routine in-scope work to one
  consolidated mandatory return without delegating scientific or disclosure
  decisions;
- `$holoforge-auto-research` governs a true campaign-level auto mode that may
  search, select, execute, verify, preserve-and-pivot, and package multiple
  candidates within one owner-authorized mission, using a sole-writer
  coordinator, read-only specialist roles, deterministic state validation, and
  honest stopped outcomes;
- `$holoforge-public-export` audits a proposed private-to-public artifact and
  includes a deterministic scanner for common private-path and forbidden-token
  leaks; and
- `$holoforge-add-benchmark` guides a literature-anchored Forge/Verify
  benchmark from contract through implementation and validation.

These skills do not contain unpublished candidate identities, scientific
results, private numerical implementations, or personal global preferences.
They are repository workflows, not substitutes for scientific review.

## Project status

The latest public release is `0.6.1`. HoloForge remains a pre-1.0 project, not
a universal phenomenology or first-principles prediction package. Its current
reference implementations reproduce published model calculations; they do not
establish those models as complete descriptions of their target physical
systems.

## License

HoloForge is released under the
[BSD 3-Clause License](LICENSE), copyright 2026 Xin-Yi Liu.
