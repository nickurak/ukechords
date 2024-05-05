import itertools
import re

from pychord.analyzer import notes_to_positions
from pychord import Chord, QualityManager

from .cache import load_scanned_chords, save_scanned_chords


class UnknownKeyException(Exception):
    pass


class ChordNotFoundException(ValueError):
    pass


class ShapeNotFoundException(ValueError):
    pass


def add_no5_quality():
    new_qs = []
    for name, quality in QualityManager().get_qualities().items():
        no5name = name + "no5"
        if "/" in name or 7 not in quality.components:
            continue
        new = tuple(filter(lambda x: x != 7, quality.components))
        new_qs.append((no5name, new))
    for name, new in new_qs:
        QualityManager().set_quality(name, new)


def add_7sus2_quality():
    new_qs = []
    for name, quality in QualityManager().get_qualities().items():
        if name != "sus2":
            continue
        components = list(quality.components)
        components.append(10)
        new_name = f"7{name}"
        new_qs.append((new_name, tuple(components)))
    for name, new in new_qs:
        QualityManager().set_quality(name, new)


def _find_pychord_from_notes(notes):
    """Faster version of pychord's find_chord_from_notes

    This is a faster version of pychord's find_chord_from_notes, which
    explicitly doesn't handle slash chords, to improve our chord
    lookup performance. Note that, unlike our get_chords
    functionality, this code requires that the notes/note-intervals be
    in-order
    """
    root = notes[0]
    positions = notes_to_positions(notes, root)
    quality = QualityManager().find_quality_from_components(positions)
    if quality is None:
        return None
    return Chord(f"{root}{quality}")


def _get_chords_from_notes(notes, force_flat=False):
    if not notes:
        return []
    chords = []
    for seq in itertools.permutations(notes):
        chord = _find_pychord_from_notes(seq)
        if chord is None:
            continue
        if force_flat:
            flat_chord = _flatify(chord.chord)
            chords.append(flat_chord)
        else:
            chords.append(chord.chord)
    return sorted(chords, key=_rank_chord_name)


class _CircularList(list):
    def __getitem__(self, index):
        return super().__getitem__(index % len(self))


def _normalize_chord(chord):
    """For duplicate and match detection, convert to a canonical
    sharp version, including replacing "maj" with "M" per pychord
    convention."""
    match = re.match("^([A-G][b#]?)(.*)$", chord)
    (root, quality) = match.groups()
    quality = quality.replace("maj", "M")
    return f"{_sharpify(root)}{quality}"


class _ChordCollection:
    def __init__(self):
        self.dictionary = {}

    def __contains__(self, chord):
        return _normalize_chord(chord) in self.dictionary

    def __setitem__(self, chord, val):
        self.dictionary[_normalize_chord(chord)] = val

    def __getitem__(self, chord):
        return self.dictionary[_normalize_chord(chord)]

    def keys(self):
        return self.dictionary.keys()


def _increment(position, max_pos, base=0):
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


def _get_shapes(config, max_fret=1):
    shape = [config.base] * len(config.tuning)
    while True:
        if max(shape) >= 0 and _get_shape_difficulty(shape)[0] <= config.max_difficulty:
            yield list(shape)
        if not _increment(shape, max_fret, base=config.base):
            return


def _barreless_shape_difficulty(shape):
    difficulty = 0.0 + max(shape) / 10.0
    last_fretted_position = None
    for string, position in enumerate(shape):
        if position > 0:
            if last_fretted_position:
                difficulty += (position - last_fretted_position - 1) ** 2 / 1.5
            last_fretted_position = position
        elif last_fretted_position:
            difficulty += 1
        if position < 0:
            if string in [0, len(shape) - 1]:
                difficulty += 5
            else:
                difficulty += 7
        else:
            difficulty += position
    return difficulty


def _get_tuned_barre_details(shape, tuning, barre_difficulty, unbarred_difficulty):
    if not tuning:
        return None
    barre_shape = [x - min(shape) for x in shape]
    chords = sorted(_get_chords_from_notes(set(_get_shape_notes(barre_shape, tuning=tuning))))
    chords.sort(key=_rank_chord_name)
    chord = chords[0] if len(chords) > 0 else None
    barre_data = {
        "fret": min(shape),
        "barred": barre_difficulty < unbarred_difficulty,
        "shape": barre_shape,
        "chord": chord,
    }
    if barre_data["barred"]:
        barre_data["unbarred_difficulty"] = unbarred_difficulty
    else:
        barre_data["barred_difficulty"] = barre_difficulty
    return barre_data


