# Research-progress snapshots

HoloForge can render one project-local research state as Markdown/Mermaid and
as standalone SVG, PNG, or PDF figures. These are optional views, generated
only on an explicit owner request. Routine scientific reports use a short
completed / unresolved / next decision or action summary, without a separate
progress diagram or progress PDF. Earlier adoption does not require continued
rendering; an explicit ongoing request can be stopped by the owner.

The JSON supplies one consistent input for a requested view. Canonical project
status, attempt history, evidence links and owner decisions remain maintained
whether or not a figure is requested. If the JSON itself serves as canonical
state, keep its state fields current without requiring a figure. Preserve old
snapshots and reviewed packets as dated history, and read current status before
resuming research. Refresh the view's inputs before rendering it again.

The snapshot describes the actual research project: source review, frozen
questions, calculations, verification, stops, owner decisions, and later
branches. It is not a HoloForge software-development chart and is not
background telemetry.

## Figure styles

Set the optional top-level `figure_style` field to one of:

- `compact` — the recommended style for a requested owner-review figure. It uses a
  clean stage rail, uniform rounded boxes, semantic status colors, a strong
  outline for the current or blocked stage, and dashed boxes for pending or
  skipped work. Group membership remains in the canonical JSON and Mermaid
  view but does not add visual boxes to the standalone figure.
- `grouped` — the original detailed map. It shows group clusters and uses
  different node shapes for tasks, checks, decisions, and outcomes.

Records created before `figure_style` existed remain valid and render with
`grouped`. The checked-in example selects `compact`, so new projects receive
the simpler owner-facing style when an explicitly requested view uses the example.

Use `layout_direction: "TB"` for a vertical research path and `"LR"` for a
wide map. The compact style is designed first for `TB`, which can fit an
explicitly requested progress page in the review-packet template.

For a long, mostly sequential `compact`/`TB` path, the optional integer
`compact_wrap_after` sets the maximum number of stages in each display column.
The renderer lays the declared stage order out as a serpentine path, so the
route may turn into the next column instead of becoming one increasingly tall
straight rail. For example:

```json
{
  "layout_direction": "TB",
  "figure_style": "compact",
  "compact_wrap_after": 9
}
```

Omit the field for the ordinary straight rail. Use wrapping only when it makes
the actual research path easier to review; the `stages` array should then
follow the intended owner-facing sequence. Wrapping changes positions only.
The declared transitions, written statuses, current stage, completed work,
and closed scope remain authoritative. Do not rearrange or omit a scientific
branch merely to make the picture tidier.

## Status language and accessibility

Every node retains a written status as well as a color:

| Semantic status | Compact appearance |
| --- | --- |
| `completed` | pale green with a green border |
| `current` | pale amber with a strong amber border |
| `pending` | pale blue with a dashed blue border |
| `blocked` | pale red with a strong red border |
| `skipped` | pale slate with a dashed slate border |

An optional stage-level `status_label` may refine the displayed wording when
the semantic state remains accurate, for example `"SOURCE STOP"` on a
`blocked` stage or `"PROPOSED"` on a `pending` stage. It must not disguise a
failed or blocked stage as completed.

Stage completion means only that the workflow task is recorded as finished.
It does not increase the scientific-support level of a claim.

## Render from one state

When a view is requested, copy the generic state and replace every example
stage with reviewed project state:

```bash
cp .agents/skills/holoforge-research-gate/assets/research-progress.example.json \
  /path/to/private-project/research-progress.json
```

Render only the requested views from that same JSON file. For Markdown and SVG:

```bash
python .agents/skills/holoforge-research-gate/scripts/render_research_progress.py \
  /path/to/private-project/research-progress.json \
  --output /path/to/private-project/research-progress.md \
  --figure-output /path/to/private-project/research-progress.svg
```

Markdown rendering needs only Python. Standalone figures require the
maintained Graphviz `dot` program. To fulfill an explicit request for a PDF
diagram, add `--figure-output /path/to/private-project/research-progress.pdf`.
Include it on its own page only when the owner requests a process figure in
that packet; set `\HoloForgeIncludeProgress`, `\researchprogressfile`, and
`\researchprogressupdated` in
[`review-packet-template.tex`](templates/review-packet-template.tex).
Needing a scientific PDF does not itself request a diagram. Scientific plots,
equations and evidence tables remain part of the ordinary review report.

## Privacy boundary

Keep unpublished state and generated figures in the access-controlled research
repository. A generic style or renderer improvement may enter public
HoloForge only after the public-export workflow; candidate identities,
equations, values, outcomes, private paths, and repository history remain
private unless separately cleared for disclosure.
