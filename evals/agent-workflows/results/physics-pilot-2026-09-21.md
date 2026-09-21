# Physics workflow availability pilot — 2026-09-21

**Decision: keep the claim/evidence utility optional.** This pilot tests its availability on six small public manufactured cases. It does not establish a research-quality improvement or justify default adoption, additional mandatory reports, production role changes, or Steps 3–4.

The [machine-readable result](physics-pilot-2026-09-21.json) includes all 36 attempts, paired measurements, case reviews, source and artifact hashes, commands, answers, and deidentified copies of the inspected artifacts. Original transcripts and host-specific runner/preflight receipts are retained in the owner’s local task archive. Public copies replace local numerical-interpreter and any trial-workspace paths; original hashes identify the unchanged local files.

## Case outcomes

These counts mean that the AI controller found the case-specific decision, evidence, provenance and execution scope satisfactory. They are separate case checks, not an aggregate scientific-quality score or human approval.

| Case requirement | Baseline | Utility available |
| --- | ---: | ---: |
| Accept bounded spectral reproduction; retain coarse-grid failure | 3 / 3 | 3 / 3 |
| Reject the converged wrong-boundary calculation | 3 / 3 | 3 / 3 |
| Stop the failed solve without excluding the physical branch | 3 / 3 | 3 / 3 |
| Refute the analytic claim with an admissible counterexample | 3 / 3 | 3 / 3 |
| Retain agreement while rejecting held-out predictive evidence | 3 / 3 | 3 / 3 |
| Reuse the compatible cache; compute only missing/incompatible modes | 3 / 3 | 3 / 3 |

The controller observed no false acceptance of the unsupported claims in cases 02–05 and no false rejection of the valid control in case 01. Case 06 compatibility decisions are reported separately above.

The utility was used to inspect an index in **0 of 18** availability sessions; **2** session(s) invoked its help. Both groups received the same index declarations and could read them directly. Availability and actual utility use must therefore be distinguished. This comparison does not test removing the declarations or the full production instruction/history stack.

## Execution measurements

| Measurement across 18 sessions per condition | Baseline | Utility available |
| --- | ---: | ---: |
| Within the 600-second time budget | 18 / 18 | 18 / 18 |
| Original inputs preserved | 18 / 18 | 18 / 18 |
| Within the 6,000-output-token budget | 18 / 18 | 18 / 18 |
| Summed worker elapsed time | 2557.2 s | 2285.0 s |
| Median worker elapsed time | 136.4 s | 130.7 s |
| Uncached input tokens | 350,514 | 265,675 |
| Cached input tokens | 1,147,648 | 1,104,768 |
| Output tokens (including reported reasoning) | 69,094 | 62,037 |
| Sessions with a failed shell command | 7 | 1 |

Observed critical failures: 0. Scientific execution-scope failures: 0. No trial was retried or replaced. Human review time was not measured. See individual records for every operational issue and failed command.

Observed worker requests for human input: 0; human interventions during trials: 0; agent-tool network calls: 0. Required model-service transport is separate from tool access to outside evidence.

Runtime and token differences are descriptive. They include service/cache variability, concurrent host activity and shell recovery, with only three paired blocks and fixed case order. They cannot establish a causal speed benefit from the index. Parent setup, preflight debugging, grading and reporting costs are excluded; these token counters are not a bill.

## Method and limits

- The unchanged [prospective protocol](../physics-pilot/protocol.json) and [rubric](../physics-pilot/evaluator/rubric.json) were frozen before dispatch. The protocol’s `prepared-not-run` status is historical; this separate result records the later execution. Implementation revision: `0247e18ec9227cb84f0db4662f715ad605bf2265`.

- Each case/condition used a fresh session. Baseline ran first in blocks 1 and 3; the availability condition ran first in block 2. Inputs, prompt, runtime, model request and budget matched apart from the utility file. No cross-trial feedback was given.

- Requested model/effort: `gpt-6-astra` / `xhigh`; CLI: `codex-cli 0.155.0-alpha.9.2`. Actual served-model identity was not separately reported by exec events. NumPy 2.4.6 and SciPy 1.17.1 were used.

- A native process sandbox and restricted model-service relay passed a model-executed preflight denying reads of the source checkout, evaluator, private research, prior history, other trials and controller, plus out-of-scope writes and direct network access. Necessary model authentication/runtime files and numerical dependencies remained accessible. This tested boundary is not a formal adversarial security proof or hermetic-container claim.

- The process-group timeout mechanism was tested before launch with a short deadline; trials used a 600-second deadline. The CLI supplied no verified hard generated-token cap: output usage was checked on completion, with any overrun retained as failed budget compliance. Native runtime warnings and failed shell here-document commands are preserved; recovery within a session is distinct from a new scientific trial or repair.

- The controller inspected actual derivations, generated numerical files and execution traces against the frozen rubric. Closed-form discrete eigenvalues independently checked the numerical references. Grading was condition-visible AI review, not independent human approval. No human PDF usability comparison occurred.

- Simple, explicit fixtures can produce a ceiling effect. Success does not establish novelty judgment, discovery productivity, private-research benefit or empirical validation. Case 06 is a saved-checkpoint exercise, not a live crash-recovery test.

Continue physics work under its existing authority and framework pins. PDF remains the human scientific review format; the optional agent-facing navigation utility gains no mandatory role from this result.
