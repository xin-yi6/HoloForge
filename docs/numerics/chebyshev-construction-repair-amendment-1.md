# Chebyshev repair: qualification amendment 1 (post-observation), frozen

- **Status: ADOPTED for one bounded continuation, and FROZEN before any
  continuation run.** AI-assisted (Claude).
  - Codex reviewed the proposal at `335331c` and recommended a bounded
    continuation under five conditions. The owner approved them on
    1 October 2026.
  - This document was revised to those conditions and then frozen. The
    commit that carries this status line is the freeze. Every continuation
    evidence file records this file's SHA-256.
- **Post-observation.** This amendment was written after the S0 results were
  seen: every metric at 84 grids on two builds, and every qualification
  failure. It is not a prospective rule for those grids, and it must never be
  described as one.
- **The original result stands.** Under the
  [frozen plan](chebyshev-construction-repair-plan.md) (`0cd24dd`), S1
  stopped with "no candidate qualifies". That stays the recorded outcome of
  the frozen rule, whatever this amendment yields.
- **Label.** A candidate that passes here is "qualified under
  post-observation amendment 1". It is never reported as passing the frozen
  rule.
- **History.** Prepared at Codex's request after its first review of PR #55
  (item R55-3). Its C-S1 entry model was corrected after the re-review of
  `d5eb95a` (item R55-F1). The changes made at the freeze are listed in
  Section 9.

## 1. What is unchanged

- **Plan and evidence:** the frozen plan and all its evidence.
- **Candidates:** the candidate set and their declared definitions.
- **Metric (a), the entrywise rule:** within 2× of the current construction,
  against the stored-node reference. No floor is added.
- **Polynomial exactness:** at most `1e-10`.
- **Selection:** the 10× improvement requirement on metric (c), and the
  tie-break.
- **Later stages:** A1, A2, the control routes, the API checks, every
  benchmark gate and threshold, and the reserved cases.

## 2. What changes

Only the rule for **metric (b)**, the row-scaled action error
`e_i = |((R - D) v̂)_i| / S_i`, against the stored-node reference.

| | A component (one matrix, one test vector, one row set) fails when |
| --- | --- |
| **Rule 1 (frozen)** | its value exceeds 2× the current construction's |
| **Rule 2 (C-S1 only)** | its value exceeds 2× the current construction's **and** its bound ratio exceeds 1 |

- **The bound ratio** is `max_i e_i / B_i` over the rows of the set. `B_i` is
  the first-order rounding bound of C-S1's own declared construction
  (Section 3), in the same row scaling.
- **Rule 2 applies to C-S1 only.** C-T1, C-T2 and C-T3 keep rule 1 for
  every component. No bound of theirs is verified, and none could cover
  their node-set difference from the stored-node reference.
- **A component of C-S1 with no finite recorded bound ratio keeps rule 1.**

**Entry requirement (C-S1 only, added at the freeze).** Every entry of
C-S1's D1 and D2 must lie inside the same first-order bound, on every grid
of both sets and on both builds:
- **Check.** `|R_ij - D_ij| / B_ij <= 1` for every `i, j`, with `B_ij` the
  entry bound of Section 3. This is the action bound applied to every
  coordinate vector. It uses the same reference matrices as the metrics.
- **Kept.** For each matrix and grid, the error, the bound and their ratio
  at the worst entry are recorded, not only a verdict.
- **A violation, or an undefined quantity, is a stop.** It is never
  permission to change the model.

**Why this, and why not a floor.**
- **The measured values are real.** Metric (b) is measured against a
  50-digit reference with an error near `1e-32`. A value below machine
  epsilon is a genuine property of the matrix, not measurement noise.
- **The problem with rule 1.** No double-precision construction has zero
  construction rounding. Rule 1 compares the rounding of two different
  correct constructions and calls any factor of 2 a regression. It does so
  even when both are inside what their algorithms can guarantee.
- **What rule 2 does.** It treats rounding inside the candidate's own
  first-order a-priori bound as not a regression.
- **What rule 2 does not settle.** Whether such rounding moves a benchmark
  output beyond its recorded regression allowance is checked separately by
  Stage A2, which is unchanged. A2 is a maintenance regression allowance. It
  is not a complete uncertainty bound on a physical observable.
- **No blanket floor.** A single constant such as `gamma_(N+1)` is not a
  bound for these metrics. It carries no term magnitudes, and it does not
  follow from the algorithm. The earlier suggestion of such a floor is
  withdrawn (Section 6).

