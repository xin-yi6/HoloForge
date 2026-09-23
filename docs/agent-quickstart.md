# Using HoloForge with a coding or research agent

This guide is for a new contributor who has cloned HoloForge and wants an AI
agent to inspect, run, or extend it safely. The agent assists with the work;
the repository's tests, scientific contracts, and human review remain the
sources of authority.

## 1. Clone and verify the project yourself

From a terminal, create an isolated environment and install the checkout:

```bash
git clone https://github.com/xin-yi6/HoloForge.git
cd HoloForge
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
holoforge verify soft-wall-vector
python -m unittest discover -s tests -v
```

Conda users may create and activate a dedicated Python 3.11 environment
instead. A passing command verifies the implementation against its declared
gate; it does not prove that the model is a complete description of nature.

## 2. Start the agent at the repository root

Open the cloned `HoloForge` folder as the agent's workspace. Starting in a
parent directory can prevent repository instructions or skills from being
loaded.

- **Codex:** open the folder in Codex or start Codex from the repository root.
  Codex reads `AGENTS.md`; supported versions also expose the workflows under
  `.agents/skills/`.
- **Claude Code:** enter the repository and run `claude`. Claude Code reads
  `CLAUDE.md`, which imports the same canonical `AGENTS.md` instructions.
- **Other agents:** open the repository root and explicitly ask the agent to
  read `AGENTS.md`. If it does not support repository skills automatically,
  direct it to the appropriate `.agents/skills/*/SKILL.md` file.

Agent products change over time. If automatic context loading is uncertain,
use the explicit first prompt below and check that the agent names the
scientific and privacy boundaries before allowing edits.

## 3. Use an inspect-only first prompt

Copy this as the first request in a new agent session:

```text
Read AGENTS.md, README.md, and the relevant scientific documentation. Inspect
the Git status and repository structure without changing files. Explain:
1. HoloForge's Forge/Verify and Explore modes;
2. which existing command demonstrates a working installation;
3. which workflow applies to my intended task; and
4. what requires human scientific or disclosure approval.
Do not implement anything until you have shown the proposed scope.
```

This establishes that the agent is operating in the correct checkout and has
understood the project before it writes.

For an existing workspace, model upgrade or maintenance hold, use the
[maintenance and resumption guide](agent-maintenance.md). Previously recorded
authorization for the exact task remains usable; rereading a skill does not
require another approval. Open a private workspace through its own `AGENTS.md`
and current-state pointers, and preserve the framework pin of every frozen gate.

## 4. Choose one task type

### Run an existing benchmark

Ask the agent to run one documented command and explain the result against its
acceptance gate. For example:

```text
Run the soft-wall-vector verifier using the documented environment. Explain
the analytic reference, numerical method, acceptance tolerance, and what a
passing result does and does not establish. Do not change files.
```

The available commands and benchmark guides are listed in `README.md`.

Before choosing or running a benchmark, inspect its exact declared public
capabilities without executing the solver:

```text
Run `holoforge inspect benchmark BENCHMARK --json`. Compare my requirement only
with exact capability IDs in the receipt. Report qualified items, known gaps,
and undeclared items separately. Do not infer that the receipt establishes
truth, novelty, publishability, or support for a new post-processing route.
```

Repeat `--require CAPABILITY_ID` to make the CLI classify exact identifiers.
Exit `0` means every requested identifier is declared qualified; exit `1`
means at least one requested identifier is a known gap or is not declared.
No solver runs during inspection.

To retain a portable, integrity-checked record, ask the agent to add
`--bundle-dir` to the selected command and run `holoforge audit bundle` on the
result. The [evidence-bundle guide](evidence-bundles.md) explains what the
audit establishes, the narrower `same-state-family` compatibility check, and
the disclosure review still required before sharing an artifact.

### Add a public Forge/Verify benchmark

Use a published, established model and request the benchmark workflow:

