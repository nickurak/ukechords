from render import get_shape_lines

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
