#!/usr/bin/env python3
import os, sys, tomllib, tempfile, argparse
from pathlib import Path

# I believe this is unfortunately necessary to be runnable as a script as well
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fontdiff.config import Config
from fontdiff import __version__, __program_name__


def create_parser(config):
    """
    Create an argument parser for the command line interface.
    """
    parser = argparse.ArgumentParser(
        description="Compares fonts",
        prefix_chars="-+",
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'{__program_name__} {__version__}'
    )
    parser.add_argument(
        "-s", "--svg",
        dest="svg_output",
        action="store_true",
        help="enable SVG output",
    )
    parser.add_argument(
        "--cell-size",
        type=int,
        default=argparse.SUPPRESS,
        help="Cell size as integer (optional)",
    )
    parser.add_argument(
        "--chars",
        type=str,
        nargs="?",
        help="Characters as string (optional)"
    )
    parser.add_argument(
        "font_A",
        type=Path,
        help="First font file/path (required)"
    )
    parser.add_argument(
        "font_B",
        type=Path,
        help="Second font file/path (required)"
    )

    if "charsets" in config:
        charsets = parser.add_argument_group("Character sets")
        for key, value in config.charsets.items():
            charsets.add_argument(
                f"+{key.lower()}",
                action="append_const",
                const=value,
                dest="additional_chars",
                help=value.replace("%", "%%"),
                default=argparse.SUPPRESS,
            )

    return parser


def read_defaults() -> Config:
    """
    Read build-in defaults.
    """
    import fontdiff.defaults, fontdiff.alphabets

    config = Config(fontdiff.defaults)
    config.charsets = Config(fontdiff.alphabets)

    return config


def read_config():
    """
    Load user configuration from a TOML file located either in the XDG
    config directory or, if that is not set, in `~/.<prog_name>/config`.
    """
    xdg_config_home = os.getenv("XDG_CONFIG_HOME")
    if xdg_config_home:
        config_path = Path(xdg_config_home) / __program_name__ / "config"
    else:
        config_path = Path.home() / f".{__program_name__}" / "config"

    if config_path.exists():
        with config_path.open("rb") as config_file:
            try:
                return Config(tomllib.load(config_file))
            except tomllib.TOMLDecodeError as e:
                print(f"Bad config file {config_path}:\n{e}", file=sys.stderr)

    return Config()


def prepare_additional_charsets(config, args, toml, default):
    """add extra symbols from character sets to config"""

    additional_chars = (
        "".join(args.additional_chars) if "additional_chars" in args else ""
    )
    if args.chars:
        config.chars = args.chars + additional_chars
    elif "chars" in toml:
        config.chars = toml.chars + additional_chars
    elif additional_chars:
        config.chars = additional_chars
    else:
        config.chars = default.chars

    return config


def calculate_cell_and_font_sizes(config, args, toml, default):
    """
    all necessary calculation for cell, font, baseline sizes or
    recalculation of them if something was only partly provided
    """

    if "cell_size" in args:
        config.font_size = round(args.cell_size * config._font_size_factor)
        config.base_line = round(args.cell_size * config._base_line_factor)
    else:
        ref_value = toml.get(
            "cell_height", toml.get("cell_size", config.cell_size)
        )
        config.font_size = toml.get(
            "font_size",
            round(ref_value * config._font_size_factor)
        )
        config.base_line = toml.get(
            "base_line",
            round(ref_value * config._base_line_factor)
        )

    config.cell_width = config.get("cell_width", config.cell_size)
    config.cell_height = config.get("cell_height", config.cell_size)

    return config


def calculate_proper_grid_size(config: Config):
    """all necessary calculation for grid size: columns and rows amount"""

    import math

    len_chars = len(config.chars)
    has_vertical = config.get("rows", 0) > 0
    has_horizontal = config.get("cols", 0) > 0
    if has_vertical and has_horizontal:
        pass
    elif has_vertical and not has_horizontal:
        config.cols = math.ceil(len_chars / config.rows)
    elif not has_vertical and has_horizontal:
        config.rows = math.ceil(len_chars / config.cols)
    elif not has_vertical and not has_horizontal:
        root = math.ceil(len_chars ** 0.5)
        lower_bound = math.floor(
            config._cols_rows_ratio ** -0.5 * root) or 1
        _reminder, side = min(
            map(lambda probe: (len_chars % probe, probe),
                range(lower_bound, root + 1)),
            key=lambda some: some[0],
        )
        config.rows = side
        config.cols = math.ceil(len_chars / side)


def prepare_temp_directory(config: Config):
    """handle temp directory creation"""

    tmp_base = Path(
        config.get("temp_dir", Path(tempfile.gettempdir()) / __program_name__)
    )
    config.temp_dir = str(tmp_base)
    tmp_base.mkdir(parents=True, exist_ok=True)
    os.environ["TMPDIR"] = config.temp_dir
    tempfile.tempdir = config.temp_dir

    return config


def init_config():
    """
    Resolve the final configuration used by the program.

    The function merges defaults, a TOML file and command‑line arguments,
    calculates derived values (font size, baseline, grid dimensions),
    validates font files, creates a temporary directory. It returns the fully
    populated configuration.
    """

    # toml config overrides defaults, args overrides toml config file
    default = read_defaults()
    current_config = Config(default)  # get a copy!
    toml = read_config()
    current_config.update(toml)
    parser = create_parser(current_config)  # parser already depends on config!
    args = parser.parse_args()
    current_config.update(args.__dict__)

    prepare_additional_charsets(current_config, args, toml, default)
    calculate_cell_and_font_sizes(current_config, args, toml, default)
    calculate_proper_grid_size(current_config)

    ##########################################################################
    #
    # check if font files exist and you have access to them
    #
    def file_exists_and_readable(path: Path) -> bool:
        if path.is_file():
            return os.access(path, os.R_OK)
        return False

    if not file_exists_and_readable(current_config.font_A):
        print(f"Can not access '{current_config.font_A}'", file=sys.stderr)
        exit(1)
    elif not file_exists_and_readable(current_config.font_B):
        print(f"Can not access '{current_config.font_B}'", file=sys.stderr)
        exit(1)

    ##########################################################################
    #
    # check for valid legend height
    #
    if current_config.legend_height < current_config._too_small_legend_size:
        current_config.legend_height = 0

    prepare_temp_directory(current_config)

    return current_config

def main():
    current_config = init_config()

    if current_config.svg_output:
        from fontdiff.svg_compare import create_atlas
        format = ""
    else:
        from fontdiff.raster_compare import create_atlas
        format = "png"

    font_atlas = create_atlas(current_config)

    if sys.stdout.isatty():
        font_atlas.show()
    else:
        font_atlas.save(sys.stdout, format=format)


if __name__ == "__main__":
    main()
