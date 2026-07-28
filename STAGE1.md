# Generated Stage 1

Status: executable Milestone 2 Stage1-A surface (`UC-STAGE1-SEED-1`)

Stage 0 now interprets the structured `stage1` declaration in
`seed/ROOT.seed.json` and emits a runnable framework/generator tree:

```bash
python3 bootstrap/stage0.py generate \
  --contract seed/stage0/TRUSTED_INPUTS.json \
  --input-root . \
  --output /tmp/uc-stage1-a
```

The generated tree is:

```text
stage1-a/
├── stage1.py
├── stage1-manifest.json
├── framework/contract.json
├── generator/contract.json
└── uem/contract.json
```

`stage1.py` is a generic generated runner. It consumes the same canonical root
seed and can produce another Stage-1 tree without the repository, Stage 0,
`PYTHONPATH`, network access, dynamic loading, or an opaque source payload:

```bash
python3 /tmp/uc-stage1-a/stage1.py \
  /isolated/ROOT.seed.json \
  /tmp/uc-stage1-b
```

## Seed authority

The root seed declares:

- canonical Thing fields, states, Standard Ten identity and L1–L13 surface;
- the closed Stage-1 generation operations;
- every generated semantic output and its originating JSON pointer;
- the UEM-16 opcode and primitive-registry input surface;
- the canonical Stage-1 boilerplate identity.

Stage 0 supplies only the pinned generic `UC-STAGE1-PY-1` syntax boilerplate
and interpreter. It does not read or copy `unified/`, `tests/`, documentation,
application source, or other untrusted checkout files.

Unsupported operations, encodings, seed nodes, paths, or boilerplate identities
fail explicitly. There is no conventional or opaque-copy fallback.

## Manifest and identity

`stage1-manifest.json` records:

- root-seed identity and canonical SHA-256;
- generator/boilerplate identity;
- every semantic file path, byte size and SHA-256;
- originating root-seed nodes for every file;
- the complete semantic-tree SHA-256;
- deterministic ordered generation evidence.

The evidence manifest is excluded from the semantic-tree hash to avoid a
self-hash. It is nevertheless byte-identical across independent runs because
it contains no timestamps, host paths, environment values, randomness, or
filesystem metadata.

## Atomicity and isolation

Both Stage 0 and generated Stage 1 render into a sibling staging tree and
publish by rename only after validation and hashing. Invalid or unsupported
input leaves the previous verified output byte-identical.

The generated runner uses only the declared root seed and Python standard
library. Tests execute it from a separate directory with no repository import
path and prove that changes to untrusted checkout files cannot affect output.

## Boundary

This closes the bounded Stage1-A generation dependency. It does not by itself
close:

- the independently isolated Stage1-A/Stage1-B fixed-point harness;
- generated independent Python/C UEM hosts;
- generated tests, documentation and audit tooling;
- external dependency provenance;
- clean-room whole-repository regeneration.

Those remain separate Milestone 2 issues and cannot be inferred from this
minimal runnable Stage-1 surface.
