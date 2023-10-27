import tempfile
import os

import pytest

from utils import cached_filename, save_scanned_chords, load_scanned_chords
from utils import error

from uketestconfig import uke_config #pylint: disable=unused-import


class FakeChordCollection(): # pylint: disable=too-few-public-methods
    def __init__(self):
        self.dictionary = {}


# pylint: disable=redefined-outer-name
@pytest.fixture(autouse=True)
def abspath_mock(mocker):
    with tempfile.TemporaryDirectory() as tmpdirname:
        mock_abspath  = mocker.patch('os.path.abspath')
        mock_abspath.return_value = os.path.join(tmpdirname, 'null.py')
        os.mkdir(os.path.join(tmpdirname, 'cached_shapes'))
        yield


def test_load_save_cache(uke_config):
    shapes = FakeChordCollection()
    shapes.dictionary = {'hello': 'world'}
    save_scanned_chords(uke_config, shapes, max_fret=4)
    shapes.dictionary = {}
    res = load_scanned_chords(uke_config, shapes, max_fret = 4)
    assert res
    assert shapes.dictionary['hello'] == 'world'


def test_load_empty_cache(uke_config):
    shapes = FakeChordCollection()
    res = load_scanned_chords(uke_config, shapes, max_fret = 4)
    assert res is False
    assert not shapes.dictionary


def test_cached_filename():
    fn_str = cached_filename(-1, 4, ['A'], 50)
    assert fn_str.endswith("/cached_shapes/cache_-1_4_A_50.pcl")


class FakeParser(): # pylint: disable=too-few-public-methods
    def __init__(self):
        self.help_shown_fds = []

    def print_help(self, file_descriptor):
        self.help_shown_fds.append(file_descriptor)


def test_error(capsys):
    parser = FakeParser()
    with pytest.raises(SystemExit) as excinfo:
        error(5, "error!", parser)
    assert excinfo.value.code == 5
    out, err = capsys.readouterr()
    assert out == ''
    assert err == 'error!\n'
