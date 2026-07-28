# Name-to-manifestation

Name-to-manifestation is the bounded successor to
[Thing v2](THING_V2.md). It resolves one pinned application address to one
verified seed identity, invokes the registered current compiler route, verifies
the resulting artifact-tree identity, and atomically publishes the artifact.

It does not interpret a name as application behavior. A name is an address to
potential whose meaning comes only from a pinned registry snapshot.

## Frozen semantic model

```text
One Thing
├── resolution machine
├── artifact-manifestation machine
├── deployment/execution machine
├── derived temporal coordinates
├── measurable delivery contract
└── scheduler coordinates
```

These machines may share the canonical Thing envelope, identity, and ordered
evidence. They do not share state enums.

This change implements only:

```text
resolution machine
artifact-manifestation machine
```

The remaining machines are boundary definitions, not speculative
implementations.

## Artifact identity is not deployment identity

```text
artifact_id   = content-addressed generated tree
deployment_id = one particular installation of an artifact
```

One artifact may have zero, one, or many deployments. This feature produces an
artifact identity and artifact directory only. It creates no deployment
identity and makes no installed/running/stopped claim.

Compiler-internal installation into a staging boundary is not a deployment
identity and is not reinterpreted as a deployment lifecycle transition.

## Public Parts

The implementation follows the repository generator layout:

```python
from unified.generator.manifestation import manifest_artifact, resolve_name

resolve_name(thing)       # Thing → Thing
manifest_artifact(thing)  # Thing → Thing
```

The public Parts contain one positional parameter and delegate physical
selection, filesystem access, compilation, and publication to named audited
primitives and boundaries. They define no classes or object graph.

Named physical boundaries are:

```text
outward_registry_read
outward_seed_read
outward_artifact_output_prepare
outward_compile_route
outward_artifact_publish
```

## Canonical Thing-state rule

Canonical states remain:

```text
unknown | absent | false | formed | valid | invalid
```

Resolution outcomes are data:

```text
unresolved | resolved | unknown | ambiguous | unavailable | conflict
```

For example, an unknown qualified address is a successfully represented
domain outcome:

```json
{
  "value": {
    "resolution": {
      "status": "unknown",
      "error": "qualified-name-unknown"
    },
    "manifestation": {
      "phase": "addressed"
    }
  },
  "state": "valid"
}
```

Malformed requests, schema violations, pinned-hash conflicts, seed tampering,
artifact tampering, and failed verification use canonical `invalid`.
Mutations that place a resolution status in `Thing.state` are rejected.

## Qualified-name law

The only canonical qualified form is:

```text
uc://applications/<application-name>@<explicit-version>
```

Resolution is:

```text
qualified name
+ exact registry snapshot
→ exactly one registry record
→ exactly one canonical seed identity
→ registered current compiler route
→ exactly one artifact-tree identity
```

No fuzzy comparison, prefix selection, closest-name lookup, AI inference,
implicit version selection, or host-dependent selection is permitted.

A short name is never sufficient by itself. A short name with one current
record remains unresolved because no version policy was pinned. Ambiguity is
proved with a test-only registry fixture containing two explicit versions; no
unbacked identity is added to the production registry.

## Canonical registry

The machine-readable schema is
[`seed/MANIFESTATION_SCHEMA.json`](seed/MANIFESTATION_SCHEMA.json). The proof
registry is [`seed/registry.json`](seed/registry.json).

Every record pins:

```json
{
  "canonical_name": "uc://applications/trajectory-meter@1",
  "product_family": "thing-v2",
  "seed_id": "thing-v2:trajectory-meter@1",
  "seed_path": "thing_v2/trajectory_meter.json",
  "seed_sha256": "...",
  "compiler_route": "thing-v2",
  "compiler_version": "THING-V2-1",
  "artifact_tree_sha256": "..."
}
```

The permanent route table contains no application names. Each
`compiler_version` is checked against the current route authority:

```text
application-v3  → UC-APPLICATION-3
thing-v2        → THING-V2-1
stateful-unfold → UC-UNFOLD-1
expression-uem  → UEM-16-v0.1
```

The registry covers exactly the five Application v3 products, two Thing v2
products, two stateful products, and two expression/UEM products.

The registry snapshot hash covers this canonical projection:

