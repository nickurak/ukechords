import pytest
from pychord import Chord


extra_quality_table = ['C9no5',
                       'C7sus2']
builtin_quality_table = ['C7']


def missing_quality_pytest_mapper():
    for chord in extra_quality_table:
        yield chord
    for chord in builtin_quality_table:
        reason = f'{chord} is present, as expected'
        yield pytest.param(chord, marks=pytest.mark.xfail(strict=True, reason=reason))


@pytest.mark.parametrize('chord', list(missing_quality_pytest_mapper()))
def test_clean_missing_quality(chord):
    with pytest.raises(ValueError):
        Chord(chord)
