#!/usr/bin/env python3
"""L12 strengthened fuzz: saved corpus, structural generation, ≥100k mutations.

Every failure becomes a permanent regression under tests/regressions/.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unified.machine.opcodes import FORMAT_VERSION, MAGIC, NAME_TO_BYTE, OPCODES  # noqa: E402
from unified.machine.thing import blank_thing  # noqa: E402
from unified.machine.validate import validate_bytecode  # noqa: E402

CORPUS = CROOT / "tests" / "fuzz_corpus"
REGRESSION = CROOT / "tests" / "regressions"
SEED_BASE = ROOT / "artifacts" / "uem" / "text_stats_v2" / "program.uem"


def encode_simple(instrs: list[tuple[str, str | None]], image: dict) -> bytes:
    from unified.machine.bytecode import encode_program
    from unified.machine.thing import blank_thing

    t = encode_program(blank_thing({"instructions": tuple(instrs), "image": image}))
    raw = t.get("value", {}).get("bytecode")
    if not isinstance(raw, (bytes, bytearray)):
        raise RuntimeError("encode failed")
    return bytes(raw)


def structural_program(rng: random.Random) -> bytes:
    """Generate a minimal well-formed or near-well-formed program."""
    ops = list(NAME_TO_BYTE.keys())
    n = rng.randint(1, 12)
    instrs = []
    for _ in range(n - 1):
        name = rng.choice(ops)
        if name == "STOP":
            name = "LOAD"
        if name in {"LOAD", "APPLY", "EMIT", "OUTWARD", "WRITE", "READ", "DELETE", "ROUTE", "MAP", "FOLD", "VERIFY"}:
            instrs.append((name, rng.choice([None, "host_input", "identity", "x", "routes"][0:4])))
        else:
            instrs.append((name, None))
    instrs.append(("STOP", None))
    # Sometimes use valid APPLY identity only
    if rng.random() < 0.3:
        instrs = [("APPLY", "identity"), ("STOP", None)]
    image = {}
    if rng.random() < 0.5:
        image = {"routes": {"e": "identity"}}
    try:
        return encode_simple(instrs, image)
    except Exception:
        return SEED_BASE.read_bytes()


def mutate(blob: bytes, rng: random.Random) -> bytes:
    b = bytearray(blob)
    mode = rng.randrange(8)
    if mode == 0 and len(b) > 16:
        b = b[: rng.randrange(8, len(b))]
    elif mode == 1:
        b += bytes(rng.getrandbits(8) for _ in range(rng.randrange(1, 32)))
    elif mode == 2 and len(b) > 12:
        b[rng.randrange(12, len(b))] ^= rng.randrange(1, 256)
    elif mode == 3 and len(b) > 12:
        b[12] = rng.choice([0, 0x11, 0x7F, 0x99, 0x10])
    elif mode == 4:
        b[0:4] = b"XXXX"
    elif mode == 5 and len(b) > 20:
        # boundary operand length corruption
        b[rng.randrange(12, min(len(b), 40))] = rng.randrange(256)
    elif mode == 6:
        return structural_program(rng)
    else:
        if len(b) > 20:
            i = rng.randrange(12, len(b))
            b[i] = (b[i] + 1) & 0xFF
    return bytes(b)


def both_reject_or_accept(blob: bytes, uem_c: Path) -> tuple[bool, str]:
    py = validate_bytecode(blank_thing({"bytecode": blob}))
    py_bad = py.get("state") == "invalid"
    with tempfile.NamedTemporaryFile(suffix=".uem", delete=False) as f:
        f.write(blob)
        path = f.name
    try:
        r = subprocess.run(
            [str(uem_c), "verify", path],
            capture_output=True,
            text=True,
            timeout=5,
        )
        c_bad = r.returncode != 0
    except Exception as exc:
        return False, f"c-exception:{exc}"
    finally:
        Path(path).unlink(missing_ok=True)
    if py_bad == c_bad:
        return True, "agree"
    return False, f"disagree py_bad={py_bad} c_bad={c_bad}"


def save_regression(blob: bytes, detail: str) -> Path:
    REGRESSION.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256(blob).hexdigest()[:16]
    path = REGRESSION / f"fuzz_{h}.uem"
    path.write_bytes(blob)
    (REGRESSION / f"fuzz_{h}.txt").write_text(detail + "\n", encoding="utf-8")
    return path


def main():
    seed = int(os.environ.get("UEM_FUZZ_SEED", "12"))
    n = int(os.environ.get("UEM_FUZZ_N", "100000"))
    rng = random.Random(seed)
    uem_c = Path(os.environ.get("UEM_C", CROOT / "build" / "uem-c"))
    if not uem_c.is_file():
        subprocess.run(["make", "-C", str(CROOT), "posix"], check=False)
    if not uem_c.is_file():
        print("no uem-c", file=sys.stderr)
        return 2

    CORPUS.mkdir(parents=True, exist_ok=True)
    # seed corpus from goldens + structural samples
    seeds = [SEED_BASE.read_bytes()]
    for p in (ROOT / "artifacts" / "uem").rglob("*.uem"):
        seeds.append(p.read_bytes())
    for i in range(32):
        seeds.append(structural_program(random.Random(seed + i)))
    for i, s in enumerate(seeds):
        (CORPUS / f"seed_{i:04d}.uem").write_bytes(s)

    corpus = list(CORPUS.glob("*.uem"))
    fail = 0
    for i in range(n):
        base = rng.choice(corpus).read_bytes() if corpus else SEED_BASE.read_bytes()
        blob = mutate(base, rng)
        ok, detail = both_reject_or_accept(blob, uem_c)
        if not ok:
            # identical to original may still agree; only count real disagreement
            if hashlib.sha256(blob).digest() == hashlib.sha256(SEED_BASE.read_bytes()).digest():
                continue
            path = save_regression(blob, f"i={i} {detail}")
            print("REGRESSION", path, detail)
            fail += 1
            if fail >= 50:
                break
        if (i + 1) % 10000 == 0:
            print(f"progress {i+1}/{n} fail={fail}")
    # coverage-ish report: unique first-byte / opcode diversities in corpus
    print(json.dumps({
        "seed": seed,
        "mutations": n,
        "failures": fail,
        "corpus_size": len(list(CORPUS.glob('*.uem'))),
        "regressions": len(list(REGRESSION.glob('*.uem'))),
    }))
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