```text
registry_version
records sorted by canonical_name and seed_id
```

The snapshot field itself is excluded to prevent recursive self-hashing.
Record order therefore cannot change registry identity.

## Canonical hashing

Registry and seed identity use UTF-8 canonical JSON:

```python
json.dumps(
    value,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
)
```

Each source seed is verified in that form before its unchanged compiler route
is invoked. This makes identity independent of dictionary insertion order
without changing any compiler's file-based semantics.

Hashes exclude:

- registry and seed filesystem locations;
- temporary and final output paths;
- record and dictionary insertion order;
- timestamps;
- host-specific serialization.

## Artifact lifecycle and evidence

The conceptual lifecycle is:

```text
potential
→ addressed
→ resolved
→ specified
→ planned
→ generated
→ compiled
→ verified
→ manifested
```

Only completed observable transitions are claimed. Existing compiler routes
may combine internal phases, so this successor does not fabricate separate
linked or packaged evidence.

A successful ordered evidence suffix is:

```text
manifestation:addressed
boundary:registry:read
resolution:registry-verified
manifestation:resolved
boundary:seed:read
manifestation:seed-verified
boundary:artifact-output:prepare
manifestation:compile-requested
manifestation:compiled
manifestation:artifact-verified
boundary:artifact:publish
manifestation:manifested
```

A failure contains no evidence for later phases.

## Public proof command

```bash
uc manifest uc://applications/trajectory-meter@1 \
  --registry seed/registry.json \
  --snapshot 83b50b02ff3a97edd12e22f62b5dc978b1e38fb5b272967e3007e57049cbaff4 \
  --output /tmp/uc-manifested-trajectory
```

The result exposes:

```json
{
  "registry_snapshot_sha256": "83b50b02ff3a97edd12e22f62b5dc978b1e38fb5b272967e3007e57049cbaff4",
  "canonical_name": "uc://applications/trajectory-meter@1",
  "seed_id": "thing-v2:trajectory-meter@1",
  "seed_sha256": "762f633c12a87bcf8a462002c253b047b980c1e1ab442a307154230c988fda49",
  "compiler_version": "THING-V2-1",
  "artifact_tree_sha256": "a8c08f617be16b5916616a30834ad6444e81ea737559eca5747ce7082e1d3841"
}
```

## Failure and atomicity contract

Expected resolution and validation outcomes do not create tickets.
Unexpected exceptions produce one deterministic redacted ticket using the
existing Thing v2 ticket shape.

Compilation always targets a sibling staging directory. The artifact is
published only after generated tests, acceptance, fixed-point checks, runtime
seed absence, seedless copied execution, and the pinned artifact hash pass.

Seed or artifact mismatch, compilation failure, and publication failure leave
the previous accepted artifact byte-identical. Failed staging trees are
diagnostic material, not accepted manifestations. Diagnostic directories use
a deterministic sibling identity and are retained until the next attempt for
that output, so repeated failures have identical canonical results.

## Proof matrix

Focused tests assert:

- all eleven current products are pinned to generic compiler routes;
- direct compiler identities equal manifested identities for every product;
- deterministic independent generation across every registered product;
- qualified resolution and two independent byte-identical manifestations;
- copied runtime execution without registry, seed, or repository;
- unknown, ambiguous, unavailable, conflict, seed-missing and tamper outcomes;
- registry and seed dictionary-order independence;
- name, version, registry, seed and output location changes as data;
- no implicit version or fuzzy-name selection;
- no resolution-status overload of canonical Thing state;
- behavioral mutations for direct/variable state overload and prefix matching;
- seed and artifact hash mismatch;
- deterministic repeated failure, atomic refusal, preservation and recovery;
- isolated copied execution with Python site initialization disabled;
- deterministic redacted ticket behavior for an unhandled fault;
- absence of proof-application vocabulary from production implementation.

## Explicit non-goals

Not implemented or modified:

- deployment identities or installation records;
- deployment/execution transitions or process lifecycle;
- temporal past/present/future queries;
- real-time or near-real-time deadline enforcement;
- scheduler ticks, frames, or advancement;
- multi-installation coordination;
- Thing v2 semantics;
- UEM host equivalence;
- Milestone 2 or root-seed self-hosting;
- new GUI/browser generator semantics.
