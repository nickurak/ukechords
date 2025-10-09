"""Test the cache module"""

from ukechords.cache import _cached_filename, save_scanned_chords, load_scanned_chords

from ukechords.config import UkeConfig
from ukechords.theory_basic import ChordCollection

from .uketestconfig import uke_config


def test_save_load_cache(uke_config: UkeConfig) -> None:
    """Verify our ability to save and load chord information to disk"""
    shapes: ChordCollection = {"SomeChord": [(1, 2, 3)]}  # type: ignore
    save_scanned_chords(uke_config, shapes, max_fret=4)
    shapes = {}  # type: ignore
    res = load_scanned_chords(uke_config, shapes, max_fret=4)
    assert res
    assert shapes["SomeChord"] == [(1, 2, 3)]


def test_load_empty_cache(uke_config: UkeConfig) -> None:
    """Verify behavior of loading an empty cache"""
    shapes: ChordCollection = {}  # type: ignore
    res = load_scanned_chords(uke_config, shapes, max_fret=4)
    assert res is False
    assert not shapes


def test_cached_filename(uke_config: UkeConfig) -> None:
    """Verify generation of a cached filename"""
    uke_config.mute = True
    uke_config.tuning = ("A",)
    fn_str = _cached_filename(uke_config, 4, 50)
    assert fn_str.endswith("/cache_mTrue_4_A_50.pcl")
