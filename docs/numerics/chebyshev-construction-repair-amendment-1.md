# Chebyshev repair: proposed qualification amendment 1 (post-observation)

- **Status: PROPOSED. Not adopted, not applied.** AI-assisted (Claude),
  prepared at Codex's request after its review of PR #55 (item R55-3).
  Continuation is a separate owner decision.
- **Post-observation.** This amendment was written after the S0 results were
  seen: every metric at 84 grids on two builds, and every qualification
  failure. It is not a prospective rule for those grids, and it must never be
  described as one.
- **The original result stands.** Under the
  [frozen plan](chebyshev-construction-repair-plan.md) (`0cd24dd`), S1
  stopped with "no candidate qualifies". That stays the recorded outcome of
  the frozen rule, whatever happens to this amendment.

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

## 2. What would change

Only the rule for **metric (b)**, the row-scaled action error
`e_i = |((R - D) v̂)_i| / S_i`, against the stored-node reference.

| | A component (one matrix, one test vector, one row set) fails when |
| --- | --- |
| **Rule 1 (frozen)** | its value exceeds 2× the current construction's |
| **Rule 2 (proposed)** | its value exceeds 2× the current construction's **and** its bound ratio exceeds 1 |

The **bound ratio** is `max_i e_i / B_i` over the rows of the set. `B_i` is
the first-order a-priori rounding bound of the candidate's own declared
construction (Section 3), in the same row scaling.

A component with no defined bound keeps rule 1. That applies to C-T1's
second derivative, which is formed by `D @ D`.

**Why this, and why not a floor.**
- **The measured values are real.** Metric (b) is measured against a
  50-digit reference with an error near `1e-32`. A value below machine
  epsilon is a genuine property of the matrix, not measurement noise.
- **The problem with rule 1.** No double-precision construction has zero
  construction rounding. Rule 1 compares the rounding of two different
  correct constructions and calls any factor of 2 a regression. It does so
  even when both are inside what their algorithms can guarantee.
- **What rule 2 does.** It treats rounding inside the candidate's own
  first-order a-priori bound as not a regression. Whether such rounding
  matters to a physical observable is a separate question. Stage A2 answers
  that question, and A2 is unchanged.
- **No blanket floor.** A single constant such as `gamma_(N+1)` is not a
  bound for these metrics. It carries no term magnitudes, and it does not
  follow from the algorithm. The earlier suggestion of such a floor is
  withdrawn (Section 6).

## 3. Roundoff convention, operation assumptions and the bound

**Convention.**
- `u = 2^-53`, the unit roundoff for round-to-nearest. This is half of
  NumPy's `eps`.
- The analysis is first order in `u`; second-order terms are neglected.
- The bound is evaluated with the 50-digit reference rounded to double,
  which changes it by a relative `1e-16`.

**Entry model.** An off-diagonal first-derivative entry satisfies
`|R1_ij - D1_ij| <= k u |R1_ij|`. The count `k` comes from each
construction's operations:

| Construction | `k` | Operations counted (one `u` each unless stated) |
| --- | ---: | --- |
| **C-S1** | 5 | quotient of the two weight products; two correction additions; the stored-node difference; the final division |
| **C-T1, C-T2, C-T3** | 12 | two sines, each `2.4u` for forming its argument plus `2u` for a library sine assumed accurate to one ulp; their product; the multiplication by the width; the final division. The total is `11.8u`, rounded up |

- **C-S1's count uses no library assumption.** Its weight products are
  accumulated in double-double arithmetic, so their own error is second
  order.
- **The C-T count assumes a library sine accurate to one ulp.** It also
  bounds only rounding against the *ideal* nodes. The C-T matrices differ
  from the stored-node reference by the node-set difference, which is not
  rounding. That difference is deliberately not covered, so C-T is expected
  to fail honestly.

**Computed node difference.** Its relative error is `k_d u`, with `k_d = 1`
for C-S1 (one subtraction) and `k_d = 11` for the C-T family (`10.8u`,
rounded up).

**Diagonals.** Each is the negative row sum of the rounded off-diagonal
entries, taken in compensated arithmetic and rounded once (`u`).

**Bounds** (absolute; divide by `S_i` for the row-scaled value):

- **First derivative.** Because the diagonal is the negative row sum, the
  entry errors act on differences of the vector:
  ```text
  B1_i = k u * sum_{j != i} |R1_ij| |v_j - v_i|  +  u |R1_ii| |v_i|
  ```
