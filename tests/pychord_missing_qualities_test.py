import subprocess
import tempfile
import contextlib

import pytest


def get_test_code_for_missing_quality(base, quality):
    chord = f'{base}{quality}'
    return f"""\
import pytest

from pychord import Chord


def test_missing_{quality}_quality():
    with pytest.raises(ValueError):
        Chord('{chord}')
"""


@contextlib.contextmanager
def get_missing_quality_tmpfile(quality):
    prefix = f'test_missing_quality_{quality}_'
    with tempfile.NamedTemporaryFile(mode='w', prefix=prefix, suffix='.py') as tmp_test:
        yield tmp_test


def run_sub_pytest(file):
    args = ['-s', '-v', '--tb=no', '--no-header']
    print()
    subprocess.run(['pytest', *args, file], check=True)


extra_quality_table = [('C', '9no5'),
                       ('C', '7sus2')]
builtin_quality_table = [('C', '7')]


def missing_quality_pytest_mapper():
    for root, quality in extra_quality_table:
        yield [root, quality]
    for root, quality in builtin_quality_table:
        reason = f'{root}{quality} is present, as expected'
        yield pytest.param(root, quality, marks=pytest.mark.xfail(strict=True, reason=reason))


@pytest.mark.parametrize('base,quality', list(missing_quality_pytest_mapper()))
def test_clean_missing_quality(base, quality):
    with get_missing_quality_tmpfile(quality) as tmp_test:
        tmp_test.write(get_test_code_for_missing_quality(base, quality))
        tmp_test.flush()
        run_sub_pytest(tmp_test.name)
