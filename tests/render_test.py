# pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring

from __future__ import annotations
from typing import TYPE_CHECKING

import pytest

from ukechords.render import _get_shape_lines, render_chord_list
from ukechords.render import render_chords_from_shape, render_key
from ukechords.render import _diff_string
from ukechords.errors import ShapeNotFoundException

from ukechords.render import _csv

from .uketestconfig import uke_config

if TYPE_CHECKING:
    from ukechords.config import UkeConfig


def get_capsys_lines(capsys):
    out, err = capsys.readouterr()
    assert err == ""
    return out.strip("\n").split("\n")


def test_get_shape_lines():
    lines = list(_get_shape_lines([-1, 0, 1]))
    expected = """
╓─┬─┬─┬──
║●│ │╷│ 
║ │ │╵│ 
║⃠ │ │ │ 
╙─┴─┴─┴──
"""  # noqa
    expected_lines = expected.split("\n")
    expected_lines = expected_lines[1:-1]
    assert len(lines) == len(expected_lines)
    assert expected_lines == lines


def test_render_chord_list(capsys, uke_config):
    sl_data = {
        "shapes": [
            {
                "shape": [1],
                "difficulty": 15.0,
                "chord_names": ["something"],
                "barre_data": {
                    "barred": False,
                    "barred_difficulty": 32.0,
                    "fret": 4,
                    "shape": [5, 4],
                    "chord": "chord",
                },
            },
            {"shape": [2, 3], "difficulty": 2.0, "chord_names": ["something"], "barre_data": None},
        ]
    }
    render_chord_list(uke_config, sl_data)
    lines = get_capsys_lines(capsys)
    assert len(lines) == len(sl_data["shapes"])
    for shape, line in zip(sl_data["shapes"], lines):
        (chords_c, shape_str, _, diff_desc) = line.split(maxsplit=3)
        assert chords_c.rstrip(":") == _csv(shape["chord_names"])
        assert shape_str == ",".join(map(str, shape["shape"]))
        diff_parts = diff_desc.strip().split(maxsplit=1)
        assert diff_parts[0] == str(shape["difficulty"])
        if shape["barre_data"] is not None:
            expected_diff_desc = _diff_string(shape["difficulty"], shape["barre_data"]).split(
                maxsplit=1
            )[1]
            assert diff_parts[1] == expected_diff_desc


def test_render_chords_from_shape(capsys, uke_config):
    sl_data = {
        "shapes": [{"shape": [1], "chords": ["c1", "c2"], "notes": ["n1", "n2"]}],
        "difficulty": 15.0,
        "barre_data": {
            "barred": False,
            "barred_difficulty": 32.0,
            "fret": 4,
            "shape": [5, 4],
            "chord": "chord",
        },
    }
    render_chords_from_shape(uke_config, sl_data)
    lines = get_capsys_lines(capsys)
    assert len(lines) == 2
    expected_shapestr = ",".join(map(str, sl_data["shapes"][0]["shape"]))
    expected_chordstr = ",".join(sl_data["shapes"][0]["chords"])
    assert lines[0] == f"{expected_shapestr}: {expected_chordstr}"
    expected_difficulty = sl_data["difficulty"]
    expected_diff_string = _diff_string(expected_difficulty, sl_data["barre_data"])
    assert lines[1] == f"Difficulty: {expected_diff_string}"


def test_render_shape_with_mute(capsys, uke_config: UkeConfig) -> None:
    data = {
        "shapes": [
            {"shape": [0, -1], "chords": [], "notes": ["G"]},
        ],
        "difficulty": 1.1,
        "barre_data": None,
    }
    render_chords_from_shape(uke_config, data)
    lines = get_capsys_lines(capsys)
    shapes_str = lines[0].split(":")[0]
    assert shapes_str == "0,x"


def test_render_key(capsys) -> None:
    data = {
        "key": "test_key",
        "other_keys": ["alias1", "alias2"],
        "notes": [f"n{x}" for x in range(0, 10)],
    }
    render_key(None, data)
    lines = get_capsys_lines(capsys)
    (header, note_str) = lines
    assert header == f"{data['key']} ({','.join(data['other_keys'])}):"
    assert note_str == ",".join(data["notes"])


def test_render_key_from_notes(capsys) -> None:
    data = {
        "other_keys": ["test_key1", "test_key2"],
        "notes": [f"n{x}" for x in range(0, 10)],
    }
    render_key(None, data)
    lines = get_capsys_lines(capsys)
    (output,) = lines
    assert output == ",".join(data["other_keys"])


def test_render_unknown_key_from_notes(capsys) -> None:
    data = {
        "other_keys": [],
        "notes": [f"n{x}" for x in range(0, 10)],
    }
    render_key(None, data)
    lines = get_capsys_lines(capsys)
    (err_msg,) = lines
    assert err_msg == "No key found"


def test_render_chords_from_shape_with_vis_and_notes(capsys, uke_config):
    uke_config.visualize = True
    uke_config.show_notes = True
    data = {
        "shapes": [
            {
                "shape": [-1, 0, 1],
                "chords": ["tc1", "tc2"],
                "notes": [f"n{x}" for x in range(0, 10)],
            },
        ],
        "difficulty": 45.6,
        "barre_data": None,
    }
    render_chords_from_shape(uke_config, data)
    lines = get_capsys_lines(capsys)
    notes_line = lines.pop(0)
    difficulty_line = lines.pop()
    shape_chord_line = lines.pop()
    assert notes_line == f"Notes: {', '.join(data['shapes'][0]['notes'])}"
    assert difficulty_line == f"Difficulty: {data['difficulty']}"
    (shape_str, chord_str) = shape_chord_line.split(": ")
    expected_pos_list = ["x" if pos < 0 else str(pos) for pos in data["shapes"][0]["shape"]]
    assert shape_str == ",".join(expected_pos_list)
    assert chord_str == ",".join(data["shapes"][0]["chords"])

    vis_expected = """
╓─┬─┬─┬──
║●│ │╷│ 
║ │ │╵│ 
║⃠ │ │ │ 
╙─┴─┴─┴──
"""  # noqa
    vis_lines = vis_expected.split("\n")
    vis_lines = vis_lines[1:-1]
    assert len(lines) == len(vis_lines)
    assert vis_lines == lines


def test_missing_chord(uke_config: UkeConfig) -> None:
    data = {"chord": "C9", "shapes": []}
    with pytest.raises(ShapeNotFoundException):
        render_chord_list(uke_config, data)


def test_empty_chord_list(capsys, uke_config):
    data = {"shapes": []}
    render_chord_list(uke_config, data)
    lines = get_capsys_lines(capsys)
    assert len(lines) == 1
    assert lines[0] == "No matching chords found"
