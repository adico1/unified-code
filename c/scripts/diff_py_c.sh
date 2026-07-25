#!/usr/bin/env bash
set -euo pipefail
CROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="$(cd "$CROOT/.." && pwd)"
BIN="$CROOT/build/uem-c"
if [[ ! -x "$BIN" ]]; then
  echo "build uem-c first" >&2
  exit 2
fi

fail=0
for g in "$CROOT"/tests/golden/*.json; do
  [[ -f "$g" ]] || continue
  name=$(basename "$g")
  bytecode=$(python3 -c "import json;print(json.load(open('$g'))['bytecode'])")
  host=$(python3 -c "import json;print(json.dumps(json.load(open('$g'))['host'],separators=(',',':')))")
  expect_state=$(python3 -c "import json;print(json.load(open('$g'))['state'])")
  expect_pres=$(python3 -c "import json;d=json.load(open('$g'));print((d.get('presentation') or {}).get('text') or '')")
  bc_path="$ROOT/$bytecode"
  out=$("$BIN" run "$bc_path" --host "$host")
  got_state=$(python3 -c "import json,sys;print(json.load(sys.stdin)['state'])" <<<"$out")
  got_pres=$(python3 -c "import json,sys;d=json.load(sys.stdin);print((d.get('presentation') or {}).get('text') or '')" <<<"$out")
  if [[ "$got_state" != "$expect_state" || "$got_pres" != "$expect_pres" ]]; then
    echo "FAIL $name"
    echo "  expect state=$expect_state pres=$expect_pres"
    echo "  got    state=$got_state pres=$got_pres"
    fail=1
  else
    echo "OK $name state=$got_state"
  fi
done

# malformed vectors
for v in "$CROOT"/tests/vectors/*.uem; do
  [[ -f "$v" ]] || continue
  if "$BIN" verify "$v" >/dev/null 2>&1; then
    echo "FAIL expected reject: $v"
    fail=1
  else
    echo "OK reject $(basename "$v")"
  fi
done

# determinism
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

exit $fail
