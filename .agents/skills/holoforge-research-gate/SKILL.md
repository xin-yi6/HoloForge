---
name: holoforge-research-gate
description: Run one bounded HoloForge Explore gate, from a frozen scientific contract through verification, owner review, and closure. Use for private feasibility work or decisions about advancing a hypothesis.
---

# HoloForge Research Gate

Run one question-sized scientific gate. Scientific support, execution authority,
and disclosure are separate states; preserve negative results and stopped work.

## Select the operation and authority

For a status request, infrastructure maintenance, or model upgrade, follow
[agent maintenance](../../../docs/agent-maintenance.md) and current canonical
state. Do not start intake, calculations, or an owner decision for those tasks.

For a scientific gate, locate its recorded framework revision, frozen contract,
current state, latest owner decision, and bounded autonomy window or mission.
Read [the Constitution](../../../CONSTITUTION.md) and
[support labels](../../../docs/scientific-support.md) at the applicable revision.
For unpublished work, also follow the private project's instructions and
[private-research policy](../../../docs/private-research-workflow.md).
An approved contract or delegated action does not need repeat approval merely
because this skill is invoked again. Personal skills are methods within that
scope; they do not choose another question, broaden an audit, or authorize work.

Read these common controls before scientific execution:

- [One gate, one bounded question](../../../docs/research-gate-workflow.md#one-gate-one-bounded-question)
- [Bounded autonomy and return triggers](../../../docs/research-gate-workflow.md#use-an-owner-approved-bounded-autonomy-window)
- [Support, review, and authorization states](../../../docs/research-gate-workflow.md#three-statuses-that-must-not-be-confused)
- [Private Git authority](../../../docs/research-gate-workflow.md#local-git-record-for-private-research)

Read controlling sections fully, including linked prerequisites, and reuse that
reading at the same relevant revision. Retrieve the phase-specific sections
below when they apply; loading this skill does not require every workflow phase.
The linked policies define the scientific contract. The current request controls
routine scope and presentation choices without amending frozen research authority.

## Load the current phase

| Operation | Required policy and working records |
| --- | --- |
| New intake or candidate assessment | [Scientific opportunity](../../../docs/research-gate-workflow.md#assess-scientific-opportunity-before-execution-readiness), [portfolio intent and search scope](../../../docs/research-gate-workflow.md#declare-portfolio-intent-and-search-scope), [research horizons](../../../docs/research-gate-workflow.md#choose-one-of-three-research-horizons), [publication pathway](../../../docs/research-gate-workflow.md#keep-publication-targeted-work-physics-first), and [next-gate qualification](../../../docs/research-gate-workflow.md#record-opportunity-and-qualify-the-next-gate). Use the [intake scorecard](assets/explore-intake-scorecard.example.md); read applicable private knowledge/closure indexes and primary evidence before proposing candidates. |
| Develop, qualify or execute numerical work | [Development and confirmation](../../../docs/research-gate-workflow.md#separate-development-from-confirmation), [physical-comparison verification](../../../docs/research-gate-workflow.md#verify-the-physical-comparison), [claim-sufficiency checkpoint](../../../docs/research-gate-workflow.md#use-a-claim-sufficiency-checkpoint), and the frozen contract. Record allowed development failures prospectively; freeze the exact implementation before confirmatory qualification and use that revision for production. |
| Source inconsistency or recurring blocker | [Version-of-record audit](../../../docs/research-gate-workflow.md#check-the-version-of-record-before-a-source-stop), then the [bounded impasse protocol](../../../docs/research-gate-workflow.md#use-a-bounded-impasse-protocol) when triggered. A search result does not validate a fix. |
| A proposed model-derived repair | [Separate repair gate](../../../docs/research-gate-workflow.md#treat-a-model-derived-repair-as-a-new-gate); preserve the original source stop and obtain the required new authority before repair work. |
| Durable evidence milestone | [Research knowledge](../../../docs/research-gate-workflow.md#update-research-knowledge-during-the-gate), [consolidated state and delivery](../../../docs/research-gate-workflow.md#consolidate-current-state-and-delivery), and the [knowledge template](../../../docs/templates/research-knowledge-template.md). Preserve provisional, challenged, retired, and human-reviewed states and their primary evidence. |
| Owner review or closure | [Recommendations](../../../docs/research-gate-workflow.md#every-decision-request-includes-a-recommendation), [A-E response paths](../../../docs/research-gate-workflow.md#give-the-owner-clear-response-paths), [post-closure handoff](../../../docs/research-gate-workflow.md#repeat-the-choices-after-a-gate-closes), and [closure lessons](../../../docs/research-gate-workflow.md#learn-from-every-closed-gate). Use the [retrospective template](../../../docs/templates/research-retrospective-template.md) when closing a gate. |
| A requested or needed owner-review PDF | [Conditional PDF policy and visual QA](../../../docs/research-gate-workflow.md#owner-review-pdf-packet) and the [review template](../../../docs/templates/review-packet-template.tex). Prepare and inspect the packet before the scientific decision when the policy requires it. |
| A requested research-progress view | [Progress-state policy](../../../docs/research-gate-workflow.md#agent-updated-workflow-snapshot) and [rendering guide](../../../docs/research-progress-snapshots.md). Use [the state example](assets/research-progress.example.json) and [renderer](scripts/render_research_progress.py); keep state and figures project-local. |

## Execute and return within the contract

Complete authorized sources, derivations, implementation, frozen checks, evidence,
knowledge updates, and hostile criticism without pausing at routine choices.
Use maintained numerical libraries when suitable and preserve actual execution
provenance. At the first declared stop or outcome, finish the permitted stop
record and return; do not expand a repair, loosen a threshold, or hide a failure.
An explicitly recoverable development test is not a milestone stop. Follow the
approved phase boundary; never infer that exception for an older contract.

Lead with the bounded outcome, supported and unsupported claims, verification,
critic findings, and any remaining uncertainty. At a real owner decision,
provide item-by-item recommendations and completed/current/next status with
the applicable A-E paths, including the option to remain paused. Apply the same
handoff policy after a gate is closed. Do not fabricate pending choices for a
terminal record with `awaiting_owner: false`.

Commit only reviewed files when the recorded authority explicitly includes
that local Git action. Scientific acceptance alone does not authorize Git,
another gate, external communication, private export, or disclosure.
