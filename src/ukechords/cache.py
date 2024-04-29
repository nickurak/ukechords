import os
import pickle

from math import ceil


def cached_filename(config, max_fret, max_difficulty):
    tn_string = ''.join(config.tuning)
    filename = f"cache_{config.base}_{max_fret}_{tn_string}_{max_difficulty}.pcl"
    return os.path.join(config.cache_dir, filename)


def load_scanned_chords(config, chord_shapes, max_fret):
    for imax_difficulty in range(ceil(config.max_difficulty), 100):
        filename = cached_filename(config, max_fret, imax_difficulty)
        if os.path.exists(filename):
            with open(filename, "rb") as cache:
                chord_shapes.dictionary |= pickle.load(cache)
                return True
    return False


def save_scanned_chords(config, chord_shapes, max_fret):
    filename = cached_filename(config, max_fret, config.max_difficulty)
    with open(filename, "wb") as cache:
        pickle.dump(chord_shapes.dictionary, cache)
