import sys
import os
import pickle

from math import ceil


def error(rc, message, parser=None):
    print(message, file=sys.stderr)
    if parser:
        parser.print_help(sys.stderr)
    sys.exit(rc)


def cached_fn(base, max_fret, tuning, max_difficulty):
    tn_string = ''.join(tuning)
    fn = f"cache_{base}_{max_fret}_{tn_string}_{max_difficulty}.pcl"
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "cached_shapes", fn)


def load_scanned_chords(config, max_fret, chord_shapes):
    for imax_difficulty in range(ceil(config.max_difficulty), 100):
        fn = cached_fn(config.base, max_fret, config.tuning, imax_difficulty)
        if os.path.exists(fn):
            with open(fn, "rb") as cache:
                chord_shapes.dictionary |= pickle.load(cache)
                return True
    return False


def save_scanned_chords(config, max_fret, chord_shapes):
    fn = cached_fn(config.base, max_fret, config.tuning, config.max_difficulty)
    with open(fn, "wb") as cache:
        pickle.dump(chord_shapes.dictionary, cache)
