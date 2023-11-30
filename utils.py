import sys
import os
import pickle

from math import ceil
from xdg import BaseDirectory


def error(return_code, message, parser=None):
    print(message, file=sys.stderr)
    if parser:
        parser.print_help(sys.stderr)
    sys.exit(return_code)


def cached_filename(base, max_fret, tuning, max_difficulty):
    tn_string = ''.join(tuning)
    filename = f"cache_{base}_{max_fret}_{tn_string}_{max_difficulty}.pcl"
    return os.path.join(BaseDirectory.save_cache_path('ukechords', 'cached_shapes'), filename)


def load_scanned_chords(config, chord_shapes, max_fret):
    for imax_difficulty in range(ceil(config.max_difficulty), 100):
        filename = cached_filename(config.base, max_fret, config.tuning, imax_difficulty)
        if os.path.exists(filename):
            with open(filename, "rb") as cache:
                chord_shapes.dictionary |= pickle.load(cache)
                return True
    return False


def save_scanned_chords(config, chord_shapes, max_fret):
    filename = cached_filename(config.base, max_fret, config.tuning, config.max_difficulty)
    with open(filename, "wb") as cache:
        pickle.dump(chord_shapes.dictionary, cache)


def csv(lst, sep=','):
    return sep.join(map(str, lst))
