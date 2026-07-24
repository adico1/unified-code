from unified import east, letter, verify, west, world


def test_unknown_is_not_false():
    thing = letter(None)
    assert thing["value"] is None
    assert thing["state"] == "formed"


def test_incomplete_axis_is_invalid():
    thing = verify(east(letter("seed")))
    assert thing["state"] == "invalid"


def test_world_preserves_verification():
    thing = world(verify(east(west(letter("seed")))))
    assert thing["state"] == "invalid"
    assert thing["evidence"][-1] == "world:composed"
