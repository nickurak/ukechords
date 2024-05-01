import pytest  # pylint: disable=unused-import

from ukechords.render import _get_shape_lines, render_chord_list
from ukechords.render import render_chords_from_shape
from ukechords.render import _diff_string

from ukechords.render import _csv

from .uketestconfig import uke_config # pylint: disable=unused-import


# pylint: disable=redefined-outer-name


def test_get_shape_lines():
    lines = list(_get_shape_lines([-1, 0, 1]))
    expected = """
╓─┬─┬─┬──
║●│ │╷│ 
║ │ │╵│ 
║⃠ │ │ │ 
╙─┴─┴─┴──
""" # noqa
    expected_lines = expected.split('\n')
    expected_lines = expected_lines[1:-1]
    assert len(lines) == len(expected_lines)
    assert expected_lines == lines


def test_render_chord_list(capsys, uke_config):
    sl_data = {'shapes': [
        {'shape': [1], 'difficulty': 15.0,
         'chord_names': ['something'],
         'barre_data': {'barred': False, 'barred_difficulty': 32.0,
                        'fret': 4, 'shape': [5, 4], 'chord': 'chord'}
         },
        {'shape': [2, 3], 'difficulty': 2.0,
         'chord_names': ['something'],
         'barre_data': None
         }]}
    render_chord_list(uke_config, sl_data)
    out, err = capsys.readouterr()
    assert err == ""
    lines = out.strip("\n").split("\n")
    assert len(lines) == len(sl_data['shapes'])
    for shape, line in zip(sl_data['shapes'], lines):
        (chords_c, shape_str, _, diff_desc) = line.split(maxsplit=3)
        assert chords_c.rstrip(":") == _csv(shape['chord_names'])
        assert shape_str == ','.join(map(str, shape['shape']))
        diff_parts = diff_desc.strip().split(maxsplit=1)
        assert diff_parts[0] == str(shape['difficulty'])
        if shape['barre_data'] is not None:
            expected_diff_desc = _diff_string(shape['difficulty'],
                                              shape['barre_data']).split(maxsplit=1)[1]
            assert diff_parts[1] == expected_diff_desc


def test_render_chords_from_shape(capsys, uke_config):
    sl_data = {'shapes': [
        {'shape': [1],
         'chords': ['c1', 'c2'],
         'notes': ['n1', 'n2']
         }],
               'difficulty': 15.0,
               'barre_data': {'barred': False, 'barred_difficulty': 32.0,
                              'fret': 4, 'shape': [5, 4], 'chord': 'chord'}}
    render_chords_from_shape(uke_config, sl_data)
    out, err = capsys.readouterr()
    assert err == ""
    lines = out.strip("\n").split("\n")
    assert len(lines) == 2
    expected_shapestr = ",".join(map(str, sl_data['shapes'][0]['shape']))
    expected_chordstr = ",".join(sl_data['shapes'][0]['chords'])
    assert lines[0] == f"{expected_shapestr}: {expected_chordstr}"
    expected_difficulty = sl_data['difficulty']
    expected_diff_string = _diff_string(expected_difficulty, sl_data['barre_data'])
    assert lines[1] == f"Difficulty: {expected_diff_string}"
