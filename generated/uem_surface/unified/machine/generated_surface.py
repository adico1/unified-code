"""Generated ROOT-authoritative UEM surface. Do not edit."""

SURFACE_VERSION = "UC-UEM-SURFACE-1"
MACHINE = "UEM-16"
FORMAT_VERSION = 1
REGISTRY_VERSION = 2
UNICODE_PROFILE = "UEM-ASCII-1"
MAGIC = b"UEM\x16"
TAG_NONE = 0
TAG_STRING = 1
OPCODES = {
    1: "LOAD",
    2: "READ",
    3: "WRITE",
    4: "DELETE",
    5: "EMIT",
    6: "ENQUEUE",
    7: "DEQUEUE",
    8: "ROUTE",
    9: "APPLY",
    10: "MAP",
    11: "FOLD",
    12: "VERIFY",
    13: "TICKET",
    14: "OUTWARD",
    15: "ACK",
    16: "STOP",
}
PRIMITIVES = (
    "identity",
    "letter",
    "mark_inward",
    "require_source",
    "accept_outward",
    "eval_expression",
    "merge_result",
    "verify_result",
    "present_json",
    "mark_part",
    "state_transition",
)
CANONICAL_RESULT_FIELDS = (
    "canonical_version",
    "registry_version",
    "unicode_profile",
    "program_sha256",
    "state",
    "stop_reason",
    "presentation",
    "stats",
    "error",
    "path",
    "ticket",
    "outward_log",
    "events_emitted",
    "events_dequeued",
    "evidence",
    "limit_hit",
    "steps",
    "instruction_count",
    "reject",
)
DEFAULT_LIMITS = {
    "max_steps": 100_000,
    "max_queue": 10_000,
    "max_depth": 64,
    "max_items": 1_000_000,
    "max_memory": 8_000_000,
    "max_output": 2_000_000,
}
