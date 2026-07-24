from unified import letter, line, plane, space, verify


def test_one_dimension_has_two_depths():
    thing = verify(line(letter("seed")))
    assert thing["axes"] == (("west", "east"),)
    assert thing["depths"] == ("west", "east")
    assert thing["state"] == "valid"


def test_two_dimensions_have_four_depths():
    thing = verify(plane(letter("seed")))
    assert len(thing["axes"]) == 2
    assert len(thing["depths"]) == 4
    assert thing["state"] == "valid"


def test_three_dimensions_have_six_depths():
    thing = verify(space(letter("seed")))
    assert len(thing["axes"]) == 3
    assert len(thing["depths"]) == 6
    assert thing["state"] == "valid"
