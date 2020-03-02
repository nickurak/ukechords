#!/usr/bin/env python3

from pychord import note_to_chord

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
        yield from note_to_chord(seq)

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


notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
vals = {}
for index, note in enumerate(notes):
    vals[note] = index

def get_shape_notes(shape, base=['G', 'C', 'E', 'A']):
    for index, value in enumerate(shape):
        yield notes[(vals[base[index]] + value) % len(notes)]
