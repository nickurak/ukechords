#!/usr/bin/env python3

# pylint: disable=missing-function-docstring,missing-class-docstring
# pylint: disable=missing-module-docstring,invalid-name

import sys
import argparse
import re
import os
import json

from pychord import note_to_chord
from pychord import Chord
from pychord.utils import note_to_val

from pychord.constants import QUALITY_DICT

def add_no5_quality():
    # Hack -- we shouldn't be editting constants, but we can, and do.
    for name, items in list(QUALITY_DICT.items()):
        no5name = name + 'no5'
        if '/' in name or not 7 in items:
            continue
        new = tuple(filter(lambda x: x != 7, items))
        QUALITY_DICT[no5name] = new

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
        yield from [c.chord for c in note_to_chord(seq) if not "/" in c.chord]

class CircularList(list):
    def __getitem__(self, index):
        return super().__getitem__(index % len(self))

class ChordCollection(dict):
    def  __contains__(self, chord):
        for name in super().keys():
            if Chord(name) == Chord(chord):
                return True
        return False

    def __getitem__(self, chord):
        for name, shapelist in super().items():
            if Chord(name) == Chord(chord):
                return shapelist
        raise IndexError

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
    if barrable > 1 and min(shape) > 0:
        barre_shape = [x-min(shape) for x in shape]
        min_barre_extra = min([0, *filter(lambda x: x > 0, barre_shape)])
        barre_difficulty = get_shape_difficulty(barre_shape, tuning=tuning)[0]*2.2 + min(shape) * 3.0  + min_barre_extra * 4.0
        chords = list(get_chords(set(get_shape_notes(barre_shape, tuning=tuning))))
        chords.sort(key=lambda c: (len(c), c))
        chord = chords[0] if len(chords) > 0 else '<nc>'
        if barre_difficulty < difficulty:
            return barre_difficulty, f"barre {min(shape)} + {','.join(map(str, barre_shape))}:{chord} , else {round(difficulty, 1)}"
        return difficulty, f"else {round(barre_difficulty, 1)} barred {min(shape)} + {','.join(map(str, barre_shape))}:{chord}"
    return difficulty, None

def note_subset(subset, superset):
    subset_vals = set(map(note_to_val, subset))
    superset_vals = map(note_to_val, superset)
    return subset_vals.issubset(superset_vals)

chromatic_scale = CircularList(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'])
note_intervals = {note: index for index, note in enumerate(chromatic_scale)}

def get_shape_notes(shape, tuning=None):
    for string, position in enumerate(shape):
        if position == -1:
            continue
        yield chromatic_scale[note_intervals[tuning[string]] + position]

def get_key_notes(key):
    match = re.match('^([A-G])([b#]?)(.*)$', key)
    (root, accidental, extra) = match.groups()
    if accidental == "b":
        root = chromatic_scale[note_intervals[root] -1]
        accidental = ""
    root = f"{root}{accidental}"
    if len(extra) == 0 or extra in ["maj", "major"]:
        intervals = [0, 2, 4, 5, 7, 9, 11]
    elif extra in ["m", "min", "minor"]:
        intervals = [0, 2, 3, 5, 7, 8, 10]
    else:
        raise Exception(f"Unknown scale modication \"{extra}\"")
    return [chromatic_scale[interval + note_intervals[root]] for interval in intervals]


def cached_fn(allowed_notes, base, max_fret, tuning):
    an_string = ''.join(allowed_notes or ['%all%'])
    tn_string = ''.join(tuning)
    fn = f"cached_shapes_{an_string}_{base}_{max_fret}_{tn_string}.json"
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), fn)

def load_scanned_chords(allowed_notes, base, max_fret, tuning, chord_shapes):
    fn = cached_fn(allowed_notes, base, max_fret, tuning)
    if not os.path.exists(fn):
        return False
    with open(fn, "r") as cache:
        j = json.load(cache)
        for chord, shapes in j.items():
            chord_shapes[chord] = shapes
    return True

def save_scanned_chords(allowed_notes, base, max_fret, tuning, chord_shapes):
    fn = cached_fn(allowed_notes, base, max_fret, tuning)
    with open(fn, "w") as cache:
        json.dump(chord_shapes, cache)

def scan_chords(allowed_notes=None, base=0, max_fret=12, tuning=None, chord_shapes=None):
    assert(tuning is not None)
    if load_scanned_chords(allowed_notes=allowed_notes, base=base, max_fret=max_fret, tuning=tuning, chord_shapes=chord_shapes):
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

def main():
    add_no5_quality()
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--chord")
    parser.add_argument("-s", "--shape")
    parser.add_argument("-t", "--tuning", default='G,C,E,A')
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
    args = parser.parse_args()
    base = -1 if args.mute else 0
    max_difficulty = args.max_difficulty or 29
    if args.qualities and args.simple:
        print("Provide only one of -p/--simple or -q/--qualities")
        return 7
    qualities = False
    chord_shapes = ChordCollection()
    if args.simple:
        qualities = ['', 'm', '7', 'dim', 'maj', 'm7']
    if args.qualities is not None:
        qualities = args.qualities.split(',')
    if list(map(bool, [args.chord, args.shape, (args.all_chords or args.key or args.allowed_chord)])).count(True) != 1:
        print("Provide exactly one of --all-chords or --chord or --shape")
        parser.print_help(sys.stderr)
        return 5
    if args.single:
        args.num = 1
    if args.chord:
        try:
            notes = Chord(args.chord).components()
        except ValueError:
            print(f"Unable to lookup chord \"{args.chord}\"")
            return 2
        scan_chords(allowed_notes=notes, base=base, tuning=args.tuning.split(','), chord_shapes=chord_shapes)
        if args.chord not in chord_shapes:
            print(f"\"{args.chord}\" not found")
            return 1
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
            notes.extend(get_key_notes(key))
        for chord in args.allowed_chord or []:
            notes.extend(Chord(chord).components())
        if notes:
            scan_chords(base=base, max_fret=7, allowed_notes=notes, tuning=args.tuning.split(','), chord_shapes=chord_shapes)
        else:
            scan_chords(base=base, max_fret=7, tuning=args.tuning.split(','), chord_shapes=chord_shapes)
        for chord in sorted(chord_shapes):
            if qualities and Chord(chord).quality.quality not in qualities:
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
