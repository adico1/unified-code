from unified import (
    east,
    inward,
    is_thing,
    letter,
    outward,
    verify,
    west,
    world,
)


def test_unknown_absent_false_invalid_are_distinct():
    unknown = inward(None)
    absent = letter(inward(None))
    false = letter(inward(False))
    invalid = verify(east(letter(inward("seed"))))

    assert unknown["state"] == "unknown"
    assert absent["state"] == "absent"
    assert false["state"] == "false"
    assert invalid["state"] == "invalid"

    states = {
        unknown["state"],
        absent["state"],
        false["state"],
        invalid["state"],
    }
    assert states == {"unknown", "absent", "false", "invalid"}


def test_absent_is_not_false():
    absent = letter(inward(None))
    false = letter(inward(False))
    assert absent["state"] == "absent"
    assert false["state"] == "false"
    assert absent["state"] != false["state"]
    assert absent["value"] is None
    assert false["value"] is False


def test_unknown_is_not_false_or_absent():
    unknown = inward("seed")
    assert unknown["state"] == "unknown"
    assert unknown["state"] not in {"false", "absent", "formed", "valid", "invalid"}


def test_verify_does_not_map_unknown_to_false():
    unknown = inward("seed")
    # Incomplete axis without letter classification path through verify:
    # east on a formed letter yields invalid, never false.
    result = verify(east(letter(unknown)))
    assert result["state"] == "invalid"
    assert result["state"] != "false"


def test_incomplete_axis_is_invalid():
    thing = verify(east(letter(inward("seed"))))
    assert thing["state"] == "invalid"


def test_world_preserves_verification():
    thing = world(verify(east(west(letter(inward("seed"))))))
    assert thing["state"] == "invalid"
    assert thing["evidence"][-1] == "world:composed"


def test_outward_records_boundary_without_changing_verdict():
    verified = verify(west(east(letter(inward("seed")))))
    emitted = outward(verified)
    assert is_thing(emitted)
    assert emitted["state"] == verified["state"]
    assert emitted["evidence"][-1] == "boundary:outward"
    assert "boundary:outward" in emitted["evidence"]


def test_inward_always_returns_canonical_thing():
    raw = inward("seed")
    already = inward(raw)
    assert is_thing(raw)
    assert is_thing(already)
    assert raw["state"] == "unknown"
    assert already["state"] == "unknown"
    assert "boundary:inward" in raw["evidence"]
