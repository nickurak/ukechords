import pytest

from theory import sharpify, flatify
from theory import get_chords_by_shape
from theory import ChordCollection, scan_chords
from theory import get_key_notes, get_dupe_scales

from uketestconfig import uke_config #pylint: disable=unused-import

# pylint: disable=redefined-outer-name

def test_sharpify():
    assert  sharpify('Bb') == 'A#'
    assert  sharpify('A#') == 'A#'
    assert  flatify('A#') == 'Bb'
    assert flatify ('Bb') == 'Bb'

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
    with pytest.raises(IndexError):
        _ = chord_shapes['C9']
    assert 'C' in chord_shapes.keys()


def test_scale():
    key1 = 'C'
    key2 = 'Am'

    notes1 = set(get_key_notes(key1))
    notes2 = set( get_key_notes(key2))
    assert notes1 == notes2
    dupes = get_dupe_scales(key1)
    assert 'Aminor' in dupes
