# Physics workflow pilot

The [September 21 execution report](../results/physics-pilot-2026-09-21.md)
records all 36 fresh sessions. Both conditions satisfied the six case-specific
checks in all three blocks under AI controller review. No session used the
utility to inspect an index, so this availability comparison does not establish
a benefit from using it. The utility remains optional; no production default
or scientific workflow changes follow from this small pilot.

The prospective protocol retains its original `prepared-not-run` status and
bytes. The separate dated result records the later execution without rewriting
that historical record.

This is a new infrastructure pilot alongside the preserved September role
pilot. The [protocol](protocol.json) defines one intervention: availability of
the optional claim/evidence navigation utility. It does not combine a model
change, new agent roles, structured attempts or lesson retrieval.

The six small cases are self-contained, manufactured mathematical/physics
examples. They are not public benchmark additions, new physical results, or
fixtures derived from unpublished research. They exercise a valid spectral
reproduction, a converged wrong boundary problem, a solver stop, an analytic
boundary-term assumption, calibration versus prediction, and cached-state
compatibility. Their simple and sometimes explicit clues limit conclusions
about open-ended scientific judgment.

## Stage one case

```bash
python evals/agent-workflows/physics-pilot/prepare.py \
  /tmp/physics-baseline-case-01 --case case-01 --condition baseline

python evals/agent-workflows/physics-pilot/prepare.py \
  /tmp/physics-index-case-01 --case case-01 --condition evidence-index
```

Destinations must not exist. Both receive identical case records, source
indexes, task instructions and the small interval calculator. Only the second
receives `claim_evidence.py`. Each gets a hash manifest. No evaluator files,
other cases, transcripts, private records or reference answers are copied.
The staged tool can be called with `case-01/index.json --root case-01`.
The calculator needs NumPy and SciPy; the navigation tool uses only Python's
standard library. Shared code is original to this pilot.

**Staging is not isolation.** Before a live agent comparison, use a host that
can actually restrict read access to the staged case and tool dependencies.
It must exclude this source checkout, the evaluator directory, other trials
and private projects. A fresh conversation with unrestricted filesystem access
is not blinded. If that separation is unavailable, record a non-blinded
development exercise and do not claim a controlled evaluation.

## Evaluate the behavior, not the self-report

Freeze the implementation revision, protocol/input hashes, model, effort,
runtime, budgets and order before dispatch. The comparison has three
paired blocks over six cases, with one fresh context per case/condition and no
retries or shared answers. Keep both conditions' ordinary instructions and
evidence identical; record the tool availability difference explicitly.

The controller retains [the evaluator rubric](evaluator/rubric.json) separately.
Use its case-specific criteria with actual derivations, source locators,
output files and execution receipts. Equivalent valid reasoning is acceptable;
do not grade prose similarity. An independent reviewer should inspect raw
artifacts before the condition identity is revealed where practical. Record
when tool traces prevent complete reviewer blinding. This pilot does not
automatically establish human approval or method independence.

Report false acceptance and false rejection, diagnosis, scope compliance,
observed interventions, elapsed time and token counters separately. Missing
measurements remain unavailable. Human PDF review effort is a separate,
counterbalanced comparison using the same scientific argument and evidence;
record prior exposure and order effects. Do not invent review-time savings
from automated checks or agent impressions.

The valid case prevents blanket rejection from winning. Failed critical checks
cannot be offset by faster execution or better results on other cases. A small
positive pilot only motivates a further bounded trial; it cannot demonstrate
discovery productivity, novelty judgment, or a generally superior architecture.

Case 06 is a saved-checkpoint exercise, not an observed process interruption.
Completing it demonstrates selective reuse/recomputation on the supplied
snapshot. A live crash-recovery claim needs a separate frozen interruption
experiment and execution receipts.

## What has been validated here

`tests/test_physics_workflow_pilot.py` checks numerical fixture reproduction,
the correct control and wrong-boundary limit, cache-state differences, index
integrity and staging isolation at the file-copy level. The index's adverse
tests are in `tests/test_claim_evidence.py`. These are software and fixture
checks, **not executed agent trials**. The later live execution and its limits
are documented in the dated report above; preparing the fixtures alone did not
establish agent performance.
