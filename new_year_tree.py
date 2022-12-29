from random import Random
from sys import stdout
from time import sleep
from os import get_terminal_size

def smoothstep(x):
    if x <= 0.0:
        return 0.0
    elif x >= 1.0:
        return 1.0
    else:
        return 3 * x * x - 2 * x * x * x

def interpolate(X,Y,xrange,interpolation = smoothstep):
    vals = sorted(zip(X,Y), key = lambda x:x[0])
    vals_iter = iter(vals)
    xrange_iter = iter(xrange)
    X_out, Y_out = [], []
    
    try:
        x1,y1 = next(vals_iter)
        x_tgt = next(xrange_iter)
        while x_tgt < x1:
            X_out.append(x_tgt)
            Y_out.append(y1)
            x_tgt = next(xrange_iter)
        
        while True:
            x2,y2 = next(vals_iter)
            while x_tgt <= x2:
                x_interpolation = (x_tgt - x1) / (x2 - x1)
                y_interpolation = interpolation(x_interpolation)
                y_interpolated = int(y1 + (y2 - y1) * y_interpolation)
                X_out.append(x_tgt)
                Y_out.append(y_interpolated)
                x_tgt = next(xrange_iter)
            
            x1,y1 = x2,y2
    except StopIteration:
        try:
            while True:
                X_out.append(x_tgt)
                Y_out.append(y2)
                x_tgt = next(xrange_iter)
        except StopIteration:
            return X_out, Y_out


def get_random_layer(rand: Random, width, step, height):
    X = list(range(0,width,step))
    Y = [rand.randint(0,height) for _ in X]

    return interpolate(X, Y, range(width))

def sum_layers(*XYs):
    keys_set = set(XYs[0][0])
    for X_set in map(lambda x:set(x[0]), XYs):
        keys_set = keys_set & X_set
    
    keys = sorted(keys_set)
    XYs_dicts = list(map(lambda x:dict(zip(x[0], x[1])), XYs))
    vals = [sum(XY[key] for XY in XYs_dicts) for key in keys]

    return keys, vals

def const_height(width, height):
    X, Y = [], []

    for x in range(width):
        X.append(x)
        Y.append(height)
    
    return X, Y

def generate_heights_map(rand: Random, width, height):
    low_height = int(0.4 * height)
    mid_height = int(0.55 * height)
    hight_height = int(0.6 * height)

    layer0 = const_height(width, low_height)
    layer1 = get_random_layer(rand, width, 30, mid_height - low_height)
    layer2 = get_random_layer(rand, width, 20, hight_height - mid_height)

    return sum_layers(layer0, layer1, layer2)

def render_background(X, Y, width, height):
    bg = [[' '] * width for _ in range(height)]

    for _,y2 in zip(X,Y):
        break

    y1 = y2

    for x2,y2 in zip(X,Y):
        if y2 < y1:
            bg[height - y1 + 1][x2] = '\\'
            if y1 - y2 > 1:
                bg[height - y2][x2] = '/'
                for y in range(y2, y1):
                    bg[height - y][x2] = '|'
        elif y2 > y1:
            bg[height - y1][x2] = '/'
            if y2 - y1 > 1:
                bg[height - y2 + 1][x2] = '\\'
                for y in range(y1, y2):
                    bg[height - y][x2] = '|'
        else:
            bg[height - y2][x2] = '_'
        
        y1 = y2
    
    return bg

def render_background_hitmask(X, Y, width, height):
    mask = [[False] * width for _ in range(height)]

    for x,y_start in zip(X,Y):
        y_start = height - y_start
        for y in range(y_start+1, height):
            mask[y][x] = True
    
    return mask

def read_figures(figures_filename):
    figures_dict = dict()
    
    def cut_nl(line):
        if line[-1] == '\n':
            return line[:-1]
        else:
            return line

    with open(figures_filename, 'rt') as figures_file:
        lines_iter = iter(map(cut_nl,figures_file))

        for header in lines_iter:
            if len(header) >= 2 and header[-1] == ':':
                figure_lines = list()
                hitmask_lines = list()
                header = header[:-1]
                width = 0
                height = 0

                for line in lines_iter:
                    if line == '':
                        break
                    
                    height += 1
                    in_figure = False

                    figure_line = list()
                    hitmask_line = list()

                    for idx,ch in enumerate(line):
                        if ch != ' ' or in_figure:
                            in_figure = True
                            figure_line.append(ch)
                            hitmask_line.append(True)
                            if idx + 1 > width:
                                width = idx + 1
                        else:
                            figure_line.append(None)
                            hitmask_line.append(False)
                    
                    figure_lines.append(figure_line)
                    hitmask_lines.append(hitmask_line)
                
                figures_dict[header] = (width, height, figure_lines, hitmask_lines)
    
    return figures_dict


def place_figure(buf, x_pos, y_pos, figure):
    width, height, figure_lines, _ = figure
    y_pos -= height
    x_pos -= width // 2

    for y_idx, line in enumerate(figure_lines):
        y = y_idx + y_pos

        for x_idx, ch in enumerate(line):
            x = x_idx + x_pos

            if y < 0 or x < 0:
                continue

            if y >= len(buf):
                continue

            buf_line = buf[y]
            
            if x >= len(buf_line):
                continue
            
            if not ch is None:
                buf_line[x] = ch

