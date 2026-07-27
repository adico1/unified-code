#!/usr/bin/env python3
"""L12 physical-target conformance report.

A target is supported only when its *native* executable runs the unchanged
golden suite with byte-identical canonical results vs the x86-64 reference.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unified.machine.canonical import (  # noqa: E402
    canonical_bytes,
    from_c_json,
    from_python_run,
)
from unified.machine.compile_decl import compile_declaration_path  # noqa: E402
from unified.machine.host import run_compiled  # noqa: E402
from unified.machine.thing import value_of  # noqa: E402


GOLDENS = [
    ("text_stats_v2", ROOT / "artifacts/uem/text_stats_v2/program.uem",
     ROOT / "examples/declarations/text_stats_v2.json", {"text": "Go go GO"}),
    ("text_stats_empty", ROOT / "artifacts/uem/text_stats_v2/program.uem",
     ROOT / "examples/declarations/text_stats_v2.json", {"text": ""}),
    ("invoice_basic", ROOT / "artifacts/uem/invoice_total/program.uem",
     ROOT / "examples/declarations/invoice_total.json",
     {"document": {
         "tax_rate": "0.10",
         "items": [
             {"description": "a", "quantity": 2, "unit_price": "10.00"},
             {"description": "b", "quantity": 1, "unit_price": "5.50"},
         ],
     }}),
    ("invoice_empty", ROOT / "artifacts/uem/invoice_total/program.uem",
     ROOT / "examples/declarations/invoice_total.json",
     {"document": {"tax_rate": "0.20", "items": []}}),
]

MALFORMED = list((CROOT / "tests/vectors").glob("*.uem"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def suite_sha() -> str:
    h = hashlib.sha256()
    for _, uem, _, host in GOLDENS:
        h.update(uem.read_bytes())
        h.update(json.dumps(host, sort_keys=True, separators=(",", ":")).encode())
    for p in sorted(MALFORMED):
        h.update(p.read_bytes())
    return h.hexdigest()


def run_c(bin_path: Path, uem: Path, host: dict) -> dict | None:
    proc = subprocess.run(
        [str(bin_path), "run", str(uem), "--host", json.dumps(host, separators=(",", ":"))],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if not proc.stdout.strip():
        return None
    line = proc.stdout.strip().splitlines()[-1]
    return from_c_json(json.loads(line))


def ref_python(decl: Path, host: dict) -> dict:
    compiled = compile_declaration_path(str(decl))
    return from_python_run(compiled, run_compiled(compiled, host))


def native_arch() -> str:
    m = platform.machine().lower()
    if m in {"x86_64", "amd64"}:
        return "x86_64"
    if m in {"arm64", "aarch64"}:
        return "arm64"
    if m.startswith("riscv"):
        return "riscv64"
    return m


def build_posix() -> Path:
    subprocess.run(
        ["make", "-C", str(CROOT), "clean"],
        check=False,
        capture_output=True,
    )
    r = subprocess.run(
        ["make", "-C", str(CROOT), "posix",
         "CFLAGS=-std=c99 -Wall -O2 -Iinclude -Ithird_party -Icore -Ihost/mcu"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr or r.stdout)
    return CROOT / "build" / "uem-c"


def evaluate_native(bin_path: Path) -> dict:
    mismatches = 0
    details = []
    times = []
    for name, uem, decl, host in GOLDENS:
        ref = ref_python(decl, host)
        t0 = time.perf_counter_ns()
        got = run_c(bin_path, uem, host)
        t1 = time.perf_counter_ns()
        times.append(t1 - t0)
        if got is None:
            mismatches += 1
            details.append({"case": name, "error": "no-output"})
            continue
        if canonical_bytes(ref) != canonical_bytes(got):
            mismatches += 1
            details.append({"case": name, "error": "canonical-mismatch"})
        # determinism
        got2 = run_c(bin_path, uem, host)
        if got2 is None or canonical_bytes(got) != canonical_bytes(got2):
            mismatches += 1
            details.append({"case": name, "error": "nondeterministic"})
    reject_ok = 0
    for p in MALFORMED:
        r = subprocess.run([str(bin_path), "verify", str(p)], capture_output=True)
        if r.returncode != 0:
            reject_ok += 1
        else:
            mismatches += 1
            details.append({"case": p.name, "error": "accepted-malformed"})
    times_sorted = sorted(times)
    p95 = times_sorted[max(0, int(0.95 * (len(times_sorted) - 1)))] if times_sorted else None
    return {
        "mismatches": mismatches,
        "details": details,
        "malformed_rejected": reject_ok,
        "malformed_total": len(MALFORMED),
        "execution_p95_ns": p95,
        "cases": len(GOLDENS),
    }


def try_compile_only(label: str, cmd: list[str], out: Path) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode == 0 and out.is_file():
            return "compile-only"
        return "unavailable"
    except Exception:
        return "unavailable"


def main():
    arch = native_arch()
    bin_path = build_posix()
    eval_n = evaluate_native(bin_path)
    native_pass = (
        eval_n["mismatches"] == 0
        and eval_n["malformed_rejected"] == eval_n["malformed_total"]
    )

    targets = []
    # Native host
    targets.append({
        "architecture": arch,
        "operating_system": platform.system().lower(),
        "compiler": "cc",
        "compiler_version": subprocess.run(["cc", "--version"], capture_output=True, text=True).stdout.splitlines()[0] if shutil.which("cc") else "unknown",
        "endianness": sys.byteorder,
        "pointer_width": 8 * struct_size(),
        "uem_version": "0.1",
        "registry_version": 1,
        "artifact_sha256": sha256_file(bin_path),
        "golden_suite_sha256": suite_sha(),
        "status": "native-pass" if native_pass else "native-fail",
        "executable_size": bin_path.stat().st_size,
        "execution_p95_ns": eval_n["execution_p95_ns"],
        "canonical_mismatch_count": eval_n["mismatches"],
        "hardware_identity": f"{platform.platform()} machine={platform.machine()} processor={platform.processor()}",
        "note": "Native hardware execution of unchanged goldens.",
    })

    # ARM64
    arm_status = "unavailable"
    arm_note = "No real ARM64 hardware in this environment; compile-only is not support."
    if arch == "arm64":
        arm_status = "native-pass" if native_pass else "native-fail"
        arm_note = "This host IS ARM64; covered by native entry."
    else:
        # compile-only attempt (not support)
        out = CROOT / "build" / "uem-c-arm64-co"
        st = try_compile_only(
            "arm64",
            ["clang", "-std=c99", "-O2", "-Iinclude", "-Ithird_party", "-Icore", "-Ihost/mcu",
             "-target", "arm64-apple-macos",
             "-o", str(out),
             "host/posix/main.c", "core/decode.c", "core/machine.c", "core/primitives.c",
             "core/expr.c", "core/decimal.c", "third_party/cJSON.c", "third_party/sha256.c"],
            out,
        )
        if st == "compile-only":
            arm_status = "compile-only"
    targets.append({
        "architecture": "arm64",
        "status": arm_status,
        "note": arm_note,
        "uem_version": "0.1",
        "registry_version": 1,
        "golden_suite_sha256": suite_sha(),
    })

    # RISC-V
    targets.append({
        "architecture": "riscv64",
        "status": "unavailable",
        "note": "QEMU/compile is not support; requires physical RISC-V golden pass.",
        "uem_version": "0.1",
        "registry_version": 1,
        "golden_suite_sha256": suite_sha(),
    })

    # Wasm
    wasm_status = "unavailable"
    wasm_out = CROOT / "build" / "uem-core.wasm"
    # Prefer wasi if present
    if shutil.which("clang"):
        r = subprocess.run(
            ["clang", "-std=c99", "-O2", "-Iinclude", "-Ithird_party", "-Icore",
             "-DUEM_HOST_WASM", "-target", "wasm32-wasi",
             "-o", str(wasm_out),
             "host/wasm/main.c", "core/decode.c", "core/machine.c", "core/primitives.c",
             "core/expr.c", "core/decimal.c", "third_party/cJSON.c", "third_party/sha256.c"],
            cwd=str(CROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode == 0 and wasm_out.is_file():
            # Need two runtimes running goldens for Wasm-host support — we only have node without wasi runner by default
            wasm_status = "compile-only"
    targets.append({
        "architecture": "wasm32",
        "status": wasm_status,
        "note": "Wasm-host support requires golden pass in ≥2 independent runtimes; not chip support.",
        "uem_version": "0.1",
        "registry_version": 1,
        "golden_suite_sha256": suite_sha(),
    })

    # MCU profile
    mcu_bin = CROOT / "build" / "uem-mcu-demo"
    subprocess.run(
        ["make", "-C", str(CROOT), "mcu",
         "CFLAGS=-std=c99 -Wall -O2 -Iinclude -Ithird_party -Icore -Ihost/mcu"],
        capture_output=True,
    )
    mcu_status = "compile-only" if mcu_bin.is_file() else "unavailable"
    targets.append({
        "architecture": "mcu-profile",
        "profile": "UEM-MCU-1",
        "status": mcu_status,
        "note": "Bounded profile defined; no MCU family claimed without physical board goldens.",
        "uem_version": "0.1",
        "registry_version": 1,
        "golden_suite_sha256": suite_sha(),
    })

    report = {
        "l12": True,
        "reference_architecture": "x86_64",
        "native_architecture": arch,
        "native_evaluation": eval_n,
        "targets": targets,
        "energy_estimate": None,
        "energy_note": "Energy only if physically measured — not estimated.",
    }
    out_dir = CROOT / "targets" / "manifests"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"l12_report_{arch}.json"
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print("wrote", out_path, file=sys.stderr)
    # Exit 0 if native pass (L12 for this machine)
    sys.exit(0 if native_pass else 1)


def struct_size() -> int:
    return 8 if sys.maxsize > 2**32 else 4


if __name__ == "__main__":
    main()
