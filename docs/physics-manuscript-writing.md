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

Use the [expanded comparative study](physics-writing-expanded-study.md), its
[machine-readable corpus](physics-writing-corpus.json), and the historical
[reading study](physics-writing-reading-study.md) and
[cross-field companion](physics-writing-cross-field-study.md) as a starting
corpus, not a substitute for reading. The collection records 64 distinct papers:
50 complete main-text readings and 14 selected-section readings, with exact
sources, reading depth, contrasting argument structures and transferable
lessons. This is a purposive sample, not proof of a universal writing style.
It includes short results, conceptual proposals,
analytic arguments, numerical studies and long frameworks. Author reputation
can help find examples; the observable quality of the argument determines
what to adopt. A larger bibliography alone does not establish a better style.

For a new manuscript, choose two to four examples with the closest argument
types from this corpus, plus a contrasting architecture when useful, and
add examples when a relevant genre or field is missing. Read across abstract,
introduction, central reasoning and conclusion; include main-text reading
when learning an unfamiliar architecture. Record the exact version and actual
sections inspected. Do not describe selected passages as a full-paper reading
or any style study as a scientific audit or novelty clearance. There is no
fixed paper-count quota for every revision.

The expanded study's fifty complete readings are a one-time study target,
not a prerequisite for each paper. Prefer deep application to the current
argument over accumulating more names. A recurring cross-field practice is
a candidate editorial principle; test its exceptions before adopting it.

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
   Use [claim-led citation tracing](#find-references-by-tracing-claims)
   to locate missing sources; do not claim priority from a small style-reading
   sample. Integrate the relevant papers around the physical question rather
   than inserting an author-by-author literature catalogue before it.
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

## Check the physical story as a connected argument

A good physical story explains why a question matters, why the chosen method
can answer it, what the evidence establishes, and what the result changes.
It is not a dramatic success narrative or a record of the order in which the
agent completed tasks. Background, motivation, methods, results and analysis
must connect, whether or not they appear as separate named sections.

Before a substantial rewrite, summarize that connection in a short private
outline using existing evidence:

1. **Background and motivation:** what is known, what consequential question
   remains, and why the reader should care about answering it.
2. **Approach:** why this model, observable, approximation or calculation
   addresses that question, including the assumptions that make it informative.
3. **Result:** what was actually established relative to the relevant baseline
   or alternative, and which equation or figure carries the evidence.
4. **Analysis:** what mechanism, relation or calculational access is learned;
   distinguish demonstrated explanation from a plausible interpretation.
5. **Consequence and limits:** how the result answers the opening question,
   where it applies, and which unresolved issue changes that answer.

This is a coherence check, not a required five-paragraph template or a new
approval gate. The abstract, introduction and conclusion must describe the
same question and level of claim. Every major section should either advance
that answer or establish a necessary condition for trusting it. Explain why
secondary results belong; place useful but separate investigations in an
appendix or a companion when appropriate, without concealing their implications.

Use the outline to distinguish a missing transition or explanation from missing
scientific evidence. Rewrite the former from the existing record; report the
latter for a separately authorized research decision. An interesting story
does not justify omitting contradictory results, inventing a mechanism,
inflating novelty, or presenting a partly answered question as settled.

## Make the reasoning visible at paragraph scale

Section length is not a quality target. When a draft feels thin, distinguish
missing explanation from missing scientific evidence. Restore the motivation,
equation-to-equation reasoning, physical interpretation and meaningful
comparisons already supported by the record; merge unnecessary fragments.
Do not pad sections, remove necessary derivations to imitate a short letter,
or commission calculations merely to make a manuscript longer.

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
- **Design the figures as part of the argument.** Follow the separate
  [physics figure guide](physics-figure-design.md) and its
  [visual reading study](physics-figure-reading-study.md). Prose reading does
  not imply visual inspection. Explain physical effect size as well as numerical
  improvement, and keep author-review graphics separate from manuscript figures.
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

## Use journal templates and source-backed bibliographies

For an APS/Physical Review manuscript, use the maintained
[REVTeX 4.2 class and official examples](https://journals.aps.org/revtex), not
an imitation made by changing the margins of the standard `article` class.
Choose the actual journal option with the authors; a formatting choice is not
a commitment to submit to that journal. For example:

```latex
\documentclass[aps,prd,reprint,amsmath,amssymb]{revtex4-2}
% Use preprint instead of reprint for the single-column review layout.
```

Use the owner's preferred two-column layout for a proposed arXiv version;
offer a single-column review copy when long derivations benefit from it. Keep
both derived from the same content, figures and bibliography. Neither layout
authorizes uploading to arXiv. REVTeX approximates journal appearance; it is
not a publisher's final typeset version. Follow its current author guide rather
than overriding its grid, fonts or bibliography machinery. REVTeX supplies
natbib; the APS bibliography style is `apsrev4-2`.

Reflow long equations without changing their mathematical content. Prefer
logical line breaks; use `widetext`, `figure*` or `table*` when a full-width
object is necessary. Inspect equations, captions, legends, tables and reference
links at the final column width. Do not shrink material until it is unreadable,
change significant figures to fit, or stretch a plot out of proportion. Build
with BibTeX and enough LaTeX passes to resolve citations and cross-references,
then render every page. Record the class, options and build versions privately.

**Use INSPIRE HEP BibTeX exports whenever the cited work is indexed there.**
Resolve the exact work by DOI, arXiv ID or record ID, check title and authors,
then use the record's export rather than manually reconstructing its fields.
The [official INSPIRE API documentation](https://github.com/inspirehep/rest-api-doc)
describes the `format=bibtex` parameter and `application/x-bibtex` response.
The web interface's BibTeX export is equally suitable.

- Keep the raw export, record URL/ID, retrieval date and checksum in the private
  source record. Preserve the original export separately from any build copy.
- Check journal, year, volume, article/page number, DOI and arXiv identifier.
  Use available publication metadata without implying that an unread published
  version was inspected. Keep the exact version actually read in the evidence
  record; a metadata refresh is not a scientific source reconciliation.
- Preserve stable citation keys or record an explicit key mapping. Document
  necessary TeX-encoding corrections without silently changing bibliographic
  facts. Deduplicate entries and check every cited key resolves after building.
- If INSPIRE has no record, use a publisher or another authoritative source
  and record that fallback honestly. This supports cross-field research; it
  does not restrict citations to high-energy physics or justify invented data.
- A plausible-looking `.bib` entry does not prove its provenance. When the
  earlier export is missing, say so and obtain a verifiable new export; never
  retroactively label the old file as an exact INSPIRE download.

Record formatting review separately from physical-result review. An attractive
APS draft, a clean BibTeX build and author approval of presentation do not mean
that the derivation, novelty, unresolved discrepancies or submission statements
have been accepted. Identify claim-critical remaining work; do not require
unrelated extensions merely to increase the paper's length.

## Find references by tracing claims

Inspecting the reference lists of relevant papers is **backward citation
chaining**; following later papers that cite them is forward citation chaining.
Both are useful discovery routes, as described in
[Abertay University's citation-chaining guide](https://intranet.abertay.ac.uk/students/study-skills/guides/researching/searching/citation-chaining/).
Use them to fill a concrete gap in attribution or context, not to reach a
reference-count target. In HoloForge, discovery and verification remain separate:

1. Identify the manuscript statement that needs support: a foundational idea,
   equation, method, prior result, competing explanation or limitation.
2. In a relevant paper already being read, inspect both the reference list and
   the passage that cites a candidate source. A citation may mark disagreement
   or background rather than evidence for the statement being written.
3. Retrieve the candidate itself and read the relevant argument, assumptions
   and result before using it as direct support. Paper A citing paper B does
   not verify B. Record the version and section, equation or page actually
   inspected; check available publication corrections when pertinent. If only
   an abstract or a secondary account is accessible, record that limit and do
   not claim to have verified a technical result available only in the full text.
4. Cite the original contribution for what it establishes. Also credit a later
   paper when using its interpretation, extension or method; finding the
   original does not erase that contribution. Use the INSPIRE export convention
   [above](#use-journal-templates-and-source-backed-bibliographies) for metadata.
5. Reuse the private claim/source notes to record the manuscript claim, source
   locator, citation purpose and any access limit; a short entry is sufficient.
   Retain the discovery link when useful. Do not copy another paper's citation
   bundle, distinctive wording or paragraph structure into the manuscript.

Read the cited papers to understand how the physical problem developed and
what is still unresolved, not just to harvest their bibliography. In the
introduction, synthesize that understanding in original prose around the
question being asked. Attribute borrowed ideas even when paraphrased.

One citation chain can miss another approach or newer contrary evidence. Use
other relevant starting papers and, where needed, forward citation or targeted
database searches. Include consequential competing results, not only sources
that support the preferred story. This complements the
[APS referencing policy](https://journals.aps.org/authors/editorial-policies#references-to-other-work):
appropriate credit and current, representative coverage, without citation
inflation. Neither a famous author nor inclusion in a seed paper is a relevance
criterion. Stop this editorial search when the identified claims and necessary
context are adequately supported; record unresolved gaps rather than claiming
an exhaustive review or novelty clearance.

## Reusable request

```text
Rewrite the authorized draft as a theoretical-physics manuscript using
docs/physics-manuscript-writing.md and its comparative reading study. Select
relevant argument types, extend the corpus if needed, record reading scope,
and explain which structural lessons fit this paper. Check that motivation,
method, results and interpretation form one evidence-supported physical story.
Trace missing references through relevant cited papers, read the candidate
sources, and integrate their contributions in original, claim-led prose.
Preserve all scientific
claims, evidence, uncertainties and unresolved issues; make no new calculation.
Use natural, author-led physics prose without formulaic recaps or invented
author experience. Retain AI provenance and the author's scientific review.
Keep the physical argument in the manuscript and the internal audit history in
a private companion note. Preserve the old draft, check the revised claim map,
and render and visually inspect the final PDF. Do not submit or disclose it.
```
