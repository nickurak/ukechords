"""Logic related to configuring ukechords"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, List

from .theory import rank_shape_by_high_fret


@dataclass(kw_only=True)
class UkeConfig:
    """Configuration settings for an invocation of ukechords"""

    # pylint: disable=too-many-instance-attributes
    qualities: Optional[List[str]] = None  # List of chord qualities to allow in output
    slide: bool = False  # Whether to report versions of a specified shape slid up/down the neck
    show_notes: bool = False  # Whether to include individual notes in the output
    no_cache: bool = False  # Whether to avoid loading any available cached chord->shape maps
    num: Optional[int] = None  # How many shapes to return for a given chord
    visualize: bool = False  # Whether to draw shapes on screen while rendering
    keys: Optional[List[str]] = None  # If specified, key(s) to limit returned chords to
    allowed_chords: Optional[List[str]] = None  # If specified, chord(s) whose notes are allowed
    force_flat: bool = False  # Whether to report chords in their flat versions rather than sharp
    max_difficulty: float = 100.0  # A maximum difficulty of shapes to scan and report
    cache_dir: str = ""  # Directory in which to store cached chord->shape maps
    tuning: tuple[str, ...] = ()  # Notes that individual strings are tuned to
    mute: bool = False  # Whether or not to consider muted shapes
    shape_ranker: Callable = (
        rank_shape_by_high_fret  # Function to use to sort discovered shapes with
    )
