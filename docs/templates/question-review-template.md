# Independent Question Review

Use these records for an owner-selected pilot use of
[Review the question independently](../research-gate-workflow.md#review-the-question-independently).
The author writes one card. One reviewer from a different provider or model
family reads only that card and public literature, in a fresh context. Its
report is preserved unchanged before the author replies.

A review is evidence for the named human research owner. It is not human
review, independent replication, or a novelty or publication certificate. It
opens no calculation and changes no frozen contract or threshold. Keep
completed cards, reports and replies in the private research repository.

A card carries an unpublished question even without numbers, code or
identifiers. Before sending it to any service, confirm that the owner has
approved the exact content class, recipient and service account, and that the
service's data-use terms have been checked.

When the review runs through `run_question_review.py`, the owner's private
reviewer configuration is that approval. The runner fills in the fixed
reviewer prompt, and its receipt records the reviewer, the hashes and the
message actually sent; the reviewer's own statements stay in its report.

## Scope brief

Written by the author of an intake after recording its own seed list, when the
owner has selected independent candidate proposals. It is sent with the fixed
proposal prompt, and each proposer returns at most five candidates. Proposed
seeds are screened like every other seed; a proposer's novelty statement is a
locator to verify, not evidence.

- **Portfolio intent and search shape:** `<as declared for the intake>`
- **Domains included:** `<scientific domains or subfields>`
- **Domains excluded, with the public reason:** `<domains, or none>`
- **Kind of contribution sought:** `<physical comparison | analytical result |
  computational or methodological advantage | any>`
- **Public constraints:** `<research horizon, model families or methods
  available, cost class>`
- **Owner-approved recipients for this brief:** `<decision record>`

Leave out unpublished candidates, results, private identifiers and the record
of stopped directions. Compare the proposals with private closures only after
they are received.

## Comparison card

Written by the author when the owner asks for independent advice before a
construction investment, after the author has sealed its own recommendation.
It is sent with the fixed construction-choice prompt. It belongs to the
question class and must fit the card limit.

For each eligible candidate, without saying who proposed it:

- **Question, in one sentence:** `<question>`
- **Physical payoff and readers:** `<what would be learned, and for whom>`
- **Deciding test:** `<what could fail, and what a negative would show>`
- **Construction cost and uncertainty:** `<estimate, confidence and main
  prerequisites>`
- **Main risk:** `<strongest reason it might not be worth the investment>`

Then once for the card:

- **Owner-approved recipients for this card:** `<decision record>`

Leave out results, private identifiers, proposer labels and the record of
stopped directions.

## Derivation setup

Written and sealed by the author of an analytic gate before it derives, when
the outcome may need a blind re-derivation. It is sent with the fixed
re-derivation prompt only if the author's own outcome is decisive. The
reviewer never sees the author's result.

- **Model or action:** `<exact action or model, with its source>`
- **Definitions and conventions:** `<fields, normalizations, signs, boundary
  terms>`
- **Fitted or fixed inputs:** `<what is calibrated and to what>`
- **Target quantity, order and regime:** `<what to determine, at which order,
  in which regime>`
- **Comparison, if any:** `<the description the result is compared with>`
- **Owner-approved recipients for this setup:** `<decision record>`

Leave out the author's result, expectation and any private identifier. If the
setup does not fit within the card limit, it is too large for this check.

## Question card

Written by the author after the intake scorecard is prepared, to inform the
owner's investment decision. One page is a target; do not omit a decisive
assumption, relation or shared input to meet it.

- **Question, in one sentence:** `<question>`
- **Contribution type:** `<physical comparison | analytical result |
  computational or methodological advantage>`
- **Planned comparison, derivation or named baseline:** `<what is compared
  with what; for a computational claim, the best nonholographic baseline for
  the same problem and regime>`
- **Inputs that already encode the answer, and shared inputs:** `<list, or
  none>`
- **Outcome value:** `<what a positive, a negative and an inconclusive outcome
  would each change for the intended readers>`
- **Closest prior work known to the author:** `<sources and search scope>`
- **Model, regime and necessary assumptions:** `<short statement>`
- **Owner-approved recipients for this card:** `<decision record>`

## Claim card

Written by the author after the claim-bearing result, or after a material
change in the central claim. A card-only review can assess framing and
contribution; it cannot certify that the calculation establishes the claim.

- **Claim registered before the work:** `<preserved as registered>`
- **Claim that survives, in one sentence:** `<claim>`
- **Contribution type:** `<physical comparison | analytical result |
  computational or methodological advantage>`
- **Model, regime, necessary assumptions and named comparison:** `<short
  statement; for a computational claim, the nonholographic baseline for the
  same problem and regime>`
- **Excluded or stopped on the way, and why:** `<list>`
- **Evidence boundary:** `<analytic | numerical | comparison; what is
  established and what is not>`
- **Inputs that already encode the answer, and shared inputs:** `<list, or
  none>`
- **Intended readers:** `<community or subfield>`
- **Owner-approved recipients for this card:** `<decision record>`

## Reviewer report

- **Provider, model and effort, as reported by the platform:** `<value or
  unavailable>`
- **Differs from the author's provider or model family:** `<yes | owner-approved
  fallback, with the decision record>`
- **Actual input scope and prior exposure to this project:** `<statement>`
- **Date and card hash:** `<ISO date; hash>`

Do not write the report's own hash inside the report. The canonical writer
records the hash of the unchanged final report in the existing execution
receipt.

Answer each item with `pass`, `concern` or `fail`, a reason of at most five
lines and an evidence locator. Use `concern` when the card gives too little
information. Do not give an aggregate score.

| Item | Verdict | Reason and locator |
| --- | --- | --- |
| 1. What is claimed, and what could undermine it? Is agreement already forced by shared assumptions, shared inputs, an identity or a fit? For an analytical result, what is new beyond a restated identity? For a computational claim, which named nonholographic comparison could refute the advantage? | `<verdict>` | `<reason>` |
| 2. Who uses the result, and what would each outcome change for them? | `<verdict>` | `<reason>` |
| 3. What is new against the closest prior work found? State the search scope. | `<verdict>` | `<reason>` |
| 4. Strongest supported referee objection. | `<verdict>` | `<objection>` |
| 5. Optional: a better question. | `<verdict or not answered>` | `<proposal, or none>` |

- **Overall reading:** `<one paragraph, no score>`

## Author reply

| Item | Reply | Evidence | Proposed action and authority needed |
| --- | --- | --- | --- |
| `<1–5>` | `<Confirmed | Disputed | Already known | Needs owner decision>` | `<locator>` | `<action, or none>` |

Brief factual clarification and one rebuttal round are allowed. Disputed items
go to the owner.

## Owner disposition

- **Disputed items decided:** `<item and decision, or none>`
- **Effect on the investment or drafting decision:** `<continue | revise the
  question | pause | decline>`
- **Work opened:** `<exact scope, or none>`
- **Work remaining closed:** `<scope>`

## Pilot record

- **Supported, useful objections not already in the project's records:** `<count>`
- **Unsupported or irrelevant concerns:** `<count>`
- **Owner disposition of the items:** `<counts; a disposition, not proof>`
- **Reviewers used and handling time:** `<count; time or unknown>`
