import subprocess
import tempfile
import contextlib

import pytest


def get_test_code_for_missing_quality(base, quality, xfail):
    chord = f'{base}{quality}'
    xfail_line = '@pytest.mark.xfail(strict=True)' if xfail else ''
    return f"""\
import pytest

from pychord import Chord

{xfail_line}
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


missing_quality_table = [('C', '9no5', True),
                         ('C', '7sus2', True),
                         ('C', '7', False)]


@pytest.mark.parametrize('base,quality,missing', missing_quality_table)
def test_clean_missing_quality(base, quality, missing):
    with get_missing_quality_tmpfile(quality) as tmp_test:
        tmp_test.write(get_test_code_for_missing_quality(base, quality, xfail = not missing))
        tmp_test.flush()
        run_sub_pytest(tmp_test.name)
