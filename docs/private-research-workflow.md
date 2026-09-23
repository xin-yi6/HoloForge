# Private Explore Research Workflow

This workflow lets a researcher use HoloForge for genuinely novel work without
publishing the project before they are ready. Scientific support and public
visibility are separate decisions.

## Three locations with different purposes

1. **Public HoloForge repository** — reusable framework code, schemas,
   published benchmarks, synthetic examples, and material explicitly cleared
   for release.
2. **Separate private research repository** — unpublished hypotheses, detailed
   literature notes, calculations, intermediate results, manuscript drafts,
   and confidential collaboration material.
3. **Reviewed public reproduction package** — the minimum code, inputs,
   provenance, tests, and documentation needed to reproduce results that have
   been accepted for publication or otherwise approved for disclosure.

The private repository should have restricted access and its own history. Do
not place it inside the public HoloForge checkout. The ignored directories
`/.private-research/` and `/unpublished/` are last-resort accidental-commit
guards, not secure storage.

## Private project structure

A private project may reuse the public HoloForge package and schemas while
keeping its research record independent:

```text
private-project/
  README.private.md
  autonomous-mission.json       # only for auto mode
  autonomous-state.json         # only for auto mode
  hypothesis-card.json
  RESEARCH_LESSONS.md
  notes/
  code/
  results/
  RETROSPECTIVE.md
  paper/
  terminal-package.json         # only for auto mode
```

The private project should pin the HoloForge version or commit it depends on,
record its own environment, and preserve negative results. It may extend the
public schemas locally, but those extensions are not automatically part of the
HoloForge public contract.

Use `RESEARCH_LESSONS.md` as the inspectable private knowledge base, following
the generic [`research-knowledge-template.md`](templates/research-knowledge-template.md).
Maintain two visibly separate states in that file: a working queue updated
after durable research milestones, and reviewed knowledge whose evidence,
scope, support level, review state, and non-inference boundary were checked by
a named human. Reviewed knowledge can come from literature, dictionaries,
derivations, methods, data, results, decisions, or reproducibility work;
closure lessons remain a subtype admitted only after owner-reviewed closure.
Working entries may be provisional, corroborated, challenged, ready for owner
review, promoted, or retired. A live observation may sharpen the next check,
but it must not silently become reviewed knowledge or rewrite the frozen gate.

## Autonomous campaign option

For unattended, campaign-level execution, use the separate
[`autonomous-research workflow`](autonomous-research-workflow.md) and
`$holoforge-auto-research` skill. This is not a larger bounded-autonomy window:
the owner prospectively authorizes an exact portfolio envelope, selection
policy, set of decisions, budgets, no-touch boundary, and terminal outcomes.
Within that frozen mission the coordinator may generate and select candidates,
run repeated detailed gates, follow its own in-scope recommendations, and pivot
without a person repeatedly choosing option A.

The campaign must use a dedicated private repository, a clean read-only
HoloForge pin, one canonical writer, and read-only specialist agents. It must not
modify another active private project or its central ledgers. Publication,
authorship, disclosure, human review, changes to scientific thresholds, and
remote or external actions remain separate owner decisions. Use a distinct
mission for every campaign; authority never rolls into a new question envelope.

## Research gates

The concise gate sequence below is expanded in the reusable
[research-gate workflow](research-gate-workflow.md), including frozen
contracts, hostile critic reports, owner decisions, local Git records, and the
standard PDF review-packet style. Every request for owner approval or choice
must also include an item-by-item recommendation and its reason, an A-E
response menu, and a completed/current/next status summary. Routine scientific
reports retain equations, results, uncertainty and useful physics figures;
use a short status summary without a research-process diagram or separate
progress PDF. Generate those optional views only on explicit owner request,
even if older reports used them. Keep status, attempt history, evidence links
and decisions current; preserve historical snapshots and reviewed packets.
Requested views remain project-local; see the
[snapshot style guide](research-progress-snapshots.md).

