# Standard Ten

Governing meta-law above L1–L13. Non-bypassable. Version **TEN-1**.

Conventional development is not an authorized fallback. When Standard Ten cannot express a requested feature, implementation must stop with `standard.gap` and open a design ticket. It must not introduce handwritten application logic, OOP, imperative control flow, parallel interface implementations, domain-specific generator branches, or untracked files.

---

## 1. One Thing

Every operation receives one canonical Thing and returns one canonical Thing.

## 2. One composition form

Programs are nested parts assembled in the same onion/babushka pattern.

## 3. One seed

All framework, generator, runtime, application, tests, documentation and interfaces derive reproducibly from one canonical seed.

## 4. No handwritten application code

Developers change declarations or the seed. Generated files are never manually corrected.

## 5. No OOP

Functions, modules and plain data only. No user-defined classes, inheritance or object architecture.

## 6. No application control flow

No loops, conditions, matching, control exceptions, comprehensions or hidden recursion. Flow is events, routes, maps, folds and stops.

## 7. One event machine

All execution targets UEM. Python, C, CLI, API, web, desktop, files, network and chips are interfaces around the same machine—not separate implementations.

## 8. Explicit boundaries and failures

Every external effect passes through a named outward boundary. Unrecovered exceptions produce ticket events. Nothing is swallowed.

## 9. Evidence and determinism

Every transformation records ordered evidence. The same seed, declaration and input must produce byte-identical artifacts and canonical results.

## 10. Complete generated verification

Tests, gauntlets, mutations, traceability and coverage are generated from the same seed and declaration. No artifact is accepted below 100% required conformance.

---

## Non-fallback law

> Conventional development is not an authorized fallback. When Standard Ten cannot express a requested feature, implementation must stop with `standard.gap` and open a design ticket. It must not introduce handwritten application logic, OOP, imperative control flow, parallel interface implementations, domain-specific generator branches, or untracked files.

---

## Provenance classifications

Every repository file must be classified as exactly one of:

```text
seed
generated
external-vendored
physical-host-boundary
evidence
```

## Generated artifact stamp

Every generated file must contain or accompany:

```json
{
  "seed_sha256": "...",
  "generator_sha256": "...",
  "declaration_sha256": "...",
  "standard_version": "TEN-1",
  "uem_version": "UEM-16-v0.1",
  "artifact_sha256": "..."
}
```

## Clean-room rule

CI must regenerate from a clean directory and compare every artifact byte-for-byte. Any unexplained file or difference fails.

## Temporary handwritten exceptions (only)

1. Canonical root seed (`seed/`)
2. Minimal physical UEM host boundary (`physical-host-boundary`)
3. Explicitly identified vendored dependencies (`external-vendored`)

These exceptions must not contain application or domain behavior.

## Relationship to L1–L13

L1–L13 remain binding laws for shape, evidence, UEM, physical targets, and multi-dimension coverage. Standard Ten governs *how* work may be performed: only seed → generate → UEM → evidence. L13 100% dimensions still apply; they do not authorize conventional fill-in of gaps.
