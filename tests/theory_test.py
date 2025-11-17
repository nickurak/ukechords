"""Test the theory module"""

from typing import Any
from collections.abc import Callable, Iterable

import pytest
from pytest_mock import MockFixture

from pychord import Chord, QualityManager

from ukechords.theory import _scan_chords, show_chords_by_notes
from ukechords.theory import show_chord, show_chords_by_shape, show_all
from ukechords.theory import add_no5_quality, add_7sus2_quality
from ukechords.theory import show_key, lookup_tuning

from ukechords.theory_basic import ChordCollection

from ukechords.errors import UnslidableEmptyShapeException, ChordNotFoundException

from ukechords.config import UkeConfig
from .uketestconfig import uke_config
from .fake_pool import fake_pool  # pylint: disable=unused-import


def test_force_flat_asharpsus2(uke_config: UkeConfig) -> None:
    """Regression test, confirm that forcing A#sus2 can be  forced into a flat"""
    uke_config.tuning = ("G", "C", "E")
    uke_config.force_flat = True
    pshape = ("3", "0", "1")
    shapes = show_chords_by_shape(uke_config, pshape)["shapes"]
    assert len(shapes) == 1
    shape = shapes[0]["shape"]
    chords = shapes[0]["chords"]
    notes = set(shapes[0]["notes"])
    assert shape == (3, 0, 1)
    assert chords == ["Fsus4", "Bbsus2"]
    assert notes == {"Bb", "F", "C"}


def test_force_flat_shape(uke_config: UkeConfig) -> None:
    """Verify that forcing a flat on chords discovered by a specifid shape works"""
    uke_config.tuning = ("G", "C", "E")
    uke_config.force_flat = True
    pshape = ("3", "2", "1")
    shapes = show_chords_by_shape(uke_config, pshape)["shapes"]
    shape = shapes[0]["shape"]
    chords = shapes[0]["chords"]
    notes = set(shapes[0]["notes"])
    assert shape == (3, 2, 1)
    assert chords == ["Bb"]
    assert notes == {"Bb", "F", "D"}


def test_no_force_flat_shape(uke_config: UkeConfig) -> None:
    """Verify that returning chords from a shape returns a sharp option"""
    uke_config.tuning = ("G", "C", "E")
    pshape = ("3", "2", "1")
    shapes = show_chords_by_shape(uke_config, pshape)["shapes"]
    assert len(shapes) == 1
    shape = shapes[0]["shape"]
    chords = shapes[0]["chords"]
    notes = set(shapes[0]["notes"])
    assert shape == (3, 2, 1)
    assert chords == ["A#"]
    assert notes == {"A#", "F", "D"}


def test_basic_scan(uke_config: UkeConfig) -> None:
    """Verify the ability to scan for shapes"""
    uke_config.tuning = ("G", "C", "E", "A")
    chord_shapes = ChordCollection()
    _scan_chords(uke_config, chord_shapes, max_fret=3)
    assert "C" in chord_shapes
    assert "Cmaj7" in chord_shapes
    with pytest.raises(KeyError):
        _ = chord_shapes["C9"]


def test_threaded_scan_exception(uke_config: UkeConfig, mocker: MockFixture) -> None:
    """Verify that an exception raised from a threaded scan triggers termination of the pool"""
    mocker.patch("ukechords.theory._get_chord_shapes_map", side_effect=ValueError())
    mocked_pool_terminate = mocker.patch("tests.fake_pool.FakePool.terminate")
    chord_shapes = ChordCollection()
    with pytest.raises(ValueError):
        _scan_chords(uke_config, chord_shapes, max_fret=3)
    mocked_pool_terminate.assert_called_once()


def test_show_chord(uke_config: UkeConfig) -> None:
    """Verify that looking up a chord by its name works"""
    uke_config.show_notes = True
    output = show_chord(uke_config, "C#")
    assert {frozenset(shape["chord_names"]) for shape in output["shapes"]} == {frozenset(["C#"])}
    assert len(output["shapes"]) == 2
    first_result = output["shapes"][0]
    assert first_result["chord_names"] == ["C#"]
    assert first_result["shape"] == (1, 1, 1)
    assert output["notes"] == ("C#", "F", "G#")


