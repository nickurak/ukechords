"""Test the theory_basic module"""

import pytest

from ukechords.theory_basic import get_key_notes, _get_dupe_scales_from_key
from ukechords.theory_basic import note_intervals, sharpify, flatify


def test_sharpify_flatify() -> None:
    """Verify that sharp/flat conversion works"""
    assert sharpify("Bb") == "A#"
    assert sharpify("A#") == "A#"
    assert flatify("A#") == "Bb"
    assert flatify("Bb") == "Bb"

    assert all(x == y for x, y in zip(sharpify(["Bb", "A#"]), ["A#", "A#"]))
    assert all(x == y for x, y in zip(flatify(["Bb", "A#"]), ["Bb", "Bb"]))


def test_scale() -> None:
    """Verify that 2 keys with the same notes are identified as related"""
    key1 = "C"
    key2 = "Am"

    notes1 = set(get_key_notes(key1))
    notes2 = set(get_key_notes(key2))
    assert notes1 == notes2
    dupes = _get_dupe_scales_from_key(key1)
    assert "Am" in dupes


def get_weird_offset(note: str) -> int:
    """Determine the interval offset caused by a weird note"""
    match note[1:]:
        case "#":
            return 1
        case "b":
            return -1
        case "##":
            return 2
        case "bb":
            return -2
    assert not "invalid weird note"
    return 0


weird_notes = ["B#", "Cb", "E#", "Fb"]
weird_notes += ["A##", "C##", "D##", "F##", "G##"]
weird_notes += ["Abb", "Bbb", "Cbb", "Dbb", "Ebb", "Fbb", "Gbb"]


@pytest.mark.parametrize("weird_note", weird_notes)
def test_weird_flat_sharps(weird_note: str) -> None:
    """Test that B#/Cb/E#/Fb notes are correctly identified"""
    diff = get_weird_offset(weird_note)
    assert note_intervals[weird_note] == (note_intervals[weird_note[0]] + diff) % 12
