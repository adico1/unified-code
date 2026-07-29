# Generated verification workflow

Authority: `c064b67c6b0074835ea215e2a89fd9b014ab31d615ef8a7e3e3a6f9176a31032`
Semantic structure: `c21b3e04a89002ecf7bcfd935981e7886d376374ec529a65562a9e2eb627b0a6`
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
