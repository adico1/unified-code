# Generated verification workflow

Authority: `90074d90922f343b1f807dd2756f3370d52776a1d2c536fc85b8b7f9c9e1d06a`
Semantic structure: `d1fcd43879f432e7abd07d52170c0fab09cbc26d6fa68e699c641fa4e5ab95e3`
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
