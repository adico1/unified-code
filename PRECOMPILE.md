# Pre-compilation specialization

Unified Code treats the seed as the complete application request and performs
semantic specialization before Python compilation:

```text
request
→ system architecture
→ systems
→ interfaces
→ full specification
→ target-specialized specification
→ seven-stage manifestation plan
→ exact generated AST/source
→ Python compilation
→ generated verification
```

The public operation remains:

```bash
uc assemble seed/application_suite.json \
  --output <directory> \
  --build \
  --install \
  --verify \
  --gauntlet-depths 10
```

No additional architecture, interface, specification or renderer input is
accepted at that boundary.

## Authority

The leaf `מה` seed owns application identity, semantics, state, presentation,
program entrypoints and acceptance. Its pinned bases own reusable `בלי־מה`
laws, registries, boundaries and seven ordered stamp identities. Resolution
selects one registered compiler profile from the capabilities provided by the
pinned bases; application shape is not guessed from its name.

The application-language build produces these projections for every product;
the five established Application v3 products retain their existing canonical
specification, application plan and seven generated stage files:

```text
authority/request.json
architecture/system-architecture.json
architecture/systems.json
architecture/interfaces.json
specification/full-specification.json
specification/specialized-specification.json
source/manifestation-plan.json
source/main.py
application/main.py
verification/test_generated.py
verification/traceability.json
verification/precompile-evidence.json
manifest.json
```

`full-specification.json` records the complete resolved authority.
`specialized-specification.json` removes build-only resolution data and retains
only the selected target declaration and registered stamps. `main.py` is
rendered from that specialized specification, not from the source seed.

## Exactness law

Before installation, the compiler compares declared and generated capability
sets. It measures operation tables, commands, initial state, semantic
functions, routes, public entrypoints, controls, acceptance cases and the
boundary contract.

```text
missing capabilities = ∅
∧ excess capabilities = ∅
∧ generated tests pass
∧ runtime seed access = 0
→ manifestation accepted
```

Removing a selected operation or interface from generated source is a failing
mutation. Build products retain only `application/main.py` at runtime; request,
architecture, specifications and evidence remain outside the runtime tree.

## Current boundary

The permanent construction vocabulary currently has three registered
specialization profiles: expression, stateful and bounded simulation. This is
not proof of arbitrary programs. A request outside their declared vocabulary
must fail rather than falling back to handwritten application code.
