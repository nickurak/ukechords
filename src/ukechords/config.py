import argparse
import json
import sys
import configparser
import os

from xdg import BaseDirectory

from .theory import get_tuning, rank_shape_by_difficulty, rank_shape_by_high_fret
from .theory import show_chord, show_all, show_chords_by_shape
from .theory import show_chords_by_notes, show_key

from .render import render_chord_list, render_chords_from_shape
from .render import render_chords_from_notes, render_key


def get_renderfunc_from_name(name):
    for f in [render_chord_list, render_chords_from_shape,
              render_chords_from_notes, render_key]:
        if f.__name__ == name:
            return f
    return False


def error(return_code, message, parser=None):
    print(message, file=sys.stderr)
    if parser:
        parser.print_help(sys.stderr)
    sys.exit(return_code)

class InvalidCommandException(Exception):
    pass

class UkeConfig():
    # pylint: disable=line-too-long
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    def __init__(self, args):
        self.set_defaults()
        self._render_text = None
        if args.mute:
            self._base = -1
        self._json = args.json
        if args.tuning:
            self._tuning = get_tuning(args.tuning)
        if args.sort_by_position:
            self._shape_ranker = rank_shape_by_high_fret
        if args.max_difficulty:
            self._max_difficulty = args.max_difficulty
        if list(map(bool, [args.render_cmd, args.notes, args.chord, args.shape, (args.all_chords or args.key or args.allowed_chord), args.show_key])).count(True) != 1:
            raise InvalidCommandException("Provide exactly one of --all-chords, --chord, --shape, --notes, --render-cmd, or --show-key")
        if args.qualities and args.simple:
            raise InvalidCommandException("Provide only one of -p/--simple or -q/--qualities")
        self._qualities = False
        if args.simple:
            self._qualities = ['', 'm', '7', 'dim', 'maj', 'm7']
        if args.qualities is not None:
            self._qualities = args.qualities.split(',')
        self._slide = args.slide
        if args.slide and not args.shape:
            raise InvalidCommandException("--slide requries a --shape")
        self._num = args.num
        if args.single:
            self._num = 1
        if not self._num and args.visualize:
            self._num = 1
        self._show_notes = args.show_notes
        self._no_cache = args.no_cache
        self._visualize = args.visualize
        self._force_flat = args.force_flat
        if args.chord:
            self._command = lambda x: show_chord(x, args.chord)
        if args.all_chords or args.key or args.allowed_chord or args.key:
            self._command = show_all
        if args.chord or args.all_chords or args.key or args.allowed_chord or args.key:
            self._render_text = render_chord_list
        self._key = args.key
        self._allowed_chord = args.allowed_chord
        if args.shape:
            self._command = lambda x: show_chords_by_shape(x, args.shape)
            self._render_text = render_chords_from_shape
        if args.notes:
            self._command = lambda x: show_chords_by_notes(x, set(args.notes.split(",")))
            self._render_text = render_chords_from_notes
        if args.show_key:
            self._command = lambda x: show_key(x, args.show_key)
            self._render_text = render_key
        if args.render_cmd:
            self.run_renderfunc(args.render_cmd)
        if args.cache_dir:
            self._cache_dir = args.cache_dir


    def set_defaults(self):
        config = configparser.ConfigParser()
        config_path = BaseDirectory.load_first_config('ukechords.ini')
        config['DEFAULTS'] = {
            'tuning': 'ukulele-c6',
            'cache_dir': os.path.join(BaseDirectory.xdg_cache_home, 'ukechords', 'cached_shapes'),
            'mute': False,
            'max_difficulty': 29.0,
            'sort_by_position': False,
        }
        if config_path and os.path.exists(config_path):
            config.read(config_path)
        defaults = config['DEFAULTS']
        self._cache_dir = defaults['cache_dir']
        self._tuning = get_tuning(defaults['tuning'])
        self._base = -1 if defaults['mute'].lower() in ("yes", "true", "t", "1") else 0
        self._max_difficulty = float(defaults['max_difficulty'])
        self._shape_ranker = rank_shape_by_difficulty
        if defaults['sort_by_position'].lower() in ("yes", "true", "t", "1"):
            self._shape_ranker = rank_shape_by_high_fret


    def run_renderfunc(self, command_name):
        if render_func := get_renderfunc_from_name(command_name):
            data = json.load(sys.stdin)
            self._command = lambda _: data
            self._render_text = render_func
        else:
            raise InvalidCommandException(f"No such rendering function \"{command_name}\"")


    @property
    def base(self):
        return self._base

    @property
    def tuning(self):
        return self._tuning

    @property
    def shape_ranker(self):
        return self._shape_ranker

    @property
    def max_difficulty(self):
        return self._max_difficulty

    @property
    def qualities(self):
        return self._qualities

    @property
    def slide(self):
        return self._slide

    @property
    def num(self):
        return self._num

    @property
    def show_notes(self):
        return self._show_notes

    @property
    def no_cache(self):
        return self._no_cache

    @property
    def visualize(self):
        return self._visualize

    @property
    def force_flat(self):
        return self._force_flat

    @property
    def json(self):
        return self._json

    @force_flat.setter
    def force_flat(self, value):
        self._force_flat = value

    def run_command(self):
        data = self._command(self)
        if self.json:
            json.dump(data, sys.stdout, indent=2 if sys.stdout.isatty() else None)
            print()
        elif self._render_text:
            self._render_text(self, data)

    @property
    def key(self):
        return self._key

    @property
    def allowed_chord(self):
        return self._allowed_chord

    @property
    def cache_dir(self):
        return self._cache_dir


