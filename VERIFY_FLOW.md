# Unified Verification Flow

`uc verify-all` is the single verification operation.

Repository and generated-product tests are plain functions with plain
assertions, executed by `python -m unified.selftest`. The runner uses only the
Python standard library. Generated Thing v2 applications do not install or
invoke a third-party test framework.

The default `local` profile excludes physical browser, compiler, clean-room,
whole-assembly and fixed-point suites. Those slow suites are declared in
[`TEST_PROFILES.json`](seed/verification/TEST_PROFILES.json) and execute through
the `complete` profile only in the GitHub physical-evidence workflow. Local
development uses `python -m unified.selftest` and `uc verify-all`; neither
rematerializes unchanged physical evidence.

```text
verification.requested
→ tools.boot.requested
→ tools.boot.completed
→ verification.clock.started
→ authorities.resolved
→ proof_graph.released
→ proof.completed
→ evidence.completed
→ verification.clock.stopped
→ budget.measured
→ verification.completed
```

The canonical event routes, dependency graph, proof inventory, cache policy and
five-second budget live in
[`seed/verification/PROOF_GRAPH.json`](seed/verification/PROOF_GRAPH.json).
Application orchestration is data. Host iteration, waiting and physical
selection are confined to named `audited_*_primitive` boundaries and their AST
control-flow count is published.

## Timing law and correction

```text
T_total = T_bootload + T_verify
T_verification ≤ 5.000 seconds
```

Tool bootload contains only Python entry, argument parsing and acquisition of
the monotonic clock. It ends before any repository read. Repository discovery,
source hashing, graph formation, proof-bundle acquisition and validation, cache
lookup or publication, proof aggregation and verdict formation are all measured
inside `T_verify`.

PR #28 incorrectly classified physical proof production as bootstrap, producing
a 281.407659-second bootstrap and a 0.000103-second verification measurement.
The corrected flow attributes that physical work to proof production and admits
its repository-carried
[`PROOF_BUNDLE.json`](seed/verification/PROOF_BUNDLE.json) only after validating
the complete canonical source tree, graph, proof contract, producer toolchain,
Stage-1 identity and bundle identity. Empty local cache creation and valid-cache
identity validation both occur inside the measured verification interval.

The bundle is physical evidence, not a downloaded verdict or CI-status proxy.
It is produced by the same graph (`UC_VERIFY_MATERIALIZE=1 uc verify-all`) and
contains no timestamps, durations, temporary paths or process identities.
Release materialization is expensive; acceptance verification is the
content-addressed acquisition and validation of that evidence.

Materialization is the one-time evidence-production boundary. Ordinary local
and CI verification is lazy: it validates the content-addressed bundle and
aggregates every proof verdict under the five-second law without rerunning
unchanged physical browser, compiler, sanitizer or coverage work.

## Browser boundary

Application assembly bootstraps one Chromium-family process. Every graphical
proof uses a fresh target with a distinct generated GUI origin, closes that
target after evidence capture, and reuses the same physical browser process.
The proof remains real browser, canvas, keyboard, request/response and rendered
frame behavior; it is not replaced by Node or a mock.

## Evidence boundary

The graph covers repository tests, Stage 0, Stage 1, the Stage-1 fixed point,
Standard Ten, L1–L13, Python/C equivalence and coverage, mutations, fuzzing,
sanitizers, native goldens, five-application assembly, manifestation identities,
CLI/GUI equality, real-browser behavior, atomic preservation, copied isolated
runtime, provenance, honest open gaps and supported-Python CI.

Expected failures route to `verification.failed`. Corrupt, stale, partial and
wrong-platform local cache projections fail closed. Every repository-dependent
activity is rejected from bootload. Missing or reordered events, unresolved
dependencies, unregistered handlers, sequentialized independent nodes,
premature completion, failure/timeout suppression, physical/logical proof
mutation and hidden application control flow are mutation failures.
