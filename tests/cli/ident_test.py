"""Test for the ident (cli) module"""

import io
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from tempfile import TemporaryDirectory

import pytest

from ukechords.cli.ident import _get_config, _get_parser, run_command
from ukechords.errors import InvalidCommandException, error

from .characterization import characterization


@contextmanager
def get_runner(cmdline: str) -> Iterator[Callable[[], None]]:
    """Generate a Runner based on the provided command line, enforcing
    a temporary directory and tuning"""
    args = cmdline.split()
    p_args = _get_parser().parse_args(args)
    assert not p_args.cache_dir, "can't specify cache in ident test"
    config = _get_config(p_args)
    if not p_args.tuning:
        config.tuning = ("G", "C", "E")
    with TemporaryDirectory() as tmp_dir:
        config.cache_dir = str(tmp_dir)
        yield lambda: run_command(config, p_args)


argstrs = [
    "-a",
    "-c C",
    "-s 0,0,0",
    "--show-key C",
    "-t A,B,C -c C",
    "-a -q 9",
    "--show-key C,D,E,G,A",
    "-v -c C",
    "-v -s 1,2,3",
]


@pytest.mark.parametrize("argstr", argstrs)
def test_ident(characterization: None, argstr: str) -> None:
    """Check that a bunch of commands work"""
    with get_runner(argstr) as runner:
        runner()


renderable_jsons = [
    (
        "--render-cmd render_chord_list",
        (
            '{"shapes": [{"shape": [0, 0, 0], "difficulty": 0.0, '
            '"barre_data": null, "chord_names": ["C"]}]}'
        ),
    ),
    (
        "--render-cmd render_chord_list --visualize",
        (
            '{"shapes": [{"shape": [0, 0, 0], "difficulty": 0.0, '
            '"barre_data": null, "chord_names": ["C"]}]}'
        ),
    ),
    (
        "--render-cmd render_chord_list --visualize",
        (
            '{"shapes": [{"shape": [1, 2, 3], "difficulty": 0.0, '
            '"barre_data": null, "chord_names": ["C"]}]}'
        ),
    ),
    (
        "--render-cmd render_chord_list --visualize",
        (
            '{"shapes": [{"shape": [1, 1, 3], "difficulty": 0.0, '
            '"barre_data": {"fret": 1, "barred": true, "shape": '
            '[0, 0, 2], "chord": null, "unbarred_difficulty": 8.0}, "chord_names": ["C"]}]}'
        ),
    ),
    (
        "--render-cmd render_chord_list --visualize",
        (
            '{"shapes": [{"shape": [1, 1, 3], "difficulty": 0.0, '
            '"barre_data": {"fret": 1, "barred": false, "shape": '
            '[0, 0, 2], "chord": null, "barred_difficulty": 8.0}, "chord_names": ["C"]}]}'
        ),
    ),
    (
        "--render-cmd render_chords_from_shape --visualize",
        (
            '{"shapes": [{"shape": [2, 0, 0], "chords": ["Am", "C6no5"], '
            '"notes": ["A", "E", "C"]}], "difficulty": 4.2, "barre_data": null}'
        ),
    ),
    (
        "--show-key C",
        (
            '{"notes": ["C", "D", "E", "F", "G", "A", "B"], "key": "C", '
            '"other_keys": ["C", "Am", "Ephmod"], "partial_keys": []}'
        ),
    ),
]


@pytest.mark.parametrize("renderable_json", renderable_jsons)
def test_rendercmd(
    characterization: None, monkeypatch: pytest.MonkeyPatch, renderable_json: tuple[str, str]
) -> None:
    """Check that several rendercmd invocations work correctly"""
    argstr, json_data = renderable_json
    monkeypatch.setattr("sys.stdin", io.StringIO(json_data))
    with get_runner(argstr) as runner:
        runner()


def test_error(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that error handling triggers an exit with exit-code"""
    with pytest.raises(SystemExit) as excinfo:
        error(5, "error!")
    assert excinfo.value.code == 5
    out, err = capsys.readouterr()
    assert out == ""
    assert err == "error!\n"


def test_no_args() -> None:
    """Test that attempting to run with empty arguments is caught"""
    parsed_args = _get_parser().parse_args([])
    with pytest.raises(InvalidCommandException):
        _get_config(parsed_args)
