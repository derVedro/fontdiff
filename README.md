# <img src="./fontdiff.svg" width="400" height="100"/>

## Overview
fontdiff is a tool to visually compare differences between two fonts by
displaying character atlases overlaid. You run it and it just shows you the
differences. It spits out PNGs or dynamic SVGs, and you can customise the
output a bit.

## Install
You can quickly install fontdiff into your home directory straight from github:
```
pip install --user git+https://github.com/derVedro/fontdiff.git
```

Alternatively, you can clone the repo and simply run fontdiff.py as a script,
or even place a symlink of fontdiff.py to your preferred bin directory. However,
you may need to install all dependencies using pip first if you haven't done so
already.
```
git clone https://github.com/derVedro/fontdiff.git
cd fontdiff/fontdiff
chmod +x fontdiff.py
ln -s $PWD/fontdiff.py ~/bin/fontdiff
```

## Usage Examples
```
# regular usage
fontdiff fontA.ttf fontB.ttf

# you can use some predefined char sets
fontdiff fontA.ttf fontB.ttf +greek +numerals

# or even try more options
fontdiff --cell-size 30 --chars "abcde1234!@#$" fontA.ttf fontB.ttf

# save result as file
fontdiff fontA.ttf fontB.ttf > diff.png

# SVG output
fontdiff -s fontA.ttf fontB.ttf

# consider to check all the possible options
fontdiff --help
```

## Dependencies
- python ≥3.11
- pillow ≥10.1.0
- skia-pathops ≥0.8.0.post1
- ziafont ≥0.11
- numpy (optional)

## Miscellaneous
You can configure fontdiff by putting a toml `config` file into
`$XDG_CONFIG_HOME/fontdiff/` or `$HOME/.fontdiff/` directory. An [example](config)
configuration file is provided in this repository. It's worth taking a look into
if you need additional functionality like extra character sets, setting sizes
or colors.
