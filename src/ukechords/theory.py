"""Logic related to music-theory, mostly for stringed instruments"""

from __future__ import annotations

from itertools import permutations, product
from functools import cache
import multiprocessing as mp
import os
from typing import Generator, Iterable, NoReturn

from pychord.analyzer import notes_to_positions
from pychord import Chord, QualityManager

from .cache import load_scanned_chords, save_scanned_chords
from .errors import ChordNotFoundException
from .errors import UnslidableEmptyShapeException, UnknownTuningException

from .theory_basic import ChordCollection, sharpify, flatify, normalize_chord
from .theory_basic import flat_scale, chromatic_scale, note_intervals
from .theory_basic import get_key_notes, get_dupe_scales_from_notes, is_flat

from .types import KeyInfo, ChordsByShape, Shape
from .types import BarreData, ChordShapes
from .config import UkeConfig


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
def _get_quality_map() -> dict[tuple[int, ...], str]:
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
def _get_chords_from_notes(notes: Iterable[str], force_flat: bool = False) -> list[str]:
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
        positions: tuple[int, ...] = tuple(notes_to_positions(seq, root))
        if (quality := _get_quality_map().get(positions)) is None:
            continue
        if force_flat:
            chord = f"{flatify(root)}{quality}"
        else:
            chord = f"{root}{quality}"
        chords.append(chord)
    return sorted(chords, key=_rank_chord_name)


def _barreless_shape_difficulty(shape: tuple[int, ...]) -> float:
    difficulty: float = 0.0 + max(shape) / 10.0
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