After an approved gate is recorded and closed, report completed/current/next
status. Present fresh A-E choices when an actual next owner or portfolio
decision is pending, including when its recommendation is to remain paused.
If no such decision is pending, report completion or the recorded pause without
inventing another approval menu. The new menu does not reopen the completed gate
or authorize a calculation. A separate portfolio choice must be identified as
a separate gate; never insert false pending state into a closed project with
`awaiting_owner: false`. Follow the [post-closure handoff policy](research-gate-workflow.md#repeat-the-choices-after-a-gate-closes).

After a detailed gate contract is frozen, the owner may reduce unnecessary
interruptions by approving a project-local
[`bounded autonomy window`](templates/bounded-autonomy-window-template.md).
The window lets the agent finish the listed routine source, derivation,
implementation, verification, criticism, knowledge, progress, and report work
before one consolidated return. It must retain explicit cost and repair
ceilings and mandatory returns for scientific-scope or threshold changes,
stops and impasses, interpretation or publication judgments, disclosure,
external communication, and Git or remote actions. It never rolls over to a
new gate or candidate. The owner may approve it together with the frozen
contract so the window does not introduce an extra decision gate.

1. **Intake:** read the current private reviewed-knowledge and closure-lesson
   indexes and record which stable knowledge and lesson IDs and evidence apply
   to this candidate. Translate each into a candidate-specific control; if none
   applies, record the knowledge classes and tags searched. Then record the
   portfolio intent, search shape, domains considered or deliberately excluded,
   and candidate-pool coverage. Before inspecting capability receipts or
   ranking by cost, complete the scientific-opportunity assessment: physical
   importance, gap plausibility, falsifiability, physical or conceptual
   holographic leverage, computational or representational holographic
   leverage, explanatory or predictive depth, outcome value, and fit with the
   named human owner's expertise and portfolio. A computational-leverage claim
   must name the hard original problem, best nonholographic baseline,
   dictionary and validity regime, accessible observables, accuracy, and total
   construction and compute cost. The agent supplies evidence and a
   recommendation; the owner decides scientific value and investment.

   Then choose an honest horizon: open discovery, strategic development, or
   short-horizon execution. For publication-targeted work, complete the
   separate publication-pathway assessment and record the minimum publishable
   physical claim, earliest honest physical-discriminator gate and its
   prerequisites, numerical-dependence lane, campaign construction budget,
   separate candidate-wide numerical-repair budget, and non-aggregate
   scientific-opportunity, physical-claim, source-and-novelty, and numerical-
   credibility status. Only the short-horizon lane normally reaches the
   physical discriminator in the first or second detailed gate.

   Finally record the candidate dictionary, assumptions, falsification test,
   AI involvement, and decision owner in a private hypothesis card. Qualify the
   proposed next gate through gate-complete inputs, an invariant target beyond
   the generic baseline, the cheapest honest discriminating test, a positive-
   result endpoint, and a cost ceiling. A conditional item may open one bounded
   evidence task or one owner-approved strategic-development milestone. A
   failed gate prerequisite stops that gate without declaring the scientific
   opportunity valueless.
2. **Screening:** search prior work and test dimensional, symmetry, boundary,
   and ensemble consistency before investing in a large calculation.
3. **Discriminating calculation:** compare against a simpler baseline and use a
   preregistered keep/reject criterion where practical.
4. **Live knowledge update:** after source review, contract freeze,
   calculation, verification, criticism, and owner decisions, update the
   evidence-linked working queue and preserve its non-inference boundary.
   Distill decision-relevant paper knowledge with an exact source version and
   locator; do not copy every paper note into the knowledge base.
5. **Internal decision and reflection:** retain, revise, or reject the
   hypothesis, then complete the generic
   [closure retrospective](templates/research-retrospective-template.md). Record
   the outcome class, evidence, lesson, non-inference boundary, prospective
   workflow change, and reopening trigger. Keeping the work private does not
   change its scientific-support label.
6. **Publication:** submit and revise the paper without copying confidential
   correspondence into the public project.
7. **Release review:** after journal acceptance or another explicit disclosure
   decision, select the exact artifacts that may become public.

### When a gate becomes stuck

When a blocker recurs or the repair budget is nearly exhausted, first honor
the current window or mission's [mandatory return triggers](research-gate-workflow.md#use-an-owner-approved-bounded-autonomy-window).
If a return is required or the budget is exhausted, preserve the permitted stop
record and return before further investigation or repair. The impasse protocol
does not itself authorize another search, audit, calculation, or budget increase.

Within explicitly authorized investigation scope and remaining limits, follow
the [bounded impasse protocol](research-gate-workflow.md#use-a-bounded-impasse-protocol):
classify the blocker, search targeted authoritative evidence, audit the physics
independently, inspect the relevant implementation, and prepare at most one
scoped repair proposal. Execute a repair only under its required frozen
authority. Internet search locates evidence; it does not validate a fix. Preserve
an unresolved source or technical stop if the bounded repair fails; do not
silently loosen thresholds or expand the hypothesis.

For publication-targeted work, the repair budget is cumulative across the
candidate, not reset by each small gate. After a first numerical repair fails,
return to a portfolio-level reassessment. A second repair requires a new owner-
approved rationale showing that it directly unlocks the already frozen
physical discriminator within the remaining cost ceiling. Otherwise pause or
pivot the candidate. Planned, owner-approved model and capability construction
uses the separate campaign construction budget and is not counted as a repair.
Every prerequisite milestone must remain necessary for the selected physical
question and retain a planned physical checkpoint; generic infrastructure work
cannot be treated as hidden research progress.

## Public export checklist

Before copying any artifact into HoloForge, a human reviewer must confirm:

- the research owner explicitly approved the public export;
- every result is published or otherwise cleared for disclosure;
- claims cite public sources or an accepted publication;
- secrets, credentials, private paths, restricted data, confidential notes,
  reviewer correspondence, and unrelated history are absent;
- the package contains only the inputs and outputs needed for reproduction;
- model or hypothesis cards, environment metadata, tests, limitations, and
  licensing are complete;
- the export is reviewed as a narrow pull request before merge and release.

If confidential material is accidentally committed, stop publication, revoke
any exposed credential, and remove the material from all reachable history
before continuing. Deleting only the latest file is not sufficient once a
commit has been shared.
