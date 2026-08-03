# Generated verification workflow

Authority: `2909fdda592157ae7057cacfd365240d770230b7d81d63815511a9d3b2b5d7d3`
Semantic structure: `b352663177e3bfa77f50884036c23b18aa2dcbe6e305d3379c2538472dad43fb`
Canonical facts: `75`
Generated test partitions: `80`
Generated behavioral mutations: `20`
Generated canonical goldens: `74`
Verification proof nodes: `24`

Run `uc verify-all`. Modify canonical seed declarations, regenerate the projection tree, and never edit generated regions or generated files directly.

Generation flow:

```text
verification-generation.requested
authorities.resolved
contracts.projected
tests.generated
mutations.generated
goldens.generated
documentation.generated
audits.generated
projections.cross-checked
fixed-point.requested
fixed-point.completed
verification.requested
verification.completed
```
