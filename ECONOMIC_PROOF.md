# Economic proof contract

Status: **experiment design; no economic result has been measured**.

Unified Code may reduce repeated application work. That is a falsifiable
hypothesis, not a conclusion derived from deterministic generation or product
count. The normative machine-readable design is
[`seed/economics/ai-swarm-economic-experiment.seed.json`](seed/economics/ai-swarm-economic-experiment.seed.json),
validated by
[`seed/economics/AI_SWARM_ECONOMIC_EXPERIMENT_SCHEMA.json`](seed/economics/AI_SWARM_ECONOMIC_EXPERIMENT_SCHEMA.json).

## Question and comparison

The experiment compares two isolated AI swarms on previously unseen, sealed
application tasks:

```text
same task + same model + same agents + same tools + same budget
├── baseline: registered conventional implementation workflow
└── unified: seed → existing single assembly API → generated product
```

The baseline is not deliberately weakened. It may write normal implementation
and tests with the same pinned tools available to the unified arm. The unified
arm may author application seeds and invoke the existing assembly operation,
but it may not modify permanent compiler machinery for a task or correct
generated products by hand. Each arm begins from its own clean worktree,
processes, cache and fresh agent contexts. Neither arm sees the other's output.

## Sealed holdouts

The confirmatory corpus contains at least 40 tasks and is unavailable while
the system, graders and analysis are being designed. Before reveal, an
independent custodian or timed-release mechanism publishes commitments to the
encrypted corpus and canonical task manifest. The protocol, grader, price
schedule, assignment seed, environments and model identities must also be
content-addressed.

Pilot tasks may estimate variance and determine sample size, but no pilot or
equivalent task may re-enter the confirmatory holdout. A task leak, changed
grader, unequal resources or cross-arm information invalidates the experiment;
it does not become an excluded inconvenience.

## Experimental units and repeats

One unit is identified by:

```text
holdout task hash
+ arm
+ repeat number
+ swarm identity
+ environment hash
+ protocol hash
```

Every task is executed at least three times in each arm. Assignment is paired
within task and randomized in balanced order. Repeats reuse no agent context,
artifact, cache or worktree. Failed and timed-out units retain their original
identities and costs; a retry is a new unit, never a replacement.

## Success before efficiency

The primary success event is complete passage of the hidden acceptance
contract within the common budget. A pinned blind grader also records
functional, security, deterministic, maintainability, performance,
accessibility and provenance outcomes.

An arm is not cheaper merely because it stops early or produces less. An
efficiency claim requires successful-delivery probability to remain within the
pre-registered five-percentage-point noninferiority margin. Timeouts receive
the full budget cost. Crashes include observed and recovery costs. Missing
telemetry gives no success or savings credit.

## Complete cost boundary

Every unit records wall time, input and output tokens, billed model cost, tool
calls, compute, memory, human interventions, attempts, failures and accepted
artifact identity. Prices are applied from a schedule sealed before execution.

Two economic quantities remain separate:

| Estimand | Included cost |
| --- | --- |
| marginal task effect | cost caused by executing one additional task |
| total amortized effect | marginal cost plus the pre-registered share of building and maintaining shared infrastructure |

Infrastructure work cannot disappear into a sunk-cost assumption. Total-cost
results must show the fixed cost and the task-volume scenarios over which it
is amortized. Opportunity costs not directly measured must be labelled as
scenario assumptions rather than observations.

## Analysis

The primary analysis is intention-to-treat and paired by task. It reports the
effect estimate and a two-sided 95% interval using task-clustered resampling
and paired randomization inference. Secondary hypotheses use Holm correction.
No unit is removed solely because it failed, timed out or cost more than
expected. Predeclared task strata may describe heterogeneity; they are not
confirmatory subgroup claims unless separately powered before reveal.

Every event is retained in canonical append-only JSONL. Input, environment,
attempt and output trees are SHA-256 identified. Secrets and personal data may
be redacted only with a redaction manifest that preserves event identities and
accounting totals.

## Allowed conclusion boundary

If the frozen experiment passes, the strongest allowed statement is local:

> Under the registered task distribution, environment, model and budget, the
> Unified Code arm changed measured delivery cost or time by the reported
> estimate and interval relative to the registered baseline.

It may also report total cost at explicitly stated task volumes after including
the measured fixed infrastructure cost. A null or inconclusive result must be
published as such.

The experiment does **not** establish:

