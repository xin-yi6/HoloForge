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

Use the [comparative reading study](physics-writing-reading-study.md) as a
starting corpus, not a substitute for reading. It records sixteen examples,
their exact versions, reading depth, contrasting argument structures and
transferable lessons. It includes short results, conceptual proposals,
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
Keep the physical argument in the manuscript and the internal audit history in
a private companion note. Preserve the old draft, check the revised claim map,
and render and visually inspect the final PDF. Do not submit or disclose it.
```
