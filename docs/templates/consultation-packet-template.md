# Optional owner-mediated consultation

Use this local handoff when the owner selects an external consultation. The
owner chooses the model and mode, sends the prepared message manually, and
returns the full answer. This does not require an API or change the existing
[automated review runner](../../.agents/skills/holoforge-research-gate/scripts/run_question_review.py).
Reuse existing selection and disclosure authority for the exact scope; a
local export does not authorize disclosure. Keep unpublished packets and
answers in the private workspace. This is optional advice, not a new gate.

## Brief to complete

- **Physical question and intended decision:** `<what would the answer change?>`
- **Physical setup, equations and conventions:** `<fields/action, normalizations,
  signs, boundary conditions, ensemble and regime before auxiliary notation>`
- **Assumptions and fixed/shared inputs:** `<what already constrains the answer?>`
- **Evidence and its limits:** `<exact sources, derived or numerical results,
  uncertainty and failed checks; name supporting text files if needed>`
- **Prior exposure and supplied attempts:** `<whether the consultant sees the
  author's proposed answer, earlier criticism or other reviews; distinguish
  an informed discussion from an independent first assessment>`
- **Exact question for the consultant:** `<a bounded question with the requested
  derivation, criticism or alternatives; state what remains outside the scope>`

Preserve enough context to reconstruct the issue. A successful packet check
only checks bytes, not whether the brief is scientifically complete.

## Local round trip

Run the [packet utility](../../.agents/skills/holoforge-research-gate/scripts/consultation_packet.py)
from the private workspace, recording its framework or maintenance revision
without changing an existing scientific framework pin. All
input and output paths below are relative to `--root` (the current directory
by default). Supply individual UTF-8 files, never a directory or a glob.
Optional `--evidence` arguments add only those named files. No project files
are discovered, no service is contacted, and no credentials are required.

```bash
python "$FRAMEWORK/.agents/skills/holoforge-research-gate/scripts/consultation_packet.py" export \
  --brief brief.md --evidence supporting-extract.txt \
  --author-family family-a --out-dir consultation-1
```

Keep the printed **packet SHA-256** separately in the existing task record.
The packet preserves the exact input bytes, their hashes and `message.md`.
Inspect `message.md` and let the owner use it with the chosen service within
the existing disclosure authority. Save the full returned answer as
`returned-answer.md` outside the packet, then import it:

```bash
python "$FRAMEWORK/.agents/skills/holoforge-research-gate/scripts/consultation_packet.py" import \
  --packet-dir consultation-1 --packet-sha256 ORIGINAL_HASH \
  --answer returned-answer.md --reported-model chosen-model \
  --reported-mode chosen-mode --reported-family family-a --out-dir consultation-answer-1
```

Use `unavailable` for metadata the owner cannot report. The import verifies
the original packet hash, preserved inputs and message, then copies the full
answer unchanged to `answer.md` and records its source hash in `receipt.json`.
Existing outputs, changed packet files, path escapes and symlink paths are
refused. Destination parents must exist. Preserve incomplete output after a
local write failure and use a fresh destination for a retry.

The receipt describes **local import**, with **owner-reported** model, mode and
family. It is not a verified provider execution receipt and does not establish
that the exact message was submitted, which context was used, or whether the
returned answer is complete. The owner supplies that provenance. Consultations
within the same model family do not establish cross-family independence;
different reported family names also remain unverified. Agreement is not
proof. The canonical writer compares the answer with primary
evidence, records useful objections and unresolved disagreements, and retains
all existing scientific, review and execution boundaries.
