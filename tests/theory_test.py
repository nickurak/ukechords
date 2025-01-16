# pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring

from __future__ import annotations
from typing import TYPE_CHECKING, Generator, Any, Callable

import pytest
from pychord import Chord, QualityManager

from ukechords.theory import _sharpify, _flatify
from ukechords.theory import _get_chords_by_shape
from ukechords.theory import _ChordCollection, _scan_chords
from ukechords.theory import _get_key_notes, _get_dupe_scales_from_key
from ukechords.theory import show_chord, show_chords_by_shape, show_all
from ukechords.theory import _weird_sharp_scale, _weird_flat_scale
from ukechords.theory import add_no5_quality, add_7sus2_quality
from ukechords.theory import show_key

from .uketestconfig import uke_config

if TYPE_CHECKING:
    from ukechords.config import UkeConfig


def test_sharpify() -> None:
    assert _sharpify("Bb") == "A#"
    assert _sharpify("A#") == "A#"
    assert _flatify("A#") == "Bb"
    assert _flatify("Bb") == "Bb"

    assert all(x == y for x, y in zip(_sharpify(["Bb", "A#"]), ["A#", "A#"]))
    assert all(x == y for x, y in zip(_flatify(["Bb", "A#"]), ["Bb", "Bb"]))


@pytest.mark.xfail(strict=True)
def test_force_flat_bbsus2(uke_config: UkeConfig) -> None:
    uke_config.tuning = ("G", "C", "E")
    uke_config.force_flat = True
    pshape = (3, 0, 1)
    resp = list(_get_chords_by_shape(uke_config, pshape))
    assert len(resp) == 1
    shape, chords, notes = resp[0]
    assert shape == (3, 2, 1)
    assert chords == ["Bb"]
    assert notes == set(["Bb", "F", "D"])


def test_force_flat_shape(uke_config: UkeConfig) -> None:
    uke_config.tuning = ("G", "C", "E")
    uke_config.force_flat = True
    pshape = (3, 2, 1)
    resp = list(_get_chords_by_shape(uke_config, pshape))
    assert len(resp) == 1
    shape, chords, notes = resp[0]
    assert shape == (3, 2, 1)
    assert chords == ["Bb"]
    assert notes == set(["Bb", "F", "D"])


def test_no_force_flat_shape(uke_config: UkeConfig) -> None:
    uke_config.tuning = ("G", "C", "E")
    pshape = (3, 2, 1)
    resp = list(_get_chords_by_shape(uke_config, pshape))
    assert len(resp) == 1
    shape, chords, notes = resp[0]
    assert shape == (3, 2, 1)
    assert chords == ["A#"]
    assert notes == set(["A#", "F", "D"])


def test_basic_scan(uke_config: UkeConfig) -> None:
    uke_config.tuning = ("G", "C", "E", "A")
    chord_shapes = _ChordCollection()
    _scan_chords(uke_config, chord_shapes, max_fret=3)
    assert "C" in chord_shapes
    assert "Cmaj7" in chord_shapes
    with pytest.raises(KeyError):
        _ = chord_shapes["C9"]


def test_scale() -> None:
    key1 = "C"
    key2 = "Am"

    notes1 = set(_get_key_notes(key1))
    notes2 = set(_get_key_notes(key2))
    assert notes1 == notes2
    dupes = _get_dupe_scales_from_key(key1)
    assert "Am" in dupes


def test_show_chord(uke_config: UkeConfig) -> None:
    uke_config.show_notes = True
    output = show_chord(uke_config, "C#")
    assert {frozenset(shape["chord_names"]) for shape in output["shapes"]} == {frozenset(["C#"])}
    assert len(output["shapes"]) == 2
    first_result = output["shapes"][0]
    assert first_result["chord_names"] == ["C#"]
    assert first_result["shape"] == (1, 1, 1)
    assert output["notes"] == ["C#", "F", "G#"]