def _barre_difficulty_details(shape, unbarred_difficulty, tuning):
    barre_difficulty = None
    barrable = len([1 for pos in shape if pos == min(shape)])
    if not (barrable > 1 and min(shape) > 0):
        return unbarred_difficulty, None

    barre_shape = [x - min(shape) for x in shape]
    min_barre_extra = min([0, *filter(lambda x: x > 0, barre_shape)])
    barre_difficulty = _get_shape_difficulty(barre_shape, tuning=tuning)[0] * 2.2
    barre_difficulty += min(shape) * 3.0 + min_barre_extra * 4.0

    barred = barre_difficulty < unbarred_difficulty
    difficulty = barre_difficulty if barred else unbarred_difficulty
    details = _get_tuned_barre_details(shape, tuning, barre_difficulty, unbarred_difficulty)
    return difficulty, details


def _get_shape_difficulty(shape, tuning=None):
    difficulty = _barreless_shape_difficulty(shape)
    difficulty, barre_data = _barre_difficulty_details(shape, difficulty, tuning)
    return difficulty, barre_data


_chromatic_scale = _CircularList(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])
_flat_scale = _CircularList(["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"])
_weird_sharps = {"C": "B#", "F": "E#"}
_weird_flats = {"B": "Cb", "E": "Fb"}
_weird_sharp_scale = _CircularList([_weird_sharps.get(n, n) for n in _chromatic_scale])
_weird_flat_scale = _CircularList([_weird_flats.get(n, n) for n in _flat_scale])
_note_intervals = {note: index for index, note in enumerate(_chromatic_scale)}
_note_intervals |= {note: index for index, note in enumerate(_flat_scale)}
_note_intervals |= {note: index for index, note in enumerate(_weird_sharp_scale)}
_note_intervals |= {note: index for index, note in enumerate(_weird_flat_scale)}


def _normalizer(arg, scale):
    if isinstance(arg, list):
        return [scale[_note_intervals[note]] for note in arg]
    return scale[_note_intervals[arg]]


def _sharpify(arg):
    return _normalizer(arg, _chromatic_scale)


def _flatify(arg):
    return _normalizer(arg, _flat_scale)


def _get_shape_notes(shape, tuning, force_flat=False):
    if force_flat:
        scale = _flat_scale
    else:
        scale = _chromatic_scale
    for string, position in enumerate(shape):
        if position == -1:
            continue
        yield scale[_note_intervals[tuning[string]] + position]


def _is_flat(note):
    return note[-1] == "b"


def _get_scales():
    scales = [
        (["", "maj", "major"], [0, 2, 4, 5, 7, 9, 11]),
        (["m", "min", "minor"], [0, 2, 3, 5, 7, 8, 10]),
        (["mblues", "minblues", "minorblues"], [0, 3, 5, 6, 7, 10]),
        (["blues", "majblues", "majorblues"], [0, 2, 3, 4, 7, 9]),
        (["pent", "p", "pentatonic", "majpentatonic"], [0, 2, 4, 7, 9]),
        (["mpent", "mp", "minorpentatonic"], [0, 3, 5, 7, 10]),
        (["phdom"], [0, 1, 4, 5, 7, 8, 10]),
        (["phmod"], [0, 1, 3, 5, 7, 8, 10]),
        (["gypsymajor"], [0, 1, 4, 5, 7, 8, 11]),
        (["gypsyminor"], [0, 2, 3, 6, 7, 8, 11]),
        (["chromatic"], range(0, 12)),
    ]

    mods = {}
    for names, intervals in scales:
        for name in names:
            mods[name] = intervals

    return mods


def _get_dupe_scales_from_intervals(root, intervals):
    mods = _get_scales()
    dupes = {}
    for inc in range(0, 12):
        for name, candidate_intervals in mods.items():
            transposed_intervals = [(x + inc) % 12 for x in candidate_intervals]
            if set(intervals) == set(transposed_intervals):
                transposed_root = _chromatic_scale[(_note_intervals[root] + inc) % 12]
                if inc in dupes:
                    continue
                dupes[inc] = f"{transposed_root}{name}"

    return {val for _, val in dupes.items()}