def get_parser():
    # pylint: disable=line-too-long
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--chord", help="Show how to play <CHORD>")
    parser.add_argument("--notes", help="Show what chord(s) these <NOTES> play")
    parser.add_argument("-s", "--shape", help="Show what chord(s) this <SHAPE> plays")
    parser.add_argument("--slide", action='store_true', help="Show what chord(s) this <SHAPE> could play when slid up or down")
    parser.add_argument("-t", "--tuning", help="comma-separated notes for string tuning")
    parser.add_argument("-1", "--single", action='store_true', help="Show only 1 shape for each chord")
    parser.add_argument("-v", "--visualize", action='store_true', help="Visualize shapes with Unicode drawings")
    parser.add_argument("-a", "--all-chords", action='store_true', help="Show all matching chords, not just one selected one")
    parser.add_argument("-m", "--mute", action='store_true', help="Include shapes that require muting strings")
    parser.add_argument("-n", "--num", type=int, help="Show <NUM> shapes for the given chord")
    parser.add_argument("-d", "--max-difficulty", type=float, help="Limit shape-scanning to the given <MAX_DIFFICULTY>", metavar="DIFFICULTY")
    parser.add_argument("-k", "--key", action='append', help="Limit chords to those playable in <KEY> (can be specified multiple times)")
    parser.add_argument("-o", "--allowed-chord", action='append', help="Limit to chords playable by the notes in <CHORD> (specify multiple times)", metavar="CHORD")
    parser.add_argument("-q", "--qualities", help="Limit chords to chords with the specified <QUALITIES>")
    parser.add_argument("-p", "--simple", action='store_true', help="Limit to chords with major, minor, and dim qualities")
    parser.add_argument("--no-cache", action='store_true', help="Ignore any available cached chord/shape information")
    parser.add_argument("--show-key", help="Show the notes in the specified <KEY>", metavar="KEY")
    parser.add_argument("--show-notes", action='store_true', help="Show the notes in chord")
    parser.add_argument("-f", "--force-flat", action='store_true', help="Show flat-variations of chord roots")
    parser.add_argument("-b", "--sort-by-position", action='store_true', help="Sort to minimize high-position instead of difficulty")
    parser.add_argument("-j", "--json", action='store_true', help="Output in json format if possible")
    parser.add_argument("-r", "--render-cmd", help="Read stdin into a rendering command")
    parser.add_argument("--cache-dir", help="Specify directory to use for cached shapes", default=False)
    return parser


def get_args(parser, args):
    return parser.parse_args(args)
