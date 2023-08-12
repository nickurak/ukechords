import pytest

from pychord import Chord

from theory import sharpify, flatify
from theory import get_chords_by_shape
from theory import add_no5_quality, add_7sus2_quality
from theory import ChordCollection, scan_chords


class UkeTestConfig():
    # pylint: disable=too-few-public-methods,too-many-instance-attributes
    def __init__(self):
        self.slide = False
        self.tuning = ['C', 'E', 'G']
        self.show_notes = False
        self.visualize = False
        self.force_flat = False
        self.qualities = False
        self.no_cache = True
        self.base = 0
        self.max_difficulty = 20


@pytest.fixture
def uke_config():
    config_obj = UkeTestConfig()
    yield config_obj

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

def test_no5_quality():
    with pytest.raises(ValueError):
        Chord('C9no5')
    add_no5_quality()
    Chord('C9no5')

def test_7sus2_quality():
    with pytest.raises(ValueError):
        Chord('C7sus2')
    add_7sus2_quality()
    Chord('C7sus2')


def test_basic_scan(uke_config):
    chord_shapes = ChordCollection()
    scan_chords(uke_config, chord_shapes, max_fret=3)
    assert chord_shapes['C'] is not None
