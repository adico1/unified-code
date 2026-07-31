# Build output

Generate the canonical local product catalog from the repository root:

```bash
uc assemble seed/application_suite.json \
  --output build \
  --build \
  --install \
  --verify \
  --gauntlet-depths 10
```

`build/` is ignored, disposable output. Publication is atomic: a failed
assembly cannot replace the previous valid tree.

```text
build/
├── calculators/       33 products
├── dashboards/         1 product
├── document-tools/     2 products
├── libraries/          1 product
├── pong-games/          9 products
├── todos/              33 products
├── README.md           generated user entrance
├── index.json          generated canonical product index
└── .unified/           internal assembly trees, registry and evidence
```

Each visible product directory is keyed by its explicit versioned identity and
contains the applicable parts of this trace:

```text
authority/
specification/
source/
application/
verification/
manifest.json
```

The exact paths are authoritative in `build/index.json`; not every compiler
profile needs a separate `source/` copy. Consumers should use the visible
family/product path. `.unified/` exists for audits and manifestation internals,
not as the product navigation surface.

The repository remains the authority. Do not commit `build/`, edit generated
files, or treat their filesystem location as product identity.
