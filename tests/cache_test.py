# pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring

from __future__ import annotations
from typing import TYPE_CHECKING

from ukechords.cache import _cached_filename, save_scanned_chords, load_scanned_chords

from .uketestconfig import uke_config

if TYPE_CHECKING:
    from ukechords.theory import _ChordCollection
    from ukechords.config import UkeConfig


def test_load_save_cache(uke_config: UkeConfig) -> None:
    shapes: _ChordCollection = {"hello": "world"}  # type: ignore
    save_scanned_chords(uke_config, shapes, max_fret=4)
    shapes = {}  # type: ignore
    res = load_scanned_chords(uke_config, shapes, max_fret=4)
    assert res
    assert shapes["hello"] == "world"


def test_load_empty_cache(uke_config: UkeConfig) -> None:
    shapes: _ChordCollection = {}  # type: ignore
    res = load_scanned_chords(uke_config, shapes, max_fret=4)
    assert res is False
    assert not shapes


def test_cached_filename(uke_config: UkeConfig) -> None:
    uke_config.mute = True
    uke_config.tuning = ("A",)
    fn_str = _cached_filename(uke_config, 4, 50)
    assert fn_str.endswith("/cache_mTrue_4_A_50.pcl")
