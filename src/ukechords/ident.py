#!/usr/bin/env python3
"""Simple command-line client to invoke ukechords functionality"""

import sys
import argparse
import json
import os
import configparser
from typing import Callable, Iterable, Any

from xdg import BaseDirectory

from ukechords.theory import add_no5_quality, add_7sus2_quality
from ukechords.errors import UnknownKeyException, ChordNotFoundException, ShapeNotFoundException
from ukechords.errors import error, InvalidCommandException
from ukechords.config import UkeConfig

from ukechords.theory import show_chord, show_all, show_chords_by_shape
from ukechords.theory import show_chords_by_notes, show_key
from ukechords.theory import get_tuning, rank_shape_by_high_fret, rank_shape_by_difficulty

from ukechords.render import render_chord_list, render_chords_from_shape
from ukechords.render import render_chords_from_notes, render_key, render_json

from ukechords.types import ChordsByNotes, ChordsByShape, ChordShapes, KeyInfo


def _get_config_from_preferences() -> UkeConfig:
    "Create a UkeConfig object based on on-disk preferences"
    config = configparser.ConfigParser()

    config_path = BaseDirectory.load_first_config("ukechords.ini")
    config["ukechords"] = {
        "tuning": "ukulele-c6",
        "cache_dir": os.path.join(BaseDirectory.xdg_cache_home, "ukechords", "cached_shapes"),
        "mute": "no",
        "max_difficulty": "29.0",
        "sort_by_position": "no",
    }
    if config_path and os.path.exists(config_path):
        config.read(config_path)
    defaults = config["ukechords"]

    cache_dir = defaults["cache_dir"]
    tuning = get_tuning(defaults["tuning"])
    mute = defaults["mute"].lower() in ("yes", "true", "t", "1")
    max_difficulty = float(defaults["max_difficulty"])
    shape_ranker: Callable[[tuple[int, ...]], Any] = rank_shape_by_difficulty
    if defaults["sort_by_position"].lower() in ("yes", "true", "t", "1"):
        shape_ranker = rank_shape_by_high_fret
    return UkeConfig(
        cache_dir=cache_dir,
        tuning=tuning,
        mute=mute,
        max_difficulty=max_difficulty,
        shape_ranker=shape_ranker,
    )


def _get_parser() -> argparse.ArgumentParser:
    "Construct and return an argparse parser for use with ukechords on the command line"
    parser = argparse.ArgumentParser()

    def pa(*args: Any, **kwargs: Any) -> None:
        parser.add_argument(*args, **kwargs)

    pa("-c", "--chord", help="Show how to play <CHORD>")
    notes_help = "Show what chord(s) these <NOTES> play"
    pa("--notes", help=notes_help, type=lambda notes: set(notes.split(",")))
    pa("-s", "--shape", help="Show what chord(s) this <SHAPE> plays")
    slide_help = "Show what chord(s) this <SHAPE> could play when slid up or down"
    pa("--slide", action="store_true", help=slide_help)
    pa("-t", "--tuning", help="comma-separated notes for string tuning")
    pa("-1", "--single", action="store_true", help="Show only 1 shape for each chord")
    pa("-v", "--visualize", action="store_true", help="Visualize shapes with Unicode drawings")
    all_help = "Show all matching chords, not just one selected one"
    pa("-a", "--all-chords", action="store_true", help=all_help)
    mute_help = "Include shapes that require muting strings"
    pa("-m", "--mute", action=argparse.BooleanOptionalAction, help=mute_help)
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


def _check_argument_errors(args: argparse.Namespace) -> None:
    def exactly_one(iterable: Iterable) -> bool:
        return 1 == len(list(filter(None, iterable)))

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


def _get_config(args: argparse.Namespace) -> UkeConfig:
    "Unpack argparse options into a new UkeConfig"
    _check_argument_errors(args)
    config = _get_config_from_preferences()
    if args.mute is not None:
        config.mute = args.mute
    if args.tuning:
        config.tuning = get_tuning(args.tuning)
    if args.sort_by_position:
        config.shape_ranker = rank_shape_by_high_fret
    if args.max_difficulty:
        config.max_difficulty = args.max_difficulty
    if args.simple:
        config.qualities = ["", "m", "7", "dim", "maj", "m7"]
    if args.qualities is not None:
        config.qualities = args.qualities.split(",")
    config.slide = args.slide
    config.num = args.num
    if args.single:
        config.num = 1
    if not config.num and args.visualize:
        config.num = 1
    config.show_notes = args.show_notes
    config.no_cache = args.no_cache
    config.visualize = args.visualize
    config.force_flat = args.force_flat
    config.keys = args.keys
    config.allowed_chords = args.allowed_chords
    if args.cache_dir:
        config.cache_dir = args.cache_dir
    return config


def _get_renderfunc_from_name(name: str) -> Callable:
    render_funcs: list[Callable] = [
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


def run_command(config: UkeConfig, args: argparse.Namespace) -> None:
    "Run a command specified by the argparsed options provided"
    renderer: Callable
    data: ChordShapes | ChordsByShape | ChordsByNotes | KeyInfo
    if args.chord:
        renderer = render_chord_list
        data = show_chord(config, args.chord)
    elif args.all_chords or args.keys or args.allowed_chords:
        renderer = render_chord_list
        data = show_all(config)
    elif args.shape:
        renderer = render_chords_from_shape
        data = show_chords_by_shape(config, args.shape)
    elif args.notes:
        renderer = render_chords_from_notes
        data = show_chords_by_notes(config, args.notes)
    elif args.show_key:
        renderer = render_key
        data = show_key(config, args.show_key)
    elif args.render_cmd:
        renderer = _get_renderfunc_from_name(args.render_cmd)
        data = json.load(sys.stdin)
    else:
        assert not "No command configuration found"
    if args.json:
        renderer = render_json
    renderer(config, data)


def main() -> int:
    # pylint: disable=missing-function-docstring
    add_no5_quality()
    add_7sus2_quality()
    try:
        args = _get_parser().parse_args(sys.argv[1:])
        config = _get_config(args)
        run_command(config, args)
    except UnknownKeyException as exc:
        error(10, exc)
    except ChordNotFoundException as exc:
        error(2, exc)
    except ShapeNotFoundException as exc:
        error(1, exc)
    except InvalidCommandException as exc:
        error(5, exc)
    except ValueError as exc:
        error(11, exc)
    except KeyboardInterrupt:
        error(128, "(aborted)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
