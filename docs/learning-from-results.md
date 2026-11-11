# Learning Throughout Research

Research knowledge does not come only from failures or closed gates. HoloForge
captures reusable, evidence-linked knowledge while reading literature,
defining a model dictionary, deriving equations, selecting data, calculating,
verifying, criticizing, deciding, and closing a gate. Positive, negative,
inconclusive, conditional, source-stopped, prior-art-stopped, and technically
stopped results are all possible sources of knowledge.

A research gate is useful even when it stops a hypothesis. HoloForge therefore
also preserves both the evidence and a short closure retrospective for every
closed Explore gate.

The retrospective is not a substitute for the result record. The result says
what the frozen gate established. The retrospective says how that bounded
experience should improve later candidate selection, contracts, methods, or
verification.

## Two-state research knowledge base

Maintain one private Markdown knowledge base with two visibly distinct states:

- **Working knowledge** changes during an active gate. Entries are
  evidence-linked and carry a lifecycle state: `provisional`, `corroborated`,
  `challenged`, `ready for owner review`, `promoted`, or `retired`.
- **Reviewed knowledge** contains stable, retrieval-oriented summaries whose
  evidence, scope, support level, review state, and non-inference boundary were
  checked by a named human. It includes literature/source, model/dictionary,
  analytic/derivation, numerical/method, data/comparison, result,
  decision/workflow, and tooling/reproducibility knowledge. Closure lessons are
  a subtype promoted only after owner-reviewed gate closure.

Use the generic
[`research-knowledge-template.md`](templates/research-knowledge-template.md).
Update a working entry after a durable milestone changes the evidence boundary:
source review, contract freeze, calculation, verification, hostile criticism,
owner decision, or closure. State what held, what failed or remains unresolved,
what must not be inferred, the next discriminating check, and applicability.

This event-driven update is agent-maintained, not background telemetry. A
working entry can guide the next check, but it is not reviewed knowledge and
must not silently strengthen a scientific claim. Preserve challenged and
retired observations with their evidence so later work can learn why an
apparent result, source interpretation, or method was unreliable.

## What belongs in the knowledge base

A reusable item may come from:

- a paper or source audit that establishes a scoped equation, convention,
  dictionary, comparison, or explicit disagreement;
- a derivation or analytic limit that was independently checked;
- numerical work that establishes method behavior, convergence limits,
  conditioning, diagnostics, or representation dependence;
- a dataset review that fixes version, uncertainty, transformation, licensing,
  or comparison conventions;
- a bounded positive, negative, conditional, inconclusive, or stopped result;
- hostile criticism that exposes a live alternative explanation or sharper
  test;
- an owner decision or workflow change with reusable rationale; or
- a reusable test, environment constraint, or reproducibility procedure.

Do not ingest every paper, conversation, command, or intermediate number. Raw
papers, literature notes, derivations, result files, and decision records remain
primary evidence. Add a distilled item only when it is reusable or
decision-relevant, evidence-linked, scoped, non-duplicative, explicit about
uncertainty, and safe for the knowledge base's disclosure class. For literature
knowledge, record the exact document version and page, equation, figure, or
section; summarize in original words; represent conflicting sources; and never
upgrade a targeted search into an exhaustive literature claim.

## Review and promotion

Working items use `WK-YYYYMMDD-NNN` identifiers. General reviewed knowledge
uses stable IDs such as `HF-K001`; owner-accepted closure lessons retain stable
IDs such as `HF-L001`. These namespaces are record types inside the same
canonical knowledge base, not separate knowledge bases.

Literature, derivation, method, data, decision, and tooling knowledge may be
promoted at a durable review milestone when a named human confirms its primary
evidence and locator, statement, applicability, uncertainty, support level,
review state, and non-inference boundary. A gate-outcome lesson still requires
owner-reviewed closure and its retrospective. Conversation or agent confidence
alone cannot promote an item.

## Required evidence layers

A closed gate should retain the artifacts appropriate to its scope:

1. the frozen contract and source record;
2. code, configuration, environment metadata, tests, and machine-readable
   evidence when calculation was authorized;
