import subprocess
import tempfile
import os
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
    tdir = os.getcwd()
    with tempfile.NamedTemporaryFile(mode='w', prefix=prefix, suffix='.py', dir=tdir) as tmp_test:
        yield tmp_test


def run_sub_pytest(file, must_pass):
    args = ['-s', '-v', '--tb=no', '--no-header']
    subprocess.run(['pytest', *args, file], check=must_pass)


missing_quality_table = [('C', '9no5', True),
                         ('C', '7sus2', True),
                         ('C', '7', False)]

@pytest.mark.parametrize('base,quality,missing', missing_quality_table)
def test_clean_missing_quality(base, quality, missing):
    with get_missing_quality_tmpfile(quality) as tmp_test:
        tmp_test.write(get_test_code_for_missing_quality(base, quality))
        tmp_test.flush()
        run_sub_pytest(tmp_test.name, must_pass=missing)
