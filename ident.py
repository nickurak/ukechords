#!/usr/bin/env python3

import sys
import argparse

from pychord import note_to_chord
from pychord import Chord
from pychord.utils import note_to_val


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

def get_shape_difficulty(shape):
    difficulty = 0.0
    last_pos = None
    for string, pos in enumerate(shape):
        if pos != 0:
            if last_pos:
                difficulty += (pos - last_pos)**2
            last_pos = pos
        elif last_pos:
            difficulty += 1
        if pos < 0:
            if  string in [0, len(shape)]:
                difficulty += 2
            else:
                difficulty += 5
        else:
            difficulty += pos
    barrable = len([1 for pos in shape if pos == min(shape)])
    if barrable > 1 and min(shape) > 0:
        barre_difficulty = get_shape_difficulty([x-min(shape) for x in shape]) + min(shape)*2 + 2
        if barre_difficulty < difficulty:
            return barre_difficulty
    return difficulty

def note_subset(subset, superset):
    subset_vals = set(map(note_to_val, subset))
    superset_vals = map(note_to_val, superset)
    return subset_vals.issubset(superset_vals)

chromatic_scale = CircularList(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'])
note_intervals = {note: index for index, note in enumerate(chromatic_scale)}

def get_shape_notes(shape, base=('G', 'C', 'E', 'A')):
    for string, position in enumerate(shape):
        if position == -1:
            continue
        yield chromatic_scale[note_intervals[base[string]] + position]

chord_shapes = ChordCollection()

def scan_chords(stop_on=None, allowed_notes=None, base=0, max_fret=12):
    for max_fret in range(0, max_fret):
        for shape in get_shapes(min_fret=max_fret, max_fret=max_fret, base=base):
            notes = set(get_shape_notes(shape))
            if allowed_notes and not note_subset(notes, allowed_notes):
                continue
            for chord in get_chords(notes):
                if not chord in chord_shapes:
                    chord_shapes[chord] = list([shape])
                else:
                    chord_shapes[chord].append(shape)
                if stop_on and all(elem in chord_shapes.keys()  for elem in stop_on):
                    return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--chord")
    parser.add_argument("-s", "--shape")
    parser.add_argument("-1", "--single", action='store_true')
    parser.add_argument("-l", "--latex", action='store_true')
    parser.add_argument("-a", "--all-chords", action='store_true')
    parser.add_argument("-i", "--ignore-difficulty", action='store_true')
    parser.add_argument("-m", "--mute", action='store_true')
    parser.add_argument("-n", "--num", type=int)
    parser.add_argument("-d", "--max-difficulty", type=int)
    args = parser.parse_args()
    base = -1 if args.mute else 0
    num = None
    max_difficulty = args.max_difficulty if args.max_difficulty else 29
    if args.single:
        num = 1
    if args.num:
        num = args.num
    if args.chord:
        try:
            notes = Chord(args.chord).components()
        except ValueError:
            print(f"Unable to lookup chord \"{args.chord}\"")
            return 2
        scan_chords(allowed_notes=notes, base=base)
        if args.chord not in chord_shapes:
            print(f"\"{args.chord}\" not found")
            return 1
        shapes = chord_shapes[args.chord]
        num = num if num else len(shapes)
        if not args.ignore_difficulty:
            shapes.sort(key=get_shape_difficulty)
        if args.latex:
            print(f"\\defineukulelechord{{{args.chord}}}{{{','.join(map(str, shapes[0]))}}}")
        else:
            for shape in shapes[:num]:
                difficulty = get_shape_difficulty(shape)
                if difficulty > max_difficulty:
                    continue
                print(f"{args.chord}: {','.join(map(str, shape))}" + "\t difficulty:" + str(difficulty))
        return 0
    if args.all_chords:
        scan_chords(base=base, max_fret=7)
        for chord in sorted(chord_shapes):
            if not args.ignore_difficulty:
                chord_shapes[chord].sort(key=get_shape_difficulty)
            shape = chord_shapes[chord][0]
            if args.latex:
                lchord = chord.replace('M', 'maj')
                print(f"\\defineukulelechord{{{lchord}}}{{{','.join(map(str, shape))}}}")
            else:
                difficulty = get_shape_difficulty(shape)
                print(f"{chord}: {','.join(map(str, shape))}" + "\t difficulty:" + str(difficulty))
        return 0
    if args.shape:
        shape = [-1 if pos == 'x' else int(pos) for pos in args.shape.split(",")]
        print(f"{shape}: {list(get_chords(set(get_shape_notes(shape))))}")
        if not args.ignore_difficulty:
            print(f"Difficulty: {get_shape_difficulty(shape)}")
        return 0
    if not (args.shape or args.chord or args.all_chords):
        parser.print_help(sys.stderr)
        return 3
    return 4
if __name__ == "__main__":
    sys.exit(main())
