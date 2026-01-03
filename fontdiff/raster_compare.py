import sys
from itertools import product
from functools import cache
from PIL import Image, ImageDraw, ImageFont, ImageColor
try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

config = None


def merge_glyphs(a_glyph, b_glyph, a_baseline, b_baseline):
    ax, ay = a_glyph.size
    bx, by = b_glyph.size

    space_above = max(a_baseline, b_baseline)
    space_below = max(ay - a_baseline, by - b_baseline)
    output_width = max(ax, bx)
    output_height = space_above + space_below

    offset_ax = (output_width - ax) // 2
    offset_bx = (output_width - bx) // 2
    offset_ay = space_above - a_baseline
    offset_by = space_above - b_baseline

    if _HAS_NUMPY:
        return _merge_with_numpy(a_glyph, b_glyph,
                                 output_width, output_height,
                                 offset_ax, offset_ay,
                                 offset_bx, offset_by), space_above

    return _merge_with_pillow(a_glyph, b_glyph,
                              output_width, output_height,
                              offset_ax, offset_ay,
                              offset_bx, offset_by), space_above

@cache
def __stmul(tup, s):
    """
    scale color 3-tuple or 4-tuple :tup: with skalar :s:
    """

    return tuple(s * val // 255 for val in tup)


def _merge_with_pillow(a_glyph, b_glyph,
                       output_width, output_height,
                       offset_ax, offset_ay,
                       offset_bx, offset_by):

    ax, ay = a_glyph.size
    bx, by = b_glyph.size

    output = Image.new("RGBA", (output_width, output_height), (0, 0, 0, 0))

    for y in range(output_height):
        for x in range(output_width):
            ax_x = x - offset_ax
            ay_y = y - offset_ay
            bx_x = x - offset_bx
            by_y = y - offset_by

            a_val = a_glyph.getpixel((ax_x, ay_y)) if 0 <= ax_x < ax and 0 <= ay_y < ay else 0
            b_val = b_glyph.getpixel((bx_x, by_y)) if 0 <= bx_x < bx and 0 <= by_y < by else 0

            if a_val > 0 and b_val == 0:
                output.putpixel((x, y), __stmul(config.a_color, a_val))
            elif b_val > 0 and a_val == 0:
                output.putpixel((x, y), __stmul(config.b_color, b_val))
            elif a_val > 0 and b_val > 0:
                max_val = max(a_val, b_val)
                output.putpixel((x, y), __stmul(config.overlap_color, max_val))
            # else transparent background? but who cares.

    return output


def _merge_with_numpy(a_glyph, b_glyph,
                      output_width, output_height,
                      offset_ax, offset_ay,
                      offset_bx, offset_by):
    ax, ay = a_glyph.size
    bx, by = b_glyph.size

    a_color = np.array(config.a_color)
    b_color = np.array(config.b_color)
    overlap_color = np.array(config.overlap_color)

    # convert images to numpy arrays (grayscale)
    a_arr = np.zeros((output_height, output_width), dtype=np.uint8)
    b_arr = np.zeros((output_height, output_width), dtype=np.uint8)

    a_arr[offset_ay:offset_ay + ay, offset_ax:offset_ax + ax] = np.array(a_glyph)
    b_arr[offset_by:offset_by + by, offset_bx:offset_bx + bx] = np.array(b_glyph)

    out_arr = np.zeros((output_height, output_width, 4), dtype=np.uint8)

    mask_a  = a_arr > 0
    mask_b  = b_arr > 0
    only_a  = mask_a & ~mask_b
    only_b  = mask_b & ~mask_a
    overlap = mask_a & mask_b

    max_alpha = np.maximum(a_arr, b_arr)
    out_arr[only_a] = (a_color * a_arr[only_a, None]) // 255
    out_arr[only_b] = (b_color * b_arr[only_b, None]) // 255
    out_arr[overlap] = (overlap_color * max_alpha[overlap, None]) // 255

    return Image.fromarray(out_arr, "RGBA")


def render_glyph(char, font):
    ascent, _ = font.getmetrics()
    left, top, right, bottom = font.getbbox(char)
    # TODO well 'left' can be negative O_o, maybe some 'kerning' shit
    #  (but for a single char?). maybe I have to investigate later
    #  how it affects the output when this is taken into account.
    height, width = bottom - top, right - left
    glyph = Image.new("L", (width, height), color="black")
    glyph_draw = ImageDraw.Draw(glyph)
    glyph_draw.text((0, -top), char, font=font, fill="white")
    baseline = -top + ascent

    return glyph, baseline


def create_cell(char, cell_dim):
    cell_width, cell_height = cell_dim
    base_line = config.base_line

    cell = Image.new(
        "RGBA", (cell_width, cell_height), color=config.cell_background_color
    )

    a_glyph, a_baseline = render_glyph(char, config.font_A)
    b_glyph, b_baseline = render_glyph(char, config.font_B)

    combi, base = merge_glyphs(a_glyph, b_glyph, a_baseline, b_baseline)
    c_paste_x = (cell_width - combi.width) // 2
    c_paste_y = base_line - base
    cell.paste(combi, (c_paste_x, c_paste_y))

    return cell


def put_txt(img, txt, cell_dim):

    cell_width, cell_height = cell_dim
    base_line = config.base_line

    layer = Image.new("RGBA", img.size, color=(0, 0, 0, 0))
    layer_draw = ImageDraw.Draw(layer)

    for char, (row, col) in zip(txt, product(range(config.rows), range(config.cols))):
        x = col * cell_width
        y = row * cell_height

        cell = create_cell(char, cell_dim)
        img.paste(cell, (x, y), mask=cell)

        layer_draw.line(
            (x, y + base_line, x + cell.width, y + base_line),
            width=1,
            fill=config.baseline_color,
        )

    img = Image.alpha_composite(
        Image.new(mode="RGBA", size=img.size, color=config.cell_background_color),
        img
    )
    return Image.alpha_composite(img, layer)


def put_grid(img, cell_dim, grid_color="black", thickness=1):
    cell_width, cell_height = cell_dim

    width, height = img.size
    layer = Image.new("RGBA", (width, height))
    draw = ImageDraw.Draw(layer)
    for y in range(0, height, cell_height):
        for x in range(0, width, cell_width):
            draw.line((0, y, width, y), fill=grid_color, width=thickness)
            draw.line((x, 0, x, height), fill=grid_color, width=thickness)
    draw.rectangle((0, 0, width - 1, height - 1), outline=grid_color)

    img = Image.alpha_composite(img, layer)

    return img


def add_legend(img):
    if config.legend_height <= 0:
        return img

    font_A_name = " ".join(config.font_A.getname())
    font_B_name = " ".join(config.font_B.getname())

    x_off = 4
    y_off = config.legend_height / 2
    smally = ImageFont.load_default(size=config.legend_height-x_off)
    left, _, right, _ = smally.getbbox(font_A_name)
    gap = config.legend_height
    x_pos_B = (right - left) + gap + x_off

    img_width, img_height = img.size
    img_with_legend = Image.new(
        "RGBA",
        (img_width, img_height + config.legend_height),
        color=config.cell_background_color,
    )
    img_with_legend.paste(img.convert("RGBA"), (0, config.legend_height))
    legend_draw = ImageDraw.Draw(img_with_legend)
    legend_draw.text((x_off, y_off), font_A_name, font=smally, fill=config.a_color, anchor="lm")
    legend_draw.text((x_pos_B, y_off), font_B_name, font=smally, fill=config.b_color, anchor="lm")

    return img_with_legend


def create_atlas(config):
    globals()["config"] = config

    ##########################################################################
    #
    # convert all colors
    #
    for k, v in config.items():
        if k.endswith("color"):
            config.__dict__[k] = ImageColor.getcolor(v, "RGBA")

    ##########################################################################
    #
    # load fonts
    #
    for font in ["font_A", "font_B"]:
        try:
            setattr(
                config,
                font,
                ImageFont.truetype(str(config.get(font)), config.font_size)
            )
        except OSError as e:
            print(f"Could not load font '{config.get(font)}': {e}", file=sys.stderr)
            exit(1)

    img = Image.new(
        "RGBA",
        (config.cell_width * config.cols, config.cell_height * config.rows),
        color=config.cell_background_color,
    )

    cell_dims = (config.cell_width, config.cell_height)
    img = put_txt(img, txt=config.chars, cell_dim=cell_dims)
    img = put_grid(img, cell_dim=cell_dims, grid_color=config.grid_color)
    img = add_legend(img)

    return img