# HoloForge research objective

## Objective

HoloForge should increase the rate at which a researcher reaches a defensible
new quantitative physical claim, subject to correctness, provenance,
uncertainty, robustness, privacy, and human scientific review. It cannot
guarantee a publication or replace judgment about significance and novelty.
Any future readiness audit must not certify novelty, physical truth, or
publication worth.

Benchmark count, test count, pull-request count, report count, release count,
and agent activity measure engineering work. They are not research-output
metrics.

## Two research loops

Use a fast **discovery loop** to compare candidates, test the simplest
alternative, and reach the first physical discriminator with bounded effort.
Use the heavier **confirmation loop** only after a result supplies a credible
signal, robust exclusion, or scientifically important tension.

```text
discovery:
  physical question -> closest prior work -> bounded claim
  -> cheap analytic/source checks -> signal pilot -> retain/revise/stop

confirmation:
  frozen claim -> necessary baseline -> full calculation
  -> uncertainty and robustness -> independent check
  -> hostile review -> human readiness decision
```

The discovery loop may include a bounded derivation, model construction, or
signal pilot when that is the cheapest honest way to distinguish a valuable
question. It must not demand a full confirmation package before any physical
work is attempted.

## Scientific value and research authority

HoloForge separates **scientific opportunity** from **execution readiness**.
Agents may assemble the evidence and compare candidates, but they cannot
certify that a question is important, novel, or publication-worthy. The named
human research owner makes the final value-and-investment decision after a
non-aggregate assessment of:

- the importance of the physical question or phenomenon;
- the plausibility and exact limitations of the prior-work gap;
- falsifiability and the existence of a meaningful physical discriminator;
- physical or conceptual holographic leverage: a mechanism, relation, regime,
  or prediction unavailable from a simpler description;
- explanatory or predictive depth beyond a generic flexible-model fit;
- the prospective value of positive, negative, and inconclusive outcomes; and
- fit with the owner's expertise, interests, time, and portfolio strategy.

Capability receipts, available artifacts, and estimated cost inform the later
feasibility and horizon decision. They must not determine scientific value or
silently privilege the subjects already represented by public benchmarks.
There is no opaque aggregate score that replaces comparative scientific
judgment.

For an autonomous campaign, the owner may make this investment decision
prospectively by authorizing an exact question envelope and candidate-selection
policy. The agent may select among candidates that satisfy that policy, but the
selection remains AI-generated and unreviewed; it cannot certify importance,
novelty, truth, or publication value. Any change to the envelope or policy
returns to the owner.

Every scientific Explore candidate must target a new physical contribution
beyond the closest prior work. State the unanswered question and the mechanism,
relation, prediction, unexplored regime or observable, or physical consistency
result that either outcome could establish. This is a prospective research aim,
not a novelty certificate or a demand for a positive result. A qualitatively new
phenomenon is not required in every project.

Computational or representational advantages are supporting means, not a
standalone scientific-value route. Assess them after the physical opportunity:
name the best nonholographic baseline, source-response dictionary and modelling
regime, then compare accessible observables, accuracy, robustness, human
construction effort, and compute cost. Explain which unanswered physical
question the advantage enables. Faster or more accurate recovery of an already
established result alone does not justify selecting an Explore direction.
Method transfer and model improvement follow the same physical-contribution
requirement. Forge/Verify reproductions, infrastructure maintenance and synthetic
workflow tests retain their separate purposes. Apply this selection policy to
future work without changing existing frozen contracts or framework pins.

## Three research horizons

Classify a selected opportunity by the work it actually requires:

1. **Open discovery** develops a new-domain or new-phenomenon dictionary,
   mechanism, or model hypothesis. Source and capability gaps are expected and
   become explicit research questions.
2. **Strategic development** deliberately constructs and qualifies the action,
   dictionary, observable, data artifact, solver, or validation route needed
   for an owner-selected physical question. Several capabilities may be
   planned when their dependencies, milestones, cost, stop rules, and first
   physical checkpoint are explicit.
3. **Short-horizon execution** uses a source-complete analytic route or already
   qualified capability to reach a physical discriminator quickly.

Only the short-horizon lane normally expects the first or second detailed gate
to evaluate the physical discriminator. Strategic development instead freezes
reviewable prerequisite milestones and an early *planned* physics checkpoint;
it is not restricted to numerical-method papers. Planned model or capability
construction is distinct from a post-failure numerical repair and does not
consume the repair budget merely by existing.

## Evidence core

Every serious claim needs:

- a precise statement and model or evidence boundary;
- a mechanism, discriminator, or controlled question;
- connection to a primary source, baseline, or exact limit;
- a result not silently reused as both calibration and prediction;
- numerical or analytic credibility appropriate to the claim;
- uncertainty, limitations, and non-inference boundaries;
- reproducible evidence links and provenance; and
- named human review.

Additional requirements are conditional on claim type. Held-out data are
mandatory for data-calibrated predictive claims, but may be not applicable to
a formal derivation or exact identity. Analytic claims require explicit
assumptions and an independent derivation audit; numerical-method claims
require error, conditioning, and applicability evidence.

## Separate evidence role from regime relation

Future research contracts must not combine how evidence was used with where a
prediction lies:

| Axis | Examples |
| --- | --- |
| Evidence role | `calibration`, `validation`, `held_out`, `none` |
| Regime relation | `interpolation`, `extrapolation`, `analytic_limit`, `not_applicable` |

A calibrated extrapolation is still calibrated. An interpolating result can
still be held out. Keeping these axes separate prevents fitted descriptions
from being relabelled as predictions.

## Research-pulled development

Do not add a public benchmark, schema, abstraction, renderer, agent role, or
runtime merely to make HoloForge look complete. Add it when it fixes a
scientific-integrity problem or when a bounded research project demonstrates
that the capability is reusable.

The next capability proof is one private, end-to-end vertical slice around an
owner-selected physical question. It may use a qualified route or an explicitly
approved strategic-development campaign. Draft its records in the private
repository, preserve its Git history, and promote only the minimum generic
artifact after a separate public-export review. The public roadmap must not
identify or disclose the private candidate.

## Valid outcomes

A research cycle may end with a supported claim, a robust negative result, an
inconclusive result, a prior-art or source stop, or a technical stop. These
outcomes are not interchangeable. In particular, a failed calculation is not
a physical negative result, and a stable calculation is not by itself a
publishable physical claim.