def _get_dupe_scales_from_notes(notes):
    root = notes[0]
    intervals = [0]
    root_interval = _note_intervals[root]
    for note in notes[1:]:
        interval = (_note_intervals[note] - root_interval) % 12
        intervals.append(interval)
    return _get_dupe_scales_from_intervals(root, intervals)


def _get_dupe_scales_from_key(key):
    mods = _get_scales()

    match = re.match(f'^([A-G][b#]?)({"|".join(mods.keys())})$', key)
    if not match:
        raise UnknownKeyException(f'Unknown key "{key}"')
    (root, extra) = match.groups()
    intervals = mods[extra]

    return _get_dupe_scales_from_intervals(root, intervals) - {key}


def _get_key_notes(key):
    mods = _get_scales()

    match = re.match(f'^([A-G][b#]?)({"|".join(mods.keys())})$', key)
    if not match:
        raise UnknownKeyException(f'Unknown key "{key}"')
    (root, extra) = match.groups()
    intervals = mods[extra]
    if _is_flat(root):
        return [_flat_scale[interval + _note_intervals[root]] for interval in intervals]
    return [_chromatic_scale[interval + _note_intervals[root]] for interval in intervals]


def _get_notes_shape_map(config, max_fret):
    notes_shapes_map = {}
    for shape in _get_shapes(config, max_fret=max_fret):
        notes = frozenset(_get_shape_notes(shape, tuning=config.tuning))
        if notes in notes_shapes_map:
            notes_shapes_map[notes].append(shape)
            continue
        notes_shapes_map[notes] = [shape]
    return notes_shapes_map


def _get_notes_chords_map(notes_shapes_map):
    notes_chords_map = {}
    for notes in notes_shapes_map:
        notes_chords_map[notes] = _get_chords_from_notes(notes)
    return notes_chords_map


def _populate_chord_shapes(chord_shapes, notes_shapes_map, notes_chords_map):
    for notes, chords in notes_chords_map.items():
        for chord in chords:
            if chord not in chord_shapes:
                chord_shapes[chord] = []
            for shape in notes_shapes_map[notes]:
                chord_shapes[chord].append(shape)


def scan_chords(config, chord_shapes, max_fret=12):
    if not config.no_cache and load_scanned_chords(config, chord_shapes, max_fret):
        return

    notes_shapes_map = _get_notes_shape_map(config, max_fret)
    notes_chords_map = _get_notes_chords_map(notes_shapes_map)
    _populate_chord_shapes(chord_shapes, notes_shapes_map, notes_chords_map)

    save_scanned_chords(config, max_fret=max_fret, chord_shapes=chord_shapes)


def rank_shape_by_difficulty(shape):
    return _get_shape_difficulty(shape)[0]


def rank_shape_by_high_fret(shape):
    return sorted(shape, reverse=True)


def _rank_chord_name(name):
    has_symbol = False
    for char in ["+", "-", "(", ")"]:
        if char in name:
            has_symbol = True
        return ("no" in name, has_symbol, len(name), name)


def get_tuning(tuning_spec):
    if tuning_spec in ("ukulele", "ukulele-c6"):
        return list("GCEA")
    if tuning_spec in ("ukulele-g6", "baritone"):
        return list("DGBE")
    if tuning_spec == "guitar":
        return list("EADGBE")
    if tuning_spec == "mandolin":
        return list("GDAE")
    return tuning_spec.split(",")


def _get_other_names(shape, chord_name, tuning):
    for chord in _get_chords_from_notes(set(_get_shape_notes(shape, tuning))):
        if _normalize_chord(chord) != _normalize_chord(chord_name):
            yield chord


