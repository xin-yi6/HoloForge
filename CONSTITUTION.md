# HoloForge Scientific Constitution

## 1. Purpose and scope

HoloForge is a bottom-up gauge/gravity research platform. Its purpose is to turn
models into inspectable chains from assumptions to equations, boundary
conditions, numerics, observables, and validation evidence. It is not restricted
to holographic QCD, but it does not claim a top-down string embedding unless one
is explicitly supplied and supported.

## 2. Two modes, one evidence standard

**Forge/Verify** reproduces and extends literature-anchored models. Every model
must state its source, conventions, parameters, equations, boundary conditions,
observables, validation tests, and known limitations.

**Explore** develops and tests three complementary kinds of research: candidate
applications in genuinely new domains; unexplored subfields, phenomena,
regimes, mechanisms, or observables inside already holographic parent fields;
and method transfer or model improvement. A candidate bottom-up dictionary may
require a new action, source-response map, observable, solver, or validation
campaign. That development distance affects the research horizon and cost; it
does not by itself decide whether the physics question is worth pursuing.

Explore work uses a hypothesis card, gives a falsification or discriminating
test, and cannot be presented as established merely because code runs or an AI
system proposed it. Agents and structured records may assemble evidence and
compare opportunities, but the named human research owner decides scientific
value and authorizes investment. In a prospectively frozen autonomous mission,
the owner may make that investment decision by approving an exact portfolio
envelope, candidate-selection policy, decision set, resource ceiling, and
mandatory-return boundary. The agent may then select and execute candidates
inside that authority without a new human choice at every transition. This
delegation neither assigns human review nor authorizes changes to the framework,
scientific thresholds, disclosure, submission, or publication. Every scientific
Explore candidate must target a new physical contribution: a mechanism,
relation, prediction, unexplored regime or observable, or physical consistency
result beyond the closest prior work. A proposed contribution remains a
hypothesis until its discriminating test supplies evidence; a qualitatively new
phenomenon is not required in every project. Computational or representational
advantages may support that physical objective, but are not a standalone reason
to select an Explore direction. Faster, more accurate or more convenient
recovery of an already established result is not sufficient. Method transfer
and model improvement must name the unanswered physical question they serve.
Forge/Verify reproductions, infrastructure maintenance and synthetic workflow
tests retain their separate purposes. Novel, unpublished Explore work may remain
in a separate private workspace; Explore is an evidence category, not a
requirement to disclose research in progress. This selection policy applies
prospectively; it does not amend existing frozen contracts or framework pins.

## 3. Claim labels

Every consequential physical claim must carry one of these support levels:

1. `established-source` — directly supported by an identified primary source.
2. `reproduced` — independently recovered by a declared calculation or test.
3. `model-extension` — new within a stated model, but not independently
   established outside it.
4. `hypothesis` — speculative and awaiting a discriminating test.

AI authorship and scientific support are separate facts. AI-generated claims
must be marked as such and remain `unreviewed` until a human checks them.

An autonomous campaign must return either a fully auditable submission-ready
candidate or an equally auditable negative, inconclusive, source, prior-art,
technical, budget, policy, or owner-return outcome. It must not guarantee a
paper, hide stopped candidates, or obtain success by changing a frozen claim or
weakening a failed check.

## 4. Verification contract

A passing result requires more than successful execution. Each benchmark must
declare:

- units, signs, normalizations, coordinates, and boundary conditions;
- numerical domain, resolution, algorithm, tolerances, and software versions;
- at least one analytic, convergence, regression, or external-data check;
- failure criteria and limitations of what the check establishes.

Plots without underlying numerical checks are illustrations, not validation.

Numerics serve the physical question; they are not the default research
endpoint. A scientific contract must define prospectively what numerical
evidence is sufficient for its claim-bearing decision. Once those checks pass,
remaining numerical uncertainty cannot change that decision, and no unresolved
source, dictionary, boundary-condition, ensemble, or artifact problem
invalidates it, further numerical refinement must stop unless it tests a new
physical alternative or materially strengthens the claim.

## 5. Separation and promotion

Mature, literature-anchored public work lives in `domains/`. The public
`incubator/` contains only synthetic examples, public-literature dry runs, or
speculative work whose owner has explicitly approved disclosure. Novel
research-in-progress should live in a separate private repository. Promotion to
`domains/` requires an identified source or derivation, a stable model card,
executable tests, documented failure modes, and human review. File location is
part of the scientific status and must not be changed merely for presentation.

## 6. Confidentiality and publication timing

HoloForge does not require researchers to open unpublished projects. By
default, novel Explore work may remain private until journal acceptance or
another explicit disclosure decision by its owner. Before any private work is
copied into this public repository, a human must approve the exact export and
check that it contains no secrets, private paths, restricted data, confidential
notes, or results that are not cleared for release. An ignored local directory
is not a confidentiality boundary; a separate access-controlled repository is
preferred.

## 7. Reproducibility and provenance

Inputs and defaults must be serializable; generated outputs must record the
configuration that produced them. Changes that alter scientific results require
updated tests and documentation. Negative results and failed hypotheses should
be retained when they provide useful provenance.

## 8. Scientific restraint

HoloForge distinguishes verification of an implementation, reproduction of a
model result, and empirical validation of nature. Passing one level never
silently implies the next. Known ambiguities and disagreements are part of the
model record, not defects to hide.

Adopted by Xin-Yi Liu on 2026-08-02.
