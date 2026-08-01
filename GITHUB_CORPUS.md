# Canonical GitHub corpus snapshot contract

Status: **contract only**. This issue does not implement a network adapter,
repository classification, seed inference or a complete GitHub census.

## Law

```text
pinned request identity
→ named GitHub OUTWARD acquisition or offline replay
→ raw content-addressed pages
→ canonical semantic snapshot
→ separate execution evidence
```

The public pure Parts are:

```text
identify_request(thing) -> thing
identify_snapshot(thing) -> thing
```

They perform no I/O. A future adapter owns GitHub transport at an audited
OUTWARD boundary and then supplies the resulting document to this contract.

## Two identities

`snapshot_sha256` hashes semantic content:

- the exact request and initial cursor;
- provider, transport, API version, endpoint and visibility scope;
- query, variables, page size and selected record fields;
- completion status and reason;
- cursor-linked pages, raw response hashes and canonical records.

`evidence_sha256` binds that snapshot identity to acquisition observations:

- `live` or `replay` mode;
- observation timestamp;
- duration;
- ordered attempts and retries.

Timestamps, durations and acquisition mode never change `snapshot_sha256`.
They do change `evidence_sha256`. Therefore, a live acquisition and offline
replay may prove the same semantic snapshot without pretending they are the
same observation.

## Canonicalization

JSON is UTF-8 with sorted object keys and compact separators. Request field
order and record order do not affect identity. Records are ordered by their
provider source identity and canonical payload hash. Pages are ordered by
their explicit zero-based index and must form one cursor chain starting at the
request's pinned initial cursor.

Different query text, variables, initial cursors, page cursors, API versions,
endpoints, transports or visibility scopes necessarily produce different
semantic request or snapshot identities.

## Completion states

| Status | Required reason | Meaning |
| --- | --- | --- |
| `complete` | `exhausted` | the pinned request reached a terminal null cursor |
| `partial` | `operator_limit`, `page_limit`, or `unknown` | acquisition stopped without claiming completeness |
| `rate_limited` | `rate_limit` | provider quota stopped acquisition |
| `unavailable` | `provider_unavailable` | no pages were accepted |

These states are domain data inside a valid Thing. `Thing.state = invalid` is
reserved for malformed documents and violated invariants. Expected invalid
documents create no ticket.

`complete` means complete only for the exact pinned request and observed API
boundary. It is not a claim that the snapshot covers every GitHub repository,
every application or every application on Earth.

## Replay example

```python
import json
from pathlib import Path

from unified.boundary import inward
from unified.github_corpus import identify_snapshot

document = json.loads(
    Path("seed/github_corpus/replay.example.json").read_text()
)
result = identify_snapshot(inward({"snapshot": document}))
assert result["state"] == "valid"
```

The schemas and frozen vectors are under `seed/github_corpus/`. Run:

```bash
pytest -q tests/test_github_corpus.py
```
