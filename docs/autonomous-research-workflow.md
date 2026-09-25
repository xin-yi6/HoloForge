# Autonomous Research Workflow

## Purpose

HoloForge auto mode is a governed campaign in which an agent can search for
ideas, compare and select candidates, run the detailed Explore workflow, write
and test code, verify results, pivot after stopped candidates, and assemble a
paper-and-code package without asking a person to choose every recommended
option.

This is broader than a bounded autonomy window for one frozen gate. It delegates
campaign-level choices prospectively, through an exact owner-authorized mission.
It does not delegate changes to HoloForge or convert AI output into human review.

The mode is valuable because it removes routine decision latency, makes
candidate failures reusable, and allows an overnight or otherwise unattended
campaign to reach an auditable terminal state. It cannot honestly guarantee a
publication. The required handoff is a terminal package; a submission-ready
paper and code are conditional on a claim surviving the frozen scientific,
source, numerical, reproduction, and hostile-review checks.

## Two nested control layers

```text
owner-authorized autonomous mission
  -> search and candidate selection
  -> candidate-specific frozen research gate
  -> discovery and confirmation
  -> independent verification and hostile criticism
  -> package, preserve-and-pivot, or terminal stop
```

The campaign layer controls which eligible candidate runs next and whether an
in-scope recommendation is followed. Each candidate layer still follows the
claim, evidence, impasse, retrospective, and non-inference requirements in
[`research-gate-workflow.md`](research-gate-workflow.md).

