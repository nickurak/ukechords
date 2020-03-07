#!/usr/bin/env python3

import sys

from pychord import note_to_chord
from pychord import Chord
from pychord.utils import note_to_val

import argparse

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

def increment(position, max_pos):
    n = 0
    while True:
        position[n] += 1
        if position[n] > max_pos:
            if (n+1) >= len(position):
                position[n] -= 1
                return False
            position[n] = 0
            n += 1
        else:
            return True

def get_shapes(strings=4, min_fret=0, max_fret=1):
    position = [0] * strings
    while True:
        if max(position) >= min_fret:
            yield list(position)
        if not increment(position, max_fret):
            return

def note_subset(subset, superset):
    subset_vals = set(map(note_to_val, subset))
    superset_vals = map(note_to_val, superset)
    return subset_vals.issubset(superset_vals)

chromatic_scale = CircularList(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'])
note_intervals = {note: index for index, note in enumerate(chromatic_scale)}

def get_shape_notes(shape, base=('G', 'C', 'E', 'A')):
    for string, position in enumerate(shape):
        yield chromatic_scale[note_intervals[base[string]] + position]

chord_shapes = ChordCollection()

def scan_chords(stop_on=None, allowed_notes=None):
    for max_fret in range(0, 12):
        for shape in get_shapes(min_fret=max_fret, max_fret=max_fret):
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
    parser.add_argument("-n", "--num", type=int)
    args = parser.parse_args()
    if args.chord:
        scan_chords(allowed_notes=Chord(args.chord).components())
        shapes = chord_shapes[args.chord]
        if args.single:
            print(f"{args.chord}: {shapes[0]}")
        elif args.num:
            print(f"{args.chord}: {shapes[:args.num]}")
        else:
            print(f"{args.chord}: {shapes}")
    if args.shape:
        shape=list(map(int, args.shape.split(',')))
        print(f"{shape}: {list(get_chords(set(get_shape_notes(shape))))}")
    if not (args.shape or args.chord):
        parser.print_help(sys.stderr)
        sys.exit(1)
if __name__ ==  "__main__":
    main()
