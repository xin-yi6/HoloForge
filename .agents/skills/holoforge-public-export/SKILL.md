---
name: holoforge-public-export
description: "Audit a proposed private-to-public HoloForge artifact transfer for disclosure authority, provenance, and private content. Use before exporting private research artifacts or reviewing such a contribution."
---

# HoloForge Public Export

Promote the smallest reusable public artifact. A clean automated scan is only
one input to human scientific and disclosure review.

## Load the policy

Read `docs/private-research-workflow.md`, especially the public-export
checklist, then read `CONTRIBUTING.md` and the relevant public contract or
schema. Identify the research owner and the source artifact's disclosure state.

## Freeze the export contract

Record:

- the exact files or behavior proposed for export;
- the public need and intended users;
- the public source, publication, or explicit owner release approval;
- what private material must remain excluded;
- whether a clean public reimplementation is safer than copying; and
- the tests and review needed before merge.

Prefer a clean public implementation from a generic specification when the
private artifact mixes reusable infrastructure with unpublished physics.

## Audit the candidate artifact

1. Inspect every proposed file and its Git diff.
2. Run the bundled deterministic scanner:

   ```bash
   python .agents/skills/holoforge-public-export/scripts/audit_export.py PATH
   ```

   Add project-specific forbidden strings without committing them:

   ```bash
   python .agents/skills/holoforge-public-export/scripts/audit_export.py \
     PATH --forbid-file /path/outside/repository/private-tokens.txt
   ```

3. Check manually for unpublished equations, parameter choices, numerical
   results, paper caches, candidate identities, private citations, novelty
   statements, author communications, and context that automated patterns
   cannot recognize.
4. Check provenance and licensing. Reimplement rather than copy material whose
   public reuse rights are unclear.
5. Add public tests and documentation that make no reference to the private
   project's existence or conclusions unless release approval explicitly
   permits it.
6. Run the complete public suite and inspect the final staged diff.

## Stop conditions

Stop and recommend no export when owner authorization, provenance, license, or
privacy cannot be established. Do not weaken a scanner rule merely to make a
candidate pass. Do not publish the private repository's history as a shortcut.

## Deliver the audit

Report:

- export, clean-room reimplementation, revise, or reject;
- the evidence and authorization supporting that recommendation;
- files approved for the public pull request;
- material that must remain private;
- automated and manual checks performed; and
- the owner decision still required, if any.
