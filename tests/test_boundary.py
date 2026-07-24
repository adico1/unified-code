"""L7 — visible effect boundaries."""

import unified
from unified import host_render, inward, is_thing, letter, outward, space, verify, world
from unified.__main__ import main


def test_main_returns_outward_marked_thing():
    result = main("seed")
    assert is_thing(result)
    assert "boundary:inward" in result["evidence"]
    assert "boundary:outward" in result["evidence"]
    assert result["state"] == "valid"


def test_main_composition_is_recursive_nesting():
    # main = outward(world(verify(space(letter(inward(...))))))
    result = main("seed")
    assert result["evidence"][0] == "boundary:inward"
    assert "letter:distinguished" in result["evidence"]
    assert "dimension-law:pass" in result["evidence"]
    assert result["evidence"][-2] == "world:composed"
    assert result["evidence"][-1] == "boundary:outward"


def test_outward_does_not_print(capsys):
    thing = verify(space(letter(inward("seed"))))
    outward(thing)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_host_render_is_not_a_kernel_side_effect_on_call_alone(capsys):
    thing = outward(world(verify(space(letter(inward("seed"))))))
    text = host_render(thing)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "boundary:outward" in text
    assert thing["state"] == "valid"


def test_inward_is_only_raw_admission_point():
    assert letter("raw")["state"] == "invalid"
    assert world("raw")["state"] == "invalid"
    assert verify("raw")["state"] == "invalid"
    assert outward("raw")["state"] == "invalid"
    assert is_thing(inward("raw"))
    assert inward("raw")["state"] == "unknown"