## 3. Roundoff convention, operation assumptions and the bound

**Correction (re-review item R55-F1).** The first version of this section
gave C-S1 a uniform entry error of `5u`. That was wrong at first order.
- **What it missed.** It counted the rounding of the operations *on* the
  weight products. It did not count the rounding already *inside* the
  differences that are multiplied. Accurate accumulation of rounded factors
  does not remove their errors.
- **Codex's counterexample.** C-S1, degree 30 on `[1e-3, 1]`, zero-based
  entry `(7, 8)`: the relative error against exact rational arithmetic is
  `14.17u`.
- **What replaces it.** The uniform constant is withdrawn. It is not
  replaced by a larger one. The C-S1 entry model below follows the
  implemented operations and depends on the stored nodes.

**Convention and assumptions.**
- `u = 2^-53`, the unit roundoff for round-to-nearest. This is half of
  NumPy's `eps`.
- IEEE binary64 arithmetic with round-to-nearest for `+`, `-`, `*` and `/`,
  and no underflow, overflow or subnormal intermediate. This is assumed. The
  tool does not check it at run time.
- The analysis is first order in `u`. The neglected terms are listed at the
  end of this section.
- The stored nodes `u_k` are inputs. The stored-node reference is defined on
  exactly those doubles, so they carry no error.

**C-S1 entry model, from the implemented operations.**

1. **Differences.** `d_ik = fl(u_i - u_k) = (u_i - u_k)(1 + delta_ik)` with
   `|delta_ik| <= u`.
   - An error-free transformation gives the exact difference as a pair of
     doubles. `delta_ik` is evaluated from that pair by one rounded sum and
     one rounded division, so its computed value has a relative error of
     about `2u`. That matters only beyond first order.
   - It is zero when the subtraction is exact.
   - `delta_ki = delta_ik`, because `d_ki = -d_ik` exactly.
2. **Weight products.** `P_i = prod_{k != i} d_ik`, accumulated in
   double-double arithmetic. The accumulation adds only second-order error,
   but `P_i` inherits every input error:
   `P_i = P_i^exact (1 + sum_{k != i} delta_ik)`.
3. **Ratio.** `P_i / P_j` is formed from the two `(high, low)` pairs by one
   rounded quotient and two rounded correction additions: `3u`.
4. **Entry.** `D1_ij = fl(ratio / d_ij)`: one more rounding, and the input
   error of `d_ij` once more.

The factor `d_ij` occurs in both `P_i` and `P_j` with the same relative
error, so it cancels in the ratio. The final division then removes it once.
The signed first-order relative error of an off-diagonal entry is therefore

```text
eps_ij = sum_{k != i, j} (delta_ik - delta_jk)  -  delta_ij  +  rho_ij,     |rho_ij| <= 4u
```

and the entry bound is

```text
|R1_ij - D1_ij| <= E_ij |R1_ij|,
E_ij = 4u + A_i + A_j - |delta_ij|,        A_i = sum_{k != i} |delta_ik|.
```

- **`E_ij` is not a constant.** It is evaluated from the actual
  `delta_ik` of the stored nodes.
- **Worst case:** `(2N + 3) u` at degree `N`, when no subtraction is exact.

**C-T1, C-T2 and C-T3 have no bound here.** An earlier version of this
section gave them a uniform operation count that assumed a library sine
accurate to one ulp. It was not verified, and it bounded rounding against
the ideal nodes only. It is withdrawn from use and removed from the
evaluator. These candidates keep rule 1.

**Computed node difference.** Its relative error `E^d_ij` is `|delta_ij|`.

**Diagonals.** Each is the negative row sum of the rounded off-diagonal
entries, taken in compensated arithmetic and rounded once (`u`).

**Bounds** (absolute; divide by `S_i` for the row-scaled value):

- **First derivative.** Because the diagonal is the negative row sum, the
  entry errors act on differences of the vector:
  ```text
  B1_i = sum_{j != i} E_ij |R1_ij| |v_j - v_i|  +  u |R1_ii| |v_i|
  ```
- **Second derivative**, explicit form `D2_ij = 2 D1_ij (D1_ii - 1/d_ij)`.
  With the diagonal error `g_i = sum_{j != i} E_ij |R1_ij| + u |R1_ii|`:
  ```text
  |R2_ij - D2_ij| <= 2 |R1_ij| ( g_i + (E^d_ij + u) / |u_i - u_j| )
                     + (E_ij + 2u) |R2_ij|            =: delta2_ij
  B2_i = sum_{j != i} delta2_ij |v_j - v_i|  +  u |R2_ii| |v_i|
  ```
  The `+ u` is the rounded reciprocal. The `2u` is the rounded subtraction
  and the rounded product. Multiplication by 2 is exact.

