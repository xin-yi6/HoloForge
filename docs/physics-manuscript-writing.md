# Writing a theoretical-physics manuscript

Use this guide when the owner asks to turn existing project evidence into
a paper draft or to revise its presentation. It is an editorial workflow, not
a new scientific gate, a novelty assessment, or permission to calculate or
publish. Apply the current task authority and preserve the research contract.

## Separate the paper from the research record

A paper explains a physical question, a calculation and its consequences to
physicists who do not know the project's internal workflow. An owner-review
packet supports an investment or approval decision. Neither substitutes for
the other or for the underlying reproducibility record.

| Artifact | What belongs here |
| --- | --- |
| Paper main text | Physical motivation, relation to prior work, model and assumptions, the central derivation or calculation, results, interpretation and consequential limitations |
| Technical appendix or supplement | Necessary derivation details, numerical methods, convergence evidence, uncertainty definitions and reproducibility information |
| Private companion record | Exact artifact mapping, hashes, gate history, failed attempts, owner decisions, AI provenance and unresolved administrative checks |
| Owner-review packet | Current status, progress map, colored status tables, critic responses and approval choices |

Do not merely move every numerical detail to an appendix. The main text must
still explain how the result was obtained and why its accuracy is adequate.
A source ambiguity or failed check that changes the interpretation belongs
beside the affected claim, even if the full audit trail lives elsewhere.
Moving text must never conceal contradictory evidence or strengthen a claim.

