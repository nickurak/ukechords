"""Test for the ident (cli) module"""

# pylint: disable=missing-function-docstring

import pytest

from ukechords.ident import _get_parser, _get_config
from ukechords.errors import InvalidCommandException, error


def test_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        error(5, "error!")
    assert excinfo.value.code == 5
    out, err = capsys.readouterr()
    assert out == ""
    assert err == "error!\n"


def test_no_args() -> None:
    parsed_args = _get_parser().parse_args([])
    with pytest.raises(InvalidCommandException):
        _get_config(parsed_args)