**Normalization.** The measured action and its bound are divided by the
same `S_i`, so the bound ratio does not depend on the row scaling.

**Neglected terms.**
- Products of two first-order errors: at most about `(2N u)^2` relative,
  which is `8e-26` at degree 1280.
- The accumulation error of the double-double products (about `N u^2`
  relative) and of the compensated sums (about `N^2 u^2 sum_j |D_ij|`
  absolute).
- The rounding of the two small correction terms in the weight ratio.
- The bound is evaluated with the 50-digit reference rounded to double and
  with `|u_i - u_j|` replaced by its rounded value. Each changes it by a
  relative `1e-16`.

**What the bound is not.**
- **It is a first-order bound, not an exact numerical certificate.** It is
  not rounded outward, it omits the terms listed above, and it assumes the
  arithmetic conditions stated above. It is checked against every entry on
  the grids of this continuation (Section 2); that is a test, not a proof.
- It is a bound for a correct implementation of the declared algorithm. It
  is not a statement about accuracy for any consumer, not an equation
  residual or a physical uncertainty, and not a bound on the node-set
  difference.
- It bounds absolute values. The signed terms can cancel, so the actual
  error can be much smaller than the bound.

### 3.1 Size of the C-S1 bound, and what remains unresolved

**Checked against exact rational arithmetic** (degree 30 on `[1e-3, 1]`, all
930 off-diagonal entries; independent of the tool's 50-digit reference):

| Quantity | Value |
| --- | ---: |
| largest entry error | `14.17u` (Codex's entry) |
| largest input term `sum (delta_ik - delta_jk) - delta_ij` | `14.96u` |
| largest remainder after subtracting the exact input term | `2.45u` (bound: `4u`) |
| `E_ij`, smallest to largest | `7.7u` to `26.7u` (worst case `63u`) |
| largest error divided by `E_ij` | `0.70` |

**Size at larger degrees.** `E_ij` was evaluated from the nodes alone at
three synthetic degrees. They are outside both the S0 set and the
confirmation set, and no candidate matrix was evaluated on them:

| Degree | Interval | Median `E_ij` | Largest `E_ij` | Largest, relative | Worst case |
| ---: | --- | ---: | ---: | ---: | ---: |
| 60 | `[-0.5, 1.5]` | `24u` | `40u` | `4.5e-15` | `123u` |
| 60 | `[1e-3, 1]` | `22u` | `53u` | `5.9e-15` | `123u` |
| 250 | `[-0.5, 1.5]` | `84u` | `157u` | `1.7e-14` | `503u` |
| 250 | `[1e-3, 1]` | `94u` | `216u` | `2.4e-14` | `503u` |
| 1000 | `[-0.5, 1.5]` | `310u` | `599u` | `6.6e-14` | `2003u` |
| 1000 | `[1e-3, 1]` | `392u` | `851u` | `9.4e-14` | `2003u` |

**Unresolved.**
- **The corrected bound grows about linearly with the degree.** That is a
  property of the derivation: it sums absolute values of up to `2N - 1`
  input errors.
- **Consequence for rule 2.** At degree 1000 the bound admits entry errors
  up to about `1e-13` relative. Rule 2 would excuse an action component that
  exceeds twice the current value whenever it stays inside a bound of that
  size. Whether that is an acceptable regression rule at the larger degrees
  is **not established**.
- **Not measured before the freeze.** Whether C-S1's actual errors grow in
  the same way was not known when this was frozen. The continuation records
  it (the entry requirement of Section 2).
- **Not tuned.** The bound was not tightened or loosened to reach an
  outcome.

**Two alternatives, neither adopted nor evaluated.**
- **A signed prediction in place of the bound.** The input term is exactly
  computable, which leaves only the `4u` remainder unknown. Using it would
  be a different rule and would need its own review.
- **A different candidate.** A construction that carries each subtraction
  error into the weight products would remove the input term. That is a new
  candidate. The candidate set is frozen and is not extended here.

## 4. Adverse controls

**Definitions** (fixed; they do not depend on the grid):

| Control | Damage to C-S1's matrices |
| --- | --- |
| `one_D1_entry` | D1 entry `(1, 2)` scaled by `1 + 1e-11` |
| `all_D1_entries` | every off-diagonal D1 entry scaled by `1 + 1e-12 g`, `g` standard normal from NumPy's `default_rng(3)`; diagonal recomputed |
| `shifted_nodes` | both matrices built for nodes whose interior values are scaled by `1 + 1e-10`, returned with the original nodes (a stored-node regression) |
| `one_D2_entry` | D2 entry `(2, 3)` scaled by `1 + 1e-10` |

**In the continuation, at the largest grid** (degree 1280 on `[1e-5, 1]`,
both builds, sharing that grid's references):
- **Combined checks.** A control is rejected if any of these fails for it:
  polynomial exactness, the metric (a) rule, the metric (b) rule 2, or the
  entry requirement. The rule and the checks are those applied to C-S1.
- **Each of the four controls must be rejected.** If one is not, the
  continuation stops and reports which checks did not reject it. The damage
  is never enlarged after the result is seen.
- **Recorded.** For each control: the checks that rejected it, the largest
  bound ratio, and the largest entry ratio. The undamaged matrices are
  evaluated in the same way, for comparison.

**Before the freeze, as tests** on a grid outside both sets (degree 21 on
`[1e-3, 1]`), with C-S1 as the candidate:

| Operator | Qualifies under rule 2 | D1 bound ratio | D2 bound ratio | Worst (a) / current |
| --- | --- | ---: | ---: | ---: |
| undamaged C-S1 | yes | `0.088` | `0.047` | `0.028` |
| one D1 entry scaled by `1 + 1e-11` | **no** | `5.4e3` | `0.047` | `154` |
| all off-diagonal D1 entries perturbed by `1e-12`, diagonal recomputed | **no** | `7.2e2` | `0.047` | `90` |
| matrices built for nodes shifted by `1e-10` (a stored-node regression) | **no** | `1.1e6` | `3.6e5` | `8.5e5` |
| one D2 entry scaled by `1 + 1e-10` | **no** | `0.088` | `7.0e3` | `1.6e3` |

The bound ratios are those of the corrected bound of Section 3. They are
smaller than in the first version because the corrected bound is larger.

Further synthetic tests show that rule 2:
- still fails a candidate on metric (a) alone, even when every action
  component is inside its bound;
- still fails it on polynomial exactness;
- still fails an action component whose bound ratio exceeds 1, or which has
  no recorded bound ratio.

**Bound validity.** On ten small grids outside the S0 node set and the
confirmation set (degrees 7, 11, 13, 21 and 30, on `[-0.5, 1.5]` and
`[1e-3, 1]`), C-S1's largest bound ratio is:

| Vectors | D1 | D2 |
| --- | ---: | ---: |
| the three smooth vectors `v1`–`v3` | `0.27` | `0.14` |
| every coordinate vector, which tests every matrix entry | `0.72` | `0.33` |

- **Regression tests** hold the counterexample, the exact-arithmetic
  accounting of Section 3.1 and the every-entry check at degree 30.
- **Limit of these checks.** They show the bound holding where it was
  tested. They are not a proof, and they say nothing about the larger
  degrees (Section 3.1).

## 5. The two sets and the qualification requirement

- **Rule 2 cannot be evaluated from the saved evidence alone.** The saved S0
  files hold the metric values but not the bounds.
- **Retrospective set.** The 84 S0 grids with vectors `v1`–`v3`.
  - These were observed before this amendment, so a pass there is a
    retrospective replay, not a confirmation.
  - The metric values are those of the saved S0 evidence. The continuation
    adds C-S1's bound ratios and entry check. It binds them to that evidence:
    the reconstructed C-S1 matrices must hash to the recorded ones, or the
    stage stops.
- **Confirmation set.** Not computed before the freeze:
  - degrees 5, 9, 12, 25, 33, 48, 100, 200, 448 and 800;
  - intervals `[0.3, 0.9]` and `[1e-4, 1]`;
  - vectors `w1 = cos(5 xi - 0.7)`, `w2 = 1/(2 + xi)` and
    `w3 = xi exp(-2 xi)`.

  Every metric is measured for every construction on these 20 grids. No
  candidate matrix was evaluated on any of them before the freeze.
- **Requirement.** A candidate qualifies under amendment 1 only if, on
  **both** sets and on **both** builds, it satisfies:
  - polynomial exactness (unchanged);
  - the metric (a) rule (unchanged);
  - the metric (b) rule: rule 2 for C-S1, rule 1 for the others;
  - for C-S1, the entry requirement of Section 2.
- **Selection** is unchanged: at least 10× improvement on metric (c), from
  the saved S0 evidence, and the tie-break.
- **Evidence admission.** The selector requires both builds' complete S0 and
  continuation outputs, from one tool version and this document's hash, with
  every recorded quantity finite.

## 6. Facts from the saved evidence (no new computation)

- **Under the frozen rule** (reproduced by Codex and by the corrected
  selector): failing comparisons are 126 / 112 / 112 / 26 on B1 and
  125 / 111 / 111 / 26 on B3, for C-T1 / C-T2 / C-T3 / C-S1.
- **C-S1 fails no metric (a) comparison.** All 26 of its failures are in
  metric (b): 23 for D1 and 3 for D2.
- **Each explicit-D2 C-T candidate fails 7 metric (a) comparisons.** Rule 2
  leaves these unchanged, so C-T2 and C-T3 would still not qualify.
- **The blanket floor is withdrawn.** Codex's sensitivity check shows that
  its outcome depends on the convention: with `(N+1) eps` C-S1 has 0
  failures, and with the conventional `gamma_(N+1)` using `u = eps/2` it has
  1 (degree 2 on `[1e-5, 1]`, D2 action, `3.8e-16` against `3.3e-16`). A
  constant chosen that way would be chosen for the result.

**Whether C-S1 qualifies under this amendment on either set was not known
at the freeze.** It had not been computed. The entry model of Section 3
comes from the implemented operations and the stored nodes, not from the S0
metric values.

## 7. Budget

- **Local execution.** The owner raised the cumulative ceiling from 60 to
  90 minutes. That includes the roughly 21.7 minutes already charged. It is
  not 90 more minutes, and nothing is reset.
- **Active work.** The original cumulative ceiling of 6 hours is unchanged.
  About 1.5 hours were used before the continuation.
- **Estimate** (not a promise): 36–50 minutes of execution for the
  continuation, of which R0 and S2 are the least certain.
- **If a ceiling is reached,** the work returns incomplete. No case is
  removed and no ceiling is extended.

## 8. Continuation stages and stops

1. **C0 — freeze.** This document, the evaluator and its tests are committed
   before any continuation run.
2. **C1 — measurements, on B1 and B3.** The oracle fixtures first. Then the
   retrospective set, the confirmation set and the adverse controls
   (Sections 4 and 5). C1 draws no verdict.
3. **C2 — qualification and selection** under this amendment (Section 5),
   from the saved S0 evidence and the two C1 outputs.
4. **Only if C2 selects a candidate,** the original plan continues in its
   declared order and unchanged: the implementation freeze, R0, S2 (with A1,
   A2, A3 and bit-identical controls) and S3.
   - R0 values and allowances are committed before any candidate verifier
     run.
   - No gate that passes at baseline may fail afterwards.

**Stops.** Each returns to the owner, with no automatic repair, no tuning
and no added candidate:
- a fixture failure, or an undefined required quantity;
- a C-S1 matrix that is not the one in the S0 evidence;
- a bound violation;
- an adverse control that is not rejected;
- no candidate qualifying, or none reaching 10×;
- every stop of the original plan: A1, A2 or a control failing, a
  post-freeze code correction, or an exhausted budget.

**Closed throughout:** gates, thresholds, tolerances and model physics;
the candidate set and the candidate implementations; reserved optical
cases; merge, release and branch deletion; installations and paid compute;
extra scientific CI dispatches; cleanup; private research and the BTZ pin.

## 9. Changes made at the freeze

From the version Codex reviewed at `335331c`, following its review and the
owner's approval:
- **Rule 2 is restricted to C-S1** (Section 2). The closed-form-weight
  candidates keep rule 1, and their operation-count model is withdrawn
  (Section 3).
- **The entry requirement is added** for C-S1 (Section 2).
- **The adverse controls are defined in the evaluator** and repeated at
  degree 1280 on `[1e-5, 1]`, with the combined checks stated (Section 4).
- **The bound is described as first order,** not as an exact certificate,
  and the evaluation of `delta` is no longer called exact (Section 3).
- **The budget and the stages** are stated (Sections 7 and 8).

Unchanged by the freeze: the C-S1 bound itself, the confirmation set, the
candidate implementations, and everything listed in Section 1.
