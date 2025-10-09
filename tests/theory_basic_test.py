"""Test the theory_basic module"""

from ukechords.theory_basic import get_key_notes, _get_dupe_scales_from_key
from ukechords.theory_basic import _weird_sharp_scale, _weird_flat_scale, sharpify, flatify


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


def test_weird_flat_sharps() -> None:
    """Test that B#/Cb/E#/Fb notes are correctly identified"""
    assert _weird_sharp_scale == ["B#", "C#", "D", "D#", "E", "E#", "F#", "G", "G#", "A", "A#", "B"]
    assert _weird_flat_scale == ["C", "Db", "D", "Eb", "Fb", "F", "Gb", "G", "Ab", "A", "Bb", "Cb"]
