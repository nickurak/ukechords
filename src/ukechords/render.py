from .utils import csv


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
    yield '╓' + '┬'.join(lines) + '─'
    for string, pos in enumerate(reversed(shape)):
        chars = [' '] * max_pos
        for mark in [3, 5, 7, 10, 12]:
            if mark < max_pos + 1 and (string - (len(shape) - 4) // 2) < len(marks[mark]):
                chars[mark-1] = marks[mark][string - (len(shape) - 4) // 2]
        if pos > 0:
            chars[pos - 1] = '●'
        yield '║' + ('⃠' if pos < 0 else '') + '│'.join(chars)
    yield '╙' + '┴'.join(lines) + '─'


def draw_shape(shape):
    for line in get_shape_lines(shape):
        print(line)


def diff_string(difficulty, barre_data, diff_width=0):
    # pylint: disable=line-too-long
    if barre_data:
        if barre_data['barred']:
            return f"{difficulty:{diff_width}.1f} (barre {barre_data['fret']} + {csv(barre_data['shape'])}:{barre_data['chord']}, else {barre_data['unbarred_difficulty']:.1f})"
        return f"{difficulty:{diff_width}.1f} (else {barre_data['barred_difficulty']:.1f}: barred {barre_data['fret']} + {csv(barre_data['shape'])}:{barre_data['chord']})"

    return f"{difficulty:{diff_width}.1f}"


def render_chord_list(config, data):
    if config.show_notes:
        print(f"Notes: {', '.join(data['notes'])}")
    name_width = 0
    shape_width = 0
    diff_width = 0
    for shape in data['shapes']:
        name_width = max(name_width, len(csv(shape['chord_names'])))
        shape_width = max(shape_width, len(csv(['x' if x == -1 else x for x in shape['shape']])))
        diff_width = max(diff_width, len(f"{shape['difficulty']:.1}"))
    for shape in data['shapes']:
        if config.latex:
            lchord = shape['chord_names'][0].replace('M', 'maj')
            shape_string = csv(shape['shape'])
            print(f"\\defineukulelechord{{{lchord}}}{{{shape_string}}}")
        else:
            shape_string = csv(['x' if x == -1 else x for x in shape['shape']])
            d_string = diff_string(shape['difficulty'], shape['barre_data'], diff_width=diff_width)
            # pylint: disable=line-too-long
            print(f"{csv(shape['chord_names'])+':':{name_width+1}} {shape_string:{shape_width}} difficulty:{d_string:}")
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
        print(f"Difficulty: {diff_string(data['difficulty'], data['barre_data'])}")


def render_chords_from_notes(_, data):
    print(f"{csv(data['notes'])}: {csv(data['chords'])}")


def render_key(_, data):
    if data['other_keys']:
        other_str = f" ({csv(data['other_keys'])})"
    else:
        other_str = ''
    if 'key' in data:
        print(f"{data['key']}{other_str}:")
        print(f"{csv(data['notes'])}")
    else:
        if not data['other_keys']:
            print("No key found")
            return
        print(f"{csv(data['other_keys'])}")