# Generated verification workflow

Authority: `944fd457fc7e42dd48c35388e306a7c43a0c1b38311444defa2e247a299b023c`
Semantic structure: `30ad98acd742bc4c095209bad24a88d4dc631c735aab49784db38c97da1630f5`
Canonical facts: `59`
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
