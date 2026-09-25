# Contributing to HoloForge

HoloForge welcomes reproducible software, documentation, benchmarks, and
carefully scoped research hypotheses. Contributions must follow the
[Scientific Constitution](CONSTITUTION.md).

## Development setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
python -m unittest discover -s tests -v
holoforge verify soft-wall-vector
```

Contributors using Codex, Claude Code, or another coding agent should first
follow the [agent quick-start guide](docs/agent-quickstart.md). The canonical
repository context is `AGENTS.md`; `CLAUDE.md` imports the same instructions so
the scientific and privacy rules are not duplicated across agent products.

## Choose the correct workflow

### Forge/Verify

A mature benchmark belongs in `domains/`. Open a Forge/Verify benchmark issue
before substantial implementation. The proposal must identify:

- public primary sources and the equations being reproduced;
- action, dimensions, signs, normalizations, coordinates, and units;
- UV, IR, or horizon boundary conditions and the physical ensemble;
- inputs, observables, numerical method, and failure criteria;
- analytic, convergence, residual, regression, or external-data checks;
- limitations of what a passing calculation establishes.

Add or update a valid model card and automated tests with the implementation.
Contributors using an agent may invoke `$holoforge-add-benchmark` from the
repository-scoped skills for this workflow.

### Explore

A speculative cross-domain application begins with a hypothesis card. It must
state the candidate dictionary, prior-work screen, calculable observable, and a
result that would falsify the idea. AI involvement must be recorded. Explore
work cannot be labelled established because code executes.

Before screening, classify it as a new-domain application, a new-subfield or
new-phenomenon application within a holographically studied parent field, or a
method-transfer/model-improvement project. Follow the bounded
[research-gate workflow](docs/research-gate-workflow.md); freeze each contract
before calculation and keep scientific support, owner authorization, and
disclosure status separate. Record the intake's portfolio intent and actual
domain coverage. Assess scientific opportunity before capability readiness;
the named human owner decides scientific value after reviewing importance,
gap plausibility, falsifiability, physical or conceptual holographic leverage,
computational or representational holographic leverage, explanatory depth,
outcome value, and owner fit. A computational-leverage route must compare the
hard original problem and best nonholographic baseline against the holographic
dictionary, validity regime, accessible observables, accuracy, robustness, and
total construction and compute cost; an extra dimension alone is not an
advantage. Then classify the opportunity as open discovery, strategic
development, or short-horizon execution. Publication-targeted
scorecards must name the minimum publishable physical claim, earliest honest
physical-discriminator gate and prerequisites, numerical-dependence lane,
campaign construction budget, and separate candidate-wide repair budget;
scientific-opportunity, physical-claim, source-and-novelty, and numerical-
credibility status remain non-aggregate. Capability receipts inform the route
and cost but never decide which question is valuable. When a blocker recurs,
use the workflow's bounded impasse protocol rather than
retrying indefinitely or loosening a threshold after seeing the result. A
failed first numerical repair at its declared qualification boundary requires
portfolio-level reassessment before a second repair. Every owner decision list
must include an explicit item-by-item recommendation, a concise evidence-based
reason, a completed/current/next
status summary, and the standard A-E response paths.
After a detailed contract is frozen, an owner may approve the
[`bounded autonomy window template`](docs/templates/bounded-autonomy-window-template.md)
so routine in-scope work reaches one consolidated owner return instead of many
intermediate approval gates. The window preserves mandatory returns for scope,
threshold, cost, repair, interpretation, disclosure, Git, and external-action
changes and never rolls over to another gate.
Where development is needed, include its permitted changes and recoverable
test failures in the same allowance; see [development and confirmation](docs/research-gate-workflow.md#separate-development-from-confirmation).
Failed development tests block production, not all remaining authorized
debugging. Preserve historical stops and cumulative costs. Qualification must
cover the exact implementation used for the physical comparison, including
affected reference results when a shared method changes.
When requested, maintain the optional research-progress map in the private
project; it describes research stages and branches, not HoloForge development.
When a gate closes, preserve its result and complete the generic
[research retrospective](docs/learning-from-results.md), including failed and
inconclusive gates. A technical, source, or prior-art stop must not be relabeled
as a physical negative result.

If the idea is novel, potentially publishable, or otherwise not cleared for
public release, develop it in a separate private repository by following the
[private Explore workflow](docs/private-research-workflow.md). The public
`incubator/` accepts only synthetic examples, public-literature dry runs, or
material whose owner has explicitly approved disclosure.
Contributors using an agent may invoke `$holoforge-research-gate` for a bounded
gate and `$holoforge-public-export` for any proposed private-to-public
promotion. Automated scanning supplements rather than replaces human privacy,
provenance, licensing, and scientific review.

## Pull requests

Keep each pull request narrow. Explain why the change is needed, distinguish
scientific changes from software refactoring, and list the exact verification
performed. Changes to scientific results require updated documentation and
tests. Do not submit secrets, private filesystem paths, or unpublished research
material. A pull request that exports formerly private work must identify the
public source or publication and confirm the research owner's explicit release
approval without copying confidential review or working notes.

Infrastructure changes to portable evidence or compatibility contracts must
also run `tests.test_evidence`, `tests.test_evidence_schemas`, the full suite,
and every affected public command. A passing evidence audit demonstrates
integrity and declared compatibility only; it is not a new scientific result.

By contributing, you agree that your contribution is licensed under the
project's [BSD 3-Clause License](LICENSE).
