from utils import csv


marks = {
    3: ' ╷╵ ',
    5: ' ╷╵ ',
    7: ' ╷╵ ',
    10: ' ╷╵ ',
    12: '╷╵╷╵',
}


def get_shape_lines(shape):
    max_pos = max([*shape, 3])+1
    lines = ['─'] * max_pos
    top = '╓' + '┬'.join(lines) + '─'
    bottom = '╙' + '┴'.join(lines) + '─'
    strings = []
    for string  in range(0, len(shape)):
        chars = [' '] * max_pos
        for mark in [3, 5, 7, 10, 12]:
            if mark < max_pos + 1 and (string - (len(shape) - 4) // 2) < len(marks[mark]):
                chars[mark-1] = list(reversed(marks[mark]))[string - (len(shape) - 4) // 2]
        new_string = ['║']
        for char in chars[:-1]:
            new_string.extend([char, '│'])
        new_string.append(chars[-1])
        strings.append(new_string)

    for string, pos in enumerate(shape):
        if pos > 0:
            strings[string][2 * pos - 1] = '●'
        elif pos < 0:
            strings[string][0] = strings[string][0] + '⃠'
    yield top
    for string in reversed(strings):
        yield ''.join(string)
    yield bottom

def draw_shape(shape):
    for line in get_shape_lines(shape):
        print(line)

def diff_string(difficulty, desc, diff_width=0):
    return f"{difficulty:{diff_width}.1f} ({desc})" if desc else f"{difficulty:{diff_width}.1f}"


def render_chord_list(config, data):
    if config.show_notes:
        print(f"Notes: {', '.join(data['notes'])}")
    name_width = 0
    shape_width = 0
    diff_width = 0
    for shape in data['shapes']:
        name_width = max(name_width, len(shape['chord_names']))
        shape_width = max(shape_width, len(csv(['x' if x == -1 else x for x in shape['shape']])))
        diff_width = max(diff_width, len(f"{shape['difficulty']:.1}"))
    for shape in data['shapes']:
        if config.latex:
            lchord = shape['chord'].replace('M', 'maj')
            shape_string = csv(shape['shape'])
            print(f"\\defineukulelechord{{{lchord}}}{{{shape_string}}}")
        else:
            shape_string = csv(['x' if x == -1 else x for x in shape['shape']])
            d_string = diff_string(shape['difficulty'], shape['desc'], diff_width=diff_width)
            # pylint: disable=line-too-long
            print(f"{shape['chord_names']+':':{name_width+1}} {shape_string:{shape_width}} difficulty:{d_string:}")
        if config.visualize:
            draw_shape(shape['shape'])


def render_chords_from_shape(config, data):
    for shape in data['shapes']:
        if config.show_notes:
            print(f"Notes: {csv(shape['notes'], sep=', ')}")
        if config.visualize:
            draw_shape([-1 if pos == 'x' else int(pos) for pos in shape['shape']])
        print(f'{csv(shape["shape"])}: {csv(shape["chords"])}')
    if not config.slide:
        print(f"Difficulty: {diff_string(*data['difficulty'])}")


def render_chords_from_notes(_, data):
    print(f"{csv(data['notes'])}: {csv(data['chords'])}")


def render_key(_, data):
    if data['other_keys']:
        other_str = f" ({csv(data['other_keys'])})"
    else:
        other_str = ''
    print(f"{data['key']}{other_str}:")
    print(f"{csv(data['notes'])}")
