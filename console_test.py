from ident import main

def test_list_all(capsys):
    main('-a -t G,C,E -p -k C'.split())
    captured = capsys.readouterr()
    lines = captured.out.split('\n')
    chords = {}
    for line in lines:
        if line == '':
            continue
        (chord, shape_str, diff_string) = line.split(maxsplit=2)
        chord = chord.rstrip(':')
        shape = shape_str.split(',')
        chords[chord] = {'shape': shape, 'difficulty': diff_string}
    assert chords['C']['shape'] == ['0', '0', '0']
    assert chords['C']['difficulty'].split() == ['difficulty:', '0.0']


def test_get_by_shape(capsys):
    main('-s 0,0,0 -t G,C,E'.split())
    captured = capsys.readouterr()
    lines = captured.out.split('\n')
    assert lines[2] == ''
    (shape, chord) = lines[0].split(': ')
    (diff_label, diff_str) = lines[1].split(': ')
    assert shape ==  '0,0,0'
    assert chord == 'C'
    assert diff_label == 'Difficulty'
    assert diff_str == '0.0'