def place_figure_hitmap(buf, x_pos, y_pos, figure):
    width, height, _, hitmask_lines = figure
    y_pos -= height
    x_pos -= width // 2

    for y_idx, line in enumerate(hitmask_lines):
        y = y_idx + y_pos

        for x_idx, flag in enumerate(line):
            x = x_idx + x_pos

            if y < 0 or x < 0:
                continue

            if y >= len(buf):
                continue

            buf_line = buf[y]
            
            if x >= len(buf_line):
                continue
            
            if flag:
                buf_line[x] = True

def get_rangom_point_from_hitmask(rand: Random, hitmask):
    height = len(hitmask)
    width = min(map(len,hitmask))
    hit = False
    x, y = None, None

    while not hit:
        x = rand.randint(0, width - 1)
        y = rand.randint(0, height - 1)
        hit = hitmask[y][x]
    
    return x, y

def get_house_place_from_hitmask(offset_y, hitmask):
    height = len(hitmask)
    width = min(map(len,hitmask))
    
    x = width // 2
    offset_y_achieved = 0
    for y in range(height):
        hit = hitmask[y][x]
        if hit:
            offset_y_achieved += 1
            if offset_y_achieved >= offset_y:
                break
    
    return x,y

def buf_to_string(buf):
    return '\n'.join(''.join(X) for X in buf)

def hitmask_to_string(mask):
    return buf_to_string([['#' if x else ' ' for x in X] for X in mask])

def generate_picture(width, height, seed = 1234):
    rand = Random(seed)
    X, Y = generate_heights_map(rand, width, height)

    buf = render_background(X, Y, width, height)
    hitmask = render_background_hitmask(X, Y, width, height)
    figures = read_figures('figures.txt')
    tree_fig = figures["tree"]
    house_fig = figures["house"]

    trees_count = int(width * height * 0.002)
    figures_to_add = list()
    house_x, house_y = get_house_place_from_hitmask(5, hitmask)
    for _ in range(trees_count):
        x,y = get_rangom_point_from_hitmask(rand, hitmask)
        while (house_x - x)**2 + (house_y - y) ** 2 < 230:
            x,y = get_rangom_point_from_hitmask(rand, hitmask)
        
        figures_to_add.append((x,y,tree_fig))

    figures_to_add.append((house_x, house_y, house_fig))
    figures_to_add.sort(key = lambda x:x[1])

    for x,y,fig in figures_to_add:
        place_figure(buf, x, y, fig)
        place_figure_hitmap(hitmask, x, y, fig)
    
    return buf, hitmask

def csi_cursor_position(n,m):
    stdout.write("\x1b[" + str(n) + ";" + str(m) + "H")

def csi_erase_data(n):
    stdout.write("\x1b[" + str(n) + "J")

def print_char_at(n,m,ch):
    csi_cursor_position(n,m)
    stdout.write(ch)

def draw_picture(buf):
    for idx, line in enumerate(buf):
        csi_cursor_position(idx, 0)
        stdout.write(''.join(line))
    stdout.flush()

class SnowFlake:
    def __init__(self, tgt_x, tgt_y, to_lay = True):
        self.tgt_x = tgt_x
        self.tgt_y = tgt_y
        self.to_lay = to_lay
        self.y = 0
    
    @property
    def x(self):
        return self.tgt_x + (self.tgt_y - self.y) % 2
    
    @property
    def finished(self):
        return self.y >= self.tgt_y
    
    def tick(self):
        if self.y < self.tgt_y:
            self.y += 1
    
def spawn_snowflake(rand: Random, width, height, snowflakes, hitmask):
    if rand.randint(0,1):
        x_pos = rand.randint(0, width - 1)
        spawned_slowflake = SnowFlake(x_pos, height, True)
    else:
        hit = False
        while not hit:
            x_pos = rand.randint(0, width - 1)
            y_pos = rand.randint(0, height - 1)
            hit = hitmask[y_pos][x_pos]
        
        spawned_slowflake = SnowFlake(x_pos, y_pos, True)
    
    snowflakes.append(spawned_slowflake)

def process_snowflakes(buf, width, height, snowflakes):
    snowflakes_to_remove = list()

    for snowflake in snowflakes:
        px, py = snowflake.x, snowflake.y
        snowflake.tick()
        x, y = snowflake.x, snowflake.y

        if x >= 0 and y >= 0 and x < width and y < height and not snowflake.finished:
            print_char_at(y, x + 1, '*')
        
        if px >= 0 and py >= 0 and px < width and py < height:
            print_char_at(py, px + 1, buf[py][px])
        
        if snowflake.finished:
            if x >= 0 and y >= 0 and x < width and y < height and snowflake.to_lay:
                print_char_at(y, x + 1, '*')
                buf[y][x] = '*'
            
            snowflakes_to_remove.append(snowflake)
    
    for snowflake in snowflakes_to_remove:
        snowflakes.remove(snowflake)

def loop():
    rand = Random()
    width, height = get_terminal_size()
    buf, hitmask = generate_picture(width, height)
    snowflakes = list()

    draw_picture(buf)

    while True:
        sleep(0.3)

        process_snowflakes(buf, width, height, snowflakes)
        for i in range(3):
            spawn_snowflake(rand, width, height, snowflakes, hitmask)
        stdout.flush()

if __name__ == '__main__':
    loop()