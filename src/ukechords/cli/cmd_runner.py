"""The Runner abstract class and its concrete subclasses provide a
clean method for both executing command logic and discovering which
implementation can handle a given command."""

import argparse
import json
import sys
from collections.abc import Callable
from typing import Any

from ukechords.cli.render import render_chord_list, render_chords_from_shape, render_key
from ukechords.config import UkeConfig
from ukechords.errors import InvalidCommandException
from ukechords.theory import (
    show_all,
    show_chord,
    show_chords_by_notes,
    show_chords_by_shape,
    show_key,
)
from ukechords.types import ChordsByShape, ChordShapes, KeyInfo


def _get_renderfunc_from_name(name: str) -> Callable[[UkeConfig, Any], None]:
    render_funcs: list[Callable[[UkeConfig, Any], None]] = [
        render_chord_list,
        render_chords_from_shape,
        render_key,
    ]
    render_func_map: dict[str, Callable[[UkeConfig, Any], None]] = {
        str(f.__name__): f for f in render_funcs if hasattr(f, "__name__")
    }
    if name in render_func_map:
        return render_func_map[name]

    msg = f'No such rendering function "{name}". Options: {", ".join(render_func_map)}'
    raise InvalidCommandException(msg)


class Runner:
    """Runner defines the API for command handlers, and provides a
    lookup method for finding appropriate subclass implementations
    based on provided arguments."""

    _runners: set[type["Runner"]] | None = None

    def __init_subclass__(cls) -> None:
        if Runner._runners is None:
            Runner._runners = set()
        Runner._runners.add(cls)

    def __init__(self, config: UkeConfig, args: argparse.Namespace) -> None:
        self.config = config
        self.args = args

    @staticmethod
    def match_command(_: argparse.Namespace, /) -> bool:
        """Allows a subclass to indicate if it can/should handle the
        specified arguments."""
        return False

    @staticmethod
    def make(config: UkeConfig, args: argparse.Namespace) -> "Runner":
        """Return a Runner of one of our subclasses capable of handling the provided arguments."""
        for runner in Runner._runners or []:
            if runner.match_command(args):
                return runner(config, args)
        assert False, "No command configuration found"

    def get_data(self) -> ChordShapes | ChordsByShape | KeyInfo:
        """Return the (unrendered) data for this command"""
        raise NotImplementedError

    def render(self) -> None:
        """Render this command's output on stdout"""
        raise NotImplementedError

    def run(self) -> None:
        """Run this command and render it either in its pretty form or
        as JSON output"""
        if self.args.json:
            json.dump(self.get_data(), sys.stdout, indent=2 if sys.stdout.isatty() else None)
            print()
        else:
            self.render()


class ShowChordRunner(Runner):
    """Show information about a single chord (ie with --chord/-c)"""

    @staticmethod
    def match_command(args: argparse.Namespace, /) -> bool:
        return bool(args.chord)

    def get_data(self) -> ChordShapes:
        return show_chord(self.config, self.args.chord)

    def render(self) -> None:
        render_chord_list(self.config, self.get_data())


class ShowAllRunner(ShowChordRunner):
    """Show all known chords (matching difficulty/qualities/key/etc filters)"""

    @staticmethod
    def match_command(args: argparse.Namespace, /) -> bool:
        return bool(args.all_chords or args.keys or args.allowed_chords)

    def get_data(self) -> ChordShapes:
        return show_all(self.config)


class ShowChordsByShapeRunner(Runner):
    """Show information about a shape"""

    @staticmethod
    def match_command(args: argparse.Namespace, /) -> bool:
        return bool(args.shape)

    def get_data(self) -> ChordsByShape:
        return show_chords_by_shape(self.config, self.args.shape)

    def render(self) -> None:
        render_chords_from_shape(self.config, self.get_data())


class ShowChordsByNotesRunner(ShowChordRunner):
    """Show information about how to play specified notes and what
    chord(s) they yield"""

    @staticmethod
    def match_command(args: argparse.Namespace, /) -> bool:
        return bool(args.notes)

    def get_data(self) -> ChordShapes:
        return show_chords_by_notes(self.config, self.args.notes)


class ShowKeyRunner(Runner):
    """Show information about a key (specified by either key name or
    matching notes)"""

    @staticmethod
    def match_command(args: argparse.Namespace, /) -> bool:
        return bool(args.show_key)

    def get_data(self) -> KeyInfo:
        return show_key(self.config, self.args.show_key)

    def render(self) -> None:
        render_key(self.config, self.get_data())


class RenderCmdRunner(Runner):
    """Render JSON from stdin with the specified render function"""

    @staticmethod
    def match_command(args: argparse.Namespace, /) -> bool:
        return bool(args.render_cmd)

    def get_data(self) -> Any:
        return json.load(sys.stdin)

    def render(self) -> None:
        _get_renderfunc_from_name(self.args.render_cmd)(self.config, self.get_data())
