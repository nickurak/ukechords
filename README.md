# ukechords

Reason about stringed instrument chords (especially ukulele).

Ukechords chiefly solves 2 problems (and add some accesory function as well.):

1. If I fret/play a particular shape on my stringed instrument, what (if any) recognized chord(s) will be made when I strum?
   - This is accomplished with the "ident" tool's `--shape/-s` option
2. If I want to play a given chord, what shape(s) can use to produce that chord?
   - This is accomplished with the "ident" tool's `--chord/-c` option

This is heavily supported by the music-theory functionality of the [pychord](https://pypi.org/project/pychord/) music-theory library.

Other miscellaneous functionality:
- Heurestically determining the difficulty of different shapes, and ranking them
- Rendering unicode drawings of those shapes on the command line
- Listing all known chords and how to play them
- Limiting lists of chords by musical key or quality
- Finding chords from lists of notes
- Accounting for muted/omitted strings
- support for several/arbitrary tunings, with any number of strings
- caching of calculated information (as this can be computationally intense)
- JSON output of all information for consumption in other tools

This started as a very basic tool/experiment, but has grown into a significant part of my music hobby.

# Installation

Get it:

```
$ git clone https://github.com/nickurak/ukechords.git
```

Install it with flit, ideally in a pyvenv:

```
$ python -m venv ~/ukechords
$ . ~/ukechords/bin/activate
$ pip install flit
$ cd ukechords
$ flit install # (tip: include flit install's -s option to create symlinks while developing the source)
$ ln -s ~/ukechords/bin/ident ~/.local/bin/ident # this will make the "ident" tool available
```

# Usage:

```
usage: ident [-h] [-c CHORD] [--notes NOTES] [-s SHAPE] [--slide] [-t TUNING] [-1] [-v] [-a] [-m] [-n NUM] [-k KEY] [-q QUALITIES] [-p] [--no-cache] [--show-key KEY] [--show-notes] [-f] [-b] [-j] [-r RENDER_CMD] [--cache-dir CACHE_DIR] [-d MAX_DIFFICULTY] [-o ALLOWED_CHORDS]

options:
  -h, --help            show this help message and exit
  -c CHORD, --chord CHORD
                        Show how to play <CHORD>
  --notes NOTES         Show what chord(s) these <NOTES> play
  -s SHAPE, --shape SHAPE
                        Show what chord(s) this <SHAPE> plays
  --slide               Show what chord(s) this <SHAPE> could play when slid up or down
  -t TUNING, --tuning TUNING
                        comma-separated notes for string tuning
  -1, --single          Show only 1 shape for each chord
  -v, --visualize       Visualize shapes with Unicode drawings
  -a, --all-chords      Show all matching chords, not just one selected one
  -m, --mute            Include shapes that require muting strings
  -n NUM, --num NUM     Show <NUM> shapes for the given chord
  -k KEY, --key KEY     Limit chords to those playable in <KEY> (can be specified multiple times)
  -q QUALITIES, --qualities QUALITIES
                        Limit chords to chords with the specified <QUALITIES>
  -p, --simple          Limit to chords with major, minor, and dim qualities
  --no-cache            Ignore any available cached chord/shape information
  --show-key KEY        Show the notes in the specified <KEY>
  --show-notes          Show the notes in chord
  -f, --force-flat      Show flat-variations of chord roots
  -b, --sort-by-position
                        Sort to minimize high-position instead of difficulty
  -j, --json            Output in json format if possible
  -r RENDER_CMD, --render-cmd RENDER_CMD
                        Read stdin into a rendering command
  --cache-dir CACHE_DIR
                        Specify directory to use for cached shapes
  -d MAX_DIFFICULTY, --max-difficulty MAX_DIFFICULTY
                        Limit shape-scanning to the given <MAX_DIFFICULTY> or less
  -o ALLOWED_CHORDS, --allowed-chords ALLOWED_CHORDS
                        Limit to chords playable by the notes in <ALLOWED_CHORD> (specify multiple times)
```
