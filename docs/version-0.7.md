# Version 0.7 — research workflows and evidence navigation

Version 0.7 collects the public workflow and tooling changes since 0.6.1 into
one reproducible release. It retains the existing numerical library and
reference benchmarks. A new software version does not establish a new physics
result or improved research quality.

## Included capabilities

| Area | What this release provides | Scope |
| --- | --- | --- |
| Bounded autonomous research | Mission, state and terminal-package schemas, a deterministic validator, and an agent workflow | Experimental; requires an explicitly authorized private mission and preserves human scientific and disclosure review |
| Evidence navigation | Read-only source-hash, locator and dependency checks | Optional; freshness does not imply support, correctness or approval |
| Workflow evaluation | Public synthetic cases, prospective protocols, execution measurements and recorded results | Bounded evaluation evidence, not a universal physics-progress score |
| Scientific writing and review | Manuscript, citation and figure guidance; concise report status summaries | Scientific PDFs remain the human review artifact; process diagrams are requested separately |

Start with the [autonomous workflow](autonomous-research-workflow.md),
[claim/evidence guide](claim-evidence-index.md),
[workflow evaluation](agent-workflow-evaluation.md), or
[physics manuscript guide](physics-manuscript-writing.md), according to the
task. These are repository workflows and utilities. The wheel supplies the
numerical package and its existing CLI; it does not install the repository's
agent skills, evaluation fixtures or standalone workflow scripts.

## What the evaluations establish

The [role-layout pilot](agent-workflow-evaluation.md#recorded-pilot-result--2026-09-05)
records bounded execution and token measurements; production research roles
were retained. The [36-session physics availability pilot](../evals/agent-workflows/results/physics-pilot-2026-09-21.md)
found no demonstrated benefit from making the evidence utility available:
none of the 18 availability sessions used it to inspect an index. That does
not establish harm or utility when actually used. Neither study establishes
scientific productivity, novelty judgment, empirical validation or human
review-time savings. No new mandatory evidence report is introduced.

## Compatibility and existing research

- Existing verifier commands, documented Python APIs, numerical equations,
  methods, defaults, tolerances and accepted benchmark results are retained.
  The package version recorded in new provenance becomes `0.7.0`.
- Existing model, hypothesis, evidence-bundle and capability record schemas
  retain their versions. Experimental campaign records and the optional
  claim/evidence index each use their own `0.1` version, not the package version.
- Keep the exact framework commit recorded by an existing private project or
  campaign. This release does not migrate pins, amend frozen contracts,
  authorize a new calculation or rewrite historical evidence.
- Experimental validator or schema adoption requires a prospective compatible
  pin or a separately recorded overlay under the project's authority. Do not
  apply a new validator silently to a frozen mission.
- Future routine reports use a short completed / unresolved / next decision
  or action summary. Scientific plots remain useful; process diagrams and
  separate progress PDFs are rendered only on explicit request. Historical
  PDFs and snapshots remain preserved.

For a new checkout, use the `v0.7.0` tag and the
[Python 3.11 quick start](../README.md#quick-start). Existing research need not
upgrade merely because a release is available. The
[compatibility policy](version-0.5-compatibility-policy.md) retains the earlier
protected interfaces and describes the current runtime and support scope.

## Release validation

Validate the release candidate's synchronized package, citation, README and
changelog metadata; run the complete unit suite and soft-wall verifier; build
and smoke-test an installed wheel; and check public content and links. The
required default CI covers Python 3.11 scientific tests, the historical audit,
package smoke checks and macOS wheel portability. Record results on the exact
release commit. The wider compatibility matrix remains an explicit separate
run; this release makes no new platform-support claim.
