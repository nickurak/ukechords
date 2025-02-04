"""Rendering logic, chiefly for CLI usage of ukechords"""

from __future__ import annotations
from typing import Generator, Any, Optional, Iterable
import json
import sys

from .errors import ShapeNotFoundException

from .config import UkeConfig
from .types import ChordShapes, ChordsByShape, ChordsByNotes, KeyInfo, BarreData


def _csv(lst: Iterable[Any], sep: str = ",") -> str:
    return sep.join(map(str, lst))


def _get_shape_lines(shape: tuple, barre: int) -> Generator[str, None, None]:
    marks = {
        3: " ╷╵ ",
        5: " ╷╵ ",
        7: " ╷╵ ",
        10: " ╷╵ ",
        12: "╷╵╷╵",
    }
    max_pos = max([*shape, 3]) + 1
    lines = ["─"] * max_pos
    yield "╓" + "┬".join(lines) + "─"
    for string, pos in enumerate(reversed(shape)):
        chars = [" "] * max_pos
        for mark in [3, 5, 7, 10, 12]:
            if mark < max_pos + 1 and (string - (len(shape) - 4) // 2) < len(marks[mark]):
                chars[mark - 1] = marks[mark][string - (len(shape) - 4) // 2]
        if pos > 0:
            chars[pos - 1] = "●"
        if barre > 0:
            chars[barre - 1] = "▒"
        yield "║" + ("⃠" if pos < 0 else "") + "│".join(chars)
    yield "╙" + "┴".join(lines) + "─"


def _draw_shape(shape: tuple[int, ...], barre_data: Optional[BarreData]) -> None:
    barre = barre_data["fret"] if barre_data else 0
    for line in _get_shape_lines(shape, barre):
        print(line)


def _diff_string(difficulty: float, barre_data: Optional[BarreData], diff_width: int = 0) -> str:
    padded_diff = f"{difficulty:{diff_width}.1f}"
    if not barre_data:
        return padded_diff

    barre_string = f"barre {barre_data['fret']}"
    if not all(fret == 0 for fret in barre_data["shape"]):
        barre_string = f"{barre_string} + {_csv(barre_data['shape'])}:{barre_data['chord']}"

    if not barre_data["barred"]:
        return f"{padded_diff} (else {barre_data['barred_difficulty']:.1f}: {barre_string})"

    return f"{padded_diff} ({barre_string}, else {barre_data['unbarred_difficulty']:.1f})"


def _get_shape_string(shape: Iterable) -> str:
    return _csv(["x" if x == -1 else str(x) for x in shape])


def render_chord_list(config: UkeConfig, data: ChordShapes) -> None:
    """Render a list of 1 or more ways to play chords, as requested by
    chord name, including shapes, and optionally the notes and a
    unicode visualization of how to play it
    """
    if config.show_notes:
        print(f"Notes: {', '.join(data['notes'])}")
    name_width = 0
    shape_width = 0
    diff_width = 0
    if not data["shapes"]:
        if "chord" in data:
            raise ShapeNotFoundException(f'No shape for "{data["chord"]}" found')
        print("No matching chords found")
    for shape in data["shapes"]:
        name_width = max(name_width, len(_csv(shape["chord_names"])))
        shape_string = _get_shape_string(shape["shape"])
        shape_width = max(shape_width, len(shape_string))
        diff_width = max(diff_width, len(f"{shape['difficulty']:.1}"))
    name_width += 1
    for shape in data["shapes"]:
        shape_string = _get_shape_string(shape["shape"])
        d_string = _diff_string(shape["difficulty"], shape["barre_data"], diff_width=diff_width)
        chord_names = _csv(shape["chord_names"]) + ":"
        print(f"{chord_names:{name_width}} {shape_string:{shape_width}} difficulty:{d_string:}")
        if config.visualize:
            _draw_shape(shape["shape"], shape["barre_data"])


def render_chords_from_shape(config: UkeConfig, data: ChordsByShape) -> None:
    """Render named chords, as identified by shapes played on frets"""
    for shape in data["shapes"]:
        if config.show_notes:
            print(f"Notes: {_csv(shape['notes'], sep=', ')}")
        if config.visualize:
            barre_data = data.get("barre_data")
            _draw_shape(tuple(-1 if pos == "x" else int(pos) for pos in shape["shape"]), barre_data)
        shape_string = _get_shape_string(shape["shape"])
        print(f'{shape_string}: {_csv(shape["chords"])}')
    if not config.slide:
        print(f"Difficulty: {_diff_string(data['difficulty'], data['barre_data'])}")


def render_chords_from_notes(_: Optional[UkeConfig], data: ChordsByNotes) -> None:
    """Render named chords, as identified by notes"""
    print(f"{_csv(data['notes'])}: {_csv(data['chords'])}")


def render_key(_: Optional[UkeConfig], data: KeyInfo) -> None:
    """Render information about a musical key"""
    if data["other_keys"]:
        other_str = f" ({_csv(data['other_keys'])})"
    else:
        other_str = ""
    if "key" in data:
        print(f"{data['key']}{other_str}:")
        print(f"{_csv(data['notes'])}")
    else:
        if not data["other_keys"]:
            print("No key found")
            return
        print(f"{_csv(data['other_keys'])}")


def render_json(_: Optional[UkeConfig], data: Any) -> None:
    """Render arbitrary input data as json"""
    json.dump(data, sys.stdout, indent=2 if sys.stdout.isatty() else None)
    print()
