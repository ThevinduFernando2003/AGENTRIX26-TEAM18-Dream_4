"""Balanced-brace JSON extraction (replaces the greedy `\\{.*\\}` regex)."""

from __future__ import annotations

from project.agents.jsonutil import extract_first_json


def test_first_balanced_object_ignores_trailing_prose():
    # The old greedy regex matched first-{ to last-} and failed to parse these.
    assert extract_first_json('{"route": "booking"} thanks! }') == {"route": "booking"}
    assert extract_first_json('prefix {"a": {"b": 1}} then } junk') == {"a": {"b": 1}}


def test_brace_inside_string_is_ignored():
    assert extract_first_json('{"msg": "a } brace in text"}') == {"msg": "a } brace in text"}


def test_fenced_json_block():
    assert extract_first_json("```json\n{\"x\": 1}\n```") == {"x": 1}


def test_no_object_returns_none():
    assert extract_first_json("no json here") is None
    assert extract_first_json("") is None
    assert extract_first_json("{ not valid json") is None
