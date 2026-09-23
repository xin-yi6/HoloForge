# Research knowledge base

## Metadata

- Research owner:
- Portfolio or project scope:
- Disclosure status: private / public-safe synthetic / approved for release
- Canonical file:
- Last reviewed Git revision:
- Generated or maintained with AI assistance: yes / no

## Evidence boundary

This file connects working observations and reviewed knowledge to their primary
records. It does not replace papers and source notes, frozen contracts, result
records, machine-readable evidence, hostile criticism, owner decisions,
closure retrospectives, or Git history.

Working knowledge is provisional. It may guide the next verification check but
must not change a frozen contract, acceptance threshold, support label, or
owner decision. A reviewed item receives a stable knowledge ID only after a
named human checks its evidence, scope, support level, and non-inference
boundary. Closure lessons are a reviewed subtype and receive stable lesson IDs
only after owner-reviewed closure.

## Knowledge classes

Use one or more classes. These are views within one knowledge base, not
separate databases:

- `literature/source` — scoped claims, equations, conventions, provenance,
  coverage limits, and disagreements from papers or other authoritative
  sources;
- `model/dictionary` — assumptions, source-response dictionaries, ensembles,
  branches, observables, and applicability domains;
- `analytic/derivation` — identities, limits, derivations, consistency checks,
  and unresolved steps;
- `numerical/method` — solver behavior, convergence, conditioning,
  diagnostics, tolerances, and representation dependence;
- `data/comparison` — dataset versions, transformations, uncertainty,
  licensing, and comparison conventions;
- `result` — positive, negative, conditional, inconclusive, or stopped bounded
  findings;
- `decision/workflow` — owner decisions, cost-saving checks, process changes,
  and their rationale; and
- `tooling/reproducibility` — reusable code, tests, environments, and artifact
  procedures.

Do not turn the knowledge base into a second paper library or lab notebook.
Admit a distilled item only when it is reusable or decision-relevant,
evidence-linked, scoped, non-duplicative, and explicit about uncertainty.
Summarize literature in original words and link an exact source version and
locator instead of copying substantial source text.

## Working knowledge queue

Create or update an entry after a durable research milestone changes the
evidence boundary: source review, contract freeze, calculation, verification,
hostile criticism, owner decision, or gate closure. Keep superseded or failed
observations visible by changing their status instead of deleting them.

Allowed lifecycle states are:

- `provisional` — newly observed and not independently checked;
- `corroborated` — supported by a named check but not yet owner reviewed;
- `challenged` — contradicted, incomplete, or exposed to a strong alternative;
- `ready for owner review` — bounded evidence and non-inference language are
  complete;
- `promoted` — human reviewed and linked to a stable knowledge or lesson ID;
  and
- `retired` — rejected, superseded, or judged non-reusable, with the reason
  preserved.

### WK-YYYYMMDD-NNN — short title

- **Project or gate:**
- **Knowledge class:** literature/source / model/dictionary /
  analytic/derivation / numerical/method / data/comparison / result /
  decision/workflow / tooling/reproducibility
- **Captured at:** source review / contract freeze / calculation / verification /
  hostile criticism / owner decision / gate closure
- **Updated on:**
- **Lifecycle state:** provisional / corroborated / challenged /
  ready for owner review / promoted / retired
- **AI provenance:**
- **Primary evidence and exact locator:** DOI, arXiv or document version, page,
  equation, figure, dataset version, commit, result file, or decision record
- **Scientific support level:** hypothesis / internally-derived /
  established-source / reproduced
- **Review state and reviewer:** unreviewed / checked / approved; name and date
- **Observation:**
- **What held:**
- **What failed or remains unresolved:**
- **What must not be inferred:**
- **Next discriminating check:**
- **Applicability boundary:**
- **Promotion or retirement record:** pending / stable knowledge ID and review
  record / stable lesson ID and closure retrospective / retirement reason and
  decision link

## Reviewed knowledge index

Promote a reusable knowledge item only after a named human review confirms the
statement, primary evidence, exact scope, support level, review state, and
non-inference boundary. Use stable knowledge IDs such as `HF-K001`. Literature
reading alone is not promotion: the reviewed item must cite an exact source
version and locator, represent disagreements or coverage limits, and avoid
claiming that a targeted search was exhaustive.

| Stable knowledge ID | Knowledge class | Retrieval tags | Reviewed statement | Primary evidence and locator | Support and review state | Applicability and non-inference boundary |
| --- | --- | --- | --- | --- | --- | --- |

## Stable closure lesson index

Add a stable lesson only after the gate outcome and retrospective receive owner
review. Link the working entry, primary evidence, closure retrospective, and
decision record. Use stable lesson IDs such as `HF-L001`. Never replace those
records with the summary here.

| Stable lesson ID | Retrieval tags | Accepted outcome | Primary evidence | Reusable lesson | Non-applicability boundary | Reopening trigger |
| --- | --- | --- | --- | --- | --- | --- |

## Update protocol

1. Read the current knowledge base and Git revision before changing it.
2. Update it in the same bounded work session that records a durable milestone.
3. Link evidence; do not store an unsupported conversational conclusion.
4. Record lifecycle-state changes and retain challenged or retired entries.
5. Update canonical project status when the milestone also changes stage.
   Keep attempt history and decisions; render a process diagram only on an
   explicit owner request, not as another required knowledge report.
6. Promote literature, derivation, method, data, decision, or tooling knowledge
   only after its named review; do not wait for failure or gate closure when a
   durable review milestone already exists.
7. At closure, promote only owner-accepted reusable lessons and leave other
   entries challenged, provisional, or retired as appropriate.
8. Commit the knowledge update with the reviewed milestone it describes.

This is an agent-updated research record, not background telemetry. A live file
is current only through its recorded revision and last evidence-linked update.