```text
Use the holoforge-add-benchmark workflow. First inspect the repository and
write a bounded benchmark contract with primary-source provenance, equations,
boundary conditions, numerical checks, acceptance gates, documentation, and
tests. Show the contract before substantial scientific implementation.
```

The procedure is stored at
`.agents/skills/holoforge-add-benchmark/SKILL.md`.

### Begin private Explore research

Do not develop unpublished research inside the public clone. Create a separate
access-controlled repository, pin the HoloForge release or commit it uses, and
open that private repository as the agent's primary workspace. Give the agent
read access to the public HoloForge checkout or copy the released generic
workflow with its provenance, then ask it to read
`.agents/skills/holoforge-research-gate/SKILL.md` from HoloForge.

Use a prompt such as:

```text
This is a separate private research repository using a pinned HoloForge
release. Run one bounded holoforge-research-gate workflow. Freeze the question,
inputs, exclusions, acceptance and stop conditions before calculation. Keep
scientific support, authorization, and disclosure status separate. Do not
publish, transfer, or disclose any artifact without a later explicit review.
```

Before the detailed gate, ask the agent to copy and complete
`.agents/skills/holoforge-research-gate/assets/explore-intake-scorecard.example.md`
inside the private repository. First ask it to assess the scientific
opportunity independently of current capabilities: importance, gap
plausibility, falsifiability, holographic leverage, explanatory depth, outcome
value, and owner fit. The agent recommends; the named human owner decides
whether the question deserves investment. Then choose open discovery,
strategic development, or short-horizon execution and qualify the proposed
next gate through its inputs, discriminator, cheapest honest test, endpoint,
cost, and stop rules. A failed next-gate prerequisite stops that gate, not the
scientific value judgment. Publication-targeted work must name the minimum
publishable physical claim, earliest honest physical-discriminator gate and
prerequisites, numerical-dependence lane, campaign construction budget, and
separate repair budget, while tracking scientific opportunity, physical-claim
progress, source and novelty readiness, and numerical credibility separately.
Only short-horizon execution normally reaches the discriminator in the first
or second detailed gate.

To let the agent work for a longer interval without weakening owner control,
freeze the detailed gate first and then approve a project-local copy of
[`bounded-autonomy-window-template.md`](templates/bounded-autonomy-window-template.md).
The agent may prepare the window with the contract so both can be approved in
one owner decision.
A useful request is:

```text
Use the frozen gate contract to prepare a bounded autonomy window. List the
routine work you may finish without another decision, the source, compute and
repair ceilings, the return milestone, and every mandatory return trigger.
After I approve that window, continue through the in-scope verification and
review packet without asking me to approve each intermediate source, plot,
test, or implementation choice. Return immediately if the scientific scope,
threshold, cost, repair, disclosure, Git, or external-action boundary changes.
```

This delegates execution only. It does not delegate the physical verdict,
novelty or publication judgment, disclosure decision, or permission to push,
merge, release, or start another gate.

If the same blocker recurs, ask the agent to use the bounded impasse protocol:
classify the problem, inspect targeted authoritative external evidence, audit
the physics independently, inspect the corresponding numerical or software
layer, and propose at most one costed repair before returning for approval.
Internet search locates evidence; it does not validate a fix or authorize a
post-hoc threshold change. For a publication-targeted candidate, a failed first
repair triggers portfolio-level reassessment; a second repair needs a new
owner-approved rationale showing that it directly unlocks the frozen physical
discriminator.

At each owner gate, and again after an approved gate is recorded and closed,
the agent should state what is completed, the current stage, the proposed next
stage, and what remains closed. It should then offer five paths: A, approve all
recommendations; B, approve selected decisions; C, request revision or
evidence; D, receive a status walkthrough only; or E, write a custom response.
The post-closure menu applies only to the next eligible handoff and must not
silently reopen the completed gate. Use a short completed / unresolved / next
decision or action summary in routine reports. A process diagram and separate
progress PDF are not required, including for projects that used them before.
When an overview would help, explicitly request the optional project-local
research picture with:

