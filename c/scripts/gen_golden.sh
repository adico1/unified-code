#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$CROOT/tests/golden"
mkdir -p "$OUT"
cd "$ROOT"
# Prefer venv python
PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then PY=python3; fi

"$PY" - <<'PY'
import json
from pathlib import Path
from unified.machine.compile_decl import compile_declaration_path
from unified.machine.host import run_compiled
from unified.machine.thing import value_of

root = Path("c/tests/golden")
root.mkdir(parents=True, exist_ok=True)

cases = [
    ("text_stats_v2", "examples/declarations/text_stats_v2.py",
     {"text": "Go go GO"}, "ts_gogo.json"),
    ("text_stats_v2", "examples/declarations/text_stats_v2.py",
     {"text": ""}, "ts_empty.json"),
    ("invoice_total", "examples/declarations/invoice_total.py",
     {"document": {"tax_rate": "0.10", "items": [
         {"description": "a", "quantity": 2, "unit_price": "10.00"},
         {"description": "b", "quantity": 1, "unit_price": "5.50"},
     ]}}, "inv_basic.json"),
    ("invoice_total", "examples/declarations/invoice_total.py",
     {"document": {"tax_rate": "0.20", "items": []}}, "inv_empty_items.json"),
]

for name, decl, host, out_name in cases:
    compiled = compile_declaration_path(decl)
    assert compiled.get("state") != "invalid", compiled.get("evidence")
    result = run_compiled(compiled, host)
    v = value_of(result)
    golden = {
        "case": out_name,
        "declaration": decl,
        "host": host,
        "program_sha256": value_of(compiled).get("program_sha256"),
        "bytecode": f"artifacts/uem/{name}/program.uem",
        "state": result.get("state"),
        "presentation": v.get("presentation"),
        "stats": v.get("stats"),
        "error": v.get("error"),
        "ticket": v.get("ticket"),
        # evidence: keep marks that are semantic (not op: counters)
        "evidence_semantic": [
            e for e in (result.get("evidence") or ())
            if not str(e).startswith("op:")
            and not str(e).startswith("host:")
            and not str(e).startswith("machine:")
            and not str(e).startswith("compile:")
            and not str(e).startswith("validate:")
            and not str(e).startswith("decode:")
            and not str(e).startswith("encode:")
            and not str(e).startswith("load:")
            and not str(e).startswith("boundary:load")
        ],
    }
    path = root / out_name
    path.write_text(json.dumps(golden, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("wrote", path)
PY
