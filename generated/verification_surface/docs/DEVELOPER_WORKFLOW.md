# Generated verification workflow

Authority: `10c7e99fa96f35459b12bd853f714b0a191c13887dd4784902667cc00e6b7045`
Semantic structure: `52760be7483ccdaf7c50611eedf3c689e97b593cc14c2a9f6383204322bc0bc0`
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