```text
Update the research-progress state and render the current research map. Show
literature screening, the frozen gate, parallel theoretical and numerical
checks, verification, decision branches, completed/current/pending status, and
the exact next action. Do not show HoloForge's software-development timeline,
and do not treat this status request as approval for further work.
```

The snapshot is updated for the requested view; it is not a background monitor.
Keep canonical research records current and generated views in the private
project. Include a dated process figure in a scientific PDF only if that figure
is explicitly requested. Preserve historical snapshots; GitHub can show only
the last committed and pushed state.

See `docs/private-research-workflow.md` for the recommended private structure.

### Draft or revise a physics manuscript

Use the [physics-manuscript writing guide](physics-manuscript-writing.md)
inside the separate private research repository. A paper develops the physical
argument; the review packet records owner decisions and workflow status. Keep
necessary methods and consequential limitations in the paper, with detailed
audit history in a private companion record. Ask for a distinguishable revised
draft, an evidence-preserving change note and a rendered PDF review. An
editorial request does not authorize new calculations or submission.

### Run a governed autonomous research campaign

Use auto mode only from a dedicated access-controlled research repository, not
from the public HoloForge checkout or another active private project. First ask
the agent to use `$holoforge-auto-research` to prepare a mission from the
synthetic examples and validate it without starting research:

```text
Prepare a HoloForge autonomous-research mission for owner review. Freeze the
research envelope, candidate-selection policy, physical and claim-sufficiency
criteria, budgets, delegated decisions, sole-writer multi-agent roles, pinned
read-only HoloForge commit, no-touch surfaces, and all terminal outcomes. Do
not start candidate search until I explicitly authorize the exact mission hash.
```

After that one authorization, the agent may search, select, execute, verify,
preserve-and-pivot, and package candidates only inside the mission. It must
return a submission-ready candidate or an audited stopped package; it cannot
guarantee a paper, change the framework or thresholds, assign human review,
publish, disclose, communicate externally, or perform remote Git actions.
The [autonomous research workflow](autonomous-research-workflow.md) defines the
AR-0--AR-5 rollout and validator.

### Propose a private-to-public export

Only do this after the research owner explicitly clears the exact artifact for
release:

```text
Use the holoforge-public-export workflow. Freeze the exact export scope, audit
every proposed file for unpublished science and private information, check
provenance and licensing, run the deterministic scanner and public tests, and
stop before publication if any authorization is missing.
```

## 5. Understand the three control layers

Repository context is deliberately split:

1. `AGENTS.md` gives short instructions that should apply in every agent
   session.
2. `.agents/skills/` contains task-specific, reusable procedures loaded only
   when relevant.
3. `CONSTITUTION.md` and `docs/` contain the durable scientific contracts that
   both humans and agents must inspect.

Prompts can select a task, but they must not silently override the Scientific
Constitution, privacy boundary, frozen acceptance gates, or requirement for
human disclosure approval.

## 6. Before accepting agent-generated changes

Confirm that the agent has:

- preserved unrelated files and shown the exact diff;
- used public sources and maintained numerical libraries where appropriate;
- selected meaningful checks using the [change-based validation policy](agent-maintenance.md#choose-checks-that-can-establish-the-intended-behavior),
  including the full suite and relevant verifier for executable or scientific
  changes, or affected link, skill, and policy checks for documentation;
- completed required default CI before accepting a public integration;
- kept support claims within the evidence;
- excluded private paths, secrets, unpublished results, and confidential
  material;
- used the standing public-repository commit/push authorization in `AGENTS.md`
  within its scope, verified the remote commit, and reported CI; and
- obtained separate authority for merging, releasing, private export or
  scientific disclosure, and honored any narrower task or frozen-campaign
  restriction.

For contributions, continue with `CONTRIBUTING.md` and submit a narrow pull
request that lists the checks performed.
