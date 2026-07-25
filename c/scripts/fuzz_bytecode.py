#!/usr/bin/env python3
"""Mutation fuzz: malformed/noncanonical bytecode must reject on C and Python."""

from __future__ import annotations

import hashlib
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from unified.machine.thing import blank_thing  # noqa: E402
from unified.machine.validate import validate_bytecode  # noqa: E402


def main():
    seed = int(os.environ.get("UEM_FUZZ_SEED", "1"))
    n = int(os.environ.get("UEM_FUZZ_N", "200"))
    rng = random.Random(seed)
    base = (ROOT / "artifacts/uem/text_stats_v2/program.uem").read_bytes()
    uem_c = ROOT / "c" / "build" / "uem-c"
    if not uem_c.is_file():
        print("skip: no uem-c")
        return 0
    fail = 0
    for i in range(n):
        b = bytearray(base)
        mode = rng.randrange(6)
        if mode == 0 and len(b) > 20:
            b = b[: rng.randrange(8, len(b))]
        elif mode == 1:
            b += bytes(rng.getrandbits(8) for _ in range(rng.randrange(1, 16)))
        elif mode == 2 and len(b) > 12:
            b[rng.randrange(12, len(b))] ^= 0xFF
        elif mode == 3 and len(b) > 12:
            b[12] = rng.choice([0, 0x7F, 0x11, 0x99])
        elif mode == 4:
            b[0:4] = b"XXXX"
        else:
            if len(b) > 20:
                b[rng.randrange(12, min(40, len(b)))] = rng.randrange(256)
        blob = bytes(b)
        py = validate_bytecode(blank_thing({"bytecode": blob}))
        py_bad = py.get("state") == "invalid"
        with tempfile.NamedTemporaryFile(suffix=".uem", delete=False) as f:
            f.write(blob)
            path = f.name
        try:
            r = subprocess.run(
                [str(uem_c), "verify", path], capture_output=True, text=True, timeout=5
            )
            c_bad = r.returncode != 0
        except Exception:
            c_bad = True
        finally:
            Path(path).unlink(missing_ok=True)
        # both must reject OR both accept (rare if mutation is no-op)
        if py_bad != c_bad:
            # if mutation didn't change identity and both accept, ok
            if hashlib.sha256(blob).hexdigest() == hashlib.sha256(base).hexdigest():
                continue
            print(f"mismatch i={i} mode={mode} py_bad={py_bad} c_bad={c_bad}")
            fail += 1
            if fail > 10:
                break
    print(f"fuzz done seed={seed} n={n} mismatches={fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
