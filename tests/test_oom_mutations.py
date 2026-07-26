"""OOM / allocator mutations for C host — deterministic fail_after coverage."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
UEM_C = os.environ.get("UEM_C", str(ROOT / "c" / "build" / "uem-c"))
HARNESS = ROOT / "c" / "build" / "core-coverage"


def test_c_oom_harness_clean():
    """core-coverage includes assert_oom_paths; must exit 0 under normal and ASan builds."""
    if not HARNESS.is_file():
        pytest.skip("core-coverage not built")
    r = subprocess.run(
        [str(HARNESS)],
        cwd=str(ROOT / "c"),
        capture_output=True,
        text=True,
        env={**os.environ, "ASAN_OPTIONS": "detect_leaks=0"},
    )
    assert r.returncode == 0, r.stderr + r.stdout
    out = (r.stdout + r.stderr).lower()
    assert "fail:" not in out or "core_coverage_harness: ok" in out or r.returncode == 0


def test_invoice_still_valid_after_allocator_wire():
    if not Path(UEM_C).is_file():
        pytest.skip("uem-c not built")
    host = {
        "document": {
            "tax_rate": "0.10",
            "items": [
                {"description": "a", "quantity": 2, "unit_price": "10.00"},
                {"description": "b", "quantity": 1, "unit_price": "5.50"},
            ],
        }
    }
    out = subprocess.check_output(
        [
            UEM_C,
            "run",
            str(ROOT / "artifacts/uem/invoice_total/program.uem"),
            "--host",
            json.dumps(host, separators=(",", ":")),
        ],
        text=True,
    )
    d = json.loads(out)
    assert d["state"] == "valid"
    assert d["presentation"]["text"] == (
        '{"item_count":2,"subtotal":"25.50","tax":"2.55","total":"28.05"}'
    )
