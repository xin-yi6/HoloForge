# HoloForge agent instructions

HoloForge is a verification-first platform for bottom-up gauge/gravity
modelling. **Forge/Verify** reproduces literature-anchored models;
**Explore** tests falsifiable hypotheses with explicit support and disclosure
states. A passing model calculation is not empirical validation of nature.

## Start with the current task

1. Inspect `git status` and preserve unrelated changes.
2. Classify the request as Forge/Verify, Explore, or infrastructure/documentation.
3. Load the matching workflow below and only the context needed for this task.
   Read [README.md](README.md) and [the quickstart](docs/agent-quickstart.md)
   when orienting to the project or its environment; reuse unchanged context.
4. Before a substantial change, state its files, validation, and scientific
   boundary. Prefer narrow, reversible changes and maintained library functions.

## Choose the matching workflow

| Task | Read and follow |
| --- | --- |
| Status, instruction upgrades, concurrent maintenance, or resumption | [Agent maintenance](docs/agent-maintenance.md) |
| Public benchmark design, review, implementation, or extension | [holoforge-add-benchmark](.agents/skills/holoforge-add-benchmark/SKILL.md) |
| One bounded Explore gate | [holoforge-research-gate](.agents/skills/holoforge-research-gate/SKILL.md) |
| An autonomous Explore campaign | [holoforge-auto-research](.agents/skills/holoforge-auto-research/SKILL.md) |
| Any private-to-public artifact transfer | [holoforge-public-export](.agents/skills/holoforge-public-export/SKILL.md) |

Invoke repository skills when available; otherwise read the linked `SKILL.md`.
Follow its relevant document links before the corresponding operation. Reuse
authorization already recorded for the same scope. Ordinary maintenance and
status requests do not open a scientific gate or require an A-E menu.

## Scientific and privacy boundaries

- Read [CONSTITUTION.md](CONSTITUTION.md) before scientific work or changing a
  scientific contract. Record conventions, equations, boundary conditions,
  ensemble, methods, tolerances, evidence, and limitations. Use the labels in
  [scientific support](docs/scientific-support.md); preserve AI provenance.
- Keep unpublished research in a separate access-controlled repository. Never
  add secrets, private paths, confidential correspondence, or unpublished
  identifiers, calculations, or results to this public repository. Calculation
  authority does not authorize publication or public transfer.
- A frozen contract, bounded autonomy window, or exact authorized mission
  controls research execution. Preserve framework pins, thresholds, budgets,
  raw evidence, and human review states. Finish authorized routine work and
  return at its first declared stop, outcome, or undelegated decision. Model
  upgrades and personal skill defaults cannot expand that authority.
- Numerics serve a registered physical decision. Apply the prospective
  [claim-sufficiency checkpoint](docs/research-gate-workflow.md#use-a-claim-sufficiency-checkpoint)
  and stop refinement that cannot change the decision or strengthen the claim.
  Never obtain sufficiency by weakening a threshold or dropping a failed check;
  a technical stop is not automatically a physical negative result.
- Use the research-gate workflow for opportunity assessment, cumulative repair
  limits, milestone knowledge, and closure lessons. Keep provisional knowledge
  evidence-linked and separate from human-reviewed knowledge. Use one canonical
  writer per mutable research project and preserve independent verification.

## Validation and completion

Choose checks using [the maintenance policy](docs/agent-maintenance.md#choose-checks-that-can-establish-the-intended-behavior).
For executable infrastructure or scientific changes, run focused checks, then
these integration checks once in the documented environment:

```bash
python -m unittest discover -s tests -v
holoforge verify soft-wall-vector
```

Run the relevant frozen scientific controls when scientific behavior changes;
keep results, model records, documentation, and tests synchronized. For
documentation-only changes, inspect links and affected skill/policy checks.
Inspect the final diff and run `git diff --check`. Finish authorized fixes and
required validation before delivery; repeat checks only after relevant changes
or new concerns. Full default CI remains required for public integration.

## Git and review

- Keep commits and pull requests limited to one logical change.
- Stage only intended files; never discard unrelated work.
- For owner-requested work in this public repository, standing owner
  authorization permits scoped local commits and normal fast-forward pushes
  to the existing `origin` remote and intended branch. Complete the relevant
  local validation and public-content review, inspect the outgoing commits,
  and check the remote state first. Do not ask again for each routine push;
  verify the remote commit and report CI afterward.
- Merging, releases, branch deletion, force pushes or history rewrites, changing
  the remote destination, and private export or scientific disclosure require
  separate explicit authorization. A later task-specific restriction overrides
  the standing public-repository permission.
- Treat a bounded autonomy window as execution authority only. A local commit
  must be explicitly included in it; push, merge, release, branch deletion,
  public export, and disclosure remain separate owner decisions for that
  research scope. Standing public-repository permission does not expand a
  frozen Explore window or autonomous mission, or permit its pinned framework
  to be changed.
- Before requesting an owner decision, give an item-by-item recommendation,
  reason, scope opened, scope remaining closed, and important uncertainty.
- At an owner gate, also state completed, current, and proposed next stages,
  then offer A-E paths: approve all recommendations, approve selected items,
  request revision or evidence, status walkthrough only, or a custom response.
  Recommend one path and never infer authorization beyond its stated scope.
