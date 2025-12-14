"""Test the render module"""

import pytest

from ukechords.cli.render import _get_shape_lines, render_chord_list
from ukechords.cli.render import render_chords_from_shape, render_key
from ukechords.cli.render import _diff_string

from ukechords.cli.render import _csv

from ukechords.types import ChordShapes, ChordsByShape, KeyInfo, BarreData
from ukechords.config import UkeConfig
from ..uketestconfig import uke_config


def _get_capsys_lines(capsys: pytest.CaptureFixture[str]) -> list[str]:
    out, err = capsys.readouterr()
    assert err == ""
    return out.strip("\n").split("\n")


def test_get_shape_lines() -> None:
    """Verify that rendering a shape as a unicode box drawing works"""
    lines = list(_get_shape_lines((-1, 0, 1), 2))
    expected = """
╓─┬─┬─┬──
║●│▒│╷│ 
║ │▒│╵│ 
║⃠ │▒│ │ 
╙─┴─┴─┴──
"""  # noqa
    expected_lines = expected.split("\n")
    expected_lines = expected_lines[1:-1]
    assert len(lines) == len(expected_lines)
    assert expected_lines == lines


def test_render_chord_list(capsys: pytest.CaptureFixture[str], uke_config: UkeConfig) -> None:
    """Verify rendering a list of chords"""
    sl_data: ChordShapes = {
        "shapes": [
            {
                "shape": (1,),
                "difficulty": 15.0,
                "chord_names": ["something"],
                "barre_data": {
                    "barred": False,
                    "barred_difficulty": 32.0,
                    "fret": 4,
                    "shape": (5, 4),
                    "chord": "chord",
                },
            },
            {"shape": (2, 3), "difficulty": 2.0, "chord_names": ["something"], "barre_data": None},
        ]
    }
    render_chord_list(uke_config, sl_data)
    lines = _get_capsys_lines(capsys)
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


def test_render_chords_from_shape(
    capsys: pytest.CaptureFixture[str], uke_config: UkeConfig
) -> None:
    """Verify rendering a list of chords by a requested shape"""
    sl_data: ChordsByShape = {
        "shapes": [{"shape": (1,), "chords": ["c1", "c2"], "notes": ("n1", "n2")}],
        "difficulty": 15.0,
        "barre_data": {
            "barred": False,
            "barred_difficulty": 32.0,
            "fret": 4,
            "shape": (5, 4),
            "chord": "chord",
        },
    }
    render_chords_from_shape(uke_config, sl_data)
    lines = _get_capsys_lines(capsys)
    assert len(lines) == 2
    expected_shapestr = ",".join(map(str, sl_data["shapes"][0]["shape"]))
    expected_chordstr = ",".join(sl_data["shapes"][0]["chords"])
    assert lines[0] == f"{expected_shapestr}: {expected_chordstr}"
    expected_difficulty = sl_data["difficulty"]
    expected_diff_string = _diff_string(expected_difficulty, sl_data["barre_data"])
    assert lines[1] == f"Difficulty: {expected_diff_string}"


def test_render_shape_with_mute(capsys: pytest.CaptureFixture[str], uke_config: UkeConfig) -> None:
    """Verify rendering a shape that includes a muted string works"""
    data: ChordsByShape = {
        "shapes": [
            {"shape": (0, -1), "chords": [], "notes": ("G",)},
        ],
        "difficulty": 1.1,
        "barre_data": None,
    }
    render_chords_from_shape(uke_config, data)
    lines = _get_capsys_lines(capsys)
    shapes_str = lines[0].split(":")[0]
    assert shapes_str == "0,x"