3. the outcome-first result record, including limitations and explicit
   non-claims;
4. hostile criticism and claim-appropriate independent verification, with
   owner review when a decision requires it;
5. the disposition, authority link and progress-state update, whether the
   owner decides directly or the agent applies
   [delegated private closure](research-gate-workflow.md#close-an-eligible-private-gate-under-delegation);
6. a closure retrospective; and
7. a scoped Git commit when authorized.

Do not delete a failed check because a later method works. That failure may be
the evidence that distinguishes a fragile representation from a reliable one.
Likewise, do not call an unavailable source, an ill-conditioned norm, or a
solver failure a physical negative result.

## Outcome classes

Choose one primary class and explain any secondary class:

- **positive:** the preregistered positive endpoint passed within its evidence
  boundary;
- **negative:** the preregistered physical negative endpoint passed;
- **inconclusive:** the evidence lies between declared endpoints;
- **conditional:** a bounded subtest passed, but a named prerequisite for the
  proposed claim remains open;
- **source stop:** required public or authorized inputs are missing or
  internally unresolved;
- **prior-art stop:** the proposed novelty target is already covered or needs
  material narrowing;
- **technical stop:** the frozen representation, numerical method, or
  verification contract failed without deciding the physical question.

These labels describe the gate, not the value of the research effort.

## Closure retrospective

Copy [`research-retrospective-template.md`](templates/research-retrospective-template.md)
into the research project when a gate closes. Record:

- the accepted outcome class and evidence links;
- what held, what failed, and the strongest unresolved alternative;
- the scientific, numerical, and workflow lessons;
- what must not be inferred;
- one concrete change, if any, to future intake or gate design; and
- the evidence required to reopen the direction.

Lessons feed forward. They may change how future candidates are scored or how
new contracts are written, but they must not retroactively change a frozen
contract, acceptance threshold, support label, or owner decision.

At owner-reviewed closure, reconcile every working entry touched by the gate:
promote the reusable accepted lesson, preserve already reviewed knowledge,
retire an unsupported or non-reusable entry with its reason, or leave an
unresolved entry visibly provisional or challenged. Do not erase the working
history after promotion.

For delegated closure, link the disposition and retrospective from the
evidence-linked working entry. Record its applicable working lifecycle state,
including any challenge or retirement. Promotion to reviewed knowledge follows
the named-human review process above.

## Agent retrieval loop

Most portfolio knowledge will be consumed by a research agent. A private
reviewed index should therefore give each entry a stable knowledge or lesson
ID, knowledge class, retrieval tags, a link and locator to primary evidence,
an applicability statement, and a non-applicability boundary. Keep Markdown as
the canonical record so an owner can still inspect it; do not maintain a second
machine-readable copy unless a real automation requires one and consistency is
tested.

Before scoring a new candidate, the agent must:

1. read the current private reviewed-knowledge and lesson indexes and their Git
   revision;
2. search by knowledge class, scientific topic, method risk, source convention,
   outcome, and failure mode;
3. open the primary evidence behind every potentially applicable item;
4. record the selected stable knowledge and lesson IDs in the new intake
   scorecard;
5. translate each applicable item into a candidate-specific source check,
   baseline, diagnostic, acceptance threshold, or stop rule; and
6. state which classes and tags were searched when no prior item applies.

The agent must not copy a past conclusion or threshold merely because two
projects sound similar. A previous failure is a prompt for a cheaper or sharper
test, not evidence that the new candidate is false.

For a portfolio with several private directions, maintain a private index of
retrospectives so a later intake can find recurring failure modes. Keep the
index claim-bounded: link the primary records instead of replacing them with a
story about what “probably” happened.

## Privacy and public export

An unpublished retrospective remains in the separate private research
repository with its project identities, literature notes, calculations, and
results. Do not copy that ledger into public HoloForge.

Only generic workflow improvements, sanitized templates, or separately
disclosure-approved reproduction artifacts may be proposed publicly, and each
proposal must pass the public-export workflow. Learning from a private result
does not authorize disclosing that result.
