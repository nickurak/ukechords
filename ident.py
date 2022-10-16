#!/usr/bin/env python3

# pylint: disable=missing-function-docstring,missing-class-docstring
# pylint: disable=missing-module-docstring,invalid-name

import sys
import argparse
import re
import os
import pickle
import itertools

from pychord import find_chords_from_notes
from pychord import Chord, QualityManager
from pychord.utils import note_to_val


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


def get_shapes(strings=4, max_fret=1, base=0, max_difficulty=29):
    shape = [base] * strings
    while True:
        if max(shape) >= 0 and get_shape_difficulty(shape)[0] <= max_difficulty:
            yield list(shape)
        if not increment(shape, max_fret, base=base):
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


def normalizer(input, scale):
    if isinstance(input, list):
        return [scale[note_intervals[note]] for note in input]
    else:
        return scale[note_intervals[input]]


def sharpify(input):
    return normalizer(input, chromatic_scale)


def flatify(input):
    return normalizer(input, flat_scale)


def get_shape_notes(shape, tuning):
    for string, position in enumerate(shape):
        if position == -1:
            continue
        yield chromatic_scale[note_intervals[tuning[string]] + position]


def is_flat(note):
    return note[-1] == "b"


def get_key_notes(key):
    mods = {q: [0, 2, 4, 5, 7, 9, 11] for q in ["", "maj", "major"]}
    mods |= {q: [0, 2, 3, 5, 7, 8, 10] for q in ["m", "min", "minor"]}
    mods |= {q: [0, 3, 5, 6, 7, 10] for q in ["minblues", "mblues", "minorblues"]}
    mods |= {q: [0, 2, 3, 4, 7, 9] for q in ["blues", "majblues", "majorblues"]}
    mods |= {q: [0, 2, 4, 7, 9] for q in ["p", "pent", "pentatonic", "majpentatonic"]}
    mods |= {q: [0, 3, 5, 7, 10] for q in ["mp", "mpent", "minorpentatonic"]}
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

def load_scanned_chords(base, max_fret, tuning, max_difficulty, chord_shapes):
    for imax_difficulty in range(max_difficulty, 100):
        fn = cached_fn(base, max_fret, tuning, imax_difficulty)
        if os.path.exists(fn):
            with open(fn, "rb") as cache:
                chord_shapes.d |= pickle.load(cache)
                return True
    return False


def save_scanned_chords(base, max_fret, tuning, max_difficulty, chord_shapes):
    fn = cached_fn(base, max_fret, tuning, max_difficulty)
    with open(fn, "wb") as cache:
        pickle.dump(chord_shapes.d, cache)


