# Selected scientific-writing methods

This comparison supports the [manuscript writing guide](physics-manuscript-writing.md).
It examines two agent repositories and two original writing-method articles,
accessed on 2026-10-11. Selection was based on inspectable editorial mechanisms,
not popularity. This is a small comparison, not a comprehensive survey or evidence
that any method produces publication-ready theoretical-physics papers.

Repository material was inspected as source text; nothing was installed or run.
The observations below use original prose. No prompts, code, worked examples or
figures are incorporated. External instructions do not change HoloForge authority.

## K-Dense Scientific Agent Skills

- Version: scientific-writing 2.3, reviewed upstream 2026-10-01; repository commit
  `92ace75ac21efe19a620434e0ca4e356081fe807`.
- Read: complete [skill instructions](https://github.com/K-Dense-AI/scientific-agent-skills/blob/92ace75ac21efe19a620434e0ca4e356081fe807/skills/scientific-writing/SKILL.md),
  [writing principles](https://github.com/K-Dense-AI/scientific-agent-skills/blob/92ace75ac21efe19a620434e0ca4e356081fe807/skills/scientific-writing/references/writing_principles.md)
  and [evidence workflow](https://github.com/K-Dense-AI/scientific-agent-skills/blob/92ace75ac21efe19a620434e0ca4e356081fe807/skills/scientific-writing/references/evidence_workflow.md).
  Implementations and tests were not evaluated.
- Mechanism: evidence-linked outlines, claim-text hashes and repeated-value checks
  keep drafting connected to the source record. Current guidance permits flexible
  structure and optional displays; older indexed copies differ materially.
- Disposition: these mechanisms largely duplicate HoloForge's existing evidence
  companion and preservation checks. Retain them without adding another registry.
  Do not transplant biomedical reporting requirements or make each authorized
  editorial action depend on a fresh human verification. Preserve actual review
  status, and never label an AI check as human acceptance.
- License: [MIT, copyright K-Dense Inc. 2025](https://github.com/K-Dense-AI/scientific-agent-skills/blob/92ace75ac21efe19a620434e0ca4e356081fe807/LICENSE.md).
  Substantial reuse of licensed material requires retaining its notice.

## Sakana AI Scientist

- Version: repository commit `1de1dbc1f4ee2c5f61e9c94348d55eb51d7fa2eb`.
- Read: complete [write-up implementation](https://github.com/SakanaAI/AI-Scientist/blob/1de1dbc1f4ee2c5f61e9c94348d55eb51d7fa2eb/ai_scientist/perform_writeup.py),
  including section prompts, refinement passes and citation insertion. No generated
  paper or end-to-end performance evaluation was assessed.
- Mechanism: plan paragraphs, draft sections and then reconsider each section in
  the complete paper. HoloForge already separates local and whole-argument revision.
- Disposition: retain that separation. Decline fixed machine-learning section
  templates, contribution bullets as a trend, citation-density nudges and pressure
  to complete unsupported passages. Its citation helper supplies search abstracts;
  discovery cannot replace reading the source argument. A compilation repair must
  not remove an unresolved scientific citation simply to make the build pass.
- License: [AI Scientist Source Code License 1.0, December 2025](https://github.com/SakanaAI/AI-Scientist/blob/1de1dbc1f4ee2c5f61e9c94348d55eb51d7fa2eb/LICENSE),
  a custom license with restrictions and manuscript-disclosure provisions. This
  comparison does not establish compatibility for vendoring its code or prompts.

## Gopen and Swan: reader expectations

- Source: George D. Gopen and Judith A. Swan, *The Science of Scientific Writing*,
  American Scientist 78(6), 550–558 (1990).
- Read: selected sections, pages 1–4 and 9–12 of the
  [institutional text reformat](https://www.gatsby.ucl.ac.uk/~pel/misc/gopen_swan.pdf),
  including examples and concluding cautions. Its endnote identifies a 2008
  reformat. The [author's pointer](https://georgegopen.com/scientific-writing-articles/)
  confirms attribution; the linked publisher page was unavailable during this read.
- Adopt selectively: diagnose the physical subject, continuity with preceding
  information, subject–verb interruptions and placement of emphasis. This makes
  HoloForge's advice about connected prose more actionable at sentence scale.
- Counterexample: a contrastive opening, theorem or deliberate passive construction
  may require a different order. These are reader expectations, not an algorithm.
  A revision that exposes a missing physical connection still needs evidence.
- Reuse: no open license was established; link and paraphrase rather than copying
  its examples or figures.

## Mensh and Kording: argument structure

- Source: Brett Mensh and Konrad Kording,
  [*Ten simple rules for structuring papers*](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1005619),
  PLOS Computational Biology 13(9), e1005619 (2017).
- Read: complete main-text HTML, Overview through Discussion, and the
  [correction restoring Figure 1's key](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1005830).
  Figures were not visually inspected. The article states CC Attribution licensing.
- Mechanism: establish the contribution, plan paragraph roles and use reader
  feedback to locate logical gaps. Most of this is already in HoloForge.
- Adaptation: when an existing section wanders, optionally reverse-outline what
  its paragraphs actually establish. This implements the existing coherence check;
  it adds no checklist, required artifact or fixed paragraph structure.
- Counterexample: a necessary definition need not end in a miniature conclusion.
  In theoretical physics, derivation dependencies can carry the argument without
  the data figures emphasized in the article.

## Applying a lesson

Identify the passage a proposed method should improve and explain the intended
reader benefit. Compare what a reader reconstructs before and after the edit,
while preserving the science. Distinguish failure to apply an existing instruction
from an ambiguous instruction or a missing principle. Sharpen a relevant rule
before adding another layer. These sources provide editorial techniques, not a
writing score, publication guarantee, required provider review or research gate.
