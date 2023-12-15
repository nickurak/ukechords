import itertools
import re

from pychord.analyzer import notes_to_positions
from pychord import Chord, QualityManager

from .utils import error, load_scanned_chords, save_scanned_chords


class UnknownKeyException(Exception):
    pass


def add_no5_quality():
    new_qs = []
    for name, quality in QualityManager().get_qualities().items():
        no5name = name + 'no5'
        if '/' in name or 7 not in quality.components:
            continue
        new = tuple(filter(lambda x: x != 7, quality.components))
        new_qs.append((no5name, new))
    for name, new in new_qs:
        QualityManager().set_quality(name, new)


def add_7sus2_quality():
    new_qs = []
    for name, quality in QualityManager().get_qualities().items():
        if name != 'sus2':
            continue
        components = list(quality.components)
        components.append(10)
        new_name = f"7{name}"
        new_qs.append((new_name, tuple(components)))
    for name, new in new_qs:
        QualityManager().set_quality(name, new)


def add_M13_quality(): # pylint: disable=invalid-name
    new_qs = []
    for name, quality in QualityManager().get_qualities().items():
        if "maj13" not in name:
            continue
        components = list(quality.components)
        new_name = name.replace("maj", "M")
        new_qs.append((new_name, tuple(components)))
    for name, new in new_qs:
        QualityManager().set_quality(name, new)


def find_chord_from_notes(notes):
    root = notes[0]
    positions = notes_to_positions(notes, root)
    quality = QualityManager().find_quality_from_components(positions)
    if quality is None:
        return None
    return Chord(f"{root}{quality}")


def get_chords(notes):
    if not notes:
        return []
    chords = []
    for seq in itertools.permutations(notes):
        chord = find_chord_from_notes(seq)
        if chord is None:
            continue
        chords.append(chord.chord)
    return chords


class CircularList(list):
    def __getitem__(self, index):
        return super().__getitem__(index % len(self))


def sharpify_chord(chord):
    match = re.match('^([A-G][b#]?)(.*)$', chord)
    (root, quality) = match.groups()
    return f"{sharpify(root)}{quality}"


class ChordCollection():
    def __init__(self):
        self.dictionary = {}

    def __contains__(self, chord):
        return sharpify_chord(chord) in self.dictionary

    def __setitem__(self, chord, val):
        self.dictionary[sharpify_chord(chord)] = val

    def __getitem__(self, chord):
        return self.dictionary[sharpify_chord(chord)]

    def keys(self):
        return self.dictionary.keys()


def increment(position, max_pos, base=0):
    string = 0
    while True:
        position[string] += 1
        if position[string] > max_pos:
            if (string + 1) >= len(position):
                position[string] -= 1
                return False
            position[string] = base
            string += 1
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
    # pylint: disable=line-too-long,too-many-branches
    difficulty = 0.0 + max(shape)/10.0
    last_pos = None
    for string, pos in enumerate(shape):
        if pos > 0:
            if last_pos:
                difficulty += (pos - last_pos - 1) ** 2 / 1.5
            last_pos = pos
        elif last_pos:
            difficulty += 1
        if pos < 0:
            if string in [0, len(shape) - 1]:
                difficulty += 5
            else:
                difficulty += 7
        else:
            difficulty += pos
    barrable = len([1 for pos in shape if pos == min(shape)])
    barre_data = None
    if barrable > 1 and min(shape) > 0:
        barre_shape = [x-min(shape) for x in shape]
        min_barre_extra = min([0, *filter(lambda x: x > 0, barre_shape)])
        barre_difficulty = get_shape_difficulty(barre_shape, tuning=tuning)[0]*2.2 + min(shape) * 3.0 + min_barre_extra * 4.0
        if tuning:
            chords = list(get_chords(set(get_shape_notes(barre_shape, tuning=tuning))))
            chords.sort(key=rank_chord_name)
            chord = chords[0] if len(chords) > 0 else None
            barre_data = { 'fret': min(shape), 'shape': barre_shape, 'chord': chord }
        if barre_difficulty < difficulty:
            if barre_data:
                barre_data['unbarred_difficulty'] = difficulty
                barre_data['barred'] = True
            difficulty = barre_difficulty
        elif barre_data:
            barre_data['barred_difficulty'] = barre_difficulty
            barre_data['barred'] = False
    return difficulty, barre_data


