import itertools
import re

from pychord import find_chords_from_notes
from pychord import Chord, QualityManager

from utils import error, load_scanned_chords, save_scanned_chords

class UnknownKeyException(Exception):
    pass

def add_no5_quality():
    new_qs = []
    # Hack -- get list of existing qualities
    for name, quality in QualityManager()._qualities.items(): # pylint: disable=protected-access
        no5name = name + 'no5'
        if '/' in name or not 7 in quality.components:
            continue
        new = tuple(filter(lambda x: x != 7, quality.components))
        new_qs.append((no5name, new))
    for name, new in new_qs:
        QualityManager().set_quality(name, new)


def add_7sus2_quality():
    new_qs = []
    for name, quality in QualityManager()._qualities.items(): # pylint: disable=protected-access
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
        for offset in range(1, 12):
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


def show_chords_by_notes(_, notes):
    print(f"{','.join(notes)}: {get_chords_from_notes(notes)}")


def show_key(_, key):
    other_keys = get_dupe_scales(key)
    if other_keys:
        other_str = f" ({', '.join(other_keys)})"
    else:
        other_str = ""
    print(f"{key}{other_str}:")
    print(f"{', '.join(get_key_notes(key))}")
