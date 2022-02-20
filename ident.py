#!/usr/bin/env python3

# pylint: disable=missing-function-docstring,missing-class-docstring
# pylint: disable=missing-module-docstring,invalid-name

import sys
import argparse
import re
import os
import pickle

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

def add_b5_quality():
    new_qs = []
    # Hack -- get list of existing qualities
    for name, quality in QualityManager()._qualities.items():
        b5name = name + '-5'
        if '/' in name or not 7 in quality.components:
            continue
        if quality.components != (0, 4, 7):
            continue
        new = tuple(map(lambda x: x if x != 7 else x - 1, quality.components))
        new_qs.append((b5name, new))
    for name, new in new_qs:
        QualityManager().set_quality(name, new)

def get_orders(vals):
    for index, value in enumerate(vals):
        list2 = list(vals)
        del list2[index]
        if len(list2) > 0:
            for vals2 in get_orders(list2):
                yield [value, *vals2]
        else:
            yield [value]

def get_chords(notes):

    for seq in get_orders(notes):
        yield from [c.chord for c in find_chords_from_notes(seq) if not "/" in c.chord]

class CircularList(list):
    def __getitem__(self, index):
        return super().__getitem__(index % len(self))

class ChordCollection():
    def __init__(self):
        self.d = dict()

    def  __contains__(self, chord):
        cchord = Chord(chord)
        for name, (_, ichord) in self.d.items():
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
        for name, (shapelist, ichord) in self.d.items():
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

def get_shapes(strings=4, min_fret=0, max_fret=1, base=0):
    position = [base] * strings
    while True:
        if max(position) >= min_fret:
            yield list(position)
        if not increment(position, max_fret, base=base):
            return

def round_result(f):
    def round_func(shape, tuning=None):
        res, desc = f(shape, tuning)
        return round(res, 1), desc
    return round_func

@round_result
def get_shape_difficulty(shape, tuning=None):
    difficulty = 0.0
    last_pos = None
    for string, pos in enumerate(shape):
        if pos != 0:
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
            details = f"else {round(barre_difficulty, 1)}: barred {min(shape)} + {barre_chord_string}" if tuning else None
        if barre_difficulty < difficulty:
            details =  f"barre {min(shape)} + {barre_chord_string}, else {round(difficulty, 1)}" if tuning else None
            difficulty = barre_difficulty
    return difficulty, details

def note_subset(subset, superset):
    subset_vals = set(map(note_to_val, subset))
    superset_vals = map(note_to_val, superset)
    return subset_vals.issubset(superset_vals)

chromatic_scale = CircularList(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'])
flat_scale = CircularList(['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B'])
note_intervals = {note: index for index, note in enumerate(chromatic_scale)}
note_intervals |= {note: index for index, note in enumerate(flat_scale)}

def get_shape_notes(shape, tuning=None):
    for string, position in enumerate(shape):
        if position == -1:
            continue
        yield chromatic_scale[note_intervals[tuning[string]] + position]

def get_key_notes(key):
    mods = {q: [0, 2, 4, 5, 7, 9, 11] for q in ["", "maj", "major"]}
    mods |= {q: [0, 2, 3, 5, 7, 8, 10] for q in ["m", "min", "minor"]}
    mods |= {q: [0, 3, 5, 6, 7, 10] for q in ["minblues", "mblues", "minorblues"]}
    mods |= {q: [0, 2, 3, 4, 7, 9] for q in ["blues", "majblues", "majorblues"]}
    mods |= {q: [0, 2, 4, 7, 9] for q in ["p", "pent", "pentatonic"]}
    match = re.match(f'^([A-G][b#]?)({"|".join(mods.keys())})$', key)
    if not match:
        raise UnknownKeyException(f"Unknown key \"{key}\"")
    (root, extra) = match.groups()
    intervals = mods[extra]
    return [chromatic_scale[interval + note_intervals[root]] for interval in intervals]


def cached_fn(allowed_notes, base, max_fret, tuning):
    an_string = ''.join(allowed_notes or ['%all%'])
    tn_string = ''.join(tuning)
    fn = f"{an_string}_{base}_{max_fret}_{tn_string}.pcl"
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "cached_shapes", fn)

def load_scanned_chords(allowed_notes, base, max_fret, tuning, chord_shapes):
    fn = cached_fn(allowed_notes, base, max_fret, tuning)
    if not os.path.exists(fn):
        return False
    with open(fn, "rb") as cache:
        chord_shapes.d |= pickle.load(cache)
    return True

def save_scanned_chords(allowed_notes, base, max_fret, tuning, chord_shapes):
    fn = cached_fn(allowed_notes, base, max_fret, tuning)
    with open(fn, "wb") as cache:
        pickle.dump(chord_shapes.d, cache)

def scan_chords(allowed_notes=None, base=0, max_fret=12, tuning=None, chord_shapes=None, no_cache=False):
    assert(tuning is not None)
    if not no_cache and load_scanned_chords(allowed_notes=allowed_notes, base=base, max_fret=max_fret, tuning=tuning, chord_shapes=chord_shapes):
        return
    for imax_fret in range(0, max_fret):
        for shape in get_shapes(min_fret=imax_fret, max_fret=imax_fret, base=base, strings=len(tuning)):
            notes = set(get_shape_notes(shape,  tuning=tuning))
            if allowed_notes and not note_subset(notes, allowed_notes):
                continue
            for chord in get_chords(notes):
                if not chord in chord_shapes:
                    chord_shapes[chord] = list([shape])
                else:
                    chord_shapes[chord].append(shape)
    save_scanned_chords(allowed_notes=allowed_notes, base=base, max_fret=max_fret, tuning=tuning, chord_shapes=chord_shapes)

