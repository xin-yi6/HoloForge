# Designing figures for a physics manuscript

Use this guide with [manuscript writing](physics-manuscript-writing.md).
A paper figure advances a physical argument; an owner-review graphic records
research progress or a decision. Their purposes and styles are different.
This guidance authorizes no new calculation, fit, threshold change or disclosure.

## Start from the question, not the palette

Before plotting, state privately what the reader should learn and which saved
data, analytic expression or schematic supports it. A figure may explain a
mechanism, show an observable, compare alternatives, expose a scaling law or
establish numerical credibility. There is no quota of figures or mandatory
combination of these roles.

| Scientific task | Useful design | Important limitation |
| --- | --- | --- |
| Compare a prediction with a reference | Observable panel plus a difference or ratio panel when needed | Agreement, improvement and physical effect size are different statements. |
| Isolate a small correction | Explicitly normalized or baseline-subtracted quantity with physical context | State the denominator, units and uncertainty transformation; do not exaggerate a small effect. |
| Compare regimes or models | Aligned small multiples with stable encodings | Shared axes suit magnitude comparisons; disclose deliberately different ranges. |
| Show a complex trajectory or multiple branches | Ordered points, path arrows and physical coordinates; complementary parameter panels if useful | Do not sort away a fold, join an uncomputed gap or label an arbitrary continuation path an equilibrium boundary. |
| Explain a mechanism or construction | Labeled schematic beside the quantity it explains | Identify the schematic as such; geometry is not computed data. |
| Establish a bound, scaling or controlled approximation | Physical comparison with the bound/limit and a diagnostic inset or panel | A straight log plot is not an independently established exponent; fitting needs its own authority. |

Numerical diagnostics may be the main result of a numerical-method paper. In a
physical model paper, do not let a sequence of residual plots replace the
observable and its interpretation. Retain consequential failures and uncertainty
beside the claims they affect, even when other checks belong in an appendix.

## Learn from suitable examples

The [figure reading study](physics-figure-reading-study.md) records selected
figures from 20 distinct papers, including a seven-paper author-supplied cohort.
It is a visual study of figures, captions and nearby discussion, not twenty
new full-paper scientific audits or proof of a universal style. The prose
corpus's reading counts do not imply that its figures were visually inspected.

Select examples by their explanatory job and the target author's preferences,
not fame alone. Compare within and across fields. Record exact source versions,
figure numbers and pages actually inspected. Learn transferable principles,
including exceptions; do not reproduce copyrighted figures or distinctive
layouts, and do not add style references to a manuscript's scientific bibliography
unless they substantively support its physics. Downloaded papers remain outside
public HoloForge. A public preprint is not necessarily a journal version.

## Preserve the meaning of every mark

- Name physical quantities, units, normalizations and held-fixed conditions.
  Label logarithmic arguments and dimensionless ratios unambiguously.
- Distinguish computed samples, analytic predictions, fitted curves, reference
  measurements and schematic guides. A joining line is not extra sampled data.
  Never add smoothing, extrapolation or a fit only to make a plot attractive.
- Keep branch order, missing intervals, excluded points and unsuccessful cases
  visible or explicitly documented. A plot of successful cases is not a complete
  uncertainty envelope for all attempted cases.
- Preserve uncertainty semantics: measurement errors, parameter variation,
  truncation estimates and empirical numerical sensitivities are not interchangeable.
  State the interval meaning and what it excludes. Do not invent statistical
  confidence or independence. Shared normalization requires correlation-aware
  propagation or an explicitly conservative transformation of existing envelopes.
- If errors are smaller than markers, say so and use a diagnostic panel or
  values when their size matters. Do not enlarge error bars for visibility.
- Use a log scale deliberately. Use point comparisons instead of magnitude bars
  on a logarithmic axis when an arbitrary positive bar baseline would mislead.
- A display transformation may replay existing arithmetic. It must not silently
  introduce a new estimator, calibration, tolerance or scientific acceptance rule.

## Adopt a consistent, readable manuscript style

Use maintained plotting libraries and their normal export facilities, not a
new plotting framework. Adapt the settings to the author's manuscript and
target journal rather than imposing a single HoloForge house template.

1. Choose final column/full-page width before setting text sizes. Inspect the
   figure embedded at that width, not only a magnified standalone preview.
2. Use consistent mathematical typography, line weights, tick formatting and
   panel labels. Keep text dark and legible; avoid tiny gray labels.
3. Assign color to a stable scientific meaning. Reinforce it with markers,
   dashes, direct labels or panel separation; test grayscale readability.
4. Use restrained grids and backgrounds. Shading should represent a stated
   region or interval, not decorate a panel. Avoid hiding curves under legends.
5. Align related panels and preserve useful plotting area. Do not shrink labels
   to fit too many curves; split panels or simplify redundant labels instead.
6. Prefer vector PDF for line plots and diagrams, with embedded fonts. Raster
   fields may remain raster at suitable resolution; increasing export DPI does
   not recover absent information.

The [APS axis guidance](https://journals.aps.org/authors/axis-labels-and-scales-on-graphs-h18)
supports clear quantities, scales and units. The
[Nature figure guide](https://research-figure-guide.nature.com/figures/building-and-exporting-figure-panels/)
provides useful final-size, font, color and export checks. Its numerical sizing
requirements are journal-specific, not universal physics rules. Check current
requirements when a journal is selected.

## Finish with captions, provenance and rendered checks

Each caption should identify the observable, panel mapping, model/conditions,
marks, normalization, uncertainty and any consequential omission. The main text
then explains what the comparison means; a caption alone is not the argument.
Avoid internal task IDs, status labels and workflow slogans in manuscript figures.

Keep the source-to-figure mapping and display arithmetic in the private companion
record. Rebuild from saved evidence, check plotted arrays and caption values,
inspect every final manuscript page, and check grayscale or redundant encodings.
Record which checks actually ran. A clean rendering does not validate the physics;
preserve scientific review, AI provenance and disclosure status.

For an editorial revision, preserve the old PDF and data. Explain why each
substantive visual change helps the physical argument. New scientific evidence
requires a separately authorized research task, not another cosmetic pass.