def test_show_chordless_shape(uke_config: UkeConfig) -> None:
    chordless_shape = "x,x,x"
    output = show_chords_by_shape(uke_config, chordless_shape)
    shapes = output["shapes"]
    assert len(shapes) == 1
    only_shape = shapes[0]
    assert only_shape["chords"] == []
    assert only_shape["shape"] == (-1, -1, -1)


def test_list_all(uke_config: UkeConfig) -> None:
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
    data = show_chords_by_shape(uke_config, "1,1,1")
    barre_data = data["barre_data"]
    assert barre_data
    assert barre_data["barred"]
    assert barre_data["fret"] == 1
    assert barre_data["shape"] == (0, 0, 0)


def test_barrable_unbarred(uke_config: UkeConfig) -> None:
    data = show_chords_by_shape(uke_config, "1,1,3")
    barre_data = data["barre_data"]
    assert barre_data
    assert not barre_data["barred"]
    assert barre_data["fret"] == 1
    assert barre_data["shape"] == (0, 0, 2)


@pytest.mark.parametrize(
    "tuning,initial_shape",
    [
        (("C", "G"), (1, 2)),
        pytest.param(
            ("C", "G"),
            (0, 0),
            marks=pytest.mark.xfail(strict=True, reason="buggy handling of sliding empty shapes"),
        ),
    ],
)
def test_slide(
    uke_config: UkeConfig, tuning: tuple[str, ...], initial_shape: tuple[int, ...]
) -> None:
    uke_config.tuning = tuning
    uke_config.slide = True
    slid_chords = list(_get_chords_by_shape(uke_config, initial_shape))
    slid_shapes = [c[0] for c in slid_chords]
    for slid_shape in slid_shapes:
        min_fret = min(slid_shape)
        unslid_shape = tuple(fret + 1 - min_fret if fret > 0 else fret for fret in slid_shape)
        assert unslid_shape == initial_shape
    assert len(slid_shapes) == 12


def test_slide_mute(uke_config: UkeConfig) -> None:
    uke_config.tuning = ("C", "G", "E")
    uke_config.slide = True
    initial_shape = (1, 2, -1)
    slid_chords = list(_get_chords_by_shape(uke_config, initial_shape))
    slid_shapes = [c[0] for c in slid_chords]
    for slid_shape in slid_shapes:
        assert slid_shape[2] == -1
        min_fret = min(fret for fret in slid_shape if fret > 0)
        unslid_shape = tuple(fret + 1 - min_fret if fret > 0 else fret for fret in slid_shape)
        assert unslid_shape == initial_shape
    assert len(slid_shapes) == 12


def test_weird_flat_sharps() -> None:
    assert _weird_sharp_scale == ["B#", "C#", "D", "D#", "E", "E#", "F#", "G", "G#", "A", "A#", "B"]
    assert _weird_flat_scale == ["C", "Db", "D", "Eb", "Fb", "F", "Gb", "G", "Ab", "A", "Bb", "Cb"]


extra_chords_and_loaders = [
    ("C9no5", add_no5_quality),
    ("C7sus2", add_7sus2_quality),
]
builtin_chords = ["C7"]


def get_missing_chord_params() -> Generator[Any, None, None]:
    for chord, _ in extra_chords_and_loaders:
        yield chord
    for chord in builtin_chords:
        reason = f"we detected that pychord already has {chord}, as expected"
        print(f"{type(pytest.param(chord, marks=pytest.mark.xfail(strict=True, reason=reason)))}")
        yield pytest.param(chord, marks=pytest.mark.xfail(strict=True, reason=reason))


@pytest.mark.parametrize("chord", list(get_missing_chord_params()))
def test_clean_missing_quality(chord: str) -> None:
    QualityManager().load_default_qualities()
    with pytest.raises(ValueError):
        Chord(chord)


@pytest.mark.parametrize("chord,loader", extra_chords_and_loaders)
def test_extra_quality(chord: str, loader: Callable) -> None:
    loader()
    Chord(chord)


def test_show_key_by_notes() -> None:
    data = show_key(None, "C,D,E,F,G,A,B")
    assert "Am" in data["other_keys"]


def test_show_key_aliases() -> None:
    data = show_key(None, "C")
    assert "Am" in data["other_keys"]
