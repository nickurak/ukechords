import argparse

from theory import get_tuning, rank_shape_by_difficulty, rank_shape_by_high_fret
from theory import show_chord, show_all, show_chords_by_shape
from theory import show_chords_by_notes, show_key

from utils import error

class UkeConfig():
    # pylint: disable=line-too-long
    # pylint: disable=too-many-instance-attributes
    def __init__(self, args):
        self._base = -1 if args.mute else 0
        self._tuning = get_tuning(args)
        self._shape_ranker = rank_shape_by_high_fret if args.sort_by_position else rank_shape_by_difficulty
        self._max_difficulty = args.max_difficulty or 29
        if list(map(bool, [args.notes, args.chord, args.shape, (args.all_chords or args.key or args.allowed_chord), args.show_key])).count(True) != 1:
            error(5, "Provide exactly one of --all-chords, --chord, --shape, --notes, or --show-key", get_parser())
        if args.qualities and args.simple:
            error(7, "Provide only one of -p/--simple or -q/--qualities")
        self._qualities = False
        if args.simple:
            self._qualities = ['', 'm', '7', 'dim', 'maj', 'm7']
        if args.qualities is not None:
            self._qualities = args.qualities.split(',')
        self._slide = args.slide
        if args.slide and not args.shape:
            error(8, "--slide requries a --shape")
        self._num = args.num
        if args.single:
            self._num = 1
        if not self._num and (args.latex or args.visualize):
            self._num = 1
        self._show_notes = args.show_notes
        self._no_cache = args.no_cache
        self._latex = args.latex
        self._visualize = args.visualize
        self._force_flat = args.force_flat
        if args.chord:
            self._command = lambda x: show_chord(x, args.chord)
        if args.all_chords or args.key or args.allowed_chord or args.key:
            self._command = show_all
        self._key = args.key
        self._allowed_chord = args.allowed_chord
        if args.shape:
            self._command = lambda x: show_chords_by_shape(x, args.shape)
        if args.notes:
            self._command = lambda x: show_chords_by_notes(x, set(args.notes.split(",")))
        if args.show_key:
            self._command = lambda x: show_key(x, args.show_key)

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
    def latex(self):
        return self._latex

    @property
    def visualize(self):
        return self._visualize

    @property
    def force_flat(self):
        return self._force_flat

    @force_flat.setter
    def force_flat(self, value):
        self._force_flat = value

    @property
    def command(self):
        return self._command

    @property
    def key(self):
        return self._key

    @property
    def allowed_chord(self):
        return self._allowed_chord


def get_parser():
    # pylint: disable=line-too-long
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--chord", help="Show how to play <CHORD>")
    parser.add_argument("--notes", help="Show what chord(s) these <NOTES> play")
    parser.add_argument("-s", "--shape", help="Show what chord(s) this <SHAPE> plays")
    parser.add_argument("--slide", action='store_true', help="Show what chord(s) this <SHAPE> could play when slid up or down")
    parser.add_argument("-t", "--tuning", default='ukulele-c6', help="comma-separated notes for string tuning")
    parser.add_argument("-1", "--single", action='store_true', help="Show only 1 shape for each chord")
    parser.add_argument("-l", "--latex", action='store_true', help="Output chord info in LaTeX format")
    parser.add_argument("-v", "--visualize", action='store_true', help="Visualize shapes with Unicode drawings")
    parser.add_argument("-a", "--all-chords", action='store_true', help="Show all matching chords, not just one selected one")
    parser.add_argument("-m", "--mute", action='store_true', help="Include shapes that require muting strings")
    parser.add_argument("-n", "--num", type=int, help="Show <NUM> shapes for the given chord")
    parser.add_argument("-d", "--max-difficulty", type=float, help="Limit shape-scanning to the given <MAX_DIFFICULTY>", metavar="DIFFICULTY")
    parser.add_argument("-k", "--key", action='append', help="Limit chords to those playable in <KEY> (can be specified multiple times)")
    parser.add_argument("-o", "--allowed-chord", action='append', help="Limit to chords playable by the notes in <CHORD> (specify multiple times)", metavar="CHORD")
    parser.add_argument("-q", "--qualities", help="Limit chords to chords with the specified <QUALITIES>")
    parser.add_argument("-p", "--simple", action='store_true', help="Limit to chords with major, minor, dim, and maj7/min7 qualities")
    parser.add_argument("--no-cache", action='store_true', help="Ignore any available cached chord/shape information")
    parser.add_argument("--show-key", help="Show the notes in the specified <KEY>", metavar="KEY")
    parser.add_argument("--show-notes", action='store_true', help="Show the notes in chord")
    parser.add_argument("-f", "--force-flat", action='store_true', help="Show flat-variations of chord roots")
    parser.add_argument("-b", "--sort-by-position",  action='store_true', help="Sort to minimize high-position instead of difficulty")
    return parser


def get_args(parser):
    return parser.parse_args()
