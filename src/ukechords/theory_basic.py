"""Basic music theory elements, not neccesarily including stringed instruments or chord qualities"""

import re
from typing import TypeVar, Any, Generator

from .errors import ChordNotFoundException, UnknownKeyException


class ChordCollection(dict[str, Any]):
    """A specialization of a dictionary, which normalizes chord names
    to catch multiple names for the same chord. For example BbM and
    A#maj are different names for the same chord, and thus produce the
    same behavior when used as a key.

    Note that because it normalizes string keys,it will not work
    correctly with non-string keys.
    """

    def __contains__(self, chord: str, /) -> bool:  # type: ignore[override]
        return super().__contains__(normalize_chord(str(chord)))

    def __setitem__(self, chord: str, /, *args: Any, **kwargs: Any) -> None:
        super().__setitem__(normalize_chord(str(chord)), *args, **kwargs)

    def __getitem__(self, chord: str) -> list[tuple[int, ...]]:
        shapes: list[tuple[int, ...]] = super().__getitem__(normalize_chord(str(chord)))
        return shapes


class _CircularList(list[Any]):
    def __getitem__(self, index: Any) -> Any:
        return super().__getitem__(index % len(self))


chromatic_scale = _CircularList(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])
flat_scale = _CircularList(["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"])
_weird_sharps = {"C": "B#", "F": "E#"}
_weird_flats = {"B": "Cb", "E": "Fb"}
_weird_sharp_scale = _CircularList([_weird_sharps.get(n, n) for n in chromatic_scale])
_weird_flat_scale = _CircularList([_weird_flats.get(n, n) for n in flat_scale])
note_intervals = {note: index for index, note in enumerate(chromatic_scale)}
note_intervals |= {note: index for index, note in enumerate(flat_scale)}
note_intervals |= {note: index for index, note in enumerate(_weird_sharp_scale)}
note_intervals |= {note: index for index, note in enumerate(_weird_flat_scale)}


def normalize_chord(chord: str) -> str:
    """For duplicate and match detection, convert to a canonical
    sharp version, including replacing "maj" with "M" per pychord
    convention."""
    if not (match := re.match("^([A-G][b#]?)(.*)$", chord)):
        raise ChordNotFoundException(f'Couldn\'t find a valid root in "{chord}"')
    (root, quality) = match.groups()
    quality = quality.replace("maj", "M")
    return f"{sharpify(root)}{quality}"


Normalizable = TypeVar("Normalizable", str, list[str], tuple[str, ...], set[str])


def _normalizer(arg: Normalizable, scale: list[str]) -> Normalizable:
    if isinstance(arg, list):
        return [scale[note_intervals[note]] for note in arg]
    if isinstance(arg, tuple):
        return tuple(scale[note_intervals[note]] for note in arg)
    if isinstance(arg, set):
        return {scale[note_intervals[note]] for note in arg}
    return scale[note_intervals[arg]]


def sharpify(arg: Normalizable) -> Normalizable:
    """Return the sharp equivelant version of the note/chord or list/tuple/set of chords"""
    return _normalizer(arg, chromatic_scale)


def flatify(arg: Normalizable) -> Normalizable:
    """Return the flat equivelant version of the note/chord or list/tuple/set of chords"""
    return _normalizer(arg, flat_scale)


def is_flat(note: str) -> bool:
    """Identify if a note is flat"""
    return note[-1] == "b"


def _get_scales() -> dict[str, list[int]]:
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
        (["chromatic"], list(range(0, 12))),
    ]

    mods = {}
    for names, intervals in scales:
        for name in names:
            mods[name] = intervals

    return mods


def _get_all_keys() -> dict[str, set[str]]:
    def _get_all_key_pairs() -> Generator[tuple[str, set[str]], None, None]:
        for root_index in range(0, 12):
            root = chromatic_scale[root_index]
            dupes: set[frozenset[str]] = set()
            for name, intervals in _get_scales().items():
                notes = set(chromatic_scale[root_index + interval] for interval in intervals)
                if frozenset(notes) in dupes:
                    continue

                dupes |= {frozenset(notes)}
                yield f"{root}{name}", notes

    return dict(_get_all_key_pairs())


def get_dupe_scales_from_notes(notes: tuple[str, ...]) -> tuple[set[str], set[str]]:
    """Given a set of notes, return a list of scales those notes fit in"""
    matching_keys: list[str] = []
    partial_keys: list[str] = []
    for key, key_notes in _get_all_keys().items():
        if "chromatic" in key:
            continue
        if set(sharpify(notes)) == set(sharpify(key_notes)):
            matching_keys.append(key)
        if set(sharpify(notes)) < sharpify(key_notes):
            partial_keys.append(key)
    return set(matching_keys), set(partial_keys)


def _get_dupe_scales_from_key(key: str) -> set[str]:
    dupe_scales, _ = get_dupe_scales_from_notes(get_key_notes(key))
    return dupe_scales


def get_key_notes(key: str) -> tuple[str, ...]:
    """Given a key, return the notes in that key"""
    mods = _get_scales()

    match = re.match(f'^([A-G][b#]?)({"|".join(mods.keys())})$', key)
    if not match:
        raise UnknownKeyException(f'Unknown key "{key}"')
    (root, extra) = match.groups()
    intervals = mods[extra]
    if is_flat(root):
        return tuple(flat_scale[interval + note_intervals[root]] for interval in intervals)
    return tuple(chromatic_scale[interval + note_intervals[root]] for interval in intervals)
