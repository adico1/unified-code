# Goals and boundaries

## Main goal

Make a complete application declaration sufficient to produce the exact
runnable product and its evidence through one public operation:

```text
seed authority
→ specification
→ plan
→ specialized source
→ build
→ installation
→ execution
→ verification
```

The seed owns application identity, behavior, validation, state, presentation,
effects, errors and acceptance. Generic compiler machinery owns only reusable
construction operations.

## Current measurable subgoals

- keep application vocabulary out of permanent compiler surfaces;
- generate only selected behavior, with no runtime seed interpreter;
- generate tests and traceability with the application;
- publish atomically and deterministically;
- preserve the six user-facing product families in `build/`;
- resolve qualified identities without guessing or silent versions;
- keep expected invalid outcomes separate from unhandled failures;
- retain Standard Ten and L1–L13 verification;
- preserve independent Python and C UEM hosts;
- reach a complete repository fixed point from `ROOT.seed`.

## Outer boundaries

Outer boundaries connect the generated system to its environment: CLI and GUI
input, files, browser presentation, clocks, persistence, installation,
subprocesses, network protocols, Git hosting and external dependencies. They
must be named, authorized and measured. Effects occur only through INWARD and
OUTWARD boundaries.

## Inner boundaries

Inner boundaries preserve meaning between declaration, canonical
specification, plan, the seven Thing v2 responsibilities, computation core,
result projection, evidence and canonical Thing state. Application behavior
must not be supplied by a renderer, watcher, test or presentation projection.

## Proven boundary

One assembly currently produces 79 products across calculators, Todo, Pong,
document tools, a math library and a development observatory. The catalog and
the original five applications use two generic compiler profiles behind the
same public operation and registry. Application-level convergence is proven;
one root-generated compiler is not.

## Explicitly open

- arbitrary programs and every calculator/Todo/game are not proven;
- GUI coverage is not every browser, native toolkit, mobile device or hardware;
- full repository generation from `ROOT.seed` is not complete;
- deployment, real-time scheduling and temporal-query systems remain separate;
- historical and economic interpretations remain research until independently
  sourced and measured.

Unsupported claims must remain open or emit `standard.gap`; conventional
handwritten fallback is not evidence of seed authority.