def test_render_key(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify rendering a key"""
    data: KeyInfo = {
        "key": "test_key",
        "other_keys": ["alias1", "alias2"],
        "notes": tuple(f"n{x}" for x in range(0, 10)),
    }
    render_key(None, data)
    lines = _get_capsys_lines(capsys)
    (header, note_str) = lines
    assert header == f"{data['key']} ({','.join(data['other_keys'])}):"
    assert note_str == ",".join(data["notes"])


def test_render_key_from_notes(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify rendering a key from a specified set of notes"""
    data: KeyInfo = {
        "other_keys": ["test_key1", "test_key2"],
        "notes": tuple(f"n{x}" for x in range(0, 10)),
        "partial_keys": ["partial1", "partial2"],
    }
    render_key(None, data)
    lines = _get_capsys_lines(capsys)
    (keys_str, partial_str) = lines
    assert keys_str == ",".join(data["other_keys"])
    assert partial_str == f"Partial match for: {",".join(data["partial_keys"])}"


def test_render_unknown_key_from_notes(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify correct handling of a list  of notes that doesn't match a known key"""
    data: KeyInfo = {
        "other_keys": [],
        "notes": tuple(f"n{x}" for x in range(0, 10)),
        "partial_keys": ["partial1", "partial2"],
    }
    render_key(None, data)
    lines = _get_capsys_lines(capsys)
    (err_msg, partial_str) = lines
    assert err_msg == "No key found"
    assert partial_str == f"Partial match for: {",".join(data["partial_keys"])}"


def test_render_chords_from_shape_with_vis_and_notes(
    capsys: pytest.CaptureFixture[str], uke_config: UkeConfig
) -> None:
    """Verify rendering a shape including its visualization and notes"""
    uke_config.visualize = True
    uke_config.show_notes = True
    data: ChordsByShape = {
        "shapes": [
            {
                "shape": (-1, 0, 1),
                "chords": ["tc1", "tc2"],
                "notes": tuple(f"n{x}" for x in range(0, 10)),
            },
        ],
        "difficulty": 45.6,
        "barre_data": None,
    }
    render_chords_from_shape(uke_config, data)
    lines = _get_capsys_lines(capsys)
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


def test_empty_shape_list(capsys: pytest.CaptureFixture[str], uke_config: UkeConfig) -> None:
    """Verify rendering an empty chord list"""
    data: ChordShapes = {"shapes": []}
    render_chord_list(uke_config, data)
    lines = _get_capsys_lines(capsys)
    assert len(lines) == 1
    assert lines[0] == "No matching shapes found"


def test_empty_shape_list_with_chord(
    capsys: pytest.CaptureFixture[str], uke_config: UkeConfig
) -> None:
    """Verify rendering an empty chord list, in a case where a chord was identified"""
    fake_chord = "SomeChord"
    data: ChordShapes = {"shapes": [], "chord": fake_chord}
    render_chord_list(uke_config, data)
    lines = _get_capsys_lines(capsys)
    assert len(lines) == 1
    assert lines[0] == f'No shape for "{fake_chord}" found'


def test_empty_shape_list_with_notes(
    capsys: pytest.CaptureFixture[str], uke_config: UkeConfig
) -> None:
    """Verify rendering an empty chord list, in a case where notes were specified"""
    notes_str = "A,B,C"
    data: ChordShapes = {"shapes": [], "notes": tuple(notes_str.split(","))}
    render_chord_list(uke_config, data)
    lines = _get_capsys_lines(capsys)
    assert len(lines) == 1
    assert lines[0] == f"No shape for notes {notes_str} found"


def test_plain_barred_shape(uke_config: UkeConfig) -> None:
    """Test that a fully barred shape has no shape on top of the barre"""
    barre_data: BarreData = {
        "fret": 1,
        "barred": True,
        "shape": (0, 0, 0),
        "unbarred_difficulty": 1.0,
        "chord": "C",
    }
    diff_string = _diff_string(0.0, barre_data)
    assert "(barre " in diff_string
    assert ":" not in diff_string


def test_plain_unbarred_option_shape(uke_config: UkeConfig) -> None:
    """Test that a fully shape which could be barred bun isn't recommended is rendered right"""
    barre_data: BarreData = {
        "fret": 1,
        "barred": False,
        "shape": (0, 0, 0),
        "barred_difficulty": 1.0,
        "chord": "Csus4",
    }
    diff_string = _diff_string(0.0, barre_data)
    assert "(else " in diff_string
