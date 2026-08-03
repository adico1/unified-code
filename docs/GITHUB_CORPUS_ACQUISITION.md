# GitHub corpus acquisition boundary

Issue #43 adds one read-only GitHub OUTWARD boundary. It performs transport
only. Repository normalization, relationship handling, candidate extraction,
holdout evaluation and Atlas projection remain separate deterministic stages.

The pinned authority is:

```text
seed/github_corpus/acquisition/PIN.json
```

Replay the verified Issue #44 public fixture without network access:

```bash
python -m unified.github_acquisition replay \
  seed/github_corpus/acquisition/PIN.json
```

Acquire the separately pinned public live request anonymously:

```bash
python -m unified.github_acquisition acquire \
  seed/github_corpus/acquisition/PIN.json
```

When authentication is required, pass an explicit credential file as the last
argument. The file must contain either an anonymous boundary or a bearer
boundary:

```json
{"kind": "bearer", "value": "..."}
```

No environment variable or implicit credential store is consulted. The
credential value, response exceptions and authorization headers never appear
in returned data or evidence.

The live result retains content-addressed raw response pages. A successful
result can be projected through `raw_replay_pack(thing)` and authenticated by
`replay_raw_acquisition(thing)`. Live and replay evidence differ, while their
canonical semantic snapshot identity remains equal.

Expected boundary outcomes remain distinct domain data:

```text
complete | partial | rate_limited | unavailable | unauthorized | malformed
```

They produce no ticket. An unexpected host failure produces one deterministic,
redacted ticket and no accepted snapshot identity.

The pinned three-repository Issue #44 fixture is replay authority. Its original
multi-repository query text is not silently rewritten for GitHub's current
REST search grammar. `LIVE_REQUEST.json` is therefore a separate, explicitly
pinned and content-identified live request.
