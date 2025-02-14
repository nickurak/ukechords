"""Logic related to configuring ukechords"""

import argparse
import json
import sys
import configparser
import os
from dataclasses import dataclass
from typing import Callable, Optional, List, Union, Any, Iterable

from xdg import BaseDirectory

from .theory import get_tuning, rank_shape_by_difficulty, rank_shape_by_high_fret
from .theory import show_chord, show_all, show_chords_by_shape
from .theory import show_chords_by_notes, show_key

from .render import render_chord_list, render_chords_from_shape
from .render import render_chords_from_notes, render_key
from .render import render_json

from .errors import InvalidCommandException


def _get_renderfunc_from_name(name: str) -> Callable:
    render_funcs: List[Callable] = [
        render_chord_list,
        render_chords_from_shape,
        render_chords_from_notes,
        render_key,
    ]
    render_func_map = {f.__name__: f for f in render_funcs}
    if name in render_func_map:
        print(f"{type(render_func_map[name])=}")
        return render_func_map[name]

    msg = f'No such rendering function "{name}". Options: {", ".join(render_func_map)}'
    raise InvalidCommandException(msg)


def _check_argument_errors(args: argparse.Namespace) -> None:
    def exactly_one(iterable: Iterable) -> bool:
        i = iter(iterable)
        return any(i) and not any(i)

    mutually_exclusive_groups = [
        args.render_cmd,
        args.notes,
        args.chord,
        args.shape,
        (args.all_chords or args.keys or args.allowed_chords),
        args.show_key,
    ]
    if not exactly_one(mutually_exclusive_groups):
        msg = "Provide exactly one of "
        msg += "--all-chords, --chord, --shape, --notes, --render-cmd, or --show-key"
        raise InvalidCommandException(msg)

    if args.qualities and args.simple:
        raise InvalidCommandException("Provide only one of -p/--simple or -q/--qualities")

    if args.slide and not args.shape:
        raise InvalidCommandException("--slide requries a --shape")


@dataclass
class UkeConfig:
    """Configuration settings for an invocation of ukechords functionality"""

    # pylint: disable=too-many-instance-attributes
    render_text: Callable = render_json  # Function to render output in command-line mode
    command: Optional[Callable] = None  # Command to call in command-line mode
    qualities: Optional[List[str]] = None  # List of chord qualities to allow in output
    slide: bool = False  # Whether to report versions of a specified shape slid up/down the neck
    show_notes: bool = False  # Whether to include individual notes in the output
    no_cache: bool = False  # Whether to avoid loading any available cached chord->shape maps
    num: Optional[int] = None  # How many shapes to return for a given chord
    visualize: bool = False  # Whether to draw shapes on screen while rendering
    keys: Optional[List[str]] = None  # If specified, a key to limit returned chords to
    allowed_chords: Optional[List[str]] = None  # If specified, chords whose notes are allowed
    force_flat: bool = False  # Whether to report chords in their flat versions rather than sharp
    max_difficulty: float = 100.0  # A maximum difficulty or shapes to scan and report
    cache_dir: str = ""  # Directory in which to store cached chord->shape maps
    tuning: tuple[str, ...] = ()  # A list of notes in the desired tuning
    mute: Optional[bool] = None  # Whether or not to consider muted shapes
    shape_ranker: Optional[Callable] = None  # Which function to use to sort discovered shapes with

    def __init__(self, args: Optional[Union[List, argparse.Namespace]] = None) -> None:
        self._set_defaults()
        if args is None:
            return
        if isinstance(args, list):
            args = get_parser().parse_args(args)
        if not isinstance(args, argparse.Namespace):
            raise TypeError(f"Unable to handle {type(args)} as UkeConfig args")
        _check_argument_errors(args)
        self.mute = args.mute
        if args.tuning:
            self.tuning = get_tuning(args.tuning)
        if args.sort_by_position:
            self.shape_ranker = rank_shape_by_high_fret
        if args.max_difficulty:
            self.max_difficulty = args.max_difficulty
        if args.simple:
            self.qualities = ["", "m", "7", "dim", "maj", "m7"]
        if args.qualities is not None:
            self.qualities = args.qualities.split(",")
        self.slide = args.slide
        self.num = args.num
        if args.single:
            self.num = 1
        if not self.num and args.visualize:
            self.num = 1
        self.show_notes = args.show_notes
        self.no_cache = args.no_cache
        self.visualize = args.visualize
        self.force_flat = args.force_flat
        self.keys = args.keys
        self.allowed_chords = args.allowed_chords
        if args.cache_dir:
            self.cache_dir = args.cache_dir
        self._setup_command(args)
        if args.json:
            self.render_text = render_json

    def _setup_command(self, args: argparse.Namespace) -> None:
        if args.chord:
            self.command = lambda x: show_chord(x, args.chord)
        if args.all_chords or args.keys or args.allowed_chords:
            self.command = show_all
        if args.chord or args.all_chords or args.keys or args.allowed_chords:
            self.render_text = render_chord_list
        if args.shape:
            self.command = lambda x: show_chords_by_shape(x, args.shape)
            self.render_text = render_chords_from_shape
        if args.notes:
            self.command = lambda x: show_chords_by_notes(x, set(args.notes.split(",")))
            self.render_text = render_chords_from_notes
        if args.show_key:
            self.command = lambda x: show_key(x, args.show_key)
            self.render_text = render_key
        if args.render_cmd:
            self.command = lambda _: json.load(sys.stdin)
            self.render_text = _get_renderfunc_from_name(args.render_cmd)

    def _set_defaults(self) -> None:
        config = configparser.ConfigParser()
        config_path = BaseDirectory.load_first_config("ukechords.ini")
        config["DEFAULTS"] = {
            "tuning": "ukulele-c6",
            "cache_dir": os.path.join(BaseDirectory.xdg_cache_home, "ukechords", "cached_shapes"),
            "mute": "no",
            "max_difficulty": "29.0",
            "sort_by_position": "no",
        }
        if config_path and os.path.exists(config_path):
            config.read(config_path)
        defaults = config["DEFAULTS"]
        self.cache_dir = defaults["cache_dir"]
        self.tuning = get_tuning(defaults["tuning"])
        self.mute = defaults["mute"].lower() in ("yes", "true", "t", "1")
        self.max_difficulty = float(defaults["max_difficulty"])
        self.shape_ranker = rank_shape_by_difficulty
        if defaults["sort_by_position"].lower() in ("yes", "true", "t", "1"):
            self.shape_ranker = rank_shape_by_high_fret

    def run_command(self) -> None:
        "Invoke the configured command with the configured configuration, and render the output"
        assert self.command
        self.render_text(self, self.command(self))


