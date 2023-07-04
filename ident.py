#!/usr/bin/env python3

# pylint: disable=missing-function-docstring,missing-class-docstring
# pylint: disable=missing-module-docstring,invalid-name

import sys
import argparse
import re
import os
import pickle
import itertools

from math import ceil

from pychord import find_chords_from_notes
from pychord import Chord, QualityManager


class UnknownKeyException(Exception):
    pass


def add_no5_quality():
    new_qs = []
    # Hack -- get list of existing qualities
    for name, quality in QualityManager()._qualities.items():
        no5name = name + 'no5'
        if '/' in name or not 7 in quality.components:
            continue
        new = tuple(filter(lambda x: x != 7, quality.components))
        new_qs.append((no5name, new))
    for name, new in new_qs:
        QualityManager().set_quality(name, new)


def add_7sus2_quality():
    new_qs = []
    for name, quality in QualityManager()._qualities.items():
        if name != 'sus2':
            continue
        c = list(quality.components)
        c.append(10)
        new_name=f"7{name}"
        new_qs.append((new_name, tuple(c)))
    for name, new in new_qs:
        QualityManager().set_quality(name, new)


def get_chords(notes):
    for seq in itertools.permutations(notes):
        yield from [c.chord for c in find_chords_from_notes(seq) if not "/" in c.chord]


class CircularList(list):
    def __getitem__(self, index):
        return super().__getitem__(index % len(self))


class ChordCollection():
    def __init__(self):
        self.d = {}

    def  __contains__(self, chord):
        cchord = Chord(chord)
        for _, (_, ichord) in self.d.items():
            try:
                if ichord == cchord:
                    return True
            except ValueError:
                pass
        return False

    def __setitem__(self, chord, val):
        self.d[chord] = (val, Chord(chord))

    def __getitem__(self, chord):
        cchord = Chord(chord)
        for _, (shapelist, ichord) in self.d.items():
            try:
                if ichord == cchord:
                    return shapelist
            except ValueError:
                pass
        raise IndexError

    def keys(self):
        return self.d.keys()


def increment(position, max_pos, base=0):
    n = 0
    while True:
        position[n] += 1
        if position[n] > max_pos:
            if (n+1) >= len(position):
                position[n] -= 1
                return False
            position[n] = base
            n += 1
        else:
            return True


def get_shapes(config, max_fret=1):
    shape = [config.base] * len(config.tuning)
    while True:
        if max(shape) >= 0 and get_shape_difficulty(shape)[0] <= config.max_difficulty:
            yield list(shape)
        if not increment(shape, max_fret, base=config.base):
            return


def get_shape_difficulty(shape, tuning=None):
    difficulty = 0.0 + max(shape)/10.0
    last_pos = None
    for string, pos in enumerate(shape):
        if pos > 0:
            if last_pos:
                difficulty += (pos - last_pos -1)**2 / 1.5
            last_pos = pos
        elif last_pos:
            difficulty += 1
        if pos < 0:
            if  string in [0, len(shape) - 1]:
                difficulty += 5
            else:
                difficulty += 7
        else:
            difficulty += pos
    barrable = len([1 for pos in shape if pos == min(shape)])
    details = None
    if barrable > 1 and min(shape) > 0:
        barre_shape = [x-min(shape) for x in shape]
        min_barre_extra = min([0, *filter(lambda x: x > 0, barre_shape)])
        barre_difficulty = get_shape_difficulty(barre_shape, tuning=tuning)[0]*2.2 + min(shape) * 3.0  + min_barre_extra * 4.0
        if tuning:
            chords = list(get_chords(set(get_shape_notes(barre_shape, tuning=tuning))))
            chords.sort(key=lambda c: (len(c), c))
            chord = chords[0] if len(chords) > 0 else '<nc>'
            barre_chord_string = f"{','.join(map(str, barre_shape))}:{chord}"
            details = f"else {barre_difficulty:.1f}: barred {min(shape)} + {barre_chord_string}" if tuning else None
        if barre_difficulty < difficulty:
            details =  f"barre {min(shape)} + {barre_chord_string}, else {difficulty:.1f}" if tuning else None
            difficulty = barre_difficulty
    return difficulty, details


