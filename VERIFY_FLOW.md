# Unified Verification Flow

`uc verify-all` is the single verification operation.

```text
verification.requested
→ authority.discovered
→ identities.resolved
→ proof_graph.formed
→ prerequisites.materialized
→ proof_nodes.released
→ proof_nodes.executed
→ evidence.collected
→ identities.compared
→ budget.measured
→ verification.completed
```

The canonical event routes, dependency graph, proof inventory, cache policy and
five-second budget live in
[`seed/verification/PROOF_GRAPH.json`](seed/verification/PROOF_GRAPH.json).
Application orchestration is data. Host iteration, waiting and physical
selection are confined to named `audited_*_primitive` boundaries and their AST
control-flow count is published.

## Timing law

```text
T_total = T_minimized_tool_bootstrap + T_verification
T_verification ≤ 5.000 seconds
```

The monotonic clock measures the critical path, not summed worker time. A cold
flow materializes required proof evidence once. A warm flow admits that evidence
only when the complete tracked-source authority and content-addressed cache
identity match. Timestamps, durations, host paths and process identities are
excluded from the semantic structure hash and remain in the evidence hash.

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

Expected failures route to `verification.failed`. Cache tampering routes to
`identity.stale`. Missing or reordered events, unresolved dependencies,
unregistered handlers, sequentialized independent nodes, premature completion,
failure/timeout suppression and hidden application control flow are mutation
failures.
