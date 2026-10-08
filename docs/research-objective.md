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

Research is nonlinear. Questions, models, observables and approximations may
develop together through failed approaches, backtracking and revised working
hypotheses. Scientific progress and value cannot be reduced to scores, elapsed
time, run counts, completed gates or a fixed sequence of steps. Quantify
physical results and uncertainty where appropriate, and account for resources
to respect the owner's investment; neither accounting nor a checklist replaces
scientific judgment. An unresolved construction can be the substance of the
research. Use checkpoints to assess learning and revise the route within the
approved scope, following [nonlinear research practice](research-gate-workflow.md#allow-nonlinear-research-within-an-agreed-scope).

## Two research loops

Use a **discovery loop** to compare candidates, develop the question and test
physical alternatives. Use cheap decisive tests when available; allow sustained
construction when the selected research horizon requires it.
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
question. The arrows show dependencies, not a mandatory linear schedule:
discovery can revisit earlier steps inside its approved envelope. It must not
demand a full confirmation package before any physical work is attempted.

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
- computational or representational holographic leverage: controlled access
  to a scientifically important strongly coupled problem that the best named
  nonholographic baseline cannot solve or control comparably;
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

Computational or representational leverage is a legitimate research-value
route even when holography does not predict a qualitatively new phenomenon.
It is not an automatic pass. The candidate must identify the hard original
problem and best available comparison method, establish the source-response
dictionary and duality or modelling regime, and compare accessible
observables, accuracy, robustness, and total construction and compute cost.
The higher-dimensional description must provide a real scientific advantage,
not merely move the difficulty into a more flexible model, an uncontrolled
dictionary, or an expensive bulk solve. This route may support a physics,
method, or combined contribution, but its claim must match the evidence.

Computational advantage compares the holographic method with the best
nonholographic baseline for the same physical problem in a stated validity
regime. Mere ease of numerical implementation, available code, or a faster bulk
solver does not establish that advantage. A new physical phenomenon is not
required for this route; a consequential comparative advantage must be
demonstrated. Nonholographic methods need not be classical.
The advantage may be access to an otherwise inaccessible observable, better
controlled accuracy, or lower total cost at comparable accuracy; compare against
closest prior methods. This clarification does not amend existing frozen
contracts or framework pins.

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
