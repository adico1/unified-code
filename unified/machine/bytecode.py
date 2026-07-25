"""Canonical UEM bytecode encode/decode — endian-independent, strict."""

from __future__ import annotations

import hashlib
import json
import struct

from .opcodes import (
    FORMAT_VERSION,
    MAGIC,
    NAME_TO_BYTE,
    OPCODES,
    TAG_NONE,
    TAG_STRING,
)
from .thing import blank_thing, with_evidence, with_state


def _u16(n):
    return struct.pack(">H", n)


def _u32(n):
    return struct.pack(">I", n)


def _read_u16(data, off):
    if off + 2 > len(data):
        raise ValueError("truncated")
    return struct.unpack(">H", data[off : off + 2])[0], off + 2


def _read_u32(data, off):
    if off + 4 > len(data):
        raise ValueError("truncated")
    return struct.unpack(">I", data[off : off + 4])[0], off + 4


def canonical_image_bytes(image):
    if image is None:
        image = {}
    if not isinstance(image, dict):
        raise ValueError("image-not-object")
    text = json.dumps(image, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return text.encode("utf-8")


def encode_program(thing):
    """Thing in: value.instructions + value.image → value.bytecode + identity."""
    value = thing.get("value") if isinstance(thing.get("value"), dict) else {}
    instructions = value.get("instructions") or ()
    image = value.get("image") or {}
    try:
        raw = _encode(instructions, image)
    except (ValueError, TypeError, KeyError) as exc:
        return with_state(
            with_evidence(thing, f"encode:fail:{exc}"),
            "invalid",
        )
    identity = hashlib.sha256(raw).hexdigest()
    return {
        **thing,
        "value": {
            **value,
            "bytecode": raw,
            "program_sha256": identity,
            "bytecode_size": len(raw),
        },
        "evidence": (*tuple(thing.get("evidence") or ()), "encode:ok", f"id:{identity[:16]}"),
        "state": "formed",
    }


def _encode(instructions, image):
    out = bytearray()
    out += MAGIC
    out += _u16(FORMAT_VERSION)
    out += _u16(0)  # flags
    out += _u32(len(instructions))
    for item in instructions:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("bad-instruction")
        name, operand = item[0], item[1]
        if name not in NAME_TO_BYTE:
            raise ValueError(f"unknown-opcode-name:{name}")
        out.append(NAME_TO_BYTE[name])
        if operand is None:
            out.append(TAG_NONE)
        else:
            if not isinstance(operand, str):
                raise ValueError("operand-not-string")
            raw = operand.encode("utf-8")
            out.append(TAG_STRING)
            out += _u32(len(raw))
            out += raw
    img = canonical_image_bytes(image)
    out += _u32(len(img))
    out += img
    return bytes(out)


def decode_program(thing):
    """Thing in: value.bytecode → instructions + image; rejects noncanonical."""
    value = thing.get("value") if isinstance(thing.get("value"), dict) else {}
    raw = value.get("bytecode")
    if not isinstance(raw, (bytes, bytearray)):
        return with_state(with_evidence(thing, "decode:missing-bytecode"), "invalid")
    try:
        instructions, image, identity = _decode(bytes(raw))
    except ValueError as exc:
        return with_state(
            with_evidence(blank_thing(value), f"decode:reject:{exc}"),
            "invalid",
        )
    return {
        **thing,
        "value": {
            **value,
            "instructions": instructions,
            "image": image,
            "program_sha256": identity,
            "bytecode": bytes(raw),
            "bytecode_size": len(raw),
        },
        "evidence": (*tuple(thing.get("evidence") or ()), "decode:ok"),
        "state": "formed",
    }


def _decode(data):
    if len(data) < 12:
        raise ValueError("truncated")
    if data[0:4] != MAGIC:
        raise ValueError("bad-magic")
    version, off = _read_u16(data, 4)
    if version != FORMAT_VERSION:
        raise ValueError("bad-version")
    flags, off = _read_u16(data, off)
    if flags != 0:
        raise ValueError("bad-flags")
    count, off = _read_u32(data, off)
    instructions = []
    index = 0
    while index < count:
        if off >= len(data):
            raise ValueError("truncated")
        code = data[off]
        off += 1
        if code not in OPCODES:
            raise ValueError(f"unknown-opcode:{code}")
        if off >= len(data):
            raise ValueError("truncated")
        tag = data[off]
        off += 1
        operand = None
        if tag == TAG_NONE:
            pass
        elif tag == TAG_STRING:
            length, off = _read_u32(data, off)
            if off + length > len(data):
                raise ValueError("truncated")
            chunk = data[off : off + length]
            off += length
            try:
                operand = chunk.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError("invalid-utf8") from exc
            # Well-formed UTF-8 (RFC 3629) round-trips through encode; no extra check.
        else:
            raise ValueError("bad-tag")
        instructions.append((OPCODES[code], operand))
        index += 1
    img_len, off = _read_u32(data, off)
    if off + img_len > len(data):
        raise ValueError("truncated")
    img_bytes = data[off : off + img_len]
    off += img_len
    if off != len(data):
        raise ValueError("trailing-bytes")
    try:
        img_text = img_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("invalid-utf8-image") from exc
    try:
        image = json.loads(img_text)
    except json.JSONDecodeError as exc:
        raise ValueError("bad-image-json") from exc
    if not isinstance(image, dict):
        raise ValueError("image-not-object")
    # noncanonical image: re-encode must match exactly
    canon = canonical_image_bytes(image)
    if canon != img_bytes:
        raise ValueError("noncanonical-image")
    # full re-encode must match (canonical program)
    rebuilt = _encode(tuple(instructions), image)
    if rebuilt != data:
        raise ValueError("noncanonical-encoding")
    identity = hashlib.sha256(data).hexdigest()
    return tuple(instructions), image, identity


def program_identity(thing):
    """Attach or recompute SHA-256 of bytecode."""
    value = thing.get("value") if isinstance(thing.get("value"), dict) else {}
    raw = value.get("bytecode")
    if not isinstance(raw, (bytes, bytearray)):
        return with_state(with_evidence(thing, "identity:missing"), "invalid")
    identity = hashlib.sha256(bytes(raw)).hexdigest()
    return {
        **thing,
        "value": {**value, "program_sha256": identity},
        "evidence": (*tuple(thing.get("evidence") or ()), f"id:{identity[:16]}"),
        "state": thing.get("state", "formed"),
    }
