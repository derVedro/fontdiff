import sys, tempfile, webbrowser, struct
from io import TextIOWrapper
from itertools import product
import ziafont
from pathops import Path, PathVerb
from pathops.operations import intersection as skia_intersection

config = None

def generate_css():
    return f'''    <style>
        .a                 {{fill: {config.a_color};}}
        .b                 {{fill: {config.b_color};}}
        .overlap           {{fill: {config.overlap_color};}}
        .baseline          {{stroke: {config.baseline_color};}}
        .legend-background {{fill: {config.cell_background_color}; stroke: {config.cell_background_color}}}
        .cell-background   {{fill: {config.cell_background_color}; stroke: {config.grid_color};}}       
    </style>'''


def generate_header():
    return (
        f'<svg version="1.1" xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 {-config.legend_height} '
        f'{config.cols * config.cell_width} '
        f'{config.rows * config.cell_height + config.legend_height}">'
    )


def d_rect(x, y, width,height):
    return f'M {x} {y} L {x+width} {y} L {x+width} {y+height} L {x} {y+height} L {x} {y} Z'


def generate_background():
    width = config.cols * config.cell_width
    height = config.rows * config.cell_height
    background_d = d_rect(0, -config.legend_height, width, height + config.legend_height)

    return f'    <path class="background" d="{background_d}"/>'


def generate_cells():
    path_string = ""
    scale_A = config.font_size / config.font_A.info.layout.unitsperem
    scale_B = config.font_size / config.font_B.info.layout.unitsperem

    def hoba(glyph, scale):
        bbox = glyph.bbox
        skia_path = glyph2skia_path(glyph)
        off = (config.cell_width - (bbox.xmax - bbox.xmin) * scale) / 2
        transform = (scale, 0, 0, -scale, x + off, y_bs, 0, 0, 1)
        return skia_path.transform(*transform)

    for char, (row, col) in zip(config.chars, product(range(config.rows), range(config.cols))):
        x = col * config.cell_width
        y = row * config.cell_height
        y_bs = y + config.base_line
        skia_A_path = hoba(config.font_A.glyph(char), scale_A)
        skia_B_path = hoba(config.font_B.glyph(char), scale_B)
        intersection = get_intersection(skia_A_path, skia_B_path)
        d_background = d_rect(x, y, config.cell_width, config.cell_height)
        path_string += f'''
    <g> 
        <path class="cell-background" d="{d_background}"/>
        <path class="a" d="{skia2d_path(skia_A_path)}"/>
        <path class="b" d="{skia2d_path(skia_B_path)}"/>
        <path class="overlap" d="{skia2d_path(intersection)}"/>
        <path class="baseline" d="M {x}, {y_bs} L {x+config.cell_width}, {y_bs}"/>
    </g>'''

    return path_string


def generate_legend():
    if config.legend_height <= 0:
        return ""

    font_A_name = config.font_A.info.names.name
    font_B_name = config.font_B.info.names.name
    x_off = 4
    font_size = config.legend_height - x_off
    gap = config.legend_height

    return (f'''    <g>
        <path class="legend-background" d="'''
        f'''{d_rect(0, 0, config.cols*config.cell_width, -config.legend_height)}"/>
        <text x="{x_off}" y="{-config.legend_height*0.5}" '''
        '''dominant-baseline="central" '''
        f'''style="font-family: sans-serif; font-size: {font_size}px">
             <tspan class="a">{font_A_name}</tspan>
             <tspan class="b" dx="{gap}">{font_B_name}</tspan>
        </text>
    </g>'''
    )


def create_atlas(config):
    globals()["config"] = config

    for font in ["font_A", "font_B"]:
        try:
            setattr(config, font, ziafont.Font(str(config.get(font))))
        except (OSError, struct.error) as e:
            print(f"Could not load font '{config.get(font)}': {e}", file=sys.stderr)
            exit(1)

    svg_string = "\n".join([
        generate_header(),
        generate_css(),
        generate_background(),
        generate_legend(),
        generate_cells(),
        "</svg>"
    ])

    return Dummy(svg_string)


def glyph2skia_path(glyph: ziafont.glyph.SimpleGlyph):
    path = Path()
    pts = lambda point: (point.x, point.y)
    for op in glyph.operators:
        match op:
            case ziafont.svgpath.Moveto():
                path.add(PathVerb.MOVE, pts(op.p))
            case ziafont.svgpath.Lineto():
                path.add(PathVerb.LINE, pts(op.p))
            case ziafont.svgpath.Quad():
                path.add(PathVerb.QUAD, pts(op.p1), pts(op.p2))
            case ziafont.svgpath.Cubic():
                path.add(PathVerb.CUBIC, pts(op.p1), pts(op.p2), pts(op.p3))
            case _:
                print(f"Unknown operator '{op}'", file=sys.stderr)

    return path


def get_intersection(path1, path2):
    result = Path()
    skia_intersection([path1], [path2], result.getPen())

    return result


def skia2d_path(skia_path):
    d_string = skia_path._to_string()

    if d_string.startswith("path.fillType"):
        d_string = " ".join(d_string.splitlines()[1:])
    else:
        d_string = " ".join(d_string.splitlines())

    d_string = (
        d_string.replace("path.moveTo(", "M ")
                .replace("path.lineTo(", "L ")
                .replace("path.cubicTo(", "C ")
                .replace("path.quadTo(", "Q ")
                .replace("path.close(", "Z ")
                .replace(")", "")
     )

    return d_string


class Dummy:

    def __init__(self, svg_string):
        self.svg_string = svg_string

    def show(self):
        svg_temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".svg").name
        self.save(svg_temp_file)
        webbrowser.get().open(svg_temp_file, new=2)

    def save(self, filename, *args, **kwargs):

        if isinstance(filename, TextIOWrapper):
            filename.write(self.svg_string)
        else:
            with open(filename, "w") as f:
                f.write(self.svg_string)