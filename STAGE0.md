# Stage-0 Bootstrap Contract

Status: executable Milestone 2 contract (`UC-STAGE0-1`)

Stage 0 is the alignment step from current hardware and its available host
runtime to the first deterministic representation that Stage 1 may consume.
It is the base of the bootstrap, not a general application framework.

```text
current substrate
+ explicitly trusted Stage-0 executable and manifest
+ pinned root seed and schemas
→ verified deterministic Stage-1 handoff
```

## Pre-bootstrap and post-bootstrap boundary

Pre-bootstrap code exists only because the current substrate cannot execute UEM
directly. For this proof it is the single file `bootstrap/stage0.py`, CPython
3.11 or newer, and five named standard-library modules. Its source hash is
pinned in `seed/stage0/TRUSTED_INPUTS.json`.

Post-bootstrap construction targets the unified UEM specification and canonical
interface. Independent Python and C hosts remain equivalence witnesses and
physical adapters; their implementation languages do not become multiple
application languages. Stage 0 is therefore a substrate adapter, not precedent
for adding another post-bootstrap language.

The `plan` operation produces the frozen handoff. The bounded `generate`
operation now interprets the root seed's structured Stage-1 declaration and
produces the first runnable Stage1-A surface. It does not prove the complete
repository fixed point or the eventual post-bootstrap language reduction.

## Trusted inputs

The complete trusted input set is:

| Role | Path | Hash mode |
|---|---|---|
| root seed | `seed/ROOT.seed.json` | canonical JSON |
| root-seed schema | `seed/SCHEMA.json` | canonical JSON |
| Stage-0 contract schema | `seed/STAGE0_SCHEMA.json` | canonical JSON |
| Stage-1 handoff schema | `seed/STAGE1_HANDOFF_SCHEMA.json` | canonical JSON |
| generation-manifest schema | `seed/STAGE0_GENERATION_MANIFEST_SCHEMA.json` | canonical JSON |
| Stage-0 executable | `bootstrap/stage0.py` | raw bytes |

The trust manifest itself is the explicit trust root. Stage 0 records its
canonical SHA-256 in the handoff. A caller, release signature, or reproducible
distribution must authenticate that manifest hash; a program cannot establish
the authenticity of its own mutable trust root.

The physical trust base also includes the current processor, operating system,
filesystem, and an externally authenticated CPython implementation satisfying
the declared profile. CPython 3.11, 3.12, and 3.13 are the verified CI
implementations; the host binary is deliberately not assigned one portable
hash. This is physical substrate provenance, not a generated dependency.

No repository file outside this set is read. No external dependency is trusted
in this proof. Future dependencies require explicit version, source, hash,
license, reproducibility, and replacement provenance under Issue #8.

After Stage 1 first exists, this entire trust base remains trusted. Nothing is
silently removed merely because a handoff was produced. Stage 0 may move from
the live trust base to a provenance ancestor only after the separate Stage-1
fixed-point and clean-room proofs establish an independently reproducible
successor.

## Public Part and command

The public Part obeys one-Thing-in/one-Thing-out:

```text
stage0_plan(thing) -> thing
stage0_generate(thing) -> thing
```

The executable operation is:

```bash
python3 bootstrap/stage0.py plan \
  --contract seed/stage0/TRUSTED_INPUTS.json \
  --input-root . \
  --output /tmp/uc-stage0-handoff
```

Success atomically writes the canonical Stage-1 handoff tree:

```text
/tmp/uc-stage0-handoff/
├── stage1-handoff.json
└── generation-manifest.json
```

The command exits nonzero and publishes no handoff when any verification fails.

After the handoff contract is verified, Stage1-A is generated with:

```bash
python3 bootstrap/stage0.py generate \
  --contract seed/stage0/TRUSTED_INPUTS.json \
  --input-root . \
  --output /tmp/uc-stage1-a
```

See [STAGE1.md](STAGE1.md) for its generated tree, manifest and isolation
contract.

## Permitted computation

Stage 0 may only:

