"""Clock boundary tests (L7 time effect, L9 nanosecond durations)."""

from inspect import Parameter, signature

from unified import LIMIT_NS, clock_end, clock_start, inward, is_thing
from unified.clock import clock_end as clock_end_mod
from unified.clock import clock_start as clock_start_mod


def test_clock_public_operations_have_one_input():
    for operation in (clock_start, clock_end, clock_start_mod, clock_end_mod):
        parameters = tuple(signature(operation).parameters.values())
        assert len(parameters) == 1
        assert parameters[0].kind is Parameter.POSITIONAL_OR_KEYWORD


def test_duration_is_integer_nanoseconds():
    thing = inward({"label": "t", "clock_feed": (100, 350)})
    started = clock_start(thing)
    assert is_thing(started)
    assert started["value"]["clock"]["start_ns"] == 100
    assert started["value"]["clock"]["duration_ns"] is None
    ended = clock_end(started)
    assert is_thing(ended)
    duration = ended["value"]["clock"]["duration_ns"]
    assert isinstance(duration, int)
    assert not isinstance(duration, bool)
    assert duration == 250
    assert ended["value"]["clock"]["status"] == "complete"
    assert "clock:duration_ns:250" in ended["evidence"]


def test_unknown_clock_is_not_false_or_valid():
    thing = inward({"clock_feed": None})
    started = clock_start(thing)
    assert started["state"] == "unknown"
    assert started["state"] not in {"false", "valid"}


def test_absent_clock_feed_is_absent():
    thing = inward({"clock_feed": ()})
    started = clock_start(thing)
    assert started["state"] == "absent"
    assert started["state"] != "false"


def test_false_clock_feed_is_false():
    thing = inward({"clock_feed": False})
    started = clock_start(thing)
    assert started["state"] == "false"


def test_clock_end_without_start_is_absent():
    thing = inward({"label": "no-start"})
    ended = clock_end(thing)
    assert ended["state"] == "absent"
    assert "clock:absent-start" in ended["evidence"]


def test_limit_ns_is_one_second():
    assert LIMIT_NS == 1_000_000_000
