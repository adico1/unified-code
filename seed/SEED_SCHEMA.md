# Canonical seed schema (TEN-1)

## Location

```text
seed/
  ROOT.seed.json          # single canonical root (required)
  declarations/           # application declarations as pure data
  packages/               # package descriptors (framework modules as data)
  stamps/                 # generation stamps and lock hashes
  SCHEMA.json             # machine-readable schema of this format
```

## Root object (`ROOT.seed.json`)

```json
{
  "standard_version": "TEN-1",
  "uem_version": "UEM-16-v0.1",
  "seed_id": "uc-canonical",
  "packages": [],
  "declarations": [],
  "hosts": [],
  "vendored": [],
  "laws": ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "L10", "L11", "L12", "L13"],
  "standard_ten": true,
  "gaps": []
}
```

### Fields

| Field | Meaning |
| --- | --- |
| `standard_version` | Always `TEN-1` for this schema |
| `uem_version` | UEM bytecode/runtime identity |
| `seed_id` | Stable name of this seed |
| `packages` | List of package descriptors (module trees as data) |
| `declarations` | Paths/ids of app declarations under `seed/declarations/` |
| `hosts` | Physical host boundary descriptors (posix/wasm/mcu) — no domain logic |
| `vendored` | Explicit third_party list |
| `laws` | L1–L13 identifiers this seed claims |
| `gaps` | Open `standard.gap` tickets (ids) the seed acknowledges |
| `artifacts` | Expected generated artifact paths + content digests (lock) |

## Declaration file (JSON)

Pure data. No Python. Expression trees use UEM-portable operator nodes only.

```json
{
  "id": "text_stats_v2",
  "project": { "name": "...", "package": "..." },
  "boundaries": [],
  "features": [],
  "cli": {},
  "verify": {},
  "presentation": {}
}
```

## Package descriptor

Describes a generatable module. Until the seed fully expresses the UEM host and generator, package bodies may be listed as `standard.gap` pending expression.

## Stamp file (alongside every generated artifact)

See STANDARD_TEN.md “Generated artifact stamp”.

## Hash discipline

- `seed_sha256` = SHA-256 of canonical `ROOT.seed.json` bytes (UTF-8, sorted keys, separators `,` `:`, trailing newline forbidden for lock; generation uses exact file bytes on disk).
- `declaration_sha256` = SHA-256 of the declaration file bytes used.
- `generator_sha256` = SHA-256 of the bootstrap generator entry (see `seed/stamps/generator.lock.json`).
- `artifact_sha256` = SHA-256 of the generated artifact body (stamp file itself excluded from its own hash).
