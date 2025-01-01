"""Logic related to music-theory, mostly for stringed instruments"""

from itertools import permutations, product
from functools import cache
import re

from typing import List

from pychord.analyzer import notes_to_positions
from pychord import Chord, QualityManager

from .cache import load_scanned_chords, save_scanned_chords
from .errors import UnknownKeyException, ChordNotFoundException


def add_no5_quality() -> None:
    """Add a fifth-less variant to many of pychord's known qualities"""
    for orig_name, quality in list(QualityManager().get_qualities().items()):
        if "/" in orig_name or 7 not in quality.components or len(quality.components) < 4:
            continue
        new = tuple(filter(lambda x: x != 7, quality.components))
        QualityManager().set_quality(f"{orig_name}no5", new)


def add_7sus2_quality() -> None:
    """Add a 7sus2 quality to pychord's known qualities"""
    sus2 = QualityManager().get_quality("sus2")
    new = (*sus2.components, 10)
    QualityManager().set_quality("7sus2", new)


@cache
def _get_quality_map():
    """
    Return a mapping of all {intervals}->quality relationships by
    reversing pychord's quality db.

    This will be used to rapidly look up qualities.
    """
    quality_map = {}
    for name, quality in QualityManager().get_qualities().items():
        if quality.components not in quality_map:
            quality_map[quality.components] = name
    return quality_map


@cache
def _get_chords_from_notes(notes, force_flat=False):
    """
    Return a list of chords the specified notes will generate, with no
    consideration to the order of those notes. Returns flat versions
    of those chords if force_flat is True.
    """
    if not notes:
        return []
    chords = []
    for seq in permutations(notes):
        root = seq[0]
        positions = tuple(notes_to_positions(seq, root))
        if (quality := _get_quality_map().get(positions)) is None:
            continue
        chord = f"{root}{quality}"
        if force_flat:
            chord = _flatify(chord)
        chords.append(chord)
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


class _ChordCollection(dict):
    def __contains__(self, chord, *args, **kwargs):
        return super().__contains__(_normalize_chord(chord), *args, **kwargs)

    def __setitem__(self, chord, *args, **kwargs):
        super().__setitem__(_normalize_chord(chord), *args, **kwargs)

    def __getitem__(self, chord, *args, **kwargs):
        return super().__getitem__(_normalize_chord(chord), *args, **kwargs)


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
    barre_shape = tuple(x - min(shape) for x in shape)
    chords = sorted(_get_chords_from_notes(frozenset(_get_shape_notes(barre_shape, tuning=tuning))))
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
    """
    Return information on how using a barre to play the given shape
    (if possible) affects the shape's difficulty.
    """
    barre_difficulty = None
    barre_level = min(shape)
    barrable = len([1 for pos in shape if pos == barre_level])
    if not (barrable > 1 and barre_level > 0):
        return unbarred_difficulty, None

    barre_shape = [x - barre_level for x in shape]
    barre_difficulty = _get_shape_difficulty(barre_shape, tuning=tuning)[0] * 2.2
    barre_difficulty += barre_level * 3.0

    barred = barre_difficulty < unbarred_difficulty
    difficulty = barre_difficulty if barred else unbarred_difficulty
    details = _get_tuned_barre_details(shape, tuning, barre_difficulty, unbarred_difficulty)
    return difficulty, details


def _get_shape_difficulty(shape, tuning=None):
    """
    Return a heuristic for how hard a shape is to play, including
    information on how barreing the shape affects that difficulty
    where appropriate.
    """
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


@cache
def _get_shape_notes(shape, tuning, force_flat=False):
    """
    For a given shape in a specified tuning, return the notes played
    by thet shape.

    If force_flat is True, return flat versions of those notes as
    appropriate.
    """
    notes = ()
    if force_flat:
        scale = _flat_scale
    else:
        scale = _chromatic_scale
    for string, position in enumerate(shape):
        if position == -1:
            continue
        notes = notes + (scale[_note_intervals[tuning[string]] + position],)
    return notes


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


def _get_shapes(config, max_fret=1):
    """
    Yield shapes playable on the fretboard, (optionally including
    muted strings) up to the specified fret.

    Shapes which are ranked as too-difficult based on the provided
    configuration will be excluded.

    """
    string_range = range(0, len(config.tuning))
    fret_range = range(-1 if config.mute else 0, max_fret + 1)
    for shape in product(*[fret_range for _ in string_range]):
        if max(shape) >= 0 and _get_shape_difficulty(shape)[0] <= config.max_difficulty:
            yield tuple(shape)


