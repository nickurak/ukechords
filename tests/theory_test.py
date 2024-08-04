# pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring

import pytest

from pychord import Chord, QualityManager

from ukechords.theory import _sharpify, _flatify
from ukechords.theory import _get_chords_by_shape
from ukechords.theory import _ChordCollection, scan_chords
from ukechords.theory import _get_key_notes, _get_dupe_scales_from_key
from ukechords.theory import show_chord, show_chords_by_shape, show_all
from ukechords.theory import _weird_sharp_scale, _weird_flat_scale
from ukechords.theory import add_no5_quality, add_7sus2_quality

from .uketestconfig import uke_config  # pylint: disable=unused-import


def test_sharpify():
    assert _sharpify("Bb") == "A#"
    assert _sharpify("A#") == "A#"
    assert _flatify("A#") == "Bb"
    assert _flatify("Bb") == "Bb"

    assert all(x == y for x, y in zip(_sharpify(["Bb", "A#"]), ["A#", "A#"]))
    assert all(x == y for x, y in zip(_flatify(["Bb", "A#"]), ["Bb", "Bb"]))


def test_force_flat_shape(uke_config):
    uke_config.tuning = ["G", "C", "E"]
    uke_config.force_flat = True
    pshape = [3, 2, 1]
    resp = list(_get_chords_by_shape(uke_config, pshape))
    assert len(resp) == 1
    shape, chords, notes = resp[0]
    assert shape == [3, 2, 1]
    assert chords == ["Bb"]
    assert notes == set(["Bb", "F", "D"])


def test_no_force_flat_shape(uke_config):
    uke_config.tuning = ["G", "C", "E"]
    pshape = [3, 2, 1]
    resp = list(_get_chords_by_shape(uke_config, pshape))
    assert len(resp) == 1
    shape, chords, notes = resp[0]
    assert shape == [3, 2, 1]
    assert chords == ["A#"]
    assert notes == set(["A#", "F", "D"])


def test_basic_scan(uke_config):
    chord_shapes = _ChordCollection()
    scan_chords(uke_config, chord_shapes, max_fret=3)
    assert "C" in chord_shapes
    assert chord_shapes["C"] is not None
    with pytest.raises(KeyError):
        _ = chord_shapes["C9"]
    assert "C" in chord_shapes.keys()


def test_basic_scan_maj(uke_config, mocker):
    uke_config.tuning = ["G", "C", "E", "A"]
    chord_shapes = _ChordCollection()

    def get_cmaj7_shape(*_, **__):
        return [[0, 0, 0, 2]]

    mock_get_shapes = mocker.patch("ukechords.theory._get_shapes", wraps=get_cmaj7_shape)
    scan_chords(uke_config, chord_shapes, max_fret=3)
    mock_get_shapes.assert_called_once()
    assert "Cmaj7" in chord_shapes
    assert chord_shapes["Cmaj7"] is not None


def test_scale():
    key1 = "C"
    key2 = "Am"

    notes1 = set(_get_key_notes(key1))
    notes2 = set(_get_key_notes(key2))
    assert notes1 == notes2
    dupes = _get_dupe_scales_from_key(key1)
    assert "Am" in dupes


def test_show_chord(uke_config):
    uke_config.show_notes = True
    output = show_chord(uke_config, "C#")
    assert {frozenset(shape["chord_names"]) for shape in output["shapes"]} == {frozenset(["C#"])}
    assert len(output["shapes"]) == 2
    first_result = output["shapes"][0]
    assert first_result["chord_names"] == ["C#"]
    assert first_result["shape"] == [1, 1, 1]
    assert output["notes"] == ["C#", "F", "G#"]


def test_show_chordless_shape(uke_config):
    chordless_shape = "x,x,x"
    output = show_chords_by_shape(uke_config, chordless_shape)
    shapes = output["shapes"]
    assert len(shapes) == 1
    only_shape = shapes[0]
    assert only_shape["chords"] == []
    assert only_shape["shape"] == [-1, -1, -1]


def test_list_all(uke_config):
    uke_config.qualities = ["", "m", "7", "dim", "maj", "m7"]
    uke_config.key = "C"
    uke_config.allowed_chords = False
    output = show_all(uke_config)

    c_shapes = [shape for shape in output["shapes"] if "C" in shape["chord_names"]]
    assert len(c_shapes) == 1
    c_shape = c_shapes[0]
    assert c_shape["shape"] == [0, 0, 0]
    assert c_shape["difficulty"] == 0.0


def test_barrable_barred(uke_config):
    data = show_chords_by_shape(uke_config, "1,1,1")
    barre_data = data["barre_data"]
    assert barre_data["barred"]
    assert barre_data["fret"] == 1
    assert barre_data["shape"] == [0, 0, 0]


def test_barrable_unbarred(uke_config):
    data = show_chords_by_shape(uke_config, "1,1,3")
    barre_data = data["barre_data"]
    assert not barre_data["barred"]
    assert barre_data["fret"] == 1
    assert barre_data["shape"] == [0, 0, 2]


def test_slide(uke_config):
    uke_config.tuning = ["C", "G"]
    uke_config.slide = True
    initial_shape = [1, 2]
    slid_chords = list(_get_chords_by_shape(uke_config, initial_shape))
    slid_shapes = [c[0] for c in slid_chords]
    for slid_shape in slid_shapes:
        min_fret = min(slid_shape)
        unslid_shape = [fret + 1 - min_fret if fret > 0 else fret for fret in slid_shape]
        assert unslid_shape == initial_shape
    assert len(slid_shapes) == 12


@pytest.mark.xfail(strict=True)
def test_slide_mute(uke_config):
    uke_config.tuning = ["C", "G", "E"]
    uke_config.slide = True
    initial_shape = [1, 2, -1]
    slid_chords = list(_get_chords_by_shape(uke_config, initial_shape))
    slid_shapes = [c[0] for c in slid_chords]
    for slid_shape in slid_shapes:
        assert slid_shape[2] == -1
        min_fret = min(fret for fret in slid_shape if fret > 0)
        unslid_shape = [fret + 1 - min_fret if fret > 0 else fret for fret in slid_shape]
        assert unslid_shape == initial_shape
    assert len(slid_shapes) == 12


def test_weird_flat_sharps():
    assert _weird_sharp_scale == ["B#", "C#", "D", "D#", "E", "E#", "F#", "G", "G#", "A", "A#", "B"]
    assert _weird_flat_scale == ["C", "Db", "D", "Eb", "Fb", "F", "Gb", "G", "Ab", "A", "Bb", "Cb"]


extra_chords_and_loaders = [
    ("C9no5", add_no5_quality),
    ("C7sus2", add_7sus2_quality),
]
builtin_chords = ["C7"]


def get_missing_chord_params():
    for chord, _ in extra_chords_and_loaders:
        yield chord
    for chord in builtin_chords:
        reason = f"we detected that pychord already has {chord}, as expected"
        yield pytest.param(chord, marks=pytest.mark.xfail(strict=True, reason=reason))


@pytest.mark.parametrize("chord", list(get_missing_chord_params()))
def test_clean_missing_quality(chord):
    QualityManager().load_default_qualities()
    with pytest.raises(ValueError):
        Chord(chord)


@pytest.mark.parametrize("chord,loader", extra_chords_and_loaders)
def test_extra_quality(chord, loader):
    loader()
    Chord(chord)
