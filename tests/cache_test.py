from ukechords.cache import cached_filename, save_scanned_chords, load_scanned_chords

from .uketestconfig import uke_config # pylint: disable=unused-import


class FakeChordCollection(): # pylint: disable=too-few-public-methods
    def __init__(self):
        self.dictionary = {}


# pylint: disable=redefined-outer-name

def test_load_save_cache(uke_config):
    shapes = FakeChordCollection()
    shapes.dictionary = {'hello': 'world'}
    save_scanned_chords(uke_config, shapes, max_fret=4)
    shapes.dictionary = {}
    res = load_scanned_chords(uke_config, shapes, max_fret=4)
    assert res
    assert shapes.dictionary['hello'] == 'world'


def test_load_empty_cache(uke_config):
    shapes = FakeChordCollection()
    res = load_scanned_chords(uke_config, shapes, max_fret=4)
    assert res is False
    assert not shapes.dictionary


def test_cached_filename(uke_config):
    uke_config.base = -1
    uke_config.tuning = ['A']
    fn_str = cached_filename(uke_config, 4, 50)
    assert fn_str.endswith("/cache_-1_4_A_50.pcl")
