import pytest

from pychord import Chord


def test_no5_quality():
    with pytest.raises(ValueError):
        Chord('C9no5')


def test_7sus2_quality():
    with pytest.raises(ValueError):
        Chord('C7sus2')
