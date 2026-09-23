# HoloForge

[![CI](https://github.com/xin-yi6/HoloForge/actions/workflows/ci.yml/badge.svg)](https://github.com/xin-yi6/HoloForge/actions/workflows/ci.yml)

HoloForge is a verification-first platform for **bottom-up gauge/gravity
modelling**. It helps researchers reproduce published calculations and develop
new physics hypotheses with explicit assumptions, reproducible checks, and
traceable evidence.

- **Forge/Verify:** run literature-anchored models and check their analytic and
  numerical predictions against declared acceptance criteria.
- **Explore:** investigate falsifiable hypotheses through bounded calculations,
  independent verification, and human scientific review.

A passing calculation verifies a declared model result; it does not establish
that the model describes nature. The public reference examples demonstrate the
framework and do not define HoloForge's scientific scope.

## Included reference implementations

Start with one of these examples:

| Example | Command | Guide |
| --- | --- | --- |
| Analytically known spectrum | `holoforge verify soft-wall-vector` | [Soft-wall vector](docs/benchmarks/soft-wall-vector.md) |
| Condensate and instability | `holoforge verify holographic-superconductor` | [Holographic superconductor](docs/benchmarks/holographic-superconductor.md) |
| DC transport | `holoforge verify linear-axion-dc` | [Linear-axion transport](docs/benchmarks/linear-axion-dc.md) |
| Einstein–dilaton thermodynamics | `holoforge verify gubser-nellore-ed` | [Gubser–Nellore model](docs/benchmarks/gubser-nellore-ed.md) |

The suite also includes chiral spectroscopy, optical response, and charged
black-hole thermodynamics. Browse the [benchmark guides](docs/benchmarks/) for
their equations, methods, and limitations, or run `holoforge verify --help`
to list every built-in verifier.

## Quick start

Use Python 3.11 for the recommended setup. On macOS or Linux:

```bash
git clone https://github.com/xin-yi6/HoloForge.git
cd HoloForge
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
holoforge verify soft-wall-vector
```

This runs a spectral calculation against an analytic reference and reports
whether the declared checks pass. Use `holoforge --help` to explore the CLI.
For development setup and tests, see [Contributing](CONTRIBUTING.md); for other
supported environments, see the [runtime policy](docs/version-0.5-compatibility-policy.md#supported-runtime-and-platforms).

To preserve and inspect a portable evidence bundle:

```bash
holoforge verify soft-wall-vector --bundle-dir evidence/soft-wall
holoforge audit bundle evidence/soft-wall
```

See the [evidence guide](docs/evidence-bundles.md) for what the bundle contains
and which integrity and scientific-state checks it supports.

## Using HoloForge for research

Keep unpublished Explore work in a **separate, access-controlled repository**
with a pinned HoloForge version. The public repository contains established
reference models, synthetic examples, and material explicitly cleared for
disclosure. Follow the [private-research guide](docs/private-research-workflow.md)
when starting a new project.

An AI coding agent can help run calculations, inspect evidence, and prepare
changes. Open the repository root and follow the
[agent quick start](docs/agent-quickstart.md), using [AGENTS.md](AGENTS.md) for
the shared project instructions. Scientific review remains part of the workflow.

## Documentation

| I want to… | Start here |
| --- | --- |
| Understand the scientific goals and standards | [Research objective](docs/research-objective.md) · [Scientific Constitution](CONSTITUTION.md) |
| Plan and assess a physics investigation | [Research workflow](docs/research-gate-workflow.md) · [Scientific support levels](docs/scientific-support.md) |
| Draft or revise a physics paper | [Manuscript guide](docs/physics-manuscript-writing.md) |
| Understand or extend the software | [Architecture](docs/architecture.md) · [Add a benchmark](docs/benchmark-extension-guide.md) |
| Explore bounded autonomous research | [Experimental campaign workflow](docs/autonomous-research-workflow.md) |

## Project status

The latest public release is [`0.7.0`](docs/version-0.7.md). HoloForge is **pre-1.0**: public interfaces
may change, so record the exact version or commit used for a calculation.
See the [changelog](CHANGELOG.md) for release history and
[CITATION.cff](CITATION.cff) for citation metadata.

## Contributing and license

Contributions to code, documentation, and reproducible benchmarks are welcome.
Please read [Contributing](CONTRIBUTING.md) before opening a substantial change.

Released under the [BSD 3-Clause License](LICENSE), copyright 2026 Xin-Yi Liu.
