from inspect import Parameter, signature

import unified
from unified import is_thing, letter, outward, verify, world


KERNEL_PARTS = (
    unified.letter,
    unified.world,
    unified.beginning,
    unified.end,
    unified.good,
    unified.bad,
    unified.below,
    unified.above,
    unified.west,
    unified.east,
    unified.south,
    unified.north,
    unified.line,
    unified.plane,
    unified.space,
    unified.time,
    unified.value,
    unified.verify,
    unified.inward,
    unified.outward,
)


def test_every_public_operation_has_one_input():
    for operation in KERNEL_PARTS:
        parameters = tuple(signature(operation).parameters.values())
        assert len(parameters) == 1
        assert parameters[0].kind is Parameter.POSITIONAL_OR_KEYWORD


def test_letter_rejects_raw_host_value():
    result = letter("seed")
    assert is_thing(result)
    assert result["state"] == "invalid"
    assert "letter:rejected-non-thing" in result["evidence"]


def test_letter_accepts_canonical_thing():
    admitted = unified.inward("seed")
    result = letter(admitted)
    assert is_thing(result)
    assert result["state"] == "formed"
    assert result["value"] == "seed"
    assert "letter:distinguished" in result["evidence"]


def test_kernel_parts_return_canonical_things():
    seed = unified.inward("seed")
    formed = letter(seed)
    assert is_thing(formed)
    assert is_thing(unified.west(formed))
    assert is_thing(unified.line(formed))
    assert is_thing(verify(unified.line(formed)))
    assert is_thing(world(verify(unified.line(formed))))
    assert is_thing(outward(world(verify(unified.line(formed)))))
