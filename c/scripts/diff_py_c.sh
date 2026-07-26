#!/usr/bin/env bash
# Complete Python/C differential suite against golden cases + reject vectors.
set -euo pipefail
CROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="$(cd "$CROOT/.." && pwd)"
BIN="$CROOT/build/uem-c"
PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then PY=python3; fi
if [[ ! -x "$BIN" ]]; then
  echo "build uem-c first" >&2
  exit 2
fi

fail=0
for g in "$CROOT"/tests/golden/*.json; do
  [[ -f "$g" ]] || continue
  name=$(basename "$g")
  bytecode=$("$PY" -c "import json;print(json.load(open('$g'))['bytecode'])")
  host=$("$PY" -c "import json;print(json.dumps(json.load(open('$g'))['host'],separators=(',',':')))")
  expect_state=$("$PY" -c "import json;print(json.load(open('$g'))['state'])")
  expect_pres=$("$PY" -c "import json;d=json.load(open('$g'));print((d.get('presentation') or {}).get('text') or '')")
  bc_path="$ROOT/$bytecode"
  if [[ ! -f "$bc_path" ]]; then
    echo "FAIL $name missing bytecode $bc_path"
    fail=1
    continue
  fi
  out=$("$BIN" run "$bc_path" --host "$host")
  got_state=$("$PY" -c "import json,sys;print(json.load(sys.stdin)['state'])" <<<"$out")
  got_pres=$("$PY" -c "import json,sys;d=json.load(sys.stdin);print((d.get('presentation') or {}).get('text') or '')" <<<"$out")
  if [[ "$got_state" != "$expect_state" || "$got_pres" != "$expect_pres" ]]; then
    echo "FAIL $name (C vs golden)"
    echo "  expect state=$expect_state pres=$expect_pres"
    echo "  got    state=$got_state pres=$got_pres"
    fail=1
    continue
  fi
  py_out=$("$PY" -c "
import json
from pathlib import Path
from unified.machine.bytecode import decode_program
from unified.machine.host import run_compiled
from unified.machine.thing import value_of
bc = Path(r'''$bc_path''').read_bytes()
host = json.loads(r'''$host''')
thing = decode_program({'value': {'bytecode': bc}, 'evidence': (), 'state': 'blank'})
r = run_compiled(thing, host)
v = value_of(r)
pres = (v.get('presentation') or {}).get('text') or ''
print(json.dumps({'state': r.get('state'), 'text': pres}, separators=(',',':')))
")
  py_state=$("$PY" -c "import json,sys;print(json.load(sys.stdin)['state'])" <<<"$py_out")
  py_pres=$("$PY" -c "import json,sys;print(json.load(sys.stdin)['text'])" <<<"$py_out")
  if [[ "$py_state" != "$got_state" || "$py_pres" != "$got_pres" ]]; then
    echo "FAIL $name (Python vs C)"
    echo "  C  state=$got_state pres=$got_pres"
    echo "  Py state=$py_state pres=$py_pres"
    fail=1
  else
    echo "OK $name state=$got_state py=c"
  fi
done

for v in "$CROOT"/tests/vectors/*.uem; do
  [[ -f "$v" ]] || continue
  if "$BIN" verify "$v" >/dev/null 2>&1; then
    echo "FAIL expected reject: $v"
    fail=1
  else
    echo "OK reject $(basename "$v")"
  fi
done

host='{"text":"Go go GO"}'
bc="$ROOT/artifacts/uem/text_stats_v2/program.uem"
a=$("$BIN" run "$bc" --host "$host")
b=$("$BIN" run "$bc" --host "$host")
if [[ "$a" != "$b" ]]; then
  echo "FAIL nondeterministic"
  fail=1
else
  echo "OK deterministic"
fi

# invoice evidence order
if ! "$PY" -c "
import json, subprocess, sys
bin_path, bc = sys.argv[1], sys.argv[2]
host = {'document': {'tax_rate': '0.0', 'items': []}}
out = subprocess.check_output([bin_path, 'run', bc, '--host', json.dumps(host, separators=(',',':'))], text=True)
d = json.loads(out)
ev = d.get('evidence') or []
# Pipeline order: inward → read_json → letter → eval → verify → present
required = (
    'boundary:inward','boundary:read_json_source','read:ok','letter:distinguished',
    'part:calculate_totals','calculate_totals:ok','script-law:pass','present_result:ok',
)
pos = 0
for mark in required:
    try:
        i = ev.index(mark, pos)
    except ValueError:
        print('FAIL evidence order missing', mark)
        sys.exit(1)
    pos = i + 1
print('OK invoice evidence order')
" "$BIN" "$ROOT/artifacts/uem/invoice_total/program.uem"; then
  fail=1
fi

exit $fail