An authorized candidate gate may include [bounded development](research-gate-workflow.md#separate-development-from-confirmation)
before confirmatory qualification. This does not add a campaign phase, schema
field or runtime permission. Attempt logs remain candidate artifacts; all
mission transitions, delegation checks and cumulative limits still apply.
Existing frozen missions and terminal campaigns are not migrated or reopened.

## Authorization contract

Before any research begins, copy and complete the mission example from
`.agents/skills/holoforge-auto-research/assets/` in a dedicated private project.
The mission freezes:

- the portfolio intent, research-question envelope, included and excluded
  domains, search shape, minimum publishable claim, and target venue;
- the prospective candidate-selection policy, physical discriminator,
  claim-sufficiency criteria, stop rules, and no-threshold-relaxation rule;
- explicit source, compute, wall-time, storage, and construction resource
  policies, plus finite candidate, pivot, and candidate-wide repair ceilings;
- the agent roles, sole canonical writer, allowed write roots, pinned clean
  HoloForge commit, and complete no-touch boundary;
- the decisions delegated to the coordinator and every honest terminal outcome;
- the authorization date, explicit expiry policy, and immutable mission hash; and
- the paper, code, evidence, ledger, environment, reproduction, and provenance
  artifacts required at handoff.

The owner may delegate `candidate_generation`, `candidate_selection`,
`gate_transition`, `bounded_revision`, `candidate_pivot`, `local_execution`,
and, separately, `local_commit`. Authorization is tied to the hash of the exact
mission. A preference such as “always choose option A” is not sufficient unless
these fields and limits have been approved.

Each resource field must be present. A numeric value sets an enforceable cap;
explicit JSON `null` in `source_limit`, `construction_hours`, `compute_hours`,
`wall_time_hours`, or `storage_gb` means the owner sets no cap for that resource.
It is not zero, an omitted value, or a large numeric substitute. All actual usage
remains mandatory, finite, nonnegative, and cumulative; source and other event
counts remain integers. Candidate, pivot, and repair limits stay finite. With
an uncapped resource, the coordinator still applies scientific sufficiency,
impasse, scope, integrity, and real resource-availability checks. Uncapped usage
does not delegate purchases, scope expansion, or other external actions.

The required `authorization.expires_on` field may likewise be explicit `null`
for no automatic expiry. A dated expiry remains enforceable. Active missions
always require a valid, nonfuture `authorized_on` date and exact owner authority.
These optional-cap semantics require the updated validator and mission schema;
older pinned validators reject them. A campaign using an older framework pin
must record and integrity-bind any separately audited validator/schema overlay.

## Multi-agent architecture

The preferred architecture separates responsibility and write authority:

| Role | Main responsibility | Canonical write access |
| --- | --- | --- |
| Coordinator/director | Mission state, recommendations, transitions, candidate ledger, final package | Yes, sole writer |
| Literature/prior-art auditor | Authoritative-source coverage, exact gap boundary, novelty challenges | No |
| Theory/numerics executor | Derivations, implementation, convergence and robustness evidence | No |
| Independent verifier/hostile critic | Reproduction, alternative explanations, strongest objections | No |

Read-only roles work from immutable snapshots or isolated worktrees and return
reports or proposed patches. They do not concurrently edit the canonical
checkout or approve their own results. If resources require one model to fill
more than one role, the mission records that loss of independence and cannot
claim a stronger check than was actually performed.

For an agent platform with selectable reasoning effort, use the strongest
available reasoning policy for the coordinator, candidate selection, frozen
scientific contract, final claim audit, and hostile review. Routine source
extraction, mechanical tests, and formatting may use cheaper workers. Model
names are intentionally not frozen into HoloForge because platform offerings
change; the mission records the actual model and effort used as provenance.

## Automatic decision rule

The coordinator may execute its own recommendation only when all of the
following are true:

1. the exact decision type is delegated by the mission;
2. the transition is legal in the campaign state machine;
3. the recommendation includes evidence, reason, uncertainty, and budget state;
4. the candidate and mission contracts remain byte-for-byte unchanged;
5. every declared finite resource and repair ceiling remains satisfied;
6. the action stays inside the allowed private write roots; and
7. the validator passes before and after the durable transition.

If any condition fails, the correct action is `owner-return` or another exact
stop outcome—not an improvised workaround.

## Surfaces auto mode must not touch

The public HoloForge checkout is only one immutable surface. Auto mode also must
not modify:

- another private project, central portfolio ledger, human-reviewed knowledge,
  or unrelated user file;
- a frozen mission or candidate question, model/action, dictionary, branch,
  boundary condition, ensemble, observable, threshold, exclusion, stop rule, or
  budget;
- raw evidence, logs, failed checks, stopped candidates, transition history,
  provenance, or hashes except through explicit append-only supersession;
- human review, scientific verdict, authorship, ethics, disclosure, novelty,
  peer-review, submission, or publication status;
- credentials, personal communications, undeclared accounts, cloud storage,
  global agent configuration, shell profiles, system software, or persistent
  services; or
- Git remotes, releases, repository visibility, external messages, purchases,
  accounts, submissions, and public exports.

Bounded retrieval from authoritative sources and local dependency installation
inside the dedicated environment are allowed only when the mission declares
them. See the skill's [`no-touch-policy.md`](../.agents/skills/holoforge-auto-research/references/no-touch-policy.md)
for the fail-closed list.

## Records and validation

The public repository supplies three experimental, generic schemas:

- `autonomous-mission.schema.json` freezes authority and scope;
- `autonomous-campaign-state.schema.json` records budgets, candidates, and legal
  transitions linked to the mission hash; and
- `autonomous-terminal-package.schema.json` records deliverables, independent
  checks, claims and non-claims, artifact hashes, and remaining human decisions.

Run semantic and JSON Schema validation before launch, after each durable
transition, before resume, and at terminal handoff. Use the pinned framework's
schemas and the documented test environment (which supplies `jsonschema` and
its `rfc3339-validator` timestamp checker):

```bash
python3 PATH_TO_HOLOFORGE/.agents/skills/holoforge-auto-research/scripts/validate_autonomous_campaign.py \
  campaign/autonomous-mission.json \
  --state campaign/autonomous-state.json \
  --package campaign/terminal-package.json \
  --framework-root PATH_TO_PINNED_HOLOFORGE \
  --schemas-root PATH_TO_PINNED_HOLOFORGE/schemas \
  --project-root .
```

During draft setup, omit state/package/artifact options for records that do not
yet exist. Without `--schemas-root`, only the standard-library semantic checks
run, and the result explicitly reports that schemas were not checked. That
partial pass cannot establish record completeness or launch readiness. Schema
mode fails if its dependency or a required schema is unavailable.

Structural and hash validation demonstrates control-plane consistency. It does
not establish novelty, physical truth, peer review, authorship consent, or
permission to publish.

Draft setup validation must retain an initialized state without research
transitions. Executed states require an authorized mission, and each transition
must use the decision delegated for that phase. A submission-ready candidate
must have completed the confirmation, verification, criticism, and packaging
sequence for its surviving candidate; an early stop cannot be relabelled as a
successful campaign.

At terminal handoff, always supply both `--package` and `--project-root`.
Record checks, claim evidence, and produced manuscript/code files in the
artifact manifest so the validator can check their existence and hashes.
Validation without a project root checks records only and cannot establish
that the declared files exist. These checks complement the private campaign's
append-only evidence controls and the owner's exact-hash authorization receipt.

## Checkpoint rollout

Treat auto mode as a sequence of owner checkpoints:

| Checkpoint | Evidence required | Scope opened |
| --- | --- | --- |
| AR-0 — isolation and concept | Clean pinned public baseline; existing private work confirmed untouched | Draft public governance only |
| AR-1 — governance | Owner review of authority, terminal outcomes, and no-touch policy | Contract implementation |
| AR-2 — contracts | Schemas, validator, synthetic legal/illegal transitions, and privacy tests pass | Private pilot proposal |
| AR-3 — private pilot | One low-cost, noncritical vertical slice closes with complete provenance | Pilot review only |
| AR-4 — pilot review | Failure analysis, cost, reproducibility, and leakage audit | Separate decision on generic public export |
| AR-5 — launcher | Repeated private evidence shows reusable orchestration needs | Optional scheduler or one-command launcher |

This public change targets AR-1 and AR-2. It deliberately does not add a
background scheduler, start a private campaign, or promise that a morning launch
will always produce a publishable paper by evening.

## Terminal handoff

One of eight exact outcomes ends the state machine:

`submission-ready-candidate`, `no-publishable-result-within-budget`,
`source-stop`, `prior-art-stop`, `technical-stop`, `budget-stop`, `policy-stop`,
or `owner-return`.

A submission-ready candidate includes a manuscript, code, tests, figures,
environment record, source and candidate ledgers, raw and processed evidence,
reproduction log, hostile review, non-claims, limitations, artifact hashes, and
AI provenance. The named human still decides the scientific verdict,
authorship, disclosure, and submission. Every stopped outcome preserves the same
level of auditability needed to understand what was attempted and avoid repeating
the dead end.
