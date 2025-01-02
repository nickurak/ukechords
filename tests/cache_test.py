# pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring

from ukechords.cache import _cached_filename, save_scanned_chords, load_scanned_chords

from .uketestconfig import uke_config


def test_load_save_cache(uke_config):
    shapes = {"hello": "world"}
    save_scanned_chords(uke_config, shapes, max_fret=4)
    shapes = {}
    res = load_scanned_chords(uke_config, shapes, max_fret=4)
    assert res
    assert shapes["hello"] == "world"


def test_load_empty_cache(uke_config):
    shapes = {}
    res = load_scanned_chords(uke_config, shapes, max_fret=4)
    assert res is False
    assert not shapes


def test_cached_filename(uke_config):
    uke_config.mute = True
    uke_config.tuning = ["A"]
    fn_str = _cached_filename(uke_config, 4, 50)
    assert fn_str.endswith("/cache_mTrue_4_A_50.pcl")
