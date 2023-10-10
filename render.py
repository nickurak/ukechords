from utils import csv


marks = {
    3: ' ╷╵ ',
    5: ' ╷╵ ',
    7: ' ╷╵ ',
    10: ' ╷╵ ',
    12: '╷╵╷╵',
}


def draw_shape(shape):
    max_pos = max([*shape, 3])+1
    lines = ['─'] * max_pos
    top = '╓' + '┬'.join(lines) + '─'
    bottom = '╙' + '┴'.join(lines) + '─'
    print(top)
    for string, pos in enumerate(reversed(shape)):
        chars = [' '] * max_pos
        for mark in [3, 5, 7, 10, 12]:
            if mark < max_pos + 1 and (string - (len(shape) - 4) // 2) < len(marks[mark]):
                chars[mark-1] = marks[mark][string - (len(shape) - 4) // 2]
        if pos >= 0:
            print('║', end='')
            if pos > 0:
                chars[pos - 1] = '●'
        else:
            print('║⃠', end='')
        print('│'.join(chars))
    print(bottom)


def diff_string(difficulty, desc):
    return f"{difficulty:.1f} ({desc})" if desc else f"{difficulty:.1f}"


def render_chord_list(config, data):
    if config.show_notes:
        print(f"Notes: {', '.join(data['notes'])}")
    for shape in data['shapes']:
        if config.latex:
            lchord = shape['chord'].replace('M', 'maj')
            shape_string = csv(shape['shape'])
            print(f"\\defineukulelechord{{{lchord}}}{{{shape_string}}}")
        else:
            shape_string = csv(['x' if x == -1 else x for x in shape['shape']])
            d_string = diff_string(shape['difficulty'], shape['desc'])
            print(f"{shape['chord_names']}: {shape_string}\tdifficulty: {d_string}")
        if config.visualize:
            draw_shape(shape['shape'])
