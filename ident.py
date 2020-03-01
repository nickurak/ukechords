import sys

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

print(list(get_chords(sys.argv[1:])))