- savings for all software, organizations, countries, models or future tasks;
- that all application behavior is expressible;
- that competition, programming languages, companies or developers are waste;
- any economy-wide or “trillions of dollars” estimate;
- historical claims about *Sefer Yetzirah*;
- causality beyond this randomized protocol.

Determinism supports reproducibility. It is not, by itself, evidence of lower
cost. Product count supports breadth. It is not, by itself, an economic sample.

## Seal transition

The checked-in contract begins with `status: designed` and explicit
`pending-seal` identities. It must not execute in that state. The lawful next
transition is:

```text
design reviewed
→ pilot completed outside holdout
→ sample size frozen
→ corpus encrypted and committed
→ protocol, grader, prices, models and environments pinned
→ assignment seed committed
→ schema validation passes
→ status: sealed
→ holdout revealed once
→ all preregistered units executed
→ complete evidence published
```

No early success stop is permitted.

## Current executable boundary

The repository currently validates this preregistration deterministically. It
does not yet execute the live experiment. In particular, no audited OUTWARD
boundary currently supplies isolated model runs together with authoritative
provider usage receipts, billing records, process accounting and retry events.

Until that boundary exists and every pending identity is sealed, the only
truthful result is:

```text
experiment-design.valid
economic-result = unknown
```

Synthetic fixtures may test accounting and analysis code, but they are not
economic observations and may never produce `economic-leverage.proven`.

## Public-code duplication pilot

The content-addressed
[`github-duplication-pilot`](artifacts/economics/github-duplication-pilot.json)
measures a deliberately small, non-random projection of twelve pinned public
repositories across calculator, Todo and Pong cohorts. It publishes no copied
source text. It distinguishes exact source-byte recurrence, normalized
Python-AST recurrence and declared dependency recurrence.

These are reuse signals, not interchangeable economic quantities. Exact bytes
provide a lower bound for content-addressable storage reuse inside the measured
projection. Normalized AST identities are a structural proxy, not behavioral
equivalence. Recurrent dependencies show shared infrastructure demand, not
waste. Causal effort, private code, semantic equivalence and worldwide savings
remain `unknown`.

The pinned pilot currently observes 180 Python source files (990,448 bytes).
Whole-file content addressing saves 0 nonempty source bytes: its only exact
cross-repository identity is the empty file. At the bounded 12–80-node AST
motif level, however, it finds 93 cross-repository structural groups, 57 of
which cross the calculator/Todo/Pong family boundary, plus three recurrent
dependency identities. This is evidence that reuse opportunities depend on
semantic or structural factoring rather than a naive whole-file cache. It is
not evidence that all 93 structures should be unified or that their historical
development cost was avoidable.

```bash
# deterministic replay from the committed pinned snapshot
python scripts/build_github_duplication_pilot.py

# explicit wet GitHub boundary; refreshes the snapshot at already pinned commits
python scripts/build_github_duplication_pilot.py --acquire
```

## Retrospective evidence already available

The privacy-preserving
[`retrospective-v1`](artifacts/economics/retrospective-v1.json) records the
project's pre-registered-cutoff Codex counters, tool events, Git history,
generated-product inventory and canonical proof outcomes. It excludes raw
conversation content, tool payloads, source patches, personal paths and raw
session identities.

This is real observational evidence of development activity and generated
outcomes. It can measure historical volume, iteration and reuse proxies. It is
not an isolated counterfactual and therefore cannot establish that Unified Code
caused savings. Its output is a pilot and power-analysis input for the sealed
experiment, not a replacement for that experiment.

## Bounded semantic-reuse pilot

The content-addressed
[`semantic-reuse-pilot`](artifacts/economics/semantic-reuse-pilot.json) advances
one coordinate beyond structural similarity. It reads three exact MIT-licensed
calculator implementations at pinned public commits, verifies their source and
selected-AST identities before execution, and runs only the registered valid
bounded-integer multiplication vector. No copied source is published and no
third-party package is installed or loaded.

All three independent public witnesses and two existing generated products—the
bounded-integer expression calculator and costed Todo—return `42` for `7 × 6`.
This proves one narrow reusable behavior coordinate. It does not prove that the
applications share validation, errors, interfaces, complete semantics or
historical cost. Those remain unknown.

```bash
# deterministic replay of committed evidence
python scripts/build_semantic_reuse_pilot.py

# one explicit wet read of the already pinned public commits
python scripts/build_semantic_reuse_pilot.py --acquire
```
