import pytest

from ident import main

@pytest.mark.xfail(strict=True)
def test_list_all(capsys):
    main('-a -t G,C,E -p -k C'.split())
    captured = capsys.readouterr()
    lines = captured.out.split('\n')
    chords = {}
    for line in lines:
        if line == '':
            continue
        (chord_shape, diff_string) = line.split("\t")
        (chord, shape_str) = chord_shape.split(': ')
        shape = shape_str.split(',')
        chords[chord] = {'shape': shape, 'difficulty': diff_string}
    assert chords['C']['shape'] == ['0', '0', '0']
    assert chords['C']['difficulty'] == 'difficulty: 0.0'
