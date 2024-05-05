# pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring

import argparse
import json
import sys
import configparser
import os
from dataclasses import dataclass
from typing import Callable, Optional, List

from xdg import BaseDirectory

from .theory import get_tuning, rank_shape_by_difficulty, rank_shape_by_high_fret
from .theory import show_chord, show_all, show_chords_by_shape
from .theory import show_chords_by_notes, show_key

from .render import render_chord_list, render_chords_from_shape
from .render import render_chords_from_notes, render_key
from .render import render_json


def _get_renderfunc_from_name(name):
    render_funcs = [
        render_chord_list,
        render_chords_from_shape,
        render_chords_from_notes,
        render_key,
    ]
    render_func_map = {f.__name__: f for f in render_funcs}
    if name in render_func_map:
        return render_func_map[name]

    msg = f'No such rendering function "{name}". Options: {", ".join(render_func_map)}'
    raise InvalidCommandException(msg)


def _reject_conflicting_commands(args):
    def exactly_one(iterable):
        i = iter(iterable)
        return any(i) and not any(i)

    mutually_exclusive_groups = [
        args.render_cmd,
        args.notes,
        args.chord,
        args.shape,
        (args.all_chords or args.key or args.allowed_chords),
        args.show_key,
    ]
    if not exactly_one(mutually_exclusive_groups):
        msg = "Provide exactly one of "
        msg += "--all-chords, --chord, --shape, --notes, --render-cmd, or --show-key"
        raise InvalidCommandException(msg)


class InvalidCommandException(Exception):
    pass


@dataclass
class UkeConfig:
    # pylint: disable=line-too-long
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements

    render_text: Callable = render_json
    command: Callable = lambda _, __: json.load(sys.stdin)
    json: bool = False
    qualities: Optional[list[str]] = None
    slide: bool = False
    show_notes: bool = False
    no_cache: bool = False
    num: Optional[int] = None
    visualize: bool = False
    key: Optional[str] = None
    allowed_chords: Optional[List[str]] = None
    force_flat: bool = False
    max_diffculty: Optional[float] = None
    cache_dir: Optional[str] = None
    tuning: Optional[str] = None
    base: Optional[int] = None
    shape_ranker: Optional[Callable] = None

    def __init__(self, args=None):
        self._set_defaults()
        if not args:
            return
        if args.json:
            self.json = True
        if args.mute:
            self.base = -1
        if args.tuning:
            self.tuning = get_tuning(args.tuning)
        if args.sort_by_position:
            self.shape_ranker = rank_shape_by_high_fret
        if args.max_difficulty:
            self.max_difficulty = args.max_difficulty
        _reject_conflicting_commands(args)
        if args.qualities and args.simple:
            raise InvalidCommandException("Provide only one of -p/--simple or -q/--qualities")
        if args.simple:
            self.qualities = ["", "m", "7", "dim", "maj", "m7"]
        if args.qualities is not None:
            self.qualities = args.qualities.split(",")
        self.slide = args.slide
        if args.slide and not args.shape:
            raise InvalidCommandException("--slide requries a --shape")
        self.num = args.num
        if args.single:
            self.num = 1
        if not self.num and args.visualize:
            self.num = 1
        self.show_notes = args.show_notes
        self.no_cache = args.no_cache
        self.visualize = args.visualize
        self.force_flat = args.force_flat
        if args.chord:
            self.command = lambda x: show_chord(x, args.chord)
        if args.all_chords or args.key or args.allowed_chords or args.key:
            self.command = show_all
        if args.chord or args.all_chords or args.key or args.allowed_chords or args.key:
            self.render_text = render_chord_list
        self.key = args.key
        self.allowed_chords = args.allowed_chords
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
            self.render_text = _get_renderfunc_from_name(args.render_cmd)
        if args.cache_dir:
            self.cache_dir = args.cache_dir
        if args.json:
            self.render_text = render_json

    def _set_defaults(self):
        config = configparser.ConfigParser()
        config_path = BaseDirectory.load_first_config("ukechords.ini")
        config["DEFAULTS"] = {
            "tuning": "ukulele-c6",
            "cache_dir": os.path.join(BaseDirectory.xdg_cache_home, "ukechords", "cached_shapes"),
            "mute": False,
            "max_difficulty": 29.0,
            "sort_by_position": False,
        }
        if config_path and os.path.exists(config_path):
            config.read(config_path)
        defaults = config["DEFAULTS"]
        self.cache_dir = defaults["cache_dir"]
        self.tuning = get_tuning(defaults["tuning"])
        self.base = -1 if defaults["mute"].lower() in ("yes", "true", "t", "1") else 0
        self.max_difficulty = float(defaults["max_difficulty"])
        self.shape_ranker = rank_shape_by_difficulty
        if defaults["sort_by_position"].lower() in ("yes", "true", "t", "1"):
            self.shape_ranker = rank_shape_by_high_fret

    def run_command(self):
        self.render_text(self, self.command(self))


def get_parser():
    # pylint: disable=line-too-long
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--chord", help="Show how to play <CHORD>")
    parser.add_argument("--notes", help="Show what chord(s) these <NOTES> play")
    parser.add_argument("-s", "--shape", help="Show what chord(s) this <SHAPE> plays")
    parser.add_argument(
        "--slide",
        action="store_true",
        help="Show what chord(s) this <SHAPE> could play when slid up or down",
    )
    parser.add_argument("-t", "--tuning", help="comma-separated notes for string tuning")
    parser.add_argument(
        "-1", "--single", action="store_true", help="Show only 1 shape for each chord"
    )
    parser.add_argument(
        "-v", "--visualize", action="store_true", help="Visualize shapes with Unicode drawings"
    )
    parser.add_argument(
        "-a",
        "--all-chords",
        action="store_true",
        help="Show all matching chords, not just one selected one",
    )
    parser.add_argument(
        "-m", "--mute", action="store_true", help="Include shapes that require muting strings"
    )
    parser.add_argument("-n", "--num", type=int, help="Show <NUM> shapes for the given chord")
    parser.add_argument(
        "-d",
        "--max-difficulty",
        type=float,
        help="Limit shape-scanning to the given <MAX_DIFFICULTY>",
        metavar="DIFFICULTY",
    )
    parser.add_argument(
        "-k",
        "--key",
        action="append",
        help="Limit chords to those playable in <KEY> (can be specified multiple times)",
    )
    parser.add_argument(
        "-o",
        "--allowed-chords",
        action="append",
        help="Limit to chords playable by the notes in <CHORD> (specify multiple times)",
        metavar="CHORD",
    )
    parser.add_argument(
        "-q", "--qualities", help="Limit chords to chords with the specified <QUALITIES>"
    )
    parser.add_argument(
        "-p",
        "--simple",
        action="store_true",
        help="Limit to chords with major, minor, and dim qualities",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Ignore any available cached chord/shape information",
    )
    parser.add_argument("--show-key", help="Show the notes in the specified <KEY>", metavar="KEY")
    parser.add_argument("--show-notes", action="store_true", help="Show the notes in chord")
    parser.add_argument(
        "-f", "--force-flat", action="store_true", help="Show flat-variations of chord roots"
    )
    parser.add_argument(
        "-b",
        "--sort-by-position",
        action="store_true",
        help="Sort to minimize high-position instead of difficulty",
    )
    parser.add_argument(
        "-j", "--json", action="store_true", help="Output in json format if possible"
    )
    parser.add_argument("-r", "--render-cmd", help="Read stdin into a rendering command")
    parser.add_argument("--cache-dir", help="Specify directory to use for cached shapes")
    return parser


def get_args(parser, args):
    return parser.parse_args(args)
