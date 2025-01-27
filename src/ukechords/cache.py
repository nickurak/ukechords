"""Tools to load and save cached ukechords data"""

from __future__ import annotations
from typing import TYPE_CHECKING
import os
import pickle

from math import ceil
from pathlib import Path

if TYPE_CHECKING:
    from .config import UkeConfig
    from .theory import _ChordCollection


def _cached_filename(config: UkeConfig, max_fret: int, max_difficulty: float) -> str:
    tn_string = "".join(config.tuning)
    filename = f"cache_m{config.mute}_{max_fret}_{tn_string}_{int(max_difficulty)}.pcl"
    return os.path.join(config.cache_dir, filename)


def load_scanned_chords(config: UkeConfig, chord_shapes: _ChordCollection, max_fret: int) -> bool:
    """Load cached chords/shapes from disk"""
    for imax_difficulty in range(ceil(config.max_difficulty), 100 + 1):
        filename = _cached_filename(config, max_fret, imax_difficulty)
        if os.path.exists(filename):
            with open(filename, "rb") as cache:
                chord_shapes |= pickle.load(cache)
                return True
    return False


def save_scanned_chords(config: UkeConfig, chord_shapes: _ChordCollection, max_fret: int) -> None:
    """Save chord/shapes to cache on disk"""
    filename = _cached_filename(config, max_fret, config.max_difficulty)
    Path(config.cache_dir).mkdir(parents=True, exist_ok=True)
    with open(filename, "wb") as cache:
        pickle.dump(chord_shapes, cache)