- **Second derivative**, explicit form `D2_ij = 2 D1_ij (D1_ii - 1/d_ij)`.
  With the diagonal error `g_i = k u sum_{j != i} |R1_ij| + u |R1_ii|`:
  ```text
  |R2_ij - D2_ij| <= 2 |R1_ij| ( g_i + (k_d + 1) u / |u_i - u_j| )
                     + (k + 2) u |R2_ij|            =: delta2_ij
  B2_i = sum_{j != i} delta2_ij |v_j - v_i|  +  u |R2_ii| |v_i|
  ```

**Normalization.** The measured action and its bound are divided by the
same `S_i`, so the bound ratio does not depend on the row scaling.

**What the bound is not.** It is a first-order bound for a correct
implementation of the declared algorithm. It is not a statement about
accuracy for any consumer, and it is not a bound on the node-set difference.

## 4. Adverse controls

Run as tests on a grid outside the S0 node set (degree 21 on `[1e-3, 1]`),
with C-S1 as the candidate:

| Operator | Qualifies under rule 2 | D1 bound ratio | D2 bound ratio | Worst (a) / current |
| --- | --- | ---: | ---: | ---: |
| undamaged C-S1 | yes | `0.18` | `0.11` | `0.028` |
| one D1 entry scaled by `1 + 1e-11` | **no** | `1.4e4` | `0.11` | `154` |
| all off-diagonal D1 entries perturbed by `1e-12`, diagonal recomputed | **no** | `1.5e3` | `0.11` | `90` |
| matrices built for nodes shifted by `1e-10` (a stored-node regression) | **no** | `1.9e6` | `7.0e5` | `8.6e5` |
| one D2 entry scaled by `1 + 1e-10` | **no** | `0.18` | `2.3e4` | `1.7e3` |

Further synthetic tests show that rule 2:
- still fails a candidate on metric (a) alone, even when every action
  component is inside its bound;
- still fails it on polynomial exactness;
- still fails an action component whose bound ratio exceeds 1, or which has
  no recorded bound ratio.

**Bound validity.** On ten small grids outside the S0 node set (degrees 7,
11, 13, 21 and 30, on `[-0.5, 1.5]` and `[1e-3, 1]`), C-S1's largest bound
ratio is `0.39` for D1 and `0.16` for D2.

## 5. Retrospective replay versus new confirmation

- **Rule 2 cannot be evaluated from the saved evidence.** The saved S0 files
  hold the metric values but not the per-row bounds. Evaluating rule 2 needs
  a new pass over the references.
- **Retrospective set.** The 84 S0 grids with vectors `v1`–`v3`. These were
  observed before this amendment, so a pass there is a retrospective replay,
  not a confirmation.
- **Confirmation set.** Defined here and not yet computed:
  - degrees 5, 9, 12, 25, 33, 48, 100, 200, 448 and 800;
  - intervals `[0.3, 0.9]` and `[1e-4, 1]`;
  - vectors `w1 = cos(5 xi - 0.7)`, `w2 = 1/(2 + xi)` and
    `w3 = xi exp(-2 xi)`.

  No grid or vector of this set was used in S0 or in the tests of Section 4.
- **Requirement.** A candidate qualifies under amendment 1 only if it
  satisfies rule 2, the unchanged metric (a) rule and polynomial exactness on
  **both** sets, on both builds.
- **Label.** Any pass is reported as "qualified under post-observation
  amendment 1". It is never reported as passing the frozen rule.

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

**Whether C-S1 would qualify under rule 2 on either set is not known.** It
has not been computed, and the constants of Section 3 come from the
operation counts, not from the S0 values.

## 7. Budget

Reconciled from the existing logs (report Section 7):
- **Charged so far:** about 21.2 of 60 minutes of local execution. That
  includes the 458 s full test suite omitted from the first table, and a
  conservative 60 s for short untimed runs.
- **Remaining:** at most about 38.8 minutes.
- **Estimated need for a continuation:**

  | Step | Estimate |
  | --- | --- |
  | One S0 pass with bounds on B1 | about 4 min |
  | B3 (inherits where matrices are bit-identical) | 1–4 min |
  | Confirmation set | about 1–2 min |
  | R0 and S2 | not yet measured; estimated 20–30 min |
  | S3 | about 2 min |
  | Full suite | about 8 min |
  | **Total** | **about 36–50 min** |

- **Consequence.** The remaining budget may not cover a continuation. A
  continuation approval should state the execution budget explicitly. It is
  not reset or extended here.

## 8. If the owner approves a continuation

1. Freeze this amendment in its own commit, with any changes from review.
2. Run the retrospective set and the confirmation set, and apply rule 2.
3. If a candidate qualifies and meets the unchanged 10× requirement,
   continue with the original plan's implementation freeze, R0, S2 and S3,
   all unchanged.
4. If none qualifies, stop again and report.
