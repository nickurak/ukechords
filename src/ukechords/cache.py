"""Tools to load and save cached ukechords data"""

import os
import pickle

from math import ceil
from pathlib import Path


def _cached_filename(config, max_fret, max_difficulty):
    tn_string = "".join(config.tuning)
    filename = f"cache_{config.base}_{max_fret}_{tn_string}_{max_difficulty}.pcl"
    return os.path.join(config.cache_dir, filename)


def load_scanned_chords(config, chord_shapes, max_fret):
    """Load cached chords/shapes from disk"""
    for imax_difficulty in range(ceil(config.max_difficulty), 100):
        filename = _cached_filename(config, max_fret, imax_difficulty)
        if os.path.exists(filename):
            with open(filename, "rb") as cache:
                chord_shapes.dictionary |= pickle.load(cache)
                return True
    return False


def save_scanned_chords(config, chord_shapes, max_fret):
    """Save chord/shapes to cache on disk"""
    filename = _cached_filename(config, max_fret, config.max_difficulty)
    Path(config.cache_dir).mkdir(parents=True, exist_ok=True)
    with open(filename, "wb") as cache:
        pickle.dump(chord_shapes.dictionary, cache)
