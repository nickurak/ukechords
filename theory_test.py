import pytest

from theory import sharpify, flatify


def test_sharpify():
    assert  sharpify('Bb') == 'A#'
    assert  sharpify('A#') == 'A#'
    assert  flatify('A#') == 'Bb'
    assert flatify ('Bb') == 'Bb'

    assert all(x == y for x, y in zip(sharpify(['Bb', 'A#']), ['A#', 'A#']))
    assert all(x == y for x, y in zip(flatify(['Bb', 'A#']), ['Bb', 'Bb']))
