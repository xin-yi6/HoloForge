# Portable evidence bundles

HoloForge evidence bundles package one public calculation with the metadata
needed to inspect its identity, integrity, numerical provenance, scientific
state, acceptance checks, limitations, and generated artifacts. They are
relocatable directories: the manifest records only paths inside the bundle.

A passing audit means that the declared files and scientific payload have not
changed and that required provenance fields are present. It does not establish
that the underlying model is physically correct, empirically validated, novel,
or appropriate for a later calculation.

An optional [claim/evidence navigation utility](claim-evidence-index.md) can
link canonical records and flag changed dependencies for agents and the
existing PDF review workflow. Its freshness checks do not replace this bundle
audit, infer scientific support, or change the protected bundle schema.

## Create and audit a bundle

Every current `verify` and `compare` command accepts an optional
`--bundle-dir`. The target must be new or empty; HoloForge will not overwrite
existing content.

```bash
holoforge verify soft-wall-vector \
  --bundle-dir output/soft-wall-default
holoforge audit bundle output/soft-wall-default
```

The same option works with the other commands listed in `README.md`. Existing
defaults, ordinary output, numerical results, acceptance gates, and exit codes
are unchanged when `--bundle-dir` is absent. Use `--json` with either the
calculation or audit command for machine-readable output.

When a calculation already generates a table or figure, use a different path
for its ordinary output and its evidence bundle. Declared artifacts are copied
inside the bundle and audited there; the manifest never depends on their
original filesystem locations.

## Bundle layout

```text
evidence-bundle/
  manifest.json
  records/
    configuration.json
    model-card.json
    result.json
  artifacts/
    ... optional copied tables or figures ...
```

`manifest.json` records:

- the HoloForge and evidence-schema versions;
- a normalized command identity;
- model-card identifiers, repository-relative locations, and content hashes;
- the declared ensemble, fixed variables, approximation, phase or branch,
  physical parameters, allowed controls, boundary/source conditions,
  conventions, units, and source-record versions;
- acceptance checks, software versions, scope, and limitations;
- every included file's relative path, role, media type, and SHA-256 digest;
  and
- a deterministic digest of the scientific payload.

Execution timestamps are retained separately and do not change the scientific
payload identity. Changing a declared record or artifact does change its file
digest and causes the audit to fail with the affected path.

## Compatibility preflight

The Version 0.4 compatibility relation is deliberately narrow:

```bash
holoforge audit compatibility BUNDLE_A BUNDLE_B \
  --relation same-state-family
```

Use it only when two inputs are intended to represent one family of physical
states, such as parameter points that may later be differentiated or
continued. It compares the declared:

- model identifier;
- ensemble and fixed variables;
- approximation and backreaction level;
- phase and branch;
- parameters other than explicitly declared controls;
- boundary and source conditions;
- conventions, normalization, and units; and
- model-card, source-record, and schema versions.

Both bundles must declare the same controls. A changed control is reported but
does not cause failure. An undeclared parameter change, a missing required
field, or any other mismatch fails the preflight. HoloForge does not infer a
branch from filenames, silently convert units, or repair incomplete metadata.

Current command profiles declare the overall scale as a control for the two
spectral reference benchmarks. The nonlinear benchmark and controlled
comparison declare no varying control because each command emits a composite
verification record rather than one continuation point.

Comparing different model constructions is not `same-state-family` work. Use
the controlled-comparison contracts and commands introduced in Version 0.3
for that purpose.

## Portability and disclosure boundary

Bundle JSON metadata rejects absolute filesystem paths and private-key
markers. The integrity audit also rejects unsafe paths, missing or symbolic
declared files, hash mismatches, undeclared files, and inconsistent bundle
identities.

These checks do not authorize disclosure. Before sharing a bundle, inspect its
records and artifacts for unpublished science, personal information, secrets,
licensing restrictions, and confidential material. Private Explore work
remains in its separate access-controlled repository unless the research owner
explicitly authorizes a reviewed public export.
