import subprocess
import tempfile
import contextlib

import pytest


def get_test_code_for_missing_quality(chord):
    return f"""\
import pytest

from pychord import Chord


def test_missing__quality_in_{chord}():
    with pytest.raises(ValueError):
        Chord('{chord}')
"""


@contextlib.contextmanager
def get_missing_quality_tmpfile(chord):
    prefix = f'test_missing_quality_{chord}_'
    with tempfile.NamedTemporaryFile(mode='w', prefix=prefix, suffix='.py') as tmp_test:
        yield tmp_test


def run_sub_pytest(file):
    args = ['-s', '-v', '--tb=no', '--no-header']
    print()
    subprocess.run(['pytest', *args, file], check=True)


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
    with get_missing_quality_tmpfile(chord) as tmp_test:
        tmp_test.write(get_test_code_for_missing_quality(chord))
        tmp_test.flush()
        run_sub_pytest(tmp_test.name)
