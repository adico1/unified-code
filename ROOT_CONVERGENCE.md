# Root Convergence — בלימה

Status: normative Milestone 2 convergence contract. This contract is
executable, but the complete root fixed point is not yet claimed.

## One Thing, exactly ten depths

Standard Ten bounds semantic depth. Generation may repeat, but it cannot add an
eleventh depth.

```text
depth count      = exactly 10
generation count = repeat within a declared bound until convergence
```

The other numeric structures used by the project describe relations inside the
ten depths. They do not expand the depth system.

## Authority and roles

```text
Watcher observes.
Verifier judges.
Creator generates.
Boundary manifests.
```

A watcher contains only an identity, assigned depths, an observed relation and
required evidence. It cannot generate application behavior. A projection
cannot correct itself. A correction returns to one registered authority:

```text
seed
specification
compiler law
canonical boilerplate
```

All affected projections are then regenerated.

The authority bundle hash includes both identity and content for every
authoritative component, plus the complete watcher registry. Equal bytes under
different authority identities do not collapse into one authority.

## Semantic and evidence identities

For generation `n`:

```text
Sₙ = canonical semantic structure
Hₙ = SHA-256(canonical_encode(Sₙ))
Eₙ = separate audit evidence

Sₙ₊₁ = unfold(Sₙ, creator_law, watchers)
```

`Sₙ` includes the authority-bundle identity, exactly ten depths, projections,
watcher verdicts, letter verdicts and law verdicts.

`Eₙ` is hashed separately from:

```text
Hₙ
ordered verdicts
execution measurements
environment identity
```

Timestamps, durations, host paths and platform details may appear in evidence.
They cannot influence `Hₙ`.

## Projection and root fixed points

```text
projection fixed point
= one API/CLI/GUI/UEM/network or other registered projection no longer changes

root fixed point
= every projection and their shared authority no longer change
```

A projection may converge while the root remains pending because another
watcher or projection still changes.

Success requires:

```text
Hₙ₊₁ = Hₙ
∧ depths(Sₙ) = exactly 10
∧ every watcher resolved
∧ every projection converged
∧ every law passed
∧ every letter valid
→ בלימה
→ גילה
```

Failure and bounded continuation are distinct:

```text
Hₙ₊₁ ∈ {H₀ … Hₙ₋₁}
→ invalid: unfolding-cycle

generation_count > declared_bound
→ invalid: bilima-limit

unresolved watcher at fixed structure
→ invalid: unresolved-distinction

projection cites a different authority bundle
→ invalid: divided-authority

structure changed and the bound remains
→ formed: pending
```

## Letter verdict

Every projected letter has exactly one verdict:

```text
required + present once + correctly placed → valid
required + absent                          → missing
not required + present                     → foreign
required + present repeatedly              → duplicate
required + wrong position or role          → misplaced
requirement not determinable               → unresolved
```

Only `valid` permits manifestation.

## Executable contract

The trace schema is
[`seed/ROOT_CONVERGENCE_SCHEMA.json`](seed/ROOT_CONVERGENCE_SCHEMA.json).
Verify a trace with:

```bash
uc converge path/to/root-convergence-trace.json
```

The verifier:

- computes the canonical authority-bundle hash;
- computes every semantic structure and projection hash;
- keeps audit hashes separate;
- detects divided authority, cycles and the generation bound;
- distinguishes projection convergence from root convergence;
- requires exactly ten ordered depths;
- requires all registered watchers, letters and laws to resolve;
- emits `convergence:bilima` and `manifestation:gila` only on success.

## Milestone boundary

Application-level convergence is established evidence, not root completion.
Milestone 2 remains open until:

```text
ROOT.seed
→ generator
→ framework
→ independent Python/C hosts
→ tests and mutations
→ documentation
→ dependencies
→ complete repository
→ byte-identical root fixed point
```

The current executable verifier judges that future proof. It does not fabricate
Stage1-A or Stage1-B, replace the missing Stage-1 generator, or close the
existing root-seed `standard.gap`.
