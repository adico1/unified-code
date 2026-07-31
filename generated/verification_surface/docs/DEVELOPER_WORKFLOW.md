# Generated verification workflow

Authority: `610dae07346e7a4bd5ecbc4159fbcd2c26e8231cbc25de237f5d748d84e7049e`
Semantic structure: `ed3eb787237d7d7de3b2815580fcd32311e927451830e4a332920919ba6637da`
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
