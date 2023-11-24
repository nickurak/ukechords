import pytest

from pychord import Chord

from uketestconfig import uke_config #pylint: disable=unused-import

from theory import sharpify, flatify
from theory import get_chords_by_shape
from theory import ChordCollection, scan_chords
from theory import get_key_notes, get_dupe_scales_from_key
from theory import show_chord, show_chords_by_shape, show_all
from theory import weird_sharp_scale, weird_flat_scale
from theory import add_no5_quality, add_7sus2_quality

# pylint: disable=redefined-outer-name


def test_sharpify():
    assert sharpify('Bb') == 'A#'
    assert sharpify('A#') == 'A#'
    assert flatify('A#') == 'Bb'
    assert flatify('Bb') == 'Bb'

    assert all(x == y for x, y in zip(sharpify(['Bb', 'A#']), ['A#', 'A#']))
    assert all(x == y for x, y in zip(flatify(['Bb', 'A#']), ['Bb', 'Bb']))


def test_force_flat_shape(uke_config):
    uke_config.tuning = ['G', 'C', 'E']
    uke_config.force_flat = True
    pshape = [3, 2, 1]
    resp = list(get_chords_by_shape(uke_config, pshape))
    assert len(resp) == 1
    shape, chords, notes = resp[0]
    assert shape == [3, 2, 1]
    assert chords == ['Bb']
    assert notes == set(['Bb', 'F', 'D'])


def test_no_force_flat_shape(uke_config):
    uke_config.tuning = ['G', 'C', 'E']
    pshape = [3, 2, 1]
    resp = list(get_chords_by_shape(uke_config, pshape))
    assert len(resp) == 1
    shape, chords, notes = resp[0]
    assert shape == [3, 2, 1]
    assert chords == ['A#']
    assert notes == set(['A#', 'F', 'D'])


def test_basic_scan(uke_config):
    chord_shapes = ChordCollection()
    scan_chords(uke_config, chord_shapes, max_fret=3)
    assert 'C' in chord_shapes
    assert chord_shapes['C'] is not None
    with pytest.raises(KeyError):
        _ = chord_shapes['C9']
    assert 'C' in chord_shapes.keys()


def test_scale():
    key1 = 'C'
    key2 = 'Am'

    notes1 = set(get_key_notes(key1))
    notes2 = set(get_key_notes(key2))
    assert notes1 == notes2
    dupes = get_dupe_scales_from_key(key1)
    assert 'Am' in dupes


def test_show_chord(uke_config):
    uke_config.show_notes = True
    output = show_chord(uke_config, 'C#')
    assert {frozenset(shape['chord_names']) for shape in output['shapes']} == {frozenset(['C#'])}
    assert len(output['shapes']) == 2
    first_result = output['shapes'][0]
    assert first_result['chord_names'] == ['C#']
    assert first_result['shape'] == [1, 1, 1]
    assert output['notes'] == ['C#', 'F', 'G#']


def test_show_chordless_shape(uke_config):
    chordless_shape = 'x,x,x'
    output = show_chords_by_shape(uke_config, chordless_shape)
    shapes = output['shapes']
    assert len(shapes) == 1
    only_shape = shapes[0]
    assert only_shape['chords'] == []
    assert only_shape['shape'] == [-1, -1, -1]


def test_list_all(uke_config):
    uke_config.qualities = ['', 'm', '7', 'dim', 'maj', 'm7']
    uke_config.key = 'C'
    uke_config.allowed_chord = False
    output = show_all(uke_config)

    c_shapes = [shape for shape in output['shapes'] if 'C' in shape['chord_names']]
    assert len(c_shapes) == 1
    c_shape = c_shapes[0]
    assert c_shape['shape'] == [0, 0, 0]
    assert c_shape['difficulty'] == 0.0


def test_weird_flat_sharps():
    assert weird_sharp_scale == ['B#', 'C#', 'D', 'D#', 'E', 'E#', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    assert weird_flat_scale == ['C', 'Db', 'D', 'Eb', 'Fb', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'Cb']

extra_chords_and_loaders = [('C9no5', add_no5_quality), ('C7sus2', add_7sus2_quality)]
builtin_chords = ['C7']

def get_missing_chord_params():
    for chord, _ in extra_chords_and_loaders:
        yield chord
    for chord in builtin_chords:
        reason = f'{chord} is present, as expected'
        yield pytest.param(chord, marks=pytest.mark.xfail(strict=True, reason=reason))


@pytest.mark.order(1)
@pytest.mark.parametrize('chord', list(get_missing_chord_params()))
def test_clean_missing_quality(chord):
    with pytest.raises(ValueError):
        Chord(chord)


@pytest.mark.parametrize('chord,loader', extra_chords_and_loaders)
def test_extra_quality(chord, loader):
    loader()
    Chord(chord)