def _get_tuned_barre_details(
    shape: tuple[int, ...],
    tuning: tuple[str, ...] | None,
    barre_difficulty: float,
    unbarred_difficulty: float,
) -> BarreData | None:
    if not tuning:
        return None
    barre_shape = tuple(x - min(shape) for x in shape)
    chords = sorted(_get_chords_from_notes(frozenset(_get_shape_notes(barre_shape, tuning=tuning))))
    chords.sort(key=_rank_chord_name)
    chord = chords[0] if len(chords) > 0 else None
    barre_data: BarreData = {
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


def _barre_difficulty_details(
    shape: tuple[int, ...], unbarred_difficulty: float, tuning: tuple[str, ...] | None
) -> tuple[float, BarreData | None]:
    """
    Return information on how using a barre to play the given shape
    (if possible) affects the shape's difficulty.
    """
    barre_level = min(shape)
    barrable = len([1 for pos in shape if pos == barre_level])
    if not (barrable > 1 and barre_level > 0):
        return unbarred_difficulty, None

    barre_shape = tuple(x - barre_level for x in shape)
    barre_difficulty = _get_shape_difficulty(barre_shape, tuning=tuning)[0] * 2.2
    barre_difficulty += barre_level * 3.0
    barre_difficulty += max(barre_shape) ** 3 / 50

    barred = barre_difficulty < unbarred_difficulty
    difficulty = barre_difficulty if barred else unbarred_difficulty
    details = _get_tuned_barre_details(shape, tuning, barre_difficulty, unbarred_difficulty)
    return difficulty, details


def _get_shape_difficulty(
    shape: tuple[int, ...], tuning: tuple[str, ...] | None = None
) -> tuple[float, BarreData | None]:
    """
    Return a heuristic for how hard a shape is to play, including
    information on how barreing the shape affects that difficulty
    where appropriate.
    """
    difficulty = _barreless_shape_difficulty(shape)
    difficulty, barre_data = _barre_difficulty_details(shape, difficulty, tuning)
    return difficulty, barre_data


def _get_shape_notes(
    shape: tuple[int, ...], tuning: tuple[str, ...], force_flat: bool = False
) -> tuple[str, ...]:
    """
    For a given shape in a specified tuning, return the notes played
    by thet shape.

    If force_flat is True, return flat versions of those notes as
    appropriate.
    """
    notes: tuple[str, ...] = ()
    if force_flat:
        scale = flat_scale
    else:
        scale = chromatic_scale
    for string, position in enumerate(shape):
        if position == -1:
            continue
        notes = notes + (scale[note_intervals[tuning[string]] + position],)
    return notes


def _get_shapes(
    config: UkeConfig,
    max_fret: int = 1,
    notes: tuple[str, ...] | None = None,
    partition: int = 0,
    partitions: int = 1,
) -> Generator[tuple[int, ...], None, None]:
    """
    Yield shapes playable on the fretboard, (optionally including
    muted strings) up to the specified fret.

    Shapes which are ranked as too-difficult based on the provided
    configuration will be excluded.

    if notes is specified, limit shapes to those that only use those notes
    """
    string_fret_options = []
    fret_range = range(-1 if config.mute else 0, max_fret + 1)
    notes_set: set[str] = set()
    if notes:
        notes_set = set(flatify(list(notes)))
    for i, string_note in enumerate(config.tuning):
        fret_options = []
        for pos in fret_range:
            if i == 0 and pos % partitions != partition:
                continue
            if not notes or pos == -1 or flat_scale[note_intervals[string_note] + pos] in notes_set:
                fret_options.append(pos)
        string_fret_options.append(fret_options)
    for shape in product(*string_fret_options):
        if max(shape) >= 0 and _get_shape_difficulty(shape)[0] <= config.max_difficulty:
            yield tuple(shape)


def _get_chord_shapes_map(
    config: UkeConfig,
    max_fret: int,
    allowed_notes: tuple[str, ...] | None = None,
    partition: int = 0,
    partitions: int = 1,
) -> ChordCollection:
    my_shapes = ChordCollection()
    for shape in _get_shapes(config, max_fret, allowed_notes, partition, partitions):
        notes = frozenset(_get_shape_notes(shape, tuning=config.tuning))
        for chord in _get_chords_from_notes(notes):
            if chord not in my_shapes:
                my_shapes[chord] = []
            my_shapes[chord].append(shape)
    return my_shapes


def _scan_chords(
    config: UkeConfig,
    chord_shapes: ChordCollection,
    max_fret: int = 12,
    notes: tuple[str, ...] | None = None,
) -> None:
    """
    Based on the provided configuration, scan for possible ways to
    play chords. Store discovered shapes in a ChordCollection that
    maps chords to a list of shapes that will generate the notes of
    that chord.
    """
    if not (notes or config.no_cache):
        if load_scanned_chords(config, chord_shapes, max_fret):
            return

    def mp_merge_shapes(mp_shapes: ChordCollection) -> None:
        for chord, shapes in mp_shapes.items():
            if chord not in chord_shapes:
                chord_shapes[chord] = []
            chord_shapes[chord].extend(shapes)

    partitions = cpu_count * 2 if (cpu_count := os.cpu_count()) is not None else 1
    with mp.get_context("fork").Pool() as pool:

        def mp_error(e: BaseException) -> NoReturn:
            pool.terminate()
            raise e

        for partition in range(0, partitions):
            args = (config, max_fret, notes, partition, partitions)
            pool.apply_async(
                _get_chord_shapes_map, args=args, callback=mp_merge_shapes, error_callback=mp_error
            )
        pool.close()
        pool.join()

    if notes:
        return
    save_scanned_chords(config, max_fret=max_fret, chord_shapes=chord_shapes)


def rank_shape_by_difficulty(shape: tuple[int, ...]) -> tuple[float, tuple[int, ...]]:
    """Enable sorting a list of shapes by how hard they are to play"""
    return _get_shape_difficulty(shape)[0], shape[::-1]


def rank_shape_by_high_fret(shape: tuple[int, ...]) -> tuple[int, ...]:
    """Enable sorting a list of shapes by how high their fret usage.
    This accomplishes finding chord shapes by "first position\" """
    return tuple(sorted(shape, reverse=True))


def _rank_chord_name(name: str) -> tuple[bool, bool, int, str]:
    has_symbol = False
    for char in ["+", "-", "(", ")"]:
        if char in name:
            has_symbol = True
    return "no" in name, has_symbol, len(name), name


def lookup_tuning(tuning_spec: str) -> tuple[str, ...]:
    """For a given named tunting, return the notes in order"""
    if tuning_spec in ("ukulele", "ukulele-c6", "uke", "u"):
        return tuple("GCEA")
    if tuning_spec in ("ukulele-g6", "baritone"):
        return tuple("DGBE")
    if tuning_spec in ("guitar", "g"):
        return tuple("EADGBE")
    if tuning_spec == "mandolin":
        return tuple("GDAE")
    if tuning_spec == "bass":
        return tuple("EADG")
    raise UnknownTuningException(f"Unknown tuning: {tuning_spec}")


def _get_other_names(
    shape: tuple[int, ...], chord_name: str, tuning: tuple[str, ...]
) -> Generator[str, None, None]:
    for chord in _get_chords_from_notes(_get_shape_notes(shape, tuning)):
        if normalize_chord(chord) != normalize_chord(chord_name):
            yield chord


def show_chord(config: UkeConfig, chord: str) -> ChordShapes:
    """Return information on how to play a given chord, including:

    - Shape options for playing it, including their difficulty and
      barre instructions
    - Other names
    - Optionally the notes in the chord, if config.show_notes is set
    """
    output: ChordShapes = {"shapes": []}
    try:
        p_chord = Chord(chord)
    except ValueError as exc:
        raise ChordNotFoundException(f'Error looking up chord "{chord}"') from exc
    notes = p_chord.components()
    if config.show_notes:
        notes = tuple(p_chord.components())
        output["notes"] = notes
    chord_shapes = ChordCollection()
    _scan_chords(config, chord_shapes, notes=notes)
    if chord not in chord_shapes:
        output["chord"] = chord
        return output
    shapes = chord_shapes[chord]
    shapes.sort(key=config.shape_ranker)
    other_names = None
    for shape in shapes[: config.num or len(shapes)]:
        if not other_names:
            other_names = list(_get_other_names(shape, chord, config.tuning))
        difficulty, barre_data = _get_shape_difficulty(shape, tuning=config.tuning)
        output["shapes"].append(
            {
                "shape": shape,
                "difficulty": difficulty,
                "barre_data": barre_data,
                "chord_names": [chord] + sorted(other_names),
            }
        )
    return output


def _chord_built_from_notes(chord: str, notes: tuple[str, ...]) -> bool:
    for note in sharpify(Chord(chord).components()):
        if note not in sharpify(list(notes)):
            return False
    return True


def show_all(config: UkeConfig) -> ChordShapes:
    """Return one way to play each known/specified chord

    If config.{key,qualities,allowed_chords} are set, they will
    restrict which chords are returned accordingly
    """
    notes: list[str] = []
    chord_shapes = ChordCollection()
    for key in config.keys or []:
        notes.extend(get_key_notes(key))
    for chord in config.allowed_chords or []:
        notes.extend(Chord(chord).components())
    if notes and any(map(is_flat, notes)):
        config.force_flat = True
    _scan_chords(config, chord_shapes, notes=tuple(notes))
    ichords = list(chord_shapes.keys())
    sort_offset = 0
    if config.keys:
        sort_offset = note_intervals[get_key_notes(config.keys[0])[0]]

    def chord_sorter(name: str) -> tuple[int, str]:
        pos = note_intervals[Chord(name).root] - sort_offset
        return pos % len(chromatic_scale), name

    ichords.sort(key=chord_sorter)
    output: ChordShapes = {"shapes": []}
    for chord in ichords:
        chord_shapes[chord].sort(key=config.shape_ranker)
        if config.force_flat:
            chord = flatify(Chord(chord).root) + Chord(chord).quality.quality
        if config.qualities and Chord(chord).quality.quality not in config.qualities:
            continue
        if notes and not _chord_built_from_notes(chord, tuple(notes)):
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


def _get_chords_by_shape(
    config: UkeConfig, pshape: tuple[int, ...]
) -> Generator[tuple[tuple[int, ...], list[str], set[str]], None, None]:
    shapes = []
    if config.slide:
        if not any(fret > 0 for fret in pshape):
            raise UnslidableEmptyShapeException("Sliding an empty shape doesn't make sense")
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


def show_chords_by_shape(config: UkeConfig, input_shape: tuple[str, ...]) -> ChordsByShape:
    """Return information on what chords are generated by a specified shape"""
    pshape = tuple(-1 if pos == "x" else int(pos) for pos in input_shape)
    shapes: list[Shape] = []

    for shape, chords, notes in _get_chords_by_shape(config, pshape):
        shapes.append({"shape": shape, "chords": chords, "notes": tuple(notes)})
    if not shapes:
        notes = set(_get_shape_notes(pshape, tuning=config.tuning, force_flat=config.force_flat))
        shapes.append({"shape": pshape, "chords": [], "notes": tuple(notes)})

    if not config.slide:
        difficulty, barre_data = _get_shape_difficulty(pshape, config.tuning)
        return {"shapes": shapes, "difficulty": difficulty, "barre_data": barre_data}
    return {"shapes": shapes}


def show_chords_by_notes(config: UkeConfig, notes: set[str]) -> ChordShapes:
    """Return information on what chords are played by the specified notes"""
    normalizer = sharpify
    if config.force_flat or any(note[-1] == "b" for note in notes):
        normalizer = flatify
    output: ChordShapes = {"notes": normalizer(tuple(notes)), "shapes": []}
    shapes = []
    for shape in _get_shapes(config, 12, notes=tuple(notes)):
        shape_notes = set(normalizer(_get_shape_notes(shape, tuning=config.tuning)))
        if shape_notes == normalizer(notes):
            shapes.append(shape)
    shapes.sort(key=config.shape_ranker)
    chords = _get_chords_from_notes(frozenset(notes))
    for shape in shapes[: config.num or len(shapes)]:
        difficulty, barre_data = _get_shape_difficulty(shape, tuning=config.tuning)
        output["shapes"].append(
            {
                "shape": shape,
                "difficulty": difficulty,
                "barre_data": barre_data,
                "chord_names": chords,
            }
        )

    return output


def show_key(_: UkeConfig | None, key: str | tuple[str, ...]) -> KeyInfo:
    """Return information on the specified key, including other names and the notes it includes"""
    if isinstance(key, str):
        notes = get_key_notes(key)
        other_keys, partial_keys = get_dupe_scales_from_notes(notes)
        output: KeyInfo = {
            "notes": notes,
            "key": key,
            "other_keys": list(other_keys),
            "partial_keys": sorted(partial_keys, key=_rank_chord_name),
        }
    else:
        keys, partial_keys = get_dupe_scales_from_notes(key)
        output = {
            "notes": tuple(key),
            "other_keys": list(keys),
            "partial_keys": sorted(partial_keys, key=_rank_chord_name),
        }
    output["other_keys"].sort(key=_rank_chord_name)
    return output
