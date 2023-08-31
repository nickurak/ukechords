import subprocess
import tempfile
import os
import contextlib

import pytest
from pychord import Chord

from theory import sharpify, flatify
from theory import get_chords_by_shape
from theory import add_no5_quality, add_7sus2_quality
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


def test_no5_quality():
    add_no5_quality()
    Chord('C9no5')


def test_7sus2_quality():
    add_7sus2_quality()
    Chord('C7sus2')


def get_test_code_for_missing_quality(base, quality):
    chord = f'{base}{quality}'
    return f"""\
import pytest

from pychord import Chord


def test_missing_{quality}_quality():
    with pytest.raises(ValueError):
        Chord('{chord}')
"""


@contextlib.contextmanager
def get_missing_quality_tmpfile(quality):
    prefix = f'test_missing_quality_{quality}_'
    tdir = os.getcwd()
    with tempfile.NamedTemporaryFile(mode='w', prefix=prefix, suffix='.py', dir=tdir) as tmp_test:
        yield tmp_test


def run_sub_pytest(file, must_pass):
    args = ['-s', '-v', '--tb=no', '--no-header']
    status = subprocess.run(['pytest', *args, file], check=False)
    if must_pass:
        assert status.returncode == 0
    else:
        assert status.returncode != 0

missing_quality_table = [('C', '9no5', True),
                         ('C', '7sus2', True),
                         ('C', '7', False)]


@pytest.mark.parametrize('base,quality,missing', missing_quality_table)
def test_clean_missing_quality(base, quality, missing):
    with get_missing_quality_tmpfile(quality) as tmp_test:
        tmp_test.write(get_test_code_for_missing_quality(base, quality))
        tmp_test.flush()
        run_sub_pytest(tmp_test.name, must_pass=missing)


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