chromatic_scale = CircularList(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'])
flat_scale = CircularList(['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B'])
note_intervals = {note: index for index, note in enumerate(chromatic_scale)}
note_intervals |= {note: index for index, note in enumerate(flat_scale)}


def normalizer(arg, scale):
    if isinstance(arg, list):
        return [scale[note_intervals[note]] for note in arg]
    return scale[note_intervals[arg]]


def sharpify(arg):
    return normalizer(arg, chromatic_scale)


def flatify(arg):
    return normalizer(arg, flat_scale)


def get_shape_notes(shape, tuning):
    for string, position in enumerate(shape):
        if position == -1:
            continue
        yield chromatic_scale[note_intervals[tuning[string]] + position]


def is_flat(note):
    return note[-1] == "b"

def get_scales():
    scales = [ (["", "maj", "major"], [0, 2, 4, 5, 7, 9, 11]),
               (["m", "min", "minor"], [0, 2, 3, 5, 7, 8, 10]),
               (["minblues", "mblues", "minorblues"], [0, 3, 5, 6, 7, 10]),
               (["blues", "majblues", "majorblues"], [0, 2, 3, 4, 7, 9]),
               (["p", "pent", "pentatonic", "majpentatonic"], [0, 2, 4, 7, 9]),
               (["mp", "mpent", "minorpentatonic"], [0, 3, 5, 7, 10]),
               (['phdom'], [0, 1, 4, 5, 7, 8, 10]),
               (['phmod'], [0, 1, 3, 5, 7, 8, 10]),
               (['gypsymajor'], [0, 1, 4, 5, 7, 8, 11]),
               (['gypsyminor'], [0, 2, 3, 6, 7, 8, 11]),
               (['chromatic'], range(0,12))
               ]

    mods = {}
    for names, intervals in scales:
        for name in names:
            mods[name] = intervals

    return mods

def get_dupe_scales(key):
    mods = get_scales()

    match = re.match(f'^([A-G][b#]?)({"|".join(mods.keys())})$', key)
    if not match:
        raise UnknownKeyException(f"Unknown key \"{key}\"")
    (root, extra) = match.groups()
    intervals = mods[extra]

    dupes = {}
    for inc in range(1, 12):
        if inc in dupes:
            continue
        for name, candidate_intervals in mods.items():
            transposed_intervals = [(x + inc) % 12 for x in candidate_intervals]
            if set(intervals) == set(transposed_intervals):
                transposed_root = chromatic_scale[(note_intervals[root] + inc) % 12]
                dupes[inc] = f'{transposed_root}{name}'

    return {val for _, val in dupes.items()}

def get_key_notes(key):
    mods = get_scales()

    match = re.match(f'^([A-G][b#]?)({"|".join(mods.keys())})$', key)
    if not match:
        raise UnknownKeyException(f"Unknown key \"{key}\"")
    (root, extra) = match.groups()
    intervals = mods[extra]
    if is_flat(root):
        return [flat_scale[interval + note_intervals[root]] for interval in intervals]
    return [chromatic_scale[interval + note_intervals[root]] for interval in intervals]


def cached_fn(base, max_fret, tuning, max_difficulty):
    tn_string = ''.join(tuning)
    fn = f"cache_{base}_{max_fret}_{tn_string}_{max_difficulty}.pcl"
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "cached_shapes", fn)

def load_scanned_chords(config, max_fret, chord_shapes):
    for imax_difficulty in range(ceil(config.max_difficulty), 100):
        fn = cached_fn(config.base, max_fret, config.tuning, imax_difficulty)
        if os.path.exists(fn):
            with open(fn, "rb") as cache:
                chord_shapes.d |= pickle.load(cache)
                return True
    return False


def save_scanned_chords(config, max_fret, chord_shapes):
    fn = cached_fn(config.base, max_fret, config.tuning, config.max_difficulty)
    with open(fn, "wb") as cache:
        pickle.dump(chord_shapes.d, cache)