The [owner-review PDF style](research-gate-workflow.md#owner-review-pdf-packet)
is **not** the default manuscript style. Progress diagrams, approval menus,
status boxes and repeated supported/unsupported labels normally stay in the
review packet. The underlying support and human-review states remain recorded
under the [scientific-support policy](scientific-support.md).

## Learn structure from papers, not an author's voice

Use the [comparative reading study](physics-writing-reading-study.md) and
its [cross-field companion](physics-writing-cross-field-study.md) as a
starting corpus, not a substitute for reading. Together they record twenty-five
examples, their exact versions, reading depth, contrasting argument structures
and transferable lessons. They include short results, conceptual proposals,
analytic arguments, numerical studies and long frameworks. Author reputation
can help find examples; the observable quality of the argument determines
what to adopt. A larger bibliography alone does not establish a better style.

For a new manuscript, choose the closest argument types from this corpus and
add examples when a relevant genre or field is missing. Read across abstract,
introduction, central reasoning and conclusion; include main-text reading
when learning an unfamiliar architecture. Record the exact version and actual
sections inspected. Do not describe selected passages as a full-paper reading
or any style study as a scientific audit or novelty clearance. There is no
fixed paper-count quota for every revision.

Distill principles in original prose, including counterexamples to a proposed
rule. Do not copy distinctive sentences, paper figures, layouts or authorial
voice. Keep downloaded papers and project-specific reading notes out of public
HoloForge. The public study contains only generic editorial observations and
primary-source links. Neither an author's prominence, a two-column layout nor
a famous paper's historical claims are substitutes for current evidence.

## Share the reasoning, adapt to the evidence

Physics communities share an argumentative core: identify a consequential
question, define the physical system and assumptions, establish a result,
and explain what it changes. Their prose and evidence conventions are not
identical. Learn from particle physics, condensed matter, statistical physics,
quantum foundations and cosmology as well as holography. Select examples by
the job the argument performs, not only by the model or an author's fame.

An analytic paper may make a theorem and its assumptions the backbone; a
model paper may explain an effect through controlled limits and contrasting
regimes; an observational paper may lead with the signal and distinguish its
significance from parameter inference. A useful shared principle is to make
every major equation, figure and check advance the argument. Do not impose
an observational significance threshold on a deterministic calculation, or
strip essential numerical methods from a theory paper to imitate a letter.

The [cross-field comparisons](physics-writing-cross-field-study.md#comparative-lessons)
include examples where an important conceptual contribution coexists with
unresolved implementation questions. This is not an exemption from validation:
the unresolved issue must not defeat the claim actually being made. Historical
success and present author reputation are not acceptance criteria for new work.

## Choose an argument architecture

Start from what the reader must understand to accept the result, not a rigid
Introduction/Methods/Results template. These are alternatives, not quotas:

| Main contribution | Useful progression | Editorial risk to avoid |
| --- | --- | --- |
| New physical proposal | Puzzle; precise proposal; tractable check; extensions and limits | Presenting an analogy as an established dictionary |
| Analytic result or bound | Question; statement and assumptions; mechanism or proof; examples and applicability | Hiding physical assumptions inside a mathematical lemma |
| Numerical model study | Physical distinction; model and observable; decisive calculation; interpretation and controls | Making solver chronology the paper's argument |
| New method | Previously inaccessible question; method; known-case check; informative application | Reporting accuracy without explaining what becomes knowable |
| Broad framework | Physical motivation; organizing structures; worked sector; general construction and consequences | Introducing all machinery before a reader sees its purpose |

Several forms can coexist. Give the paper a principal result and explain why
secondary results follow from it or test its interpretation. Do not make every
calculation a coequal headline. Conversely, do not remove a long derivation
when it supplies the physical mechanism. The reading study contrasts
simple-example-first, result-first and framework-first approaches.

## Build the argument before polishing sentences

1. **Write the central claim privately in one paragraph.** Name the physical
   object, what was found, the evidence and its domain of validity. Map each
   consequential statement to an existing derivation, result or primary source.
   Missing evidence is a scientific question, not an invitation to invent it.
2. **Organize by logical dependence, not execution chronology.** A common
   sequence is introduction; model and observables; derivation/calculation;
   results and interpretation; discussion/conclusion; technical appendices.
   Combine or rearrange sections for the actual argument and target journal.
3. **Make the abstract stand alone.** State the problem, approach, principal
   result and physical implication. Include a decisive qualification if its
   omission would mislead. Avoid internal IDs, pass counts, promises of
   publishability and a catalogue of everything the paper does not do.
4. **Use the introduction to locate the question.** Explain why it matters,
   what prior work establishes, what remains to be answered and precisely
   what this work contributes. Cite sources for claims, not decorative breadth.
   Do not claim priority from a small style-reading sample.
5. **Make equations part of sentences and reasoning.** Introduce the physical
   quantity, state assumptions and conventions, define symbols when used,
   present the equation, then explain its consequence. Preserve dimensions,
   normalizations, signs, limiting conditions and approximation orders.
6. **Give each result paragraph a job.** Explain what was calculated, show
   the result or comparison, then say what physical distinction it resolves.
   Numerical accuracy is important evidence, not automatically the result.
7. **Make figures answer questions.** Refer to every figure in the text and
   explain its physical content. Captions identify observables, units,
   parameters, curves and uncertainty conventions. Never add smoothing,
   extrapolated curves, fitted values or error bars merely for presentation.
8. **End with the physics.** Summarize what has been learned and the most
   consequential open question. Do not end with an owner approval request or
   claim that better prose has made the work publication-ready.

Use direct, connected prose, meaningful topic sentences and proportionate
qualifications. Distinguish an established result, a model-dependent finding,
an interpretation and a conjecture by precise language. Do not replace all
qualifications with confident assertions, or all conclusions with caveats.
Avoid unnecessary bold slogans, marketing claims and workflow jargon. Lists,
tables and negative results are legitimate when they clarify the argument;
there is no blanket ban on them or on numerical-method papers.

## Make the reasoning visible at paragraph scale

- **Open a paragraph with a physical task or inference.** Then supply the
  evidence and explain its consequence. Change paragraphs when the logical
  job changes, not after every equation. This is a diagnostic, not a mandatory
  three-sentence formula.
- **Bridge adjacent sections.** Explain what the preceding result leaves
  unresolved and why the next calculation answers it. A table of contents
  alone does not establish that dependence.
- **Interpret organizing equations.** State which term controls the effect,
  which information remains model-dependent and which limit is being taken.
  Do not add a physical interpretation that the existing evidence cannot bear.
- **Contrast meaningful alternatives.** A baseline, counterexample or known
  limit should isolate the physical distinction, not merely provide another
  curve. State what a successful check does and does not establish.
- **Place qualifications by consequence.** Put a limitation beside the claim
  it changes. Group remaining scope limits coherently in the discussion;
  avoid repeatedly attaching the whole audit disclaimer to each result.
- **Use the conclusion to synthesize.** Answer the opening question, explain
  the mechanism or information gained, and identify the consequential unknown.
  Neither a section-by-section inventory nor an unqualified success claim is
  an adequate ending.

## Distinguish a readable draft from a submission-ready argument

Assess scientific substance separately from presentation. Neither page count,
figure count, elapsed effort nor a famous short paper establishes that a new
manuscript contains enough work. Ask:

1. What precise physical or methodological knowledge does the reader gain?
2. How does it differ from the closest prior result, routine application or
   known limiting behavior? State the literature search's scope and uncertainty.
3. Does the evidence establish that claim under its stated assumptions, and
   explain why it matters? A useful new calculation, representation or access
   to a previously difficult observable can contribute without a new exponent.
4. Which unresolved issues could invalidate the central result or its claimed
   significance, and which are genuinely future extensions?

Do not require every possible extension for a focused paper. Conversely, do
not promote a working solver, a long validation history or a known mechanism
into a new physical discovery. Publication readiness is a reasoned assessment
for a contribution and readership, not an automatic score or journal guarantee.

An early draft can reveal a missing argument before the research is complete.
If the missing item is evidence or physical interpretation rather than prose,
identify it and propose the smallest meaningful research milestone under the
existing research workflow. Do not conceal it with another cosmetic rewrite,
an ever-growing style corpus, or calculations added only to make the paper
longer. Necessary new science needs the appropriate task authority; an
editorial request does not open it. Preserve promising ideas and verified
results rather than declaring a project failed merely because its draft is
not ready for submission.

## Write natural, author-led physics prose

The manuscript should read as a physicist's connected argument, not an agent's
task-completion report. Natural prose comes from precise reasoning and editorial
judgment, not cosmetic attempts to look human. Use the reading studies to learn
how authors explain choices, handle objections and connect results; do not
imitate a named author's distinctive voice.

- **Replace empty framing with the physical reason.** Rather than repeatedly
  announcing a comprehensive analysis or a crucial insight, say which assumption
  matters, what the calculation resolves and why the next step is needed.
- **Let paragraphs have different jobs and lengths.** A definition, a derivation,
  an objection and an interpretation need not share a stock three-part pattern.
  Use a topic sentence when it helps; do not force every paragraph into a slogan
  followed by evidence and a miniature conclusion.
- **Make transitions specific.** Explain the actual dependence between results.
  Remove repeated generic bridges, recap paragraphs and section-ending promises
  that add no physical information. Do not mechanically ban connective words.
- **State findings directly and qualify them where needed.** Avoid both inflated
  importance claims and an anxious disclaimer after every sentence. Keep every
  scientifically consequential qualification; consolidate only genuine repetition.
- **Use ordinary technical language.** Prefer concrete observables, assumptions
  and mechanisms to vague praise of the framework. Keep necessary terminology
  and stable notation; do not vary technical terms merely to avoid repetition.
- **Read the argument aloud or sentence by sentence.** Check whether its rhythm
  is natural, pronouns are clear, and each sentence gives a physicist a reason
  to read the next. Delete padding, not derivations needed to understand the result.
- **Leave judgment with the authors.** Do not invent personal motivations,
  historical anecdotes, intuitions or certainty to simulate a human voice. Ask
  for the author's intended emphasis when it would change the scientific argument.

This is an editorial objective, not a claim about how every human or AI writes.
Do not add deliberate errors or promise an AI-detector outcome. Natural prose
does not establish human authorship or remove AI assistance: preserve the
recorded provenance, human scientific review and applicable disclosure duties.
Do not replace an unresolved physical question with more fluent assertions.

## Revise without changing the science

- Preserve the original draft and source evidence; write a distinguishable
  revision and a short change note. Retain human review and AI provenance.
- Keep a private mapping of substantive claims and equations to the previous
  draft/evidence. Check values, uncertainty types, counts, captions and scope
  qualifiers after restructuring. Document omissions and where their evidence
  remains accessible; do not report unfinished tests as passed.
- Do not start new fits, derivations, searches about a source discrepancy or
  numerical repairs under an editorial request. Use separately authorized
  work when needed. Literature reading for style is not a novelty clearance.
- Use an appropriate manuscript class and restrained typography; choose
  one- or two-column format for the journal and reader, not as a scientific
  quality signal. Render and inspect every final page, equations, tables,
  figures and references. Compilation alone is insufficient.
- Ask whether a physicist can explain the question and result after reading
  the abstract, introduction and figures without the private gate log.
  Report this as editorial review, not an independent mathematical proof.
- Make separate revision passes for argument order, paragraph/equation
  reasoning, and scientific preservation. In the private change note, connect
  substantial edits to specific lessons and explain why they fit this paper.
  Check that the abstract's headline is actually established in the main text
  and that restructuring has not hidden a failed comparison or source issue.
- Keep drafts private until the owner's separate disclosure decision. Never
  invent authors, affiliations, funding, acknowledgments or code-availability
  promises. Proposed authorship, AI-use statements and journal requirements
  need author review before submission.

## Reusable request

```text
Rewrite the authorized draft as a theoretical-physics manuscript using
docs/physics-manuscript-writing.md and its comparative reading study. Select
relevant argument types, extend the corpus if needed, record reading scope,
and explain which structural lessons fit this paper. Preserve all scientific
claims, evidence, uncertainties and unresolved issues; make no new calculation.
Use natural, author-led physics prose without formulaic recaps or invented
author experience. Retain AI provenance and the author's scientific review.
Keep the physical argument in the manuscript and the internal audit history in
a private companion note. Preserve the old draft, check the revised claim map,
and render and visually inspect the final PDF. Do not submit or disclose it.
```