def show_chord(config, chord):
    output = {}
    if config.show_notes:
        try:
            p_chord = Chord(chord)
            notes = p_chord.components()
            output["notes"] = notes
        except ValueError as exc:
            raise ChordNotFoundException(f"Error looking up chord {chord}") from exc
    chord_shapes = _ChordCollection()
    scan_chords(config, chord_shapes)
    if chord not in chord_shapes:
        raise ShapeNotFoundException(f'No shape for "{chord}" found')
    shapes = chord_shapes[chord]
    shapes.sort(key=config.shape_ranker)
    other_names = None
    output["shapes"] = []
    for shape in shapes[: config.num or len(shapes)]:
        if not other_names:
            other_names = list(_get_other_names(shape, chord, config.tuning))
        difficulty, barre_data = _get_shape_difficulty(shape, tuning=config.tuning)
        if difficulty > config.max_difficulty:
            continue
        output["shapes"].append(
            {
                "shape": shape,
                "difficulty": difficulty,
                "barre_data": barre_data,
                "chord_names": [chord] + sorted(other_names),
            }
        )
    return output


def _chord_built_from_notes(chord, notes):
    for note in _sharpify(Chord(chord).components()):
        if note not in _sharpify(notes):
            return False
    return True


def show_all(config):
    notes = []
    chord_shapes = _ChordCollection()
    for key in config.key or []:
        notes.extend(_get_key_notes(key))
    for chord in config.allowed_chords or []:
        notes.extend(Chord(chord).components())
    if notes and any(map(_is_flat, notes)):
        config.force_flat = True
    scan_chords(config, chord_shapes)
    ichords = list(chord_shapes.keys())
    sort_offset = 0
    if config.key:
        sort_offset = _note_intervals[_get_key_notes(config.key[0])[0]]

    def chord_sorter(name):
        pos = _note_intervals[Chord(name).root] - sort_offset
        return pos % len(_chromatic_scale), name

    ichords.sort(key=chord_sorter)
    output = {}
    output["shapes"] = []
    for chord in ichords:
        chord_shapes[chord].sort(key=config.shape_ranker)
        if config.force_flat:
            chord = _flatify(Chord(chord).root) + Chord(chord).quality.quality
        if config.qualities and Chord(chord).quality.quality not in config.qualities:
            continue
        if notes and not _chord_built_from_notes(chord, notes):
            continue
        shape = chord_shapes[chord][0]
        difficulty, barre_data = _get_shape_difficulty(shape, tuning=config.tuning)
        if difficulty > config.max_difficulty:
            continue
        output["shapes"].append(
            {
                "shape": shape,
                "difficulty": difficulty,
                "barre_data": barre_data,
                "chord_names": [chord],
            }
        )
    return output


def _get_chords_by_shape(config, pshape):
    shapes = []
    if config.slide:
        fretted_positions = [fret for fret in pshape if fret > 0]
        min_fret = min(fretted_positions)
        unslid_shape = [fret + 1 - min_fret if fret > 0 else 0 for fret in pshape]
        for offset in range(0, 12):
            cshape = [pos + offset if pos > 0 else pos for pos in unslid_shape]
            shapes.append(cshape)
    else:
        shapes.append(pshape)
    for shape in shapes:
        notes = set(_get_shape_notes(shape, tuning=config.tuning, force_flat=config.force_flat))
        chords = _get_chords_from_notes(notes, config.force_flat)
        if config.qualities:
            chords = [c for c in chords if Chord(c).quality.quality in config.qualities]
        if chords:
            yield shape, chords, notes


def show_chords_by_shape(config, pshape):
    pshape = [-1 if pos == "x" else int(pos) for pos in pshape.split(",")]
    output = {}
    output["shapes"] = []

    def append_shape(shape, chords, notes):
        output["shapes"].append({"shape": shape, "chords": chords, "notes": list(notes)})

    for shape, chords, notes in _get_chords_by_shape(config, pshape):
        append_shape(shape, chords, notes)
    if not output["shapes"]:
        notes = set(_get_shape_notes(pshape, tuning=config.tuning, force_flat=config.force_flat))
        append_shape(pshape, [], notes)

    if not config.slide:
        output["difficulty"], output["barre_data"] = _get_shape_difficulty(pshape, config.tuning)
    return output


def show_chords_by_notes(_, notes):
    return {"notes": list(notes), "chords": _get_chords_from_notes(notes)}


def show_key(_, key):
    output = {}
    notes = key.split(",")
    if len(notes) > 1:
        output["notes"] = notes
        output["other_keys"] = list(_get_dupe_scales_from_notes(notes))
    else:
        output["key"] = key
        output["other_keys"] = list(_get_dupe_scales_from_key(key))
        output["notes"] = _get_key_notes(key)
    output["other_keys"].sort(key=_rank_chord_name)
    return output
