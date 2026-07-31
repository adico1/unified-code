# How to read Unified Code

Start with outcomes, then trace one product back to authority.

1. Read [README](../README.md) for status and the runnable commands.
2. Read [Vision](../VISION.md) for direction, then
   [Goals and boundaries](GOALS_AND_BOUNDARIES.md) for the measurable claim.
3. Run the assembly command in [Build output](BUILD_OUTPUT.md).
4. Open `build/index.json`, choose one product, and follow its recorded paths:
   `authority → specification → application → verification → manifest`.
5. Compare two products in one family to see specialization, then compare two
   families to see what the compiler actually reuses.
6. Read `seed/application_suite.json`, the selected application seed and
   `seed/APPLICATION_V3_SCHEMA.json` before reading generator code.
7. Read `unified/generator/assembly.py` for orchestration and the registered
   application-language compiler for the catalog route.
8. Read [Standard Ten](../STANDARD_TEN.md), [Thing v2](../THING_V2.md),
   [Manifestation](../MANIFESTATION.md) and [UEM](../UEM_SPEC.md) for the deeper
   laws.
9. Use tests as executable contracts; use generated evidence as measurements,
   not as authority.

Generated files under `build/` explain an assembly result but are disposable.
Never correct them manually: correct the responsible seed, schema or generic
compiler law and regenerate.
