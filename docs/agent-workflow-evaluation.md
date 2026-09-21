# Evaluating agent workflow changes

The scientific framework and its agent workflow need different evidence.
Regression tests can establish numerical or record-handling behavior. A role
arrangement needs observed task outcomes, cost, intervention and recovery
measurements before it becomes a default.

## Physics workflow availability pilot — 2026-09-21

The separate [physics pilot](../evals/agent-workflows/physics-pilot/README.md)
uses six public synthetic cases to compare otherwise matched sessions with
and without the optional [claim/evidence index](claim-evidence-index.md)
utility. It includes a valid acceptance control as well as scientific and
numerical failure cases.

The [execution report](../evals/agent-workflows/results/physics-pilot-2026-09-21.md)
records 36 fresh sessions across three paired blocks. Both conditions met all
case-specific requirements under AI controller review, with no observed critical
failures. None of the 18 utility-available sessions actually inspected an index
with the utility; two invoked its help. Both groups received identical index
declarations. This result cannot establish a benefit from using the utility or
from the declarations themselves, and human PDF review time was not measured.

**Decision:** keep the utility optional and production roles unchanged. The
small, explicit fixtures do not establish improved research judgment or
discovery productivity. The prospective protocol retains its historical
`prepared-not-run` status; the dated report records the subsequent execution.
The historical role pilot below remains unchanged.

## Synthetic role pilot

The first pilot compares the current four-role pattern with a consolidated
executor/coordinator plus an independent verifier. It is an infrastructure
experiment, not a research gate, new scientific result or campaign migration.
The frozen [protocol](../evals/agent-workflows/protocol.json),
[role prompts](../evals/agent-workflows/prompts.json), and
[fixture task](../evals/agent-workflows/fixtures/task.md) define the comparison.

Each of two paired blocks gives both conditions identical immutable fixtures
and the same snapshot of repository instructions, maintenance guidance and the
auto-research skill. All agents use the same inherited model and reasoning
effort. The cases cover an affine calibration repair with disjoint verification,
a source conflict with an exhausted repair budget, and a corrupted checkpoint.
Independent verifiers receive raw inputs before any worker outputs. A second
block reverses condition dispatch order. Outputs are preserved without retries.

The four-role pattern uses a source auditor, executor, verifier and final
coordinator. In the two-role condition, the executor also assesses sources and
receives one follow-up containing its verifier's sealed findings. Role counts
therefore differ from turn counts. This is a controlled approximation of role
patterns, not a comparison of complete production research campaigns.

## Recorded pilot result — 2026-09-05

All 12 fresh agents ran with runtime-reported `gpt-6-astra` and `xhigh` effort.
The two conditions each completed both trials, with no retries, observed extra
owner questions or unauthorized actions. Each passed all 32 deterministic
checks across its two trials. Independent verifiers established their findings
before worker outputs were supplied to the final coordinating role.

| Measurement across two trials | Four roles | Two roles |
| --- | ---: | ---: |
| Deterministic checks passed | 32 / 32 | 32 / 32 |
| Uncached input tokens | 111,106 | 65,205 |
| Cached input tokens | 1,470,080 | 1,074,944 |
| Output tokens, including reported reasoning | 21,206 | 16,195 |
| Top-level tool dispatches | 35 | 24 |
| Summed role-turn duration | 1,297.3 s | 930.1 s |
| Mean observed cohort elapsed time | 423.2 s | 352.7 s |

The consolidated arrangement used 41.3% less uncached input and 23.6% fewer
output tokens in this pilot. It showed lower observed elapsed time in both
blocks, but scheduling gaps, cache behavior and concurrent work prevent a
controlled latency claim. Parent-agent work, fixture construction and report
writing are excluded from these figures. They are token measurements, not a
bill or a measure of research productivity.

The [machine-readable report](../evals/agent-workflows/results/pilot-2026-09-05.json)
preserves each run, output, per-check result, runtime counter, input hash and
limitations. Raw role transcripts and their local locators remain outside the
public tree. Their source hashes are included for the owner's audit.

**Decision:** retain production research roles. The observed savings justify a
harder comparison of the two-role candidate before adoption. All roles mostly
used the same elementary arithmetic; separate execution contexts do not prove
independent scientific methods. The structured example also exposed some
expected review flags, so these cases provide weak evidence about open-ended
judgment. No real literature search, scientific repair or recovery run occurred.

## Scoring and measurement

Run the deterministic scorer on the coordinating role's final JSON:

```bash
python3 evals/agent-workflows/score.py path/to/final-answer.json
```

Sixteen checks cover arithmetic, a corrected inverse evaluated at additional
inputs, source versions, frozen thresholds, stop decisions, file integrity and
review labels. Critical failures remain visible individually. A total cannot
compensate for an unauthorized repair, false scientific claim or reused corrupt
checkpoint. The scorer evaluates only a restricted arithmetic expression and
does not execute submitted programs.

Inspect actual role transcripts separately: a claimed independent check or
absence of human questions is not proved by a JSON field. Record model/effort,
role and turn counts, individual turn durations, cohort elapsed time, tool
calls, observed questions and input-scope violations. Count native runtime
token usage once per response; do not sum cumulative counters. Separate cached
input, uncached input, output and reported reasoning tokens. Missing counters
are unavailable, not zero, and character counts are not token counts.

For the observed Codex JSONL telemetry, pass the exact role logs explicitly:

```bash
python3 evals/agent-workflows/measure.py role-one.jsonl role-two.jsonl
```

The parser checks response-level counts against cumulative totals and emits
source hashes without log paths or message text. Tool counts are top-level
dispatches; one dispatch may batch several underlying operations. Cohort elapsed
time includes parent scheduling and handoff gaps. Summed turn duration counts
parallel work separately and is not CPU time or billed cost.

Keep raw runtime logs, absolute local paths and task identifiers outside the
public repository. A public result should contain only generic measurements,
fixture/protocol hashes, checks and limitations. Local raw receipts allow the
owner to trace those measurements without exposing other project context.

## Interpretation boundary

Two easy paired trials can reveal a broken evaluation setup, unnecessary
handoffs or clear local overhead. They cannot establish a superior research
architecture, source-search skill, physical judgment, long-run recovery or
publication productivity. Explicit task instructions and a structured output
interface make these cases easier than open research. A hash-stop case tests
detection, not actual crash recovery. Shared runtime context, cache state,
concurrency and parent scheduling can influence costs and elapsed time.

Do not change default roles from this pilot alone. A further comparison should
use less explicit cases, competing source evidence, a meaningful repair and an
actual interrupted/resumed operation. Preserve identical model, scope, budget
and acceptance criteria across conditions. Test shorter instruction loading as
a separate factor so its effect is not confused with changing role counts.
