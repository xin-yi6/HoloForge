---
name: holoforge-add-benchmark
description: "Design, review, or implement a public HoloForge Forge/Verify benchmark from established literature. Use for public model contracts and reproducible checks; use research-gate for unpublished hypotheses."
---

# HoloForge Add Benchmark

Add one literature-anchored executable verification target without forcing a
new numerical problem into an unsuitable common solver interface.

For status or documentation maintenance, use [agent maintenance](../../../docs/agent-maintenance.md).
For scientific work, reuse a current approved contract and its authorization
when the requested scope is unchanged; review only a new or changed contract.

## Freeze the benchmark contract

1. Read `CONSTITUTION.md`, `CONTRIBUTING.md`, `docs/scientific-support.md`,
   `schemas/model-card.schema.json`, and `src/holoforge/core/contracts.py`.
2. Inspect the current built-in registry and the closest relevant benchmark
   implementations, guides, model cards, adapters, and tests. The reference
   suite can grow; do not assume it contains only two benchmarks.
3. Record the primary public source and exact equations or figures reproduced.
4. For a classical bottom-up example, quantitatively reproduce at least one
   scientifically central source figure or table when feasible. If no source
   figure or table is suitable, record an owner-reviewed reason and an
   alternative quantitative literature check in the frozen contract. Visual
   resemblance alone is not validation; retain the underlying numerical
   comparison, provenance, and tolerance.
5. State action, dimensions, signs, coordinates, units, normalization,
   ensemble, sources, responses, UV conditions, and IR or horizon conditions.
6. Define observables, numerical inputs, analytic or external reference values,
   acceptance tolerances, limitations, and explicit failure conditions.

Do not begin substantial implementation until the scientific contract is
reviewable.

## Make scientific review readable

When equations, tables, or plots are difficult to review reliably in Markdown,
stop before requesting owner approval and prepare a PDF from
`docs/templates/review-packet-template.tex`. Include the conventions, sources
and responses, equations, parameters, acceptance gates, limitations, hostile
critic, and exact owner decisions with an item-by-item recommendation.

Compile twice, inspect the log for layout warnings, render every page to an
image, and visually check clipping, overlaps, equations, tables, plots,
headers, and page numbers. A readable packet enables review; it is not itself
approval. Do not begin implementation until the owner reviews the packet and
confirms or revises the scientific contract.

## Implement narrowly

1. Use maintained NumPy/SciPy functions for eigenproblems, root finding,
   integration, interpolation, and boundary-value problems when they match the
   mathematics. Write a numerical primitive only with a documented reason.
2. Reuse `holoforge.core` metadata and `VerificationRecord`; add a new shared
   abstraction only when at least two heterogeneous benchmarks need it.
3. Keep model physics in its benchmark module and expose one bounded verifier.
4. Record configuration, solver method, software versions, results, acceptance
   checks, scope, and limitations in machine-readable output.
5. Add the CLI route without changing existing benchmark defaults or output.

## Verify the scientific claim

Require checks proportional to the claim, including as applicable:

- analytic limits or exact solutions;
- grid, cutoff, tolerance, and method convergence;
- equation and boundary residuals;
- constraints, sources, Ward identities, or thermodynamic identities;
- independent solver or formulation comparison;
- regression data generated from declared public provenance; and
- expected failures for invalid inputs and rejected tolerances.

Use more than one numerical resolution for a convergence claim. Do not tune an
acceptance threshold after seeing a disagreement without documenting and
reviewing the reason.

## Complete the public artifact

Update:

- `src/holoforge/benchmarks/` and its exports;
- `src/holoforge/cli.py`;
- the corresponding model card under `domains/`;
- a guide under `docs/benchmarks/`;
- analytic, numerical, CLI, schema, and failure tests under `tests/`; and
- release documentation when the public behavior changes.

Run the new verifier in human and JSON modes, its declared scientific checks,
schema validation, the full test suite, and the documented fast smoke verifier.
Run package build/install checks when packaged behavior changes. Existing
verifiers already exercised by the full suite need not be duplicated unless a
new concern requires it. Run `git diff --check` and inspect generated figures
visually when present. Use `docs/agent-maintenance.md` for documentation-only
maintenance; it does not authorize another scientific calculation.

## Report the outcome

Lead with what the benchmark reproduces and the strongest limitation. List the
source, equations, conventions, solver, acceptance gates, checks run, and exact
unsupported claims. Classify disagreement as a scientific or numerical result;
do not hide it by weakening the benchmark.
