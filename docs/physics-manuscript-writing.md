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

Choose a small, task-relevant set spanning the needed forms: an analytic
argument, a numerical model study, or a methods paper. Inspect the abstract,
introduction, a central result with its equations/figures, and the conclusion.
Record the exact version and inspected sections; do not describe selective
reading as a full scientific audit. Read further only when it resolves a
specific writing or interpretation question.

These examples illustrate useful rhetorical choices, not a universal journal
template or an endorsement of every historical scientific claim:

- **Hartnoll, Herzog and Horowitz, _Building an AdS/CFT superconductor_**,
  [arXiv:0803.3295v1](https://arxiv.org/html/0803.3295v1), published in
  [PRL 101, 031601](https://doi.org/10.1103/PhysRevLett.101.031601).
  The inspected abstract and sections 1-4 move from a physical motivation to
  the minimal model, boundary observables, figures and their interpretation.
  The probe approximation's low-temperature limitation is explained where
  it matters. This illustrates connecting a numerical result to physics.
- **Kovtun, Son and Starinets, _Viscosity in Strongly Interacting Quantum
  Field Theories from Black Hole Physics_**,
  [arXiv:hep-th/0405231v2](https://arxiv.org/html/hep-th/0405231v2), published in
  [PRL 94, 111601](https://doi.org/10.1103/PhysRevLett.94.111601).
  The abstract, introduction, absorption argument and discussion foreground
  a compact result, derive it under specified assumptions, and distinguish
  it from a broader conjecture. Adopt that distinction, not a historical
  conjecture as an unrestricted current theorem.
- **Bhattacharyya, Hubeny, Minwalla and Rangamani, _Nonlinear Fluid Dynamics
  from Gravity_**, [arXiv:0712.2456v4](https://arxiv.org/html/0712.2456v4),
  published in [JHEP 02 (2008) 045](https://doi.org/10.1088/1126-6708/2008/02/045).
  The abstract, introduction, section 5.5, opening of section 6 and discussion
  link a systematic construction to a stress tensor and its physical uses.
  The long derivation serves the result; length alone is not poor style.
- **Basar, Dunne and Yin, _Uniformizing Lee-Yang singularities_**,
  [PRD 105, 105002](https://doi.org/10.1103/PhysRevD.105.105002), with
  [arXiv:2112.14269v1](https://arxiv.org/abs/2112.14269v1).
  The published abstract, introduction, model setup and conclusion organize
  the method around physical information it recovers and the comparisons
  demonstrating that recovery. A methods paper still needs a scientific
  question, interpretable examples and a defined domain of validity.

These are editorial observations from selected passages, not a systematic
survey of theoretical physics. Distill general principles in original prose;
do not copy distinctive sentences, paper figures, layouts or authorial voice.
Keep downloaded papers and project-specific reading notes out of public
HoloForge. A journal class or two-column layout cannot repair a weak argument.

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
- Keep drafts private until the owner's separate disclosure decision. Never
  invent authors, affiliations, funding, acknowledgments or code-availability
  promises. Proposed authorship, AI-use statements and journal requirements
  need author review before submission.

## Reusable request

```text
Rewrite the authorized draft as a theoretical-physics manuscript using
docs/physics-manuscript-writing.md. Read a small relevant sample of primary
papers for structure and explain what you adopt. Preserve all scientific
claims, evidence, uncertainties and unresolved issues; make no new calculation.
Keep the physical argument in the manuscript and the internal audit history in
a private companion note. Preserve the old draft, check the revised claim map,
and render and visually inspect the final PDF. Do not submit or disclose it.
```
