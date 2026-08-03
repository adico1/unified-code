# ROOT Projection Language

Status: implemented projection vocabulary; whole-repository manifestation is
not yet proven.

`seed/ROOT.seed.json` now declares a repository contract with exactly ten
depths, ten ordered watchers, a fixed generation bound, registered renderer
identities and dependency-ordered projections. The generated Stage-1 runner
interprets those declarations using the same generic projection machinery as
the trusted Stage-0 boundary.

Each projection declares exactly:

```json
{
  "path": "generated/root_surface/watchers.json",
  "seed_node": "/repository/watchers",
  "renderer": "canonical-json",
  "depends_on": ["generated/root_surface/repository-contract.json"]
}
```

The registered renderer vocabulary is bounded to canonical JSON, UTF-8 line
documents and explicit hexadecimal bytes. Unknown renderers, duplicate or
escaping paths, unresolved or forward dependencies, malformed values, and
non-ten-depth repository contracts are rejected before atomic publication.
The output manifest records the seed node, dependency edges, byte size and
SHA-256 of every file.

The current root authority projects its own canonical seed, repository
contract, watcher registry and status document. Independent Stage-0 and
generated Stage-1 runs produce the same nine-file tree byte for byte.

## Boundary

This vocabulary does not make existing handwritten repository source
root-generated. A file is root-generated only after a typed projection in the
root authority emits it and its manifest proves that provenance. Encoding an
existing source file as an opaque string or byte blob in the seed is prohibited
and would not close the authority gap.

Issue #9 remains open until every required framework, host, generator,
application, test, mutation, golden, document, audit and workflow surface is
expressed through lawful root declarations, regenerated in a clean room, and
the successor root operation produces zero changed bytes.