def scan_chords(base=0, max_fret=12, tuning=None, chord_shapes=None, no_cache=False, max_difficulty=None):
    assert tuning is not None
    assert max_difficulty is not None
    if not no_cache and load_scanned_chords(base=base, max_fret=max_fret, tuning=tuning, max_difficulty=max_difficulty, chord_shapes=chord_shapes):
        return
    for shape in get_shapes(max_fret=max_fret, base=base, strings=len(tuning), max_difficulty=max_difficulty):
        notes = set(get_shape_notes(shape,  tuning=tuning))
        for chord in get_chords(notes):
            if not chord in chord_shapes:
                chord_shapes[chord] = list([shape])
            else:
                chord_shapes[chord].append(shape)
    save_scanned_chords(base=base, max_fret=max_fret, tuning=tuning, chord_shapes=chord_shapes, max_difficulty=max_difficulty)

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
    max_pos = max([*shape, 3]) + 1
    lines = ['─'] * max_pos
    top = '┌' + '┬'.join(lines) + '┐'
    bottom = '└' + '┴'.join(lines) + '┘'
    print(top)
    for string, pos in enumerate(reversed(shape)):
        chars = [' '] * max_pos
        for mark in [3, 5, 7, 10, 12]:
            if mark < max_pos + 1 and (string - (len(shape) - 4) // 2) < len(marks[mark]):
                chars[mark-1] = marks[mark][string - (len(shape) - 4) // 2]
        if pos >= 0:
            print('│', end='')
            if pos > 0:
                chars[pos - 1] = '●'
        else:
            print('│⃠', end='')
        print('│'.join(chars), end='')
        print('│')
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


def main():
    add_no5_quality()
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--chord", help="Show how to play <CHORD>")
    parser.add_argument("-s", "--shape", help="Show what chord(s) this <SHAPE> plays")
    parser.add_argument("-t", "--tuning", default='ukulele-c6', help="comma-separated notes for string tuning")
    parser.add_argument("-1", "--single", action='store_true', help="Show only 1 shape for each chord")
    parser.add_argument("-l", "--latex", action='store_true', help="Output chord info in LaTeX format")
    parser.add_argument("-v", "--visualize", action='store_true', help="Visualize shapes with Unicode drawings")
    parser.add_argument("-a", "--all-chords", action='store_true', help="Show all matching chords, not just one selected one")
    parser.add_argument("-m", "--mute", action='store_true', help="Include shapes that require muting strings")
    parser.add_argument("-n", "--num", type=int, help="Show <NUM> shapes for the given chord")
    parser.add_argument("-d", "--max-difficulty", type=int, help="Limit shape-scanning to the given <MAX_DIFFICULTY>", metavar="DIFFICULTY")
    parser.add_argument("-k", "--key", action='append', help="Limit chords to those playable in <KEY> (can be specified multiple times)")
    parser.add_argument("-o", "--allowed-chord", action='append', help="Limit to chords playable by the notes in <CHORD> (specify multiple times)", metavar="CHORD")
    parser.add_argument("-q", "--qualities", help="Limit chords to chords with the specified <QUALITIES>")
    parser.add_argument("-p", "--simple", action='store_true', help="Limit to chords with major, minor, dim, and maj7/min7 qualities")
    parser.add_argument("--no-cache", action='store_true', help="Ignore any available cached chord/shape information")
    parser.add_argument("--show-key", help="Show the notes in the specified <KEY>", metavar="KEY")
    parser.add_argument("-f", "--force-flat", action='store_true', help="Show flat-variations of chord roots")
    parser.add_argument("-b", "--sort-by-position",  action='store_true', help="Sort to minimize high-position instead of difficulty")
    args = parser.parse_args()
    base = -1 if args.mute else 0
    max_difficulty = args.max_difficulty or 29
    shape_ranker = rank_shape_by_high_fret if args.sort_by_position else rank_shape_by_difficulty
    if args.tuning in ("ukulele", "ukulele-c6"):
        args.tuning = "G,C,E,A"
    elif args.tuning == "ukulele-g6":
        args.tuning = "D,G,B,E"
    elif args.tuning == "guitar":
        args.tuning = "E,A,D,G,B,E"
    elif args.tuning == "mandolin":
        args.tuning = "G,D,E,A"
    tuning = args.tuning.split(',')
    if args.qualities and args.simple:
        error(7, "Provide only one of -p/--simple or -q/--qualities")
    qualities = False
    chord_shapes = ChordCollection()
    if args.simple:
        qualities = ['', 'm', '7', 'dim', 'maj', 'm7']
    if args.qualities is not None:
        qualities = args.qualities.split(',')
    if list(map(bool, [args.chord, args.shape, (args.all_chords or args.key or args.allowed_chord), args.show_key])).count(True) != 1:
        error(5, "Provide exactly one of --all-chords or --chord or --shape or --show-key", parser)
    if args.single:
        args.num = 1
    if args.chord:
        scan_chords(base=base, tuning=tuning, chord_shapes=chord_shapes, no_cache=args.no_cache, max_difficulty=max_difficulty)
        if args.chord not in chord_shapes:
            error(1, f"\"{args.chord}\" not found")
        shapes = chord_shapes[args.chord]
        shapes.sort(key=shape_ranker)
        if not args.num:
            args.num = 1 if args.latex or args.visualize else len(shapes)
        chord_names = None
        for shape in shapes[:args.num]:
            if not chord_names:
                other_names = [c for c in get_chords(set(get_shape_notes(shape, tuning=tuning))) if c != args.chord]
                chord_names = ",".join([args.chord] + sorted(other_names))
            difficulty, desc = get_shape_difficulty(shape, tuning=tuning)
            if difficulty > max_difficulty:
                continue
            if args.latex:
                lchord = args.chord.replace('M', 'maj')
                print(f"\\defineukulelechord{{{lchord}}}{{{','.join(map(str, shape))}}}")
            else:
                print(f"{chord_names}: {','.join(map(str, shape))}\t difficulty: {diff_string(difficulty, desc)}")
            if args.visualize:
                draw_shape(shape)
    if args.all_chords or args.key or args.allowed_chord:
        notes = []
        for key in args.key or []:
            try:
                notes.extend(get_key_notes(key))
            except UnknownKeyException as e:
                error(10, e)
        for chord in args.allowed_chord or []:
            notes.extend(Chord(chord).components())
        if notes and any(map(is_flat, notes)):
            args.force_flat = True
        scan_chords(base=base, tuning=args.tuning.split(','), chord_shapes=chord_shapes, no_cache=args.no_cache, max_difficulty=max_difficulty)
        ichords = list(chord_shapes.keys())
        sort_offset = 0
        if args.key:
            sort_offset = note_intervals[get_key_notes(args.key[0])[0]]
        ichords.sort(key=lambda x: ((note_intervals[Chord(x).root] - sort_offset) % len(chromatic_scale), x))
        for chord in ichords:
            chord_shapes[chord].sort(key=shape_ranker)
            if args.force_flat:
                chord = flatify(Chord(chord).root) + Chord(chord).quality.quality
            if qualities and Chord(chord).quality.quality not in qualities:
                continue
            if notes and not all(note in sharpify(notes) for note in sharpify(Chord(chord).components())):
                continue
            shape = chord_shapes[chord][0]
            difficulty, desc = get_shape_difficulty(shape, tuning=args.tuning.split(','))
            if difficulty > max_difficulty:
                continue
            if args.latex:
                lchord = chord.replace('M', 'maj')
                print(f"\\defineukulelechord{{{lchord}}}{{{','.join(map(str, shape))}}}")
            else:
                print(f"{chord}: {','.join(map(str, shape))}\t difficulty: {diff_string(difficulty, desc)}")
            if args.visualize:
                draw_shape(shape)
    if args.shape:
        shape = [-1 if pos == 'x' else int(pos) for pos in args.shape.split(",")]
        if args.visualize:
            draw_shape(shape)
        chords = list(get_chords(set(get_shape_notes(shape, tuning=tuning))))
        chords.sort(key=lambda c: (len(c), c))
        print(f"{shape}: {', '.join(chords)}")
        print(f"Difficulty: {diff_string(*get_shape_difficulty(shape, tuning=args.tuning.split(',')))}")
    if args.show_key:
        print(f"{', '.join(get_key_notes(args.show_key))}")
    return 0
if __name__ == "__main__":
    sys.exit(main())