1. canonicalize JSON;
2. calculate SHA-256;
3. validate the trust contract;
4. validate the root-seed and schema identities;
5. validate and confine relative paths;
6. read pinned trusted inputs;
7. construct the Stage-1 handoff;
8. interpret the closed structured Stage-1 declaration;
9. specialize the pinned generic Stage-1 boilerplate;
10. hash the complete Stage-1 semantic tree;
11. atomically publish verified output.

Application-domain behavior, unverified copying, network access, subprocesses,
dynamic loading, fuzzy resolution, environment-dependent selection, randomness,
and time-dependent output are prohibited.

Imperative control flow inside the standalone file is audited physical
bootstrap machinery. It may verify and move bytes; it may not express domain
commands or application behavior. The public Part remains nested composition.

## Determinism

`UC-CANONICAL-JSON-1` is UTF-8 JSON with:

- object keys sorted lexicographically;
- no insignificant whitespace;
- no ASCII escaping for Unicode text;
- one final line feed;
- duplicate object keys rejected.

Trusted-input records are sorted by `(role, path)` before contract identity and
handoff construction. Output contains no absolute paths, timestamps, temporary
paths, locale values, host identity, environment data, or running Python
version. JSON inputs are hashed after canonicalization; executable inputs are
hashed as raw bytes.

The handoff pins:

- Stage-0 version and canonical contract hash;
- root seed identity and hash;
- schema hashes;
- every trusted input and hash mode;
- the empty external-dependency set;
- Stage-1 output and manifest names.

The `plan` result deliberately does not claim a generated Stage-1 tree or fixed
point. The separate `generate` result claims only the bounded Stage1-A tree
defined in [STAGE1.md](STAGE1.md).

Here “Stage-1 tree” means this verified two-file input package for Stage 1, not
a generated Stage-1 implementation. `generation-manifest.json` inventories all
trusted inputs and the handoff payload. Its `stage1_payload_tree_sha256` hashes
the ordered `path`, NUL separator, file hash, and line feed for the handoff
payload. The manifest is excluded from that identity to avoid a self-hash.

## Resource and security boundary

The trust manifest fixes maximum input count, per-input bytes, JSON depth, and
path length. Paths must be relative POSIX paths without `..`, backslashes, NUL,
or symlink escape. Inputs must be regular files contained by the explicit input
root.

Stage 0 has three named boundaries:

```text
INWARD  contract read
INWARD  pinned trusted-input reads
OUTWARD atomic handoff publication
```

The output is built in a sibling staging directory and renamed only after all
gates pass. A failed replacement restores the last verified output. Expected
contract, path, resource, and hash failures return `Thing.state = invalid`
without a ticket. A genuinely unhandled boundary failure opens exactly one
deterministic redacted ticket.

## Ordered evidence

Success produces exactly:

```text
boundary:contract:read
stage0:contract-verified
boundary:trusted-inputs:read
stage0:inputs-verified
stage0:handoff-planned
boundary:handoff:publish
stage0:handoff-published
```

A rejected transition stops at its rejection mark. It never claims handoff
publication or Stage-1 generation.

## Stage-1 handoff

`seed/STAGE1_HANDOFF_SCHEMA.json` is the machine-readable handoff contract.
Stage 1 must verify the identities again before using them and must emit its
output under the declared deterministic tree and manifest names.

The Stage1-A extension does not generate the complete repository, execute
application behavior, certify the isolated fixed point, generate independent
UEM hosts, or account for vendored dependencies. It also does not implement
deployment, scheduling, real-time behavior, lifecycle coordination, or
name-to-manifestation.

## Conformance

```bash
pytest tests/test_stage0.py -q
```

The focused suite proves independent-directory determinism, record-order
invariance, canonical-JSON whitespace invariance, path confinement, symlink
rejection, missing/tampered inputs, resource limits, prohibited-capability
mutations, atomic preservation, redacted ticket behavior, one-Thing signatures,
and absence of proof-application vocabulary and dynamic capabilities.
