import sys, tempfile, webbrowser
from itertools import product
import ziafont
from pathops import Path, PathVerb
from pathops.operations import intersection as skia_intersection


config = None


def generate_grid():
    width = config.cols * config.cell_width
    height = config.rows * config.cell_height
    grid_string = '    <path d="'
    for col in range(config.cols + 1):
        grid_string += (f'M {col * config.cell_width}, 0 '
                        f'L {col * config.cell_width}, {height} ')
    for row in range(config.rows + 1):
        grid_string += (f'M 0, {row * config.cell_height} '
                        f'L {width}, {row * config.cell_height} ')
    grid_string += f'" stroke="{config.grid_color}"/>'

    return grid_string


def generate_header():
    return (
        f'<svg version="1.1" xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 {-config.legend_height} '
        f'{config.cols * config.cell_width} '
        f'{config.rows * config.cell_height + config.legend_height}">'
    )


def generate_background():
    width = config.cols * config.cell_width
    height = config.rows * config.cell_height

    return (
        f'    <path d="M 0, {-config.legend_height} '
        f'L {width}, {-config.legend_height} L {width}, {height} '
        f'L {0}, {height} L {0}, {-config.legend_height} Z" '
        f'stroke="none" fill="{config.cell_background_color}"/>'
    )


def generate_txt():
    path_string = ""
    scale_A = config.font_size / config.font_A.info.layout.unitsperem
    scale_B = config.font_size / config.font_B.info.layout.unitsperem

    def hoba(glyph, scale):
        bbox = glyph.bbox
        skia_path = glyph2skia_path(glyph)
        off = (config.cell_width - (bbox.xmax - bbox.xmin) * scale) / 2
        transform = (scale, 0, 0, -scale, x + off, y, 0, 0, 1)
        return skia_path.transform(*transform)

    for char, (row, col) in zip(config.chars, product(range(config.rows), range(config.cols))):
        x = col * config.cell_width
        y = row * config.cell_height + config.base_line
        skia_A_path = hoba(config.font_A.glyph(char), scale_A)
        skia_B_path = hoba(config.font_B.glyph(char), scale_B)
        intersection = get_intersection(skia_A_path, skia_B_path)
        path_string += f'''
    <path d="{skia2d_path(skia_A_path)}" fill="{config.a_color}"/>
    <path d="{skia2d_path(skia_B_path)}" fill="{config.b_color}"/>
    <path d="{skia2d_path(intersection)}" fill="{config.overlap_color}"/>
    <path d="M {x}, {y} L {x+config.cell_width}, {y}" stroke="{config.baseline_color}"/>'''

    return path_string


def generate_legend():
    font_A_name = config.font_A.info.names.name
    font_B_name = config.font_B.info.names.name

    return (
        f'''    <text x="0" y="{-config.legend_height}" dominant-baseline="hanging" '''
        f'''style="font-family: sans-serif; font-size:{config.legend_height}">
         <tspan fill="{config.a_color}">{font_A_name}</tspan>
         <tspan dx="{config.legend_height}" fill="{config.b_color}">{font_B_name}</tspan>
    </text>'''
    )


def create_atlas(config):
    globals()["config"] = config

    config.legend_height = 10

    for font in ["font_A", "font_B"]:
        try:
            setattr(config, font, ziafont.Font(str(config.get(font))))
        except OSError as e:
            print(f"Could not load '{config.get(font)}': {e}", file=sys.stderr)
            exit(1)

    svg_string = "\n".join([
        generate_header(),
        generate_background(),
        generate_txt(),
        generate_grid(),
        generate_legend(),
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

    def save(self, filename, *args):
        with open(filename, "w") as f:
            f.write(self.svg_string)