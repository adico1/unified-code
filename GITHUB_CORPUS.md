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
python -m unified.selftest tests/test_github_corpus.py
```

## Canonical offline fixture pack

`seed/github_corpus/fixtures/` contains three minimal public-repository records
across two content-addressed pages. Each record retains its GitHub source URL
and available SPDX license metadata. Each page pins the retrieval-contract
version, source URL and canonical content hash. The pack is deliberately small:
it proves replay mechanics, not application classification or corpus coverage.

Replay supplies the checked-in manifest and page text to the pure public Part:

```python
replay_fixture_pack(thing) -> thing
```

The Part performs no network or credential access. Missing, duplicate,
malformed and content-altered pages are rejected without tickets; record and
manifest page order do not change the canonical identity. The contributor
verification command remains the repository's single cached operation:

```bash
uc verify-all
```

## Deterministic repository normalization

The next pure Part consumes a complete or explicitly partial canonical
snapshot:

```python
normalize_repositories(thing) -> thing
```

It produces stable repository records, explicit `fork_of` and `mirror_of`
edges, relationship components, declared monorepo boundaries and unresolved
verdicts. Provider source identity remains the repository identity. Names may
change and retain ordered rename history without silently creating a new
identity.

An explicit fork or mirror relation places repositories in one relationship
component. A multi-member component deliberately has
`selection_status = unresolved`; normalization does not choose an implicit
winner or claim semantic equivalence. Missing boundary declarations also
remain unresolved. Archived, deleted, unavailable, renamed and ambiguous
states remain distinct.

The golden identity graph and ambiguity vectors are under
`seed/github_corpus/normalization/`. These are contract vectors, not public
repository observations. The public fixture pack supplies the separate
measured positive proof. Normalization performs no network access, ranking,
classification, seed inference or fuzzy matching.

## Traceable candidate seeds

Evidence-bearing observations may be projected from normalized repositories by
the pure public Part:

```python
extract_candidate_seeds(thing) -> thing
```

Each semantic letter is either traced to a pinned repository revision, source
path and source SHA-256, or retained with an explicit `missing` or `unresolved`
verdict. The full verdict vocabulary keeps `valid`, `missing`, `foreign`,
`duplicate`, `misplaced` and `unresolved` distinct. Collection order and
repository names do not select behavior or change stable candidate identity.

Candidate seeds are not proven application seeds. They always carry
`catalog_status = candidate` and `promotion_eligible = false`; the production
manifestation registry rejects their shape. Human review can retain or reject a
candidate, but cannot silently promote it. Independent acceptance and a
separate proven-seed operation remain required.

The checked-in observation authority, schema and golden identities are under
`seed/github_corpus/candidates/`. They pin two public repository families and
copy no opaque source blobs. Extraction performs no network access, untrusted
source execution, application ranking, seed inference, compiler mutation or
live acquisition.

## Frozen unseen holdout

Issue #47 pins two repositories by immutable commit and source hashes before
evaluation. The first exposes an unsupported distinction: its documented GUI
omits the backspace control currently assumed by generated expression tests.
The compiler is unchanged; the result is the exact `standard.gap` identity
`gap.unsupported-feature:application-language-without-backspace-control`.

The second holdout selects its README-documented desktop keyboard projection.
The existing replay, normalization, candidate extraction and application
assembly operations produce seven passing cases with compiler identity
`ca64e9fe7ed25a0d30b12ff8b1420329ed61780e23a20c93157a7b06a699af98`
and generated tree identity
`bc4a12032771aaaec094bec5240c66817a6fec19c9c71ae778461d60de58ded8`.
The acquired source's dynamic evaluation and undocumented controls remain
foreign observations; they are not copied into the seed or generated runtime.

Run the offline behavioral proof:

```bash
PYTHONPATH=. python -m unified.selftest tests/test_github_holdout.py
```

Regenerate the accepted artifact with the existing compiler:

```bash
PYTHONPATH=. python -m unified.generator.application_language.seed_compiler \
  seed/github_corpus/holdout/accepted/application.seed.json \
  --output build/holdouts/documented-keyboard-calculator-holdout@1
```

This proves one pinned unsupported verdict and one pinned accepted projection.
It does not prove universal repository-to-application generation, live corpus
acquisition, seed inference, fuzzy merging or automatic catalog promotion.
