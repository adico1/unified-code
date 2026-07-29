# Universal calculator application generator

`uc://generators/calculator-application-generator@1` composes independently
versioned atomic truths into one calculator IR, one UEM-16 artifact, a derived
semantic interface, and platform projections.

```bash
uc calculator generate seed/applications/bounded_integer_expression.json \
  --output /tmp/calculator --build --install --verify --gauntlet-depths 10

uc calculator generate-suite seed/calculator_suite.json \
  --output /tmp/unified-calculator-suite \
  --build --install --verify --gauntlet-depths 10
```

Atomic seed families are quantities, operations, rules, formulas, calculation
models, domains, interfaces, platforms, targets, themes, and locales. Every
request selects explicit versioned identities. A missing version is never
selected implicitly.

The reference suite generates bounded-integer expression, scientific decimal,
unit conversion, percentage, date-duration, mortgage, and statistics
calculators. `discount_price.json` is the unseen composition proof: it required
no generator change.

The verified targets in this slice are static web, Intel macOS desktop,
Windows x64 desktop, and CLI. Other declared targets remain
`declared-unverified`. Platform shells differ, while the canonical UEM
calculation artifact, fixtures, results, error identities, and evidence order
remain shared.

Generated public composition has one Thing input and one Thing output, exactly
ten semantic depths, and no explicit conditions or loops. Necessary parsing,
iteration, arithmetic selection, filesystem effects, and atomic replacement
remain named audited primitives in the generator/runtime boundary.
