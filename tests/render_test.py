from uketestconfig import uke_config #pylint: disable=unused-import

from render import get_shape_lines, render_chord_list
from render import render_chords_from_shape

# pylint: disable=redefined-outer-name

def test_get_shape_lines():
    lines = list(get_shape_lines([-1, 0, 1]))
    expected = """
╓─┬─┬─┬──
║●│ │╷│ 
║ │ │╵│ 
║⃠ │ │ │ 
╙─┴─┴─┴──
"""
    expected_lines = expected.split('\n')
    expected_lines = expected_lines[1:-1]
    assert len(lines) == len(expected_lines)
    assert expected_lines == lines


def test_render_chord_list(capsys, uke_config):
    uke_config.latex = False
    sl_data = { 'shapes': [
        {'shape': [1], 'difficulty': 15.0,
         'chord_names': 'something',
         'desc': 'desc1'
         },
        {'shape': [2], 'difficulty': 2.0,
         'chord_names': 'something',
         'desc': 'desc2'
         } ] }
    render_chord_list(uke_config, sl_data)
    out, err = capsys.readouterr()
    assert err == ""
    lines = out.strip("\n").split("\n")
    assert len(lines) == len(sl_data['shapes'])
    for shape, line in zip(sl_data['shapes'], lines):
        (chord, shape_diff_str, diff_desc) = line.split(":")
        assert chord.strip() == shape['chord_names']
        (shape_str, _) = shape_diff_str.split()
        assert shape_str == ','.join(map(str, shape['shape']))
        (diff, desc) = diff_desc.strip().split(maxsplit=1)
        assert diff == str(shape['difficulty'])
        assert desc == f"({shape['desc']})"


def test_render_chords_from_shape(capsys, uke_config):
    uke_config.latex = False
    sl_data = { 'shapes': [
        {'shape': [1],
         'chords': ['c1', 'c2'],
         'notes': ['n1', 'n2']
         }],
                'difficulty': [15.0, "desc"]}
    render_chords_from_shape(uke_config, sl_data)
    out, err = capsys.readouterr()
    assert err == ""
    lines = out.strip("\n").split("\n")
    assert len(lines) == 2
    expected_shapestr = ",".join(map(str, sl_data['shapes'][0]['shape']))
    expected_chordstr = ",".join(sl_data['shapes'][0]['chords'])
    assert lines[0] == f"{expected_shapestr}: {expected_chordstr}"
    expected_difficulty = f"{sl_data['difficulty'][0]}"
    expected_desc = f"{sl_data['difficulty'][1]}"
    assert lines[1] == f"Difficulty: {expected_difficulty} ({expected_desc})"
