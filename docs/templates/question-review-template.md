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
- **Date, card hash and report hash:** `<ISO date; hashes>`

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