def test_show_chord_by_sharp_notes(uke_config: UkeConfig) -> None:
    """Verify that looking up a chord by sharp notes works"""
    output = show_chords_by_notes(uke_config, {"C#", "F", "G#"})
    first_result = output["shapes"][0]
    assert first_result["chord_names"] == ["C#"]
    assert first_result["shape"] == (1, 1, 1)
    assert set(output["notes"]) == {"C#", "F", "G#"}


def test_show_chord_by_flat_notes(uke_config: UkeConfig) -> None:
    """Verify that looking up a chord by sharp notes works"""
    output = show_chords_by_notes(uke_config, {"Db", "F", "Ab"})
    first_result = output["shapes"][0]
    assert first_result["chord_names"] == ["Db"]
    assert first_result["shape"] == (1, 1, 1)
    assert set(output["notes"]) == {"Db", "F", "Ab"}


def test_show_chordless_shape(uke_config: UkeConfig) -> None:
    """Verify that an empty shape returns an empty result without crashing"""
    chordless_shape = ("x", "x", "x")
    output = show_chords_by_shape(uke_config, chordless_shape)
    shapes = output["shapes"]
    assert len(shapes) == 1
    only_shape = shapes[0]
    assert only_shape["chords"] == []
    assert only_shape["shape"] == (-1, -1, -1)


def test_list_all(uke_config: UkeConfig) -> None:
    """Verify that listing all chordsmatching a set of qualities works"""
    uke_config.qualities = ["", "m", "7", "dim", "maj", "m7"]
    uke_config.keys = ["C"]
    uke_config.allowed_chords = None
    output = show_all(uke_config)

    c_shapes = [shape for shape in output["shapes"] if "C" in shape["chord_names"]]
    assert len(c_shapes) == 1
    c_shape = c_shapes[0]
    assert c_shape["shape"] == (0, 0, 0)
    assert c_shape["difficulty"] == 0.0


def test_barrable_barred(uke_config: UkeConfig) -> None:
    """Verify that barred chords are detected and suggested"""
    data = show_chords_by_shape(uke_config, ("1", "1", "1"))
    barre_data = data["barre_data"]
    assert barre_data
    assert barre_data["barred"]
    assert barre_data["fret"] == 1
    assert barre_data["shape"] == (0, 0, 0)


def test_barrable_unbarred(uke_config: UkeConfig) -> None:
    """Verify barred options are avaiable even when possible but not recommended"""
    data = show_chords_by_shape(uke_config, ("1", "1", "3"))
    barre_data = data["barre_data"]
    assert barre_data
    assert not barre_data["barred"]
    assert barre_data["fret"] == 1
    assert barre_data["shape"] == (0, 0, 2)


def test_slide(uke_config: UkeConfig) -> None:
    """Verify that sliding a shape works correctly"""
    initial_shape = ("1", "2")
    uke_config.tuning = ("C", "G")
    uke_config.slide = True
    shapes = show_chords_by_shape(uke_config, initial_shape)["shapes"]
    slid_shapes = [c["shape"] for c in shapes]
    for slid_shape in slid_shapes:
        min_fret = min(slid_shape)
        unslid_shape = tuple(fret + 1 - min_fret if fret > 0 else fret for fret in slid_shape)
        assert tuple(str(fret) for fret in unslid_shape) == initial_shape
    assert len(slid_shapes) == 12


def test_empty_slide(uke_config: UkeConfig) -> None:
    """Regression test: verify that sliding an empty shape is prevented"""
    initial_shape = ("0", "0")
    uke_config.tuning = ("C", "G")
    uke_config.slide = True
    with pytest.raises(UnslidableEmptyShapeException):
        list(show_chords_by_shape(uke_config, initial_shape))


def test_slide_mute(uke_config: UkeConfig) -> None:
    """Verify that sliding a shape with a mute works"""
    uke_config.tuning = ("C", "G", "E")
    uke_config.slide = True
    initial_shape = ("1", "2", "x")
    shapes = show_chords_by_shape(uke_config, initial_shape)["shapes"]
    slid_shapes = [c["shape"] for c in shapes]
    for slid_shape in slid_shapes:
        assert slid_shape[2] == -1
        min_fret = min(fret for fret in slid_shape if fret > 0)
        unslid_shape = tuple(fret + 1 - min_fret if fret > 0 else fret for fret in slid_shape)
        assert tuple("x" if fret < 0 else str(fret) for fret in unslid_shape) == initial_shape
    assert len(slid_shapes) == 12


