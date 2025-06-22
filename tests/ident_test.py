"""Test for the ident (cli) module"""

import pytest

from ukechords.ident import _get_parser, _get_config
from ukechords.errors import InvalidCommandException, error


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
