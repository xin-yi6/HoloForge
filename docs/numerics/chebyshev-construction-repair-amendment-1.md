# Chebyshev repair: proposed qualification amendment 1 (post-observation)

- **Status: PROPOSED. Not adopted, not applied.** AI-assisted (Claude),
  prepared at Codex's request after its review of PR #55 (item R55-3).
  Continuation is a separate owner decision.
- **Revised once, after Codex's re-review of `d5eb95a` (item R55-F1).** The
  first version's C-S1 entry model was wrong at first order. Section 3 now
  derives it from the implemented operations, and Section 3.1 states what
  remains unresolved. The rule in Section 2 is unchanged.
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
   - `delta_ik` is known exactly from an error-free transformation of the
     subtraction. It is zero when the subtraction is exact.
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

**C-T1, C-T2 and C-T3** (closed-form weights, trigonometric differences)
keep a uniform model, because their weights are exact and no product of
differences occurs:

| Quantity | Units of `u` | Operations counted (one `u` each unless stated) |
| --- | ---: | --- |
| off-diagonal D1 entry, `E_ij` | 12 | two sines, each `2.4u` for forming its argument plus `2u` for a library sine assumed accurate to one ulp; their product; the multiplication by the width; the final division. The total is `11.8u`, rounded up |
| node difference | 11 | the same without the final division (`10.8u`, rounded up) |

- **Assumption.** The library sine is accurate to one ulp. This is assumed
  and not verified here. Unlike the C-S1 model, the C-T model is not checked
  against exact arithmetic.
- **Scope.** It bounds only rounding against the *ideal* nodes. The C-T
  matrices differ from the stored-node reference by the node-set difference,
  which is not rounding. That difference is deliberately not covered, so C-T
  is expected to fail honestly.

**Computed node difference.** Its relative error `E^d_ij` is `|delta_ij|`
for C-S1 and `11u` for the C-T family.

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
- It is a first-order bound for a correct implementation of the declared
  algorithm. It is not a statement about accuracy for any consumer, and it
  is not a bound on the node-set difference.
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
- **Not measured.** Whether C-S1's actual errors grow in the same way is not
  known. Measuring it needs a pass over the S0 grids, which this correction
  step does not include.
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

Run as tests on a grid outside the S0 node set (degree 21 on `[1e-3, 1]`),
with C-S1 as the candidate:

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
has not been computed. The entry model of Section 3 comes from the
implemented operations and the stored nodes, not from the S0 metric values.

## 7. Budget

Reconciled from the existing logs (report Sections 1, 7 and 8):
- **Charged so far:** about 21.7 of 60 minutes of local execution. That
  includes the 458 s full test suite omitted from the first table, a
  conservative 60 s for short untimed runs, and 30 s for the correction
  step after the re-review.
- **Remaining:** at most about 38.3 minutes.
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
