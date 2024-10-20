# pylint: disable=missing-function-docstring,missing-class-docstring,missing-module-docstring

import pytest

from ukechords.config import UkeConfig, InvalidCommandException


def test_no_args():
    with pytest.raises(InvalidCommandException):
        UkeConfig([])