def scan_chords(config, chord_shapes, max_fret=12) -> None:
    """
    Based on the provided configuration, scan for possible ways to
    play chords. Store discovered shapes in a ChordCollection that
    maps chords to a list of shapes that will generate the notes of
    that chord.
    """
    if not config.no_cache and load_scanned_chords(config, chord_shapes, max_fret):
        return

    for shape in _get_shapes(config, max_fret=max_fret):
        notes = frozenset(_get_shape_notes(shape, tuning=config.tuning))
        for chord in _get_chords_from_notes(notes):
            if chord not in chord_shapes:
                chord_shapes[chord] = []
            chord_shapes[chord].append(shape)

    save_scanned_chords(config, max_fret=max_fret, chord_shapes=chord_shapes)


def rank_shape_by_difficulty(shape) -> tuple:
    """Enable sorting a list of shapes by how hard they are to play"""
    return (_get_shape_difficulty(shape)[0], shape[::-1])


def rank_shape_by_high_fret(shape) -> List:
    '''Enable sorting a list of shapes by how high their fret usage.
    This accomplishes finding chord shapes by "first position"'''
    return sorted(shape, reverse=True)


def _rank_chord_name(name):
    has_symbol = False
    for char in ["+", "-", "(", ")"]:
        if char in name:
            has_symbol = True
        return ("no" in name, has_symbol, len(name), name)


def get_tuning(tuning_spec) -> tuple[str, ...]:
    """For a given tuning (by name or comma-separated notes), return
    the notes in order
    """
    if tuning_spec in ("ukulele", "ukulele-c6", "uke", "u"):
        return tuple("GCEA")
    if tuning_spec in ("ukulele-g6", "baritone"):
        return tuple("DGBE")
    if tuning_spec in ("guitar", "g"):
        return tuple("EADGBE")
    if tuning_spec == "mandolin":
        return tuple("GDAE")
    return tuple(tuning_spec.split(","))


def _get_other_names(shape, chord_name, tuning):
    for chord in _get_chords_from_notes(_get_shape_notes(shape, tuning)):
        if _normalize_chord(chord) != _normalize_chord(chord_name):
            yield chord


def show_chord(config, chord) -> dict:
    """Return information on how to play a given chord, including:

    - Shape options for playing it, including their difficulty and
      barre instructions
    - Other names
    - Optionally the notes in the chord, if config.show_notes is set
    """
    output = {}
    try:
        p_chord = Chord(chord)
    except ValueError as exc:
        raise ChordNotFoundException(f'Error looking up chord "{chord}"') from exc
    if config.show_notes:
        notes = p_chord.components()
        output["notes"] = notes
    chord_shapes = _ChordCollection()
    scan_chords(config, chord_shapes)
    if chord not in chord_shapes:
        output["chord"] = chord
        output["shapes"] = []
        return output
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


def show_all(config) -> dict:
    """Return one way to play each known/specified chord

    If config.{key,qualities,allowed_chords} are set, they will
    restrict which chords are returned accordingly
    """
    notes = []
    chord_shapes = _ChordCollection()
    for key in config.keys or []:
        notes.extend(_get_key_notes(key))
    for chord in config.allowed_chords or []:
        notes.extend(Chord(chord).components())
    if notes and any(map(_is_flat, notes)):
        config.force_flat = True
    scan_chords(config, chord_shapes)
    ichords = list(chord_shapes.keys())
    sort_offset = 0
    if config.keys:
        sort_offset = _note_intervals[_get_key_notes(config.keys[0])[0]]

    def chord_sorter(name):
        pos = _note_intervals[Chord(name).root] - sort_offset
        return pos % len(_chromatic_scale), name

    ichords.sort(key=chord_sorter)
    output: dict = {}
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
        min_fret = min(fret for fret in pshape if fret > 0)
        unslid_shape = tuple(fret + 1 - min_fret if fret > 0 else fret for fret in pshape)
        for offset in range(0, 12):
            cshape = tuple(pos + offset if pos > 0 else pos for pos in unslid_shape)
            shapes.append(cshape)
    else:
        shapes.append(pshape)
    for shape in shapes:
        notes = _get_shape_notes(shape, tuning=config.tuning, force_flat=config.force_flat)
        chords = _get_chords_from_notes(frozenset(notes), config.force_flat)
        if config.qualities:
            chords = [c for c in chords if Chord(c).quality.quality in config.qualities]
        if chords:
            yield shape, chords, set(notes)


def show_chords_by_shape(config, pshape) -> dict:
    """Return information on what chords are generated by a specified shape"""
    pshape = tuple(-1 if pos == "x" else int(pos) for pos in pshape.split(","))
    output: dict = {}
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


def show_chords_by_notes(_, notes) -> dict:
    """Return information on what chords are played by the specified notes"""
    return {"notes": list(notes), "chords": _get_chords_from_notes(tuple(notes))}


def show_key(_, key) -> dict:
    """Return information on the specified key, including other names and the notes it includes"""
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
