# pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring

import pytest

from ukechords.config import UkeConfig, get_parser, InvalidCommandException


def test_no_args():
    parser = get_parser()
    args = parser.parse_args([])
    with pytest.raises(InvalidCommandException):
        UkeConfig(args)
