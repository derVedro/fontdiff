#!/usr/bin/env python3
import os, sys, tomllib, tempfile, argparse
from pathlib import Path
from dot_dict import DotDict
from raster_compare import create_atlas

PROG_NAME = "fontdiff"


def create_parser(config):
    """
    Create an argument parser for the command line interface.
    """
    parser = argparse.ArgumentParser(
        description="Compares fonts",
        prefix_chars="-+",
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

    if hasattr(config, "charsets"):
        charsets = parser.add_argument_group("Character sets")
        for key, value in config.charsets.items():
            charsets.add_argument(
                f"+{key.lower()}",
                action="append_const",
                const=value,
                dest="additional_chars",
                help=f"{value.replace("%", "%%")}",
                default=argparse.SUPPRESS,
            )

    return parser


def read_defaults() -> DotDict:
    """
    Read build-in defaults.
    """
    import defaults, alphabets

    config = DotDict.from_module(defaults)
    config["charsets"] = DotDict.from_module(alphabets)

    return config


def read_config():
    """
    Load user configuration from a TOML file located either in the XDG
    config directory or, if that is not set, in `~/.<prog_name>/config`.
    """
    xdg_config_home = os.getenv("XDG_CONFIG_HOME")
    if xdg_config_home:
        config_path = Path(xdg_config_home) / PROG_NAME / "config"
    else:
        config_path = Path.home() / f".{PROG_NAME}" / "config"

    if config_path.exists():
        with config_path.open("rb") as config_file:
            try:
                return DotDict(tomllib.load(config_file))
            except tomllib.TOMLDecodeError as e:
                print(f"Bad config file {config_path}:\n{e}", file=sys.stderr)

    return DotDict()


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
    current_config = DotDict(default)  # get a copy!
    toml = read_config()
    current_config.update(toml)
    parser = create_parser(current_config)  # parser already depends on config!
    args = parser.parse_args()
    current_config.update(args.__dict__)

    ##########################################################################
    #
    # characters and extra characters part
    #
    additional_chars = (
        "".join(args.additional_chars) if hasattr(args, "additional_chars") else ""
    )
    if args.chars:
        current_config["chars"] = args.chars + additional_chars
    elif hasattr(toml, "chars") and toml.chars:
        current_config["chars"] = toml.chars + additional_chars
    elif additional_chars:
        current_config["chars"] = additional_chars
    else:
        current_config["chars"] = default.chars

    ##########################################################################
    #
    # cell, font, baseline sizes calculation part
    #
    if current_config.cell_size != default.cell_size:

        if hasattr(args, "cell_size") and args.cell_size != default.cell_size:
            current_config["font_size"] = round(
                args.cell_size * current_config._font_size_factor
            )
            current_config["base_line"] = round(
                args.cell_size * current_config._base_line_factor
            )
        else:
            current_config["font_size"] = toml.get(
                "font_size",
                round(current_config.cell_size * current_config._font_size_factor),
            )
            current_config["base_line"] = toml.get(
                "base_line",
                round(current_config.cell_size * current_config._base_line_factor),
            )

    current_config["cell_width"] = current_config.get(
        "cell_width", current_config.cell_size
    )
    current_config["cell_height"] = current_config.get(
        "cell_height", current_config.cell_size
    )

    ##########################################################################
    #
    # all necessary calculation for grid size: colums and rows amount
    #
    import math

    len_chars = len(current_config.chars)
    has_vertical = hasattr(current_config, "rows") and current_config.rows
    has_horizontal = hasattr(current_config, "cols") and current_config.cols
    if has_vertical and has_horizontal:
        pass
    elif has_vertical and not has_horizontal:
        current_config["cols"] = math.ceil(len_chars / current_config.rows)
    elif not has_vertical and has_horizontal:
        current_config["rows"] = math.ceil(len_chars / current_config.cols)
    elif not has_vertical and not has_horizontal:
        root = math.ceil(len_chars**0.5)
        lower_bound = math.floor(current_config._cols_rows_ratio**-0.5 * root) or 1
        _reminder, side = min(
            map(lambda probe: (len_chars % probe, probe), range(lower_bound, root + 1)),
            key=lambda some: some[0],
        )
        current_config["rows"] = side
        current_config["cols"] = math.ceil(len_chars / side)

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
    # temp directory part
    #
    tmp_base = Path(
        current_config.get("temp_dir", Path(tempfile.gettempdir()) / PROG_NAME)
    )
    current_config["temp_dir"] = str(tmp_base)
    tmp_base.mkdir(parents=True, exist_ok=True)
    os.environ["TMPDIR"] = current_config.temp_dir
    tempfile.tempdir = current_config.temp_dir

    return current_config


def main():
    current_config = init_config()
    font_atlas = create_atlas(current_config)

    if sys.stdout.isatty():
        font_atlas.show()
    else:
        font_atlas.save(sys.stdout, format="png")


if __name__ == "__main__":
    main()