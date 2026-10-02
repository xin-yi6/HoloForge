# Autonomous campaign workflow

This reference defines the reusable control loop for an owner-authorized
HoloForge auto-research mission. The detailed scientific work inside each
candidate still follows `holoforge-research-gate`.

## State machine

The legal nonterminal phases are:

`initialized -> searching -> screening -> selected -> discovery -> confirmation -> verification -> critique -> packaging -> awaiting-owner`

The coordinator may move from `screening`, `discovery`, `confirmation`,
`verification`, or `critique` back to `searching` when a candidate is preserved
as stopped and a pivot remains within the frozen budget. Any nonterminal phase
may move to `terminal` for a stop condition. `awaiting-owner` may move only to
`terminal`; publication and disclosure are outside this state machine.

Every transition records:

- the prior and next phase;
- the coordinator's recommendation and reason;
- the delegated decision type that authorizes it;
- evidence and candidate identifiers;
- budget totals after the transition; and
- an append-only timestamped record.

An agent recommendation is executable only when all six items are present and
the mission validator passes. Otherwise the campaign returns to the owner.

## Candidate loop

### Search and screen

Use the mission's declared domains, exclusions, search shape, authoritative
source policy, and coverage target. Read the private reviewed-knowledge and
closure-lesson indexes first. Record every serious candidate, including the
reason it was screened out.

Rank scientific opportunity without allowing capability receipts to select the
question. Every scientific Explore candidate must target a new physical
contribution beyond the closest prior work; computational or representational
advantages are supporting means, not a standalone selection route. This applies
prospectively and does not amend an existing mission or its pinned framework.
Synthetic workflow tests retain their explicitly declared nonphysical purpose.
Then evaluate execution readiness, physical discriminator, cheapest
honest test, source and novelty status, construction cost, and total numerical
dependence. Do not aggregate these distinct judgments into one misleading score.

### Select and freeze

Select only a candidate that satisfies the prospectively frozen selection
policy. Create a candidate-specific gate contract with claim, non-claim,
assumptions, dictionary, validity regime, inputs, exclusions, discriminator,
sufficiency thresholds, numerical lane, repair budget, and stop conditions.
Hash the contract before calculations.

### Discover and confirm

Discovery may use fast approximations to learn whether a candidate deserves a
confirmation attempt. Discovery output cannot bear the final claim. Confirmation
uses frozen inputs and thresholds, maintained numerical methods, convergence or
analytic checks, and a reproduction route independent enough to catch shared
mistakes.

Stop numerical refinement once the frozen evidence is sufficient for the named
physical decision. Continue only if new work can change that decision, test a
distinct physical alternative, or materially strengthen the claim.

### Verify and criticize

The verifier recomputes central results from an immutable snapshot. The hostile
critic leads with the strongest challenge, tests prior art and alternative
explanations, and distinguishes physical failure from source, numerical, and
technical stops. Neither role edits the canonical result or assigns human
approval.

### Package or pivot

Package a candidate only after its independent checks pass. If it fails or
stops, preserve its evidence, retrospective, and non-inference boundary. Pivot
only if `candidate_selection` and `candidate_pivot` were delegated and the
campaign remains within cumulative candidate, pivot, repair, and resource caps.

## Terminal outcomes

Exactly one outcome closes the mission:

- `submission-ready-candidate`: a manuscript-and-code candidate survived the
  mission's frozen checks; human review and submission remain open;
- `no-publishable-result-within-budget`: candidates were tested honestly but no
  claim met the frozen submission standard;
- `source-stop`: required authoritative evidence was unavailable or unusable;
- `prior-art-stop`: the target claim was already established or not positioned
  as required;
- `technical-stop`: a reproducible technical blocker prevented the physical
  decision and the repair budget is exhausted or ineligible;
- `budget-stop`: a declared resource ceiling was reached;
- `policy-stop`: an action crossed or would cross the mission boundary; or
- `owner-return`: an undelegated scientific or operational decision is needed.

A stopped outcome is not a lesser deliverable. It includes the same provenance,
ledger, evidence preservation, reproduction record, and retrospective needed to
prevent repeated dead ends.

## Checkpoints for adding the mode

- **AR-0 — isolation and concept:** confirm the pinned public baseline and that
  current private work is untouched.
- **AR-1 — governance:** approve the mission authority and no-touch policy.
- **AR-2 — contracts:** validate schemas, state transitions, hashes, and
  synthetic terminal packages.
- **AR-3 — private pilot:** run one low-cost, noncritical private vertical slice.
- **AR-4 — pilot review:** compare the pilot with the mission and decide which
  generic artifacts, if any, are eligible for a separately authorized public
  export.
- **AR-5 — launcher:** only after the pilot, decide whether a scheduler or
  one-command launcher is justified.

Completing one checkpoint does not authorize the next. AR-3 and later operate
outside the public HoloForge repository.
