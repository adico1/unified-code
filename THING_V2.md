# Thing v2 — Compile-time specialization

Thing v2 is a focused compile-time generator. A JSON seed is interpreted once
by the compiler, which specializes seven application files and verifies the
result before atomic installation. The installed application neither needs nor
interprets the seed.

The permanent construction vocabulary is called **`בלי_מה`** (“seedless” in
portable code identifiers). Boilerplate vocabulary remains stable; generated
specialization changes with declared seed sections.

```text
compile time
בלי_מה boilerplates + seed.json + deterministic compiler
                              │
                              ▼
                  specialized application tree

runtime
outer input + runtime parameters
              │
              ▼
  generated application (no seed)
              │
              ▼
         outer output
```

## Public command

```bash
uc compile seed/thing_v2/trajectory_meter.json \
  --output /tmp/uc-trajectory-meter \
  --verify
```

The compiler validates the declaration, resolves dependencies, specializes all
seven stages, writes a sibling temporary tree, checks source laws, runs
generated tests and acceptance cases, runs the copied application without its
seed, records a deterministic manifest, and only then replaces the destination.
A failure returns nonzero, retains its diagnostic staging tree, and leaves an
existing valid destination byte-identical.

## Canonical seed

The machine-readable schema is
[`seed/THING_V2_SCHEMA.json`](seed/THING_V2_SCHEMA.json). The complete native
example is
[`seed/thing_v2/trajectory_meter.json`](seed/thing_v2/trajectory_meter.json).
Its sections have these responsibilities:

| Seed section | Compile-time meaning |
|---|---|
| `application` | Stable project/package identity and generated metadata |
| `formats` | Outer, inner, core-input, core-output and return representations |
| `core.mode` | Exactly one of `native` or `foreign_fixture` |
| `computation_seed` | Selected operation, domain field names and coefficient |
| `compile_time_constants` | Specialized constants, including the affine bias |
| `runtime_parameter_schema` | Named runtime parameters and numeric bounds |
| `validation` | Canonical input requirement |
| `evidence_requirements` | Exact ordered success evidence |
| `selected_adapters` | Explicit outer input/output adapter selection |
| `acceptance` | Inputs, parameters, canonical outputs, errors and evidence |
| `foreign_dependency` | Required foreign-mode version/hash/license/effect record |

The current computation seed is intentionally bounded to a numeric affine
operation. This is a real compile-time programming vocabulary, not a claim of
arbitrary-program support.

## Seven generated responsibilities

For package `<package>`, the generated pipeline is:

| File | Responsibility |
|---|---|
| `stage_01_outer_to_inner.py` | Parse/normalize the declared outer input |
| `stage_02_inner_to_core.py` | Select and validate input and runtime parameter |
| `stage_03_core_prepare.py` | Prepare the canonical core payload and constants |
| `stage_04_core_processing.py` | Invoke the selected native core or foreign adapter |
| `stage_05_core_collect.py` | Validate and collect the canonical core result |
| `stage_06_core_to_inner.py` | Construct the declared inner output |
| `stage_07_inner_to_outer.py` | Encode the declared outer output |

`compose.py` nests these seven Parts. Every public generated Part has one
signature: `part(thing) -> thing`; composition exposes `program(thing) ->
thing`. The stage and composition files contain no user-defined classes,
conditions, loops, matching, comprehensions, or exception handling. Physical
control flow lives in the generated audited runtime and named process boundary.

## Core modes

### Native Standard Ten-shaped core

The compiler specializes a core stage from the declared computation,
compile-time constants, formats and runtime parameter schema. Domain names
occur only in specialized output, never in the permanent compiler or
boilerplates.

### Foreign-core adapter

The second proof,
[`seed/thing_v2/orchard_yield.json`](seed/thing_v2/orchard_yield.json), uses an
explicitly labeled incompatible foreign-API fixture. It is not represented as a
production third-party integration. The generated adapter converts canonical
input, invokes the fixture, validates and converts output, catches foreign
exceptions, and returns a deterministic error identity. Raw types, tuple tags,
exceptions and messages do not cross the adapter. The seed records fixture
version, source, SHA-256, license and whether the call is pure or OUTWARD.
The current fixture contract is `pure`; OUTWARD foreign calls are not yet a
supported mode.

## Manifest and fixed point

`.thing_v2/manifest.json` records:

- seed, compiler, boilerplate-family and seed-section hashes;
- every generated-file hash and a complete tree hash;
- seed-section-to-file dependency edges;
- the seven specialized files;
- the verified foreign provenance record;
- source-law, generated-test, acceptance, seed-absence, seedless-copy and
  fixed-point results.

The complete tree hash covers generated files other than the manifest itself;
this avoids recursive self-hashing. Rendering the same seed twice must produce
identical file maps, tree hashes and deterministic manifest bytes. File
timestamps are not inputs.

## Dependency and churn contract

The compiler compares the installed manifest's seed-section hashes with the new
seed. Unaffected files whose bytes still match the prior manifest are copied
unchanged; affected files are regenerated.

| Change | Permitted generated change |
|---|---|
| Description only | `README.md`, package metadata and manifest; no runtime file |
| Outer-output format | Stage 07 plus declared acceptance/evidence and manifest |
| Computation seed | Stage 04 plus declared acceptance/evidence and manifest |

Tests compare actual hashes, not only deterministic full rebuild results.
Unchanged runtime files retain identical bytes.

## Verification and anti-overfitting

Both proofs compile, run generated tests, assert exact ordered evidence, rebuild
to a fixed point, and run from a copied directory containing neither seed nor
source repository. Runtime-source gates prohibit generator imports, seed paths,
declaration parsing, `eval`, `exec`, dynamic imports and dynamic compilation.

`scripts/check_thing_v2_overfit.py` derives domain vocabulary from both proof
seeds. It requires an empty intersection with the seed compiler,
transformation boilerplate, native-core boilerplate, foreign-adapter
boilerplate and runtime composition. It then injects every derived term into
every surface and requires every mutation to be detected.

## Honest limitations

Thing v2 currently proves two applications inside one deliberately small
numeric/affine seed language and two outer formats. The foreign mode proves the
adapter contract with a fixture already in the generated tree, not compatibility
with all third-party libraries.

It does **not** prove arbitrary programs, every third-party library,
self-hosting, complete-repository generation, GUI/browser generation, or all
hardware. It does not begin Milestone 2. The generated Python target demonstrates
the requested Thing-to-Thing and control-flow source laws; it does not close the
repository's already documented TEN-1 full-tree or UEM-only migration gaps.