extra_chords_and_loaders = [
    ("C9no5", add_no5_quality),
    ("C7sus2", add_7sus2_quality),
]
builtin_chords = ["C7"]


def get_missing_chord_params() -> Iterable[Any]:
    """Generate inputs for tests that detect missing chords in pychord"""
    for chord, _ in extra_chords_and_loaders:
        yield chord
    for chord in builtin_chords:
        reason = f"we detected that pychord already has {chord}, as expected"
        yield pytest.param(chord, marks=pytest.mark.xfail(strict=True, reason=reason))


@pytest.mark.parametrize("chord", list(get_missing_chord_params()))
def test_clean_missing_quality(chord: str) -> None:
    """
    Verify that chords we don't expect pychord to handle are in
    fact missing.

    This will allow us to detect if pychord learns how to handle
    these, in which case we can remove our custom implementation of
    them.

    Parameters provided by get_missing_chord_params also let us
    confirm that this test correctly does fail (with an xfail) when a
    chord is built-in unexpectedly.
    """
    QualityManager().load_default_qualities()
    with pytest.raises(ValueError):
        Chord(chord)


@pytest.mark.parametrize("chord,loader", extra_chords_and_loaders)
def test_extra_quality(chord: str, loader: Callable[[], None]) -> None:
    """Verify that our new chord qualities can be added to pychord"""
    loader()
    Chord(chord)


def test_show_key_by_notes() -> None:
    """Verify that looking up a key by notes works"""
    data = show_key(None, tuple("C,D,E,F,G,A,B".split(",")))
    assert "Am" in data["other_keys"]


def test_show_key_by_notes_with_partial_match() -> None:
    """Verify that looking up a key by notes works"""
    data = show_key(None, tuple("C,D,E,F,G,A".split(",")))
    assert "Dm" in data["partial_keys"]


def test_show_key_aliases() -> None:
    """Verify that detecting keys with the same notes works"""
    data = show_key(None, "C")
    assert "Am" in data["other_keys"]


def test_get_named_tuning() -> None:
    """Confirm that we can look up a tuning by name"""
    tuning = lookup_tuning("ukulele")
    assert tuning == ("G", "C", "E", "A")


def test_invalid_chord_root() -> None:
    """Confirm that normalizing an invalid chord with a
    ChordCollection raises an error"""
    c = ChordCollection()
    with pytest.raises(ChordNotFoundException):
        c["H"] = None


def test_show_chord_aliases(uke_config: UkeConfig) -> None:
    """Verify that looking up a chord also shows other names with the same notes"""
    output = show_chord(uke_config, "Csus4")
    names = output["shapes"][0]["chord_names"]
    assert "Csus4" in names
    assert "Fsus2" in names


def test_show_unknown_chord(uke_config: UkeConfig) -> None:
    """Verify that looking up an unknown chord raises an appropriate error"""
    with pytest.raises(ChordNotFoundException):
        _ = show_chord(uke_config, "C49")


def test_show_unplayable_chord(uke_config: UkeConfig) -> None:
    """Verify that looking up an unknown chord yields no results"""
    assert len(uke_config.tuning) < 4
    data = show_chord(uke_config, "C9")
    assert not data["shapes"]


def test_allowed_chords(uke_config: UkeConfig) -> None:
    """Verify that listing chords by allowed-chords can add new chords"""
    uke_config.tuning = ("G", "C")

    uke_config.allowed_chords = ["C"]
    c_data = show_all(uke_config)

    uke_config.allowed_chords = ["C"]
    g_data = show_all(uke_config)

    uke_config.allowed_chords = ["C", "G"]
    both_data = show_all(uke_config)

    extra_chord = "E5"

    assert not [shape for shape in c_data["shapes"] if extra_chord in shape["chord_names"]]
    assert not [shape for shape in g_data["shapes"] if extra_chord in shape["chord_names"]]
    assert [shape for shape in both_data["shapes"] if extra_chord in shape["chord_names"]]
