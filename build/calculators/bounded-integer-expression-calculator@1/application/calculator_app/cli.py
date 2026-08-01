"""Generated executable process boundary."""

import argparse
import json
import sys

from .compose import program
from .runtime import ticket_payload


def execute(request, root="."):
    thing = {
        "value": {"outer_input": request, "host": {"root": root}},
        "depths": (), "axes": (), "evidence": (), "state": "formed",
    }
    try:
        result = program(thing)
    except Exception as error:
        return {
            "state": "invalid",
            "output": None,
            "error": "unhandled-failure",
            "evidence": ["ticket.open", "boundary:outward"],
            "ticket": ticket_payload(type(error).__name__),
        }
    value = result.get("value") or {}
    return {
        "state": result.get("state"), "output": value.get("outer_output"),
        "error": value.get("error"), "evidence": list(result.get("evidence") or ()),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(prog='calculator_app')
    parser.add_argument("--request", required=True)
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    try:
        request = json.loads(args.request)
    except ValueError:
        result = {"state": "invalid", "output": None, "error": "invalid-host-json", "evidence": []}
    else:
        result = execute(request, args.root)
    sys.stdout.write(json.dumps(result, separators=(",", ":"), sort_keys=True) + "\n")
    return 0 if result["state"] == "valid" else 1