def scan_chords(config, max_fret=12, chord_shapes=None):
    if not config.no_cache and load_scanned_chords(config, max_fret=max_fret, chord_shapes=chord_shapes):
        return
    notes_shapes_map = {}
    notes_chords_map = {}
    for shape in get_shapes(config, max_fret=max_fret):
        notes = frozenset(get_shape_notes(shape,  tuning=config.tuning))
        if notes in notes_shapes_map:
            notes_shapes_map[notes].append(shape)
            continue
        notes_shapes_map[notes] = [shape]
        notes_chords_map[notes] = get_chords(notes)

    for notes, chords in notes_chords_map.items():
        for chord in chords:
            for shape in notes_shapes_map[notes]:
                if not chord in chord_shapes:
                    chord_shapes[chord] = list([shape])
                else:
                    chord_shapes[chord].append(shape)

    save_scanned_chords(config, max_fret=max_fret, chord_shapes=chord_shapes)

def diff_string(difficulty, desc):
    return f"{difficulty:.1f} ({desc})" if desc else f"{difficulty:.1f}"


marks = {
    3: ' ╷╵ ',
    5: ' ╷╵ ',
    7: ' ╷╵ ',
    10: ' ╷╵ ',
    12: '╷╵╷╵',
}


def draw_shape(shape):
    max_pos = max([*shape, 3])+1
    lines = ['─'] * max_pos
    top = '╓' + '┬'.join(lines) + '─'
    bottom = '╙' + '┴'.join(lines) + '─'
    print(top)
    for string, pos in enumerate(reversed(shape)):
        chars = [' '] * max_pos
        for mark in [3, 5, 7, 10, 12]:
            if mark < max_pos + 1 and (string - (len(shape) - 4) // 2) < len(marks[mark]):
                chars[mark-1] = marks[mark][string - (len(shape) - 4) // 2]
        if pos >= 0:
            print('║', end='')
            if pos > 0:
                chars[pos - 1] = '●'
        else:
            print('║⃠', end='')
        print('│'.join(chars))
    print(bottom)


def error(rc, message, parser=None):
    print(message, file=sys.stderr)
    if parser:
        parser.print_help(sys.stderr)
    sys.exit(rc)

def rank_shape_by_difficulty(shape):
    return get_shape_difficulty(shape)[0]

def rank_shape_by_high_fret(shape):
    return sorted(shape, reverse=True)

def get_chords_from_notes(notes):
    chords = list(get_chords(notes))
    chords.sort(key=lambda c: (len(c), c))
    return ','.join(chords)

def get_tuning(args):
    if args.tuning in ("ukulele", "ukulele-c6"):
        return ["G", "C", "E", "A"]
    if args.tuning == "ukulele-g6":
        return ["D", "G", "B", "E"]
    if args.tuning == "guitar":
        return ["E", "A", "D", "G", "B", "E"]
    if args.tuning == "mandolin":
        return ["G", "D", "E", "A"]
    return args.tuning.split(',')

def show_chord(config, chord):
    chord_shapes = ChordCollection()
    try:
        c = Chord(chord)
        if config.show_notes:
            notes = c.components()
            print(f"Notes: {', '.join(notes)}")
    except ValueError as e:
        error(2, f"Error looking up chord {chord}: {e}")
    scan_chords(config, chord_shapes=chord_shapes)
    if chord not in chord_shapes:
        error(1, f"No shape for \"{chord}\" found")
    shapes = chord_shapes[chord]
    shapes.sort(key=config.shape_ranker)
    chord_names = None
    for shape in shapes[:config.num or len(shapes)]:
        if not chord_names:
            other_names = [c for c in get_chords(set(get_shape_notes(shape, tuning=config.tuning))) if c != chord]
            chord_names = ",".join([chord] + sorted(other_names))
        difficulty, desc = get_shape_difficulty(shape, tuning=config.tuning)
        if difficulty > config.max_difficulty:
            continue
        if config.latex:
            lchord = chord.replace('M', 'maj')
            print(f"\\defineukulelechord{{{lchord}}}{{{','.join(map(str, shape))}}}")
        else:
            print(f"{chord_names}: {','.join(['x' if x == -1 else str(x) for x in shape])}\t difficulty: {diff_string(difficulty, desc)}")
        if config.visualize:
            draw_shape(shape)

def show_all(config):
    notes = []
    chord_shapes = ChordCollection()
    for key in config.key or []:
        try:
            notes.extend(get_key_notes(key))
        except UnknownKeyException as e:
            error(10, e)
    for chord in config.allowed_chord or []:
        notes.extend(Chord(chord).components())
    if notes and any(map(is_flat, notes)):
        config.force_flat = True
    scan_chords(config, chord_shapes=chord_shapes)
    ichords = list(chord_shapes.keys())
    sort_offset = 0
    if config.key:
        sort_offset = note_intervals[get_key_notes(config.key[0])[0]]
    ichords.sort(key=lambda x: ((note_intervals[Chord(x).root] - sort_offset) % len(chromatic_scale), x))
    for chord in ichords:
        chord_shapes[chord].sort(key=config.shape_ranker)
        if config.force_flat:
            chord = flatify(Chord(chord).root) + Chord(chord).quality.quality
        if config.qualities and Chord(chord).quality.quality not in config.qualities:
            continue
        if notes and not all(note in sharpify(notes) for note in sharpify(Chord(chord).components())):
            continue
        shape = chord_shapes[chord][0]
        difficulty, desc = get_shape_difficulty(shape, tuning=config.tuning)
        if difficulty > config.max_difficulty:
            continue
        if config.latex:
            lchord = chord.replace('M', 'maj')
            print(f"\\defineukulelechord{{{lchord}}}{{{','.join(map(str, shape))}}}")
        else:
            print(f"{chord}: {','.join(map(str, shape))}\t difficulty: {diff_string(difficulty, desc)}")
        if config.visualize:
            draw_shape(shape)

def show_chords_by_shape(config, pshape):
    shape = [-1 if pos == 'x' else int(pos) for pos in pshape.split(",")]
    shapes = [shape]
    if config.slide:
        for offset in [i for i in range(1, 12)]:
            cshape = [(pos + offset) % 12 if pos > 0 else pos for pos in  shape]
            shapes.append(cshape)
    for shape in shapes:
        notes = set(get_shape_notes(shape, tuning=config.tuning))
        if config.show_notes:
            print(f"Notes: {', '.join(notes)}")
        prefix = ",".join(["x" if x == -1 else str(x) for x in shape])
        chords = get_chords_from_notes(notes)
        if config.visualize:
            draw_shape(shape)
        if chords != '':
            print(f'{prefix}: {chords}')
    if not config.slide:
        print(f"Difficulty: {diff_string(*get_shape_difficulty(shape, config.tuning))}")


def show_chords_by_notes(config, notes):
    print(f"{','.join(notes)}: {get_chords_from_notes(notes)}")


def show_key(config, key):
    other_keys = get_dupe_scales(key)
    if other_keys:
        other_str = f" ({', '.join(other_keys)})"
    else:
        other_str = ""
    print(f"{key}{other_str}:")
    print(f"{', '.join(get_key_notes(key))}")


class UkeConfig():
    def __init__(self, args):
        self._base = -1 if args.mute else 0
        self._tuning = get_tuning(args)
        self._shape_ranker = rank_shape_by_high_fret if args.sort_by_position else rank_shape_by_difficulty
        self._max_difficulty = args.max_difficulty or 29
        if list(map(bool, [args.notes, args.chord, args.shape, (args.all_chords or args.key or args.allowed_chord), args.show_key])).count(True) != 1:
            error(5, "Provide exactly one of --all-chords, --chord, --shape, --notes, or --show-key", get_parser())
        if args.qualities and args.simple:
            error(7, "Provide only one of -p/--simple or -q/--qualities")
        self._qualities = False
        if args.simple:
            self._qualities = ['', 'm', '7', 'dim', 'maj', 'm7']
        if args.qualities is not None:
            self._qualities = args.qualities.split(',')
        self._slide = args.slide
        if args.slide and not args.shape:
            error(8, "--slide requries a --shape")
        self._num = args.num
        if args.single:
            self._num = 1
        if not self._num and (args.latex or args.visualize):
            self._num = 1
        self._show_notes = args.show_notes
        self._no_cache = args.no_cache
        self._latex = args.latex
        self._visualize = args.visualize
        self._force_flat = args.force_flat
        if args.chord:
            self._command = lambda x: show_chord(x, args.chord)
        if args.all_chords or args.key or args.allowed_chord or args.key:
            self._command = show_all
        self._key = args.key
        self._allowed_chord = args.allowed_chord
        if args.shape:
            self._command = lambda x: show_chords_by_shape(x, args.shape)
        if args.notes:
            self._command = lambda x: show_chords_by_notes(x, set(args.notes.split(",")))
        if args.show_key:
            self._command = lambda x: show_key(x, args.show_key)

    @property
    def base(self):
        return self._base

    @property
    def tuning(self):
        return self._tuning

    @property
    def shape_ranker(self):
        return self._shape_ranker

    @property
    def max_difficulty(self):
        return self._max_difficulty

    @property
    def qualities(self):
        return self._qualities

    @property
    def slide(self):
        return self._slide

    @property
    def num(self):
        return self._num

    @property
    def show_notes(self):
        return self._show_notes

    @property
    def no_cache(self):
        return self._no_cache

    @property
    def latex(self):
        return self._latex

    @property
    def visualize(self):
        return self._visualize

    @property
    def force_flat(self):
        return self._force_flat

    @force_flat.setter
    def force_flat(self, value):
        self._force_flat = value

    @property
    def command(self):
        return self._command

    @property
    def key(self):
        return self._key

    @property
    def allowed_chord(self):
        return self._allowed_chord


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--chord", help="Show how to play <CHORD>")
    parser.add_argument("--notes", help="Show what chord(s) these <NOTES> play")
    parser.add_argument("-s", "--shape", help="Show what chord(s) this <SHAPE> plays")
    parser.add_argument("--slide", action='store_true', help="Show what chord(s) this <SHAPE> could play when slid up or down")
    parser.add_argument("-t", "--tuning", default='ukulele-c6', help="comma-separated notes for string tuning")
    parser.add_argument("-1", "--single", action='store_true', help="Show only 1 shape for each chord")
    parser.add_argument("-l", "--latex", action='store_true', help="Output chord info in LaTeX format")
    parser.add_argument("-v", "--visualize", action='store_true', help="Visualize shapes with Unicode drawings")
    parser.add_argument("-a", "--all-chords", action='store_true', help="Show all matching chords, not just one selected one")
    parser.add_argument("-m", "--mute", action='store_true', help="Include shapes that require muting strings")
    parser.add_argument("-n", "--num", type=int, help="Show <NUM> shapes for the given chord")
    parser.add_argument("-d", "--max-difficulty", type=float, help="Limit shape-scanning to the given <MAX_DIFFICULTY>", metavar="DIFFICULTY")
    parser.add_argument("-k", "--key", action='append', help="Limit chords to those playable in <KEY> (can be specified multiple times)")
    parser.add_argument("-o", "--allowed-chord", action='append', help="Limit to chords playable by the notes in <CHORD> (specify multiple times)", metavar="CHORD")
    parser.add_argument("-q", "--qualities", help="Limit chords to chords with the specified <QUALITIES>")
    parser.add_argument("-p", "--simple", action='store_true', help="Limit to chords with major, minor, dim, and maj7/min7 qualities")
    parser.add_argument("--no-cache", action='store_true', help="Ignore any available cached chord/shape information")
    parser.add_argument("--show-key", help="Show the notes in the specified <KEY>", metavar="KEY")
    parser.add_argument("--show-notes", action='store_true', help="Show the notes in chord")
    parser.add_argument("-f", "--force-flat", action='store_true', help="Show flat-variations of chord roots")
    parser.add_argument("-b", "--sort-by-position",  action='store_true', help="Sort to minimize high-position instead of difficulty")
    return parser


def get_args(parser):
    return parser.parse_args()


def main():
    add_no5_quality()
    add_7sus2_quality()
    config = UkeConfig(get_args(get_parser()))
    config.command(config)
    return 0
if __name__ == "__main__":
    sys.exit(main())
