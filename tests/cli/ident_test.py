"""Test for the ident (cli) module"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from tempfile import TemporaryDirectory

import pytest

from ukechords.cli.ident import _get_config, _get_parser, run_command
from ukechords.errors import InvalidCommandException, error


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
