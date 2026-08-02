# Unified Application Preprocessor

Status: bounded vertical proof.

The preprocessor is a request-adapter boundary in front of the existing
canonical JSON declaration compiler and UEM-16. It is not a second application
language or a second generator.

```text
JSON request or restricted Python literal
→ one canonical JSON declaration
→ existing declaration normalization
→ existing UEM compiler
→ existing UEM host
→ deterministic result
```

The Python adapter accepts exactly one assignment named `STANDARD_TEN`. Its
value is parsed with `ast.literal_eval`; the module is never imported, compiled
or executed. Application behavior still comes exclusively from the referenced
JSON declaration.

## Commands

```bash
uc run examples/run/invoice-total.request.json
uc run examples/run/invoice-total.request.py
uc run examples/run/invoice-total.request.json --materialize build/invoice-run
```

Ordinary execution writes no generated application. Explicit materialization
retains only the exact UEM program, symbolic image and content-addressed
manifest. Both adapters must produce the same canonical declaration hash, UEM
program hash, execution identity and runtime result.

## Boundaries

- JSON remains the sole authoritative application declaration.
- Request adapters select authority and provide host input; they cannot define
  application behavior.
- Materialization is explicit and atomic; ordinary execution is ephemeral.
- User state, local/remote cache resolution and checkpoint/resume are not
  implemented by this proof.
- This does not prove arbitrary source-language translation or applications.