def diff_string(difficulty, desc):
    return f"{difficulty} ({desc})" if desc else str(difficulty)

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
    exit(rc)

def main():
    add_no5_quality()
    add_b5_quality()
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--chord")
    parser.add_argument("-s", "--shape")
    parser.add_argument("-t", "--tuning", default='ukulele-c6')
    parser.add_argument("-1", "--single", action='store_true')
    parser.add_argument("-l", "--latex", action='store_true')
    parser.add_argument("-v", "--visualize", action='store_true')
    parser.add_argument("-a", "--all-chords", action='store_true')
    parser.add_argument("-i", "--ignore-difficulty", action='store_true')
    parser.add_argument("-m", "--mute", action='store_true')
    parser.add_argument("-n", "--num", type=int)
    parser.add_argument("-d", "--max-difficulty", type=int)
    parser.add_argument("-k", "--key", action='append')
    parser.add_argument("-o", "--allowed-chord", action='append')
    parser.add_argument("-q", "--qualities")
    parser.add_argument("-p", "--simple", action='store_true')
    parser.add_argument("--no-cache", action='store_true')
    args = parser.parse_args()
    base = -1 if args.mute else 0
    max_difficulty = args.max_difficulty or 29
    if args.tuning == "ukulele" or args.tuning == "ukulele-c6":
        args.tuning = "G,C,E,A"
    elif args.tuning == "ukulele-g6":
        args.tuning = "D,G,B,E"
    elif args.tuning == "guitar":
        args.tuning = "E,A,D,G,B,E"
    elif args.tuning == "mandolin":
        args.tuning = "G,D,E,A"

    if args.qualities and args.simple:
        error(7, "Provide only one of -p/--simple or -q/--qualities")
    qualities = False
    chord_shapes = ChordCollection()
    if args.simple:
        qualities = ['', 'm', '7', 'dim', 'maj', 'm7']
    if args.qualities is not None:
        qualities = args.qualities.split(',')
    if list(map(bool, [args.chord, args.shape, (args.all_chords or args.key or args.allowed_chord)])).count(True) != 1:
        error(5, "Provide exactly one of --all-chords or --chord or --shape", parser)
    if args.single:
        args.num = 1
    if args.chord:
        try:
            notes = Chord(args.chord).components()
        except ValueError:
            error(2, f"Unable to lookup chord \"{args.chord}\"")
        scan_chords(base=base, tuning=args.tuning.split(','), chord_shapes=chord_shapes, no_cache=args.no_cache)
        if args.chord not in chord_shapes:
            error(1, f"\"{args.chord}\" not found")
        shapes = chord_shapes[args.chord]
        if not args.num:
            args.num = 1 if args.latex or args.visualize else len(shapes)
        if not args.ignore_difficulty:
            shapes.sort(key=lambda x: get_shape_difficulty(x, tuning=args.tuning.split(','))[0])
        for shape in shapes[:args.num]:
            difficulty, desc = get_shape_difficulty(shape, tuning=args.tuning.split(','))
            if difficulty > max_difficulty:
                continue
            if args.latex:
                lchord = args.chord.replace('M', 'maj')
                print(f"\\defineukulelechord{{{lchord}}}{{{','.join(map(str, shape))}}}")
            else:
                print("{}: {}\t difficulty: {}".format(
                    args.chord,
                    ','.join(map(str, shape)),
                    diff_string(difficulty, desc)
                ))
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
        scan_chords(base=base, max_fret=7, tuning=args.tuning.split(','), chord_shapes=chord_shapes, no_cache=args.no_cache)
        for chord in sorted(chord_shapes.keys()):
            if qualities and Chord(chord).quality.quality not in qualities:
                continue
            if notes and not all(note in notes for note in Chord(chord).components()):
                continue
            if not args.ignore_difficulty:
                chord_shapes[chord].sort(key=lambda x: get_shape_difficulty(x, tuning=args.tuning.split(','))[0])
            shape = chord_shapes[chord][0]
            difficulty, desc = get_shape_difficulty(shape, tuning=args.tuning.split(','))
            if difficulty > max_difficulty:
                continue
            if args.latex:
                lchord = chord.replace('M', 'maj')
                print(f"\\defineukulelechord{{{lchord}}}{{{','.join(map(str, shape))}}}")
            else:
                print("{}: {}\t difficulty: {}".format(
                    chord,
                    ','.join(map(str, shape)),
                    diff_string(difficulty, desc)
                ))
            if args.visualize:
                draw_shape(shape)
    if args.shape:
        shape = [-1 if pos == 'x' else int(pos) for pos in args.shape.split(",")]
        if args.visualize:
            draw_shape(shape)
        chords = list(get_chords(set(get_shape_notes(shape, tuning=args.tuning.split(',')))))
        chords.sort(key=lambda c: (len(c), c))
        print(f"{shape}: {', '.join(chords)}")
        if not args.ignore_difficulty:
            print(f"Difficulty: {diff_string(*get_shape_difficulty(shape, tuning=args.tuning.split(',')))}")
    return 0
if __name__ == "__main__":
    sys.exit(main())
