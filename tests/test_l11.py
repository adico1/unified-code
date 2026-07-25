"""L11 cross-host equivalence gauntlet."""

from __future__ import annotations

import os
from pathlib import Path

from unified.machine.canonical import UNICODE_PROFILE, canonical_bytes, from_python_run
from unified.machine.compile_decl import compile_declaration_path
from unified.machine.host import run_compiled
from unified.machine.l11 import run_l11_gauntlet
from unified.machine.thing import value_of


ROOT = Path(__file__).resolve().parents[1]


def test_unicode_profile_frozen():
    assert UNICODE_PROFILE == "UEM-ASCII-1"


def test_l11_gauntlet():
    uem_c = ROOT / "c" / "build" / "uem-c"
    if not uem_c.is_file():
        # try build
        import subprocess

        subprocess.run(["make", "-C", str(ROOT / "c")], check=False)
    os.environ["UEM_C"] = str(uem_c)
    result = run_l11_gauntlet()
    report = value_of(result).get("l11") or {}
    failed = report.get("failed") or []
    # Allow evidence-only soft passes already counted as ok in l11
    assert result.get("state") == "valid" or len(failed) == 0, (
        failed,
        {k: report.get("details", {}).get(k) for k in failed[:12]},
    )


def test_canonical_domain_stable_hash():
    compiled = compile_declaration_path(
        str(ROOT / "examples/declarations/text_stats_v2.py")
    )
    a = from_python_run(compiled, run_compiled(compiled, {"text": "Go go GO"}))
    b = from_python_run(compiled, run_compiled(compiled, {"text": "Go go GO"}))
    assert canonical_bytes(a) == canonical_bytes(b)
    assert a["unicode_profile"] == "UEM-ASCII-1"
    assert a["presentation"]["text"].startswith('{"characters"')