def get_parser() -> argparse.ArgumentParser:
    "Construct and return an argparse parser for use with ukechords on the command line"
    parser = argparse.ArgumentParser()

    def pa(*args: Any, **kwargs: Any) -> None:
        parser.add_argument(*args, **kwargs)

    pa("-c", "--chord", help="Show how to play <CHORD>")
    pa("--notes", help="Show what chord(s) these <NOTES> play")
    pa("-s", "--shape", help="Show what chord(s) this <SHAPE> plays")
    slide_help = "Show what chord(s) this <SHAPE> could play when slid up or down"
    pa("--slide", action="store_true", help=slide_help)
    pa("-t", "--tuning", help="comma-separated notes for string tuning")
    pa("-1", "--single", action="store_true", help="Show only 1 shape for each chord")
    pa("-v", "--visualize", action="store_true", help="Visualize shapes with Unicode drawings")
    all_help = "Show all matching chords, not just one selected one"
    pa("-a", "--all-chords", action="store_true", help=all_help)
    pa("-m", "--mute", action="store_true", help="Include shapes that require muting strings")
    pa("-n", "--num", type=int, help="Show <NUM> shapes for the given chord")
    keys_help = "Limit chords to those playable in <KEY> (can be specified multiple times)"
    pa("-k", "--keys", action="append", help=keys_help)
    pa("-q", "--qualities", help="Limit chords to chords with the specified <QUALITIES>")
    simple_help = "Limit to chords with major, minor, and dim qualities"
    pa("-p", "--simple", action="store_true", help=simple_help)
    nocache_help = "Ignore any available cached chord/shape information"
    pa("--no-cache", action="store_true", help=nocache_help)
    pa("--show-key", help="Show the notes in the specified <KEY>", metavar="KEY")
    pa("--show-notes", action="store_true", help="Show the notes in chord")
    pa("-f", "--force-flat", action="store_true", help="Show flat-variations of chord roots")
    sort_by_pos_help = "Sort to minimize high-position instead of difficulty"
    pa("-b", "--sort-by-position", action="store_true", help=sort_by_pos_help)
    pa("-j", "--json", action="store_true", help="Output in json format if possible")
    pa("-r", "--render-cmd", help="Read stdin into a rendering command")
    pa("--cache-dir", help="Specify directory to use for cached shapes")
    difficulty_help = "Limit shape-scanning to the given <MAX_DIFFICULTY> or less"
    pa("-d", "--max-difficulty", type=float, help=difficulty_help)
    ac_help = "Limit to chords playable by the notes in <ALLOWED_CHORD> (specify multiple times)"
    pa("-o", "--allowed-chords", action="append", help=ac_help)
    return parser
