"""Types defined by Ukechords, especially those returned from the
theory module to the render module"""

from typing import TypedDict, NotRequired


class KeyInfo(TypedDict):
    "Return value of show_key"

    notes: tuple[str, ...]
    other_keys: list[str]
    key: NotRequired[str]


class ChordsByNotes(TypedDict):
    "Return value of show_chords_by_notes"

    notes: tuple[str, ...]
    chords: list[str]


class Shape(TypedDict):
    "One instance of a shape as returned in get_chord_by_shape (which may be a slid shape)"

    shape: tuple[int, ...]
    chords: list[str]
    notes: tuple[str, ...]


class BarreData(TypedDict):
    "Information on how to barre a shape"

    fret: int
    barred: bool
    shape: tuple[int, ...]
    chord: str | None
    unbarred_difficulty: NotRequired[float]
    barred_difficulty: NotRequired[float]


class ChordsByShape(TypedDict):
    "Return value of show_chords_by_shape"

    shapes: list[Shape]
    difficulty: NotRequired[float]
    barre_data: NotRequired[BarreData | None]


class ChordShape(TypedDict):
    "A single shape used to play a chord, as contained inside the list of a ChordShapes dict"

    shape: tuple[int, ...]
    difficulty: float
    barre_data: NotRequired[BarreData | None]
    chord_names: list[str]


class ChordShapes(TypedDict):
    "A list of shapes, as returned by show_all and show_chord"

    shapes: list[ChordShape]
    notes: NotRequired[tuple[str, ...]]
    chord: NotRequired[str]