chromatic_scale = CircularList(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'])
flat_scale = CircularList(['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B'])
weird_sharps = {'C': 'B#', 'F': "E#"}
weird_flats = {'B': 'Cb', 'E': 'Fb'}
weird_sharp_scale = CircularList([weird_sharps.get(n, n) for n in chromatic_scale])
weird_flat_scale = CircularList([weird_flats.get(n, n) for n in flat_scale])
note_intervals = {note: index for index, note in enumerate(chromatic_scale)}
note_intervals |= {note: index for index, note in enumerate(flat_scale)}
note_intervals |= {note: index for index, note in enumerate(weird_sharp_scale)}
note_intervals |= {note: index for index, note in enumerate(weird_flat_scale)}


def normalizer(arg, scale):
    if isinstance(arg, list):
        return [scale[note_intervals[note]] for note in arg]
    return scale[note_intervals[arg]]


def sharpify(arg):
    return normalizer(arg, chromatic_scale)


def flatify(arg):
    return normalizer(arg, flat_scale)


def get_shape_notes(shape, tuning, force_flat=False):
    if force_flat:
        scale = flat_scale
    else:
        scale = chromatic_scale
    for string, position in enumerate(shape):
        if position == -1:
            continue
        yield scale[note_intervals[tuning[string]] + position]


def is_flat(note):
    return note[-1] == "b"


def get_scales():
    scales = [(["", "maj", "major"], [0, 2, 4, 5, 7, 9, 11]),
              (["m", "min", "minor"], [0, 2, 3, 5, 7, 8, 10]),
              (["mblues", "minblues", "minorblues"], [0, 3, 5, 6, 7, 10]),
              (["blues", "majblues", "majorblues"], [0, 2, 3, 4, 7, 9]),
              (["pent", "p", "pentatonic", "majpentatonic"], [0, 2, 4, 7, 9]),
              (["mpent", "mp", "minorpentatonic"], [0, 3, 5, 7, 10]),
              (['phdom'], [0, 1, 4, 5, 7, 8, 10]),
              (['phmod'], [0, 1, 3, 5, 7, 8, 10]),
              (['gypsymajor'], [0, 1, 4, 5, 7, 8, 11]),
              (['gypsyminor'], [0, 2, 3, 6, 7, 8, 11]),
              (['chromatic'], range(0, 12))
              ]

    mods = {}
    for names, intervals in scales:
        for name in names:
            mods[name] = intervals

    return mods


def get_dupe_scales_from_intervals(root, intervals):
    mods = get_scales()
    dupes = {}
    for inc in range(0, 12):
        for name, candidate_intervals in mods.items():
            transposed_intervals = [(x + inc) % 12 for x in candidate_intervals]
            if set(intervals) == set(transposed_intervals):
                transposed_root = chromatic_scale[(note_intervals[root] + inc) % 12]
                if inc in dupes:
                    continue
                dupes[inc] = f'{transposed_root}{name}'

    return {val for _, val in dupes.items()}


def get_dupe_scales_from_notes(notes):
    root = notes[0]
    intervals = [0]
    root_interval = note_intervals[root]
    for note in notes[1:]:
        interval = (note_intervals[note] - root_interval) % 12
        intervals.append(interval)
    return get_dupe_scales_from_intervals(root, intervals)


def get_dupe_scales_from_key(key):
    mods = get_scales()

    match = re.match(f'^([A-G][b#]?)({"|".join(mods.keys())})$', key)
    if not match:
        raise UnknownKeyException(f"Unknown key \"{key}\"")
    (root, extra) = match.groups()
    intervals = mods[extra]

    return get_dupe_scales_from_intervals(root, intervals) - {key}


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


def get_notes_shape_map(config, max_fret):
    notes_shapes_map = {}
    for shape in get_shapes(config, max_fret=max_fret):
        notes = frozenset(get_shape_notes(shape, tuning=config.tuning))
        if notes in notes_shapes_map:
            notes_shapes_map[notes].append(shape)
            continue
        notes_shapes_map[notes] = [shape]
    return notes_shapes_map


def get_notes_chords_map(notes_shapes_map):
    notes_chords_map = {}
    for notes in notes_shapes_map:
        notes_chords_map[notes] = get_chords(notes)
    return notes_chords_map


def populate_chord_shapes(chord_shapes, notes_shapes_map, notes_chords_map):
    for notes, chords in notes_chords_map.items():
        for chord in chords:
            if chord not in chord_shapes:
                chord_shapes[chord] = []
            for shape in notes_shapes_map[notes]:
                chord_shapes[chord].append(shape)


def scan_chords(config, chord_shapes, max_fret=12):
    if not config.no_cache and load_scanned_chords(config, chord_shapes, max_fret):
        return

    notes_shapes_map = get_notes_shape_map(config, max_fret)
    notes_chords_map = get_notes_chords_map(notes_shapes_map)
    populate_chord_shapes(chord_shapes, notes_shapes_map, notes_chords_map)

    save_scanned_chords(config, max_fret=max_fret, chord_shapes=chord_shapes)


def rank_shape_by_difficulty(shape):
    return get_shape_difficulty(shape)[0]


def rank_shape_by_high_fret(shape):
    return sorted(shape, reverse=True)

def rank_chord_name(name):
    has_symbol = False
    for char in ['+', '-', '(', ')']:
        if char in name:
            has_symbol = True
        return ("no" in name, has_symbol, len(name), name)

def get_chords_from_notes(notes, force_flat=False):
    chords = []
    for chord in get_chords(notes):
        if force_flat:
            flat_chord = flatify(Chord(chord).root) + Chord(chord).quality.quality
            chords.append(flat_chord)
        else:
            chords.append(chord)
    return sorted(chords, key=rank_chord_name)


def get_tuning(args):
    if args.tuning in ("ukulele", "ukulele-c6"):
        return list("GCEA")
    if args.tuning in ("ukulele-g6", "baritone"):
        return list("DGBE")
    if args.tuning == "guitar":
        return list("EADGBE")
    if args.tuning == "mandolin":
        return list("GDEA")
    return args.tuning.split(',')


def get_other_names(shape, chord_name, tuning):
    for chord in get_chords(set(get_shape_notes(shape, tuning))):
        if sharpify_chord(chord) != sharpify_chord(chord_name):
            yield chord


def show_chord(config, chord):
    output = {}
    if config.show_notes:
        try:
            p_chord = Chord(chord)
            notes = p_chord.components()
            output['notes'] = notes
        except ValueError as exc:
            error(2, f"Error looking up chord {chord}: {exc}")
    chord_shapes = ChordCollection()
    scan_chords(config, chord_shapes)
    if chord not in chord_shapes:
        error(1, f"No shape for \"{chord}\" found")
    shapes = chord_shapes[chord]
    shapes.sort(key=config.shape_ranker)
    other_names = None
    output['shapes'] = []
    for shape in shapes[:config.num or len(shapes)]:
        if not other_names:
            other_names = list(get_other_names(shape, chord, config.tuning))
        difficulty, barre_data = get_shape_difficulty(shape, tuning=config.tuning)
        if difficulty > config.max_difficulty:
            continue
        output['shapes'].append({
            'shape': shape, 'difficulty': difficulty, 'barre_data': barre_data,
            'chord_names': [chord] + sorted(other_names)
        })
    return output


def chord_built_from_notes(chord, notes):
    for note in sharpify(Chord(chord).components()):
        if note not in sharpify(notes):
            return False
    return True


def show_all(config):
    # pylint: disable=too-many-branches
    notes = []
    chord_shapes = ChordCollection()
    for key in config.key or []:
        try:
            notes.extend(get_key_notes(key))
        except UnknownKeyException as exc:
            error(10, exc)
    for chord in config.allowed_chord or []:
        notes.extend(Chord(chord).components())
    if notes and any(map(is_flat, notes)):
        config.force_flat = True
    scan_chords(config, chord_shapes)
    ichords = list(chord_shapes.keys())
    sort_offset = 0
    if config.key:
        sort_offset = note_intervals[get_key_notes(config.key[0])[0]]
    def chord_sorter(name):
        pos = note_intervals[Chord(name).root] - sort_offset
        return pos % len(chromatic_scale), name
    ichords.sort(key=chord_sorter)
    output = {}
    output['shapes'] = []
    for chord in ichords:
        chord_shapes[chord].sort(key=config.shape_ranker)
        if config.force_flat:
            chord = flatify(Chord(chord).root) + Chord(chord).quality.quality
        if config.qualities and Chord(chord).quality.quality not in config.qualities:
            continue
        if notes and not chord_built_from_notes(chord, notes):
            continue
        shape = chord_shapes[chord][0]
        difficulty, barre_data = get_shape_difficulty(shape, tuning=config.tuning)
        if difficulty > config.max_difficulty:
            continue
        output['shapes'].append({
            'shape': shape, 'difficulty': difficulty, 'barre_data': barre_data,
            'chord_names': [chord]
        })
    return output


def get_chords_by_shape(config, pshape):
    shapes = [pshape]
    if config.slide:
        for offset in range(1, 12):
            cshape = [(pos + offset) % 12 if pos > 0 else pos for pos in pshape]
            shapes.append(cshape)
    for shape in shapes:
        notes = set(get_shape_notes(shape, tuning=config.tuning, force_flat=config.force_flat))
        chords = get_chords_from_notes(notes, config.force_flat)
        if config.qualities:
            chords = [c for c in chords if Chord(c).quality.quality in config.qualities]
        if chords:
            yield shape, chords, notes


def show_chords_by_shape(config, pshape):
    pshape = [-1 if pos == 'x' else int(pos) for pos in pshape.split(",")]
    output = {}
    output['shapes'] = []
    def append_shape(shape, chords, notes):
        output['shapes'].append({
            'shape': shape,
            'chords': chords,
            'notes': list(notes)
        })
    for shape, chords, notes in get_chords_by_shape(config, pshape):
        append_shape(shape, chords, notes)
    if not output['shapes']:
        notes = set(get_shape_notes(pshape, tuning=config.tuning, force_flat=config.force_flat))
        append_shape(pshape, [], notes)

    if not config.slide:
        output['difficulty'], output['barre_data'] = get_shape_difficulty(pshape, config.tuning)
    return output


def show_chords_by_notes(_, notes):
    return {
        'notes': list(notes),
        'chords': get_chords_from_notes(notes)
    }


def show_key(_, key):
    output = {}
    notes = key.split(',')
    if len(notes) > 1:
        output['notes'] = notes
        output['other_keys'] = list(get_dupe_scales_from_notes(notes))
    else:
        output['key'] = key
        try:
            output['other_keys'] = list(get_dupe_scales_from_key(key))
            output['notes'] = get_key_notes(key)
        except UnknownKeyException as exc:
            error(11, exc)
    output['other_keys'].sort(key=rank_chord_name)
    return output
