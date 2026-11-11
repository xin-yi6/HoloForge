# Scientific Support and Review State

HoloForge records two independent labels for a claim:

- **Support level** describes the evidence: `established-source`, `reproduced`,
  `model-extension`, or `hypothesis`.
- **Review state** describes human checking: `unreviewed`, `checked`,
  `approved`, or `rejected`.

Public visibility is a separate decision from both labels. A strong support
level does not require disclosure before the research owner is ready, and a
public hypothesis is not strengthened merely by being visible. Novel Explore
work may follow the [private-research workflow](private-research-workflow.md)
until it is cleared for release.

For example, a formula copied from a paper can be `established-source` while
still `unreviewed` in HoloForge. A numerical value becomes `reproduced` only
after an identified calculation passes its declared tolerance. Neither label
alone means that nature agrees with the model.

When a claim was generated or materially rewritten by AI, `generated_by_ai`
must be `true`. Human review may change the review state, but must not erase the
provenance.

A claim marked `checked`, `approved`, or `rejected` must also record the human
reviewer's name and review date. This makes scientific approval attributable
without erasing AI assistance.

Record agent technical verification with its evidence and provenance. An
eligible private gate can [retain and close under delegation](research-gate-workflow.md#close-an-eligible-private-gate-under-delegation)
with human review recorded as `unreviewed`.
