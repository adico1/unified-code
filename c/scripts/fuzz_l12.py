#!/usr/bin/env python3
"""L12/L13 fuzz: ≥100k deterministic mutations, one C process (verify-batch).

Every real py/C disagreement becomes a permanent regression under tests/regressions/.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unified.machine.opcodes import NAME_TO_BYTE  # noqa: E402
from unified.machine.thing import blank_thing  # noqa: E402
from unified.machine.validate import validate_bytecode  # noqa: E402

CORPUS = CROOT / "tests" / "fuzz_corpus"
REGRESSION = CROOT / "tests" / "regressions"
SEED_BASE = ROOT / "artifacts" / "uem" / "text_stats_v2" / "program.uem"
BATCH = 2000  # cases per C process chunk (still one process reused via pipe)


def encode_simple(instrs: list[tuple[str, str | None]], image: dict) -> bytes:
    from unified.machine.bytecode import encode_program

    t = encode_program(blank_thing({"instructions": tuple(instrs), "image": image}))
    raw = t.get("value", {}).get("bytecode")
    if not isinstance(raw, (bytes, bytearray)):
        raise RuntimeError("encode failed")
    return bytes(raw)


def structural_program(rng: random.Random) -> bytes:
    ops = list(NAME_TO_BYTE.keys())
    n = rng.randint(1, 12)
    instrs = []
    for _ in range(n - 1):
        name = rng.choice(ops)
        if name == "STOP":
            name = "LOAD"
        if name in {
            "LOAD",
            "APPLY",
            "EMIT",
            "OUTWARD",
            "WRITE",
            "READ",
            "DELETE",
            "ROUTE",
            "MAP",
            "FOLD",
            "VERIFY",
        }:
            instrs.append(
                (name, rng.choice([None, "host_input", "identity", "x", "routes"]))
            )
        else:
            instrs.append((name, None))
    instrs.append(("STOP", None))
    if rng.random() < 0.3:
        instrs = [("APPLY", "identity"), ("STOP", None)]
    image = {"routes": {"e": "identity"}} if rng.random() < 0.5 else {}
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
        b[rng.randrange(12, min(len(b), 40))] = rng.randrange(256)
    elif mode == 6:
        return structural_program(rng)
    else:
        if len(b) > 20:
            i = rng.randrange(12, len(b))
            b[i] = (b[i] + 1) & 0xFF
    return bytes(b)


def py_reject(blob: bytes) -> bool:
    return validate_bytecode(blank_thing({"bytecode": blob})).get("state") == "invalid"


def save_regression(blob: bytes, detail: str) -> Path:
    REGRESSION.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256(blob).hexdigest()[:16]
    path = REGRESSION / f"fuzz_{h}.uem"
    path.write_bytes(blob)
    (REGRESSION / f"fuzz_{h}.txt").write_text(detail + "\n", encoding="utf-8")
    return path


def ensure_binary(uem_c: Path) -> bool:
    if uem_c.is_file():
        return True
    subprocess.run(
        [
            "make",
            "-C",
            str(CROOT),
            "posix",
            "CFLAGS=-std=c99 -Wall -O2 -Iinclude -Ithird_party -Icore -Ihost/mcu",
        ],
        check=False,
        capture_output=True,
    )
    return uem_c.is_file()


def c_batch_verify(uem_c: Path, blobs: list[bytes]) -> list[bool]:
    """Return list of reject-bool (True = C rejected) for each blob. One process."""
    if not blobs:
        return []
    payload = bytearray()
    for b in blobs:
        payload += struct.pack(">I", len(b))
        payload += b
    r = subprocess.run(
        [str(uem_c), "verify-batch"],
        input=bytes(payload),
        capture_output=True,
        timeout=max(30, len(blobs) // 50 + 10),
    )
    out = r.stdout
    if len(out) != len(blobs):
        # Partial or crash — treat missing as reject for remainder only if stderr empty;
        # any shortfall is a harness defect → raise
        raise RuntimeError(
            f"verify-batch length mismatch got={len(out)} want={len(blobs)} "
            f"rc={r.returncode} err={(r.stderr or b'')[:200]!r}"
        )
    return [ch != ord("0") for ch in out]


def main():
    seed = int(os.environ.get("UEM_FUZZ_SEED", "12"))
    n = int(os.environ.get("UEM_FUZZ_N", "100000"))
    rng = random.Random(seed)
    uem_c = Path(os.environ.get("UEM_C", CROOT / "build" / "uem-c"))
    if not ensure_binary(uem_c):
        print("no uem-c", file=sys.stderr)
        return 2

    CORPUS.mkdir(parents=True, exist_ok=True)
    seeds = [SEED_BASE.read_bytes()]
    for p in (ROOT / "artifacts" / "uem").rglob("*.uem"):
        seeds.append(p.read_bytes())
    for i in range(32):
        seeds.append(structural_program(random.Random(seed + i)))
    for i, s in enumerate(seeds):
        (CORPUS / f"seed_{i:04d}.uem").write_bytes(s)

    corpus_files = list(CORPUS.glob("*.uem"))
    corpus_bytes = [p.read_bytes() for p in corpus_files] or [SEED_BASE.read_bytes()]

    fail = 0
    done = 0
    while done < n:
        chunk_n = min(BATCH, n - done)
        blobs = []
        for _ in range(chunk_n):
            base = corpus_bytes[rng.randrange(len(corpus_bytes))]
            blobs.append(mutate(base, rng))
        py_bad = [py_reject(b) for b in blobs]
        try:
            c_bad = c_batch_verify(uem_c, blobs)
        except Exception as exc:
            print("BATCH_FAIL", exc, file=sys.stderr)
            return 2
        for i, blob in enumerate(blobs):
            if py_bad[i] == c_bad[i]:
                continue
            path = save_regression(
                blob, f"i={done + i} disagree py_bad={py_bad[i]} c_bad={c_bad[i]}"
            )
            print("REGRESSION", path, f"py_bad={py_bad[i]} c_bad={c_bad[i]}")
            fail += 1
            if fail >= 50:
                done = n
                break
        done += chunk_n
        if done % 10000 == 0 or done >= n:
            print(f"progress {done}/{n} fail={fail}", flush=True)

    report = {
        "seed": seed,
        "mutations": n,
        "failures": fail,
        "corpus_size": len(corpus_bytes),
        "regressions": len(list(REGRESSION.glob("*.uem"))),
        "mode": "verify-batch",
    }
    print(json.dumps(report))
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
