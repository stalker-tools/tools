# Stalker xray tools

This python cross-platform command-line tools used for analysis and editing of gamedata `.ltx` files. Developed and tested on Linux/Wine.

## .ltx files analysis tool

Command-line tools is 100% python, so it has wide usage as cross-platform.
* `ltx_tool.py` for **text**-based view/edit and has .ltx-specific filters capabilities;
* `graph_tool.py` for **graph**-based view and has .ltx-specific filters capabilities. Out format: matplotlib graphs embedded in html as images.
* `tree_tool.py` for **graph**-based view and has .ltx-specific import tree representation capabilities. Out format: [graphviz dot](https://www.graphviz.org/) and dot embedded in html as image. See available dot [layouts](https://www.graphviz.org/docs/layouts/).

## Tools usage examples

### Analysis examples for stalker games:
* [Clear Sky Analysis](analysis_cs.md) and [Run Clear Sky](run_cs.md)

### Tools help

* **ltx_tool.py** help:
```sh
python ltx_tool.py -h
usage: ltx_tool.py [-h] -f FILE_PATH [FILE_PATH ...] [-p [SECTION NAMES ...]] [-s [SECTION NAMES ...]] [-l [LET RLVALUES ...]] [-r] [-m VALUE]

X-ray .ltx file parser

options:
  -h, --help            show this help message and exit
  -f FILE_PATH [FILE_PATH ...], --ltx FILE_PATH [FILE_PATH ...]
                        one or more paths of directories and/or .ltx files
  -p [SECTION NAMES ...]
                        show all descendants of this parents; regexp, escaped symbols: ^$()[]?!
  -s [SECTION NAMES ...]
                        section name filter; regexp, escaped symbols: ^$()[]?!
  -l [LET RLVALUES ...]
                        left value filter for assign; regexp, escaped symbols: ^$()[]?!
  -r                    show info reversed
  -m VALUE              modify (set) value

Examples: ltx_tool.py -f 1.ltx 2.ltx
```

Output format (line for each found value):
1. .ltx file path (gamedata relative)
1. [.ltx section name]
1. lvalue = rvalue

Output format can be reversed for sorting with `-r` option.

Example of `hit_fraction` for Clear Sky:
```sh
python3 ltx_tool.py -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" -l hit_fraction
configs/creatures/damages.ltx [stalker_hero_1] hit_fraction = 0.1
configs/creatures/damages.ltx [stalker_lesnik_1] hit_fraction = 0.1
configs/creatures/damages.ltx [stalker_bandit_1] hit_fraction = 0.5
configs/creatures/damages.ltx [stalker_bandit_2] hit_fraction = 0.3
configs/creatures/damages.ltx [stalker_bandit_3] hit_fraction = 0.2
configs/creatures/damages.ltx [stalker_bandit_4] hit_fraction = 0.2
configs/creatures/damages.ltx [stalker_dolg_1] hit_fraction = 0.3
configs/creatures/damages.ltx [stalker_dolg_2] hit_fraction = 0.3
configs/creatures/damages.ltx [stalker_dolg_3] hit_fraction = 0.2
configs/creatures/damages.ltx [stalker_dolg_4] hit_fraction = 0.1
configs/creatures/damages.ltx [stalker_freedom_1] hit_fraction = 0.3
configs/creatures/damages.ltx [stalker_freedom_2] hit_fraction = 0.3
configs/creatures/damages.ltx [stalker_freedom_3] hit_fraction = 0.2
configs/creatures/damages.ltx [stalker_freedom_4] hit_fraction = 0.1
configs/creatures/damages.ltx [stalker_merc_1] hit_fraction = 0.3
configs/creatures/damages.ltx [stalker_merc_2] hit_fraction = 0.3
configs/creatures/damages.ltx [stalker_merc_3] hit_fraction = 0.3
configs/creatures/damages.ltx [stalker_merc_4] hit_fraction = 0.1
configs/creatures/damages.ltx [stalker_monolith_1] hit_fraction = 0.3
configs/creatures/damages.ltx [stalker_monolith_2] hit_fraction = 0.3
configs/creatures/damages.ltx [stalker_monolith_3] hit_fraction = 0.2
configs/creatures/damages.ltx [stalker_monolith_4] hit_fraction = 0.1
configs/creatures/damages.ltx [stalker_nebo_1] hit_fraction = 0.3
configs/creatures/damages.ltx [stalker_nebo_2] hit_fraction = 0.2
configs/creatures/damages.ltx [stalker_nebo_3] hit_fraction = 0.2
configs/creatures/damages.ltx [stalker_neutral_1] hit_fraction = 0.5
configs/creatures/damages.ltx [stalker_neutral_2] hit_fraction = 0.3
configs/creatures/damages.ltx [stalker_neutral_3] hit_fraction = 0.2
configs/creatures/damages.ltx [stalker_neutral_4] hit_fraction = 0.1
configs/creatures/damages.ltx [stalker_oon_1] hit_fraction = 0.1
configs/creatures/damages.ltx [stalker_oon_2] hit_fraction = 0.1
configs/creatures/damages.ltx [stalker_soldier_1] hit_fraction = 0.3
configs/creatures/damages.ltx [stalker_soldier_2] hit_fraction = 0.2
configs/creatures/damages.ltx [stalker_soldier_3] hit_fraction = 0.2
configs/creatures/damages.ltx [stalker_soldier_4] hit_fraction = 0.1
configs/creatures/damages.ltx [stalker_zombied_1] hit_fraction = 0.2
configs/creatures/damages.ltx [stalker_zombied_2] hit_fraction = 0.2
configs/creatures/damages.ltx [stalker_zombied_3] hit_fraction = 0.2
configs/creatures/damages.ltx [stalker_zombied_4] hit_fraction = 0.15
configs/mp/weapons_mp/outfit_mp.ltx [mp_scien_outfit_bones] hit_fraction = 0.21
configs/mp/weapons_mp/outfit_mp.ltx [mp_military_outfit_bones] hit_fraction = 0.11
configs/mp/weapons_mp/outfit_mp.ltx [mp_exo_outfit_bones] hit_fraction = 0.2
```

* **graph_tool.py** help:
```sh
python graph_tool.py -h
usage: graph_tool.py [-h] -f PATH [--head TEXT]

X-ray .ltx file parser. Out format: matplotlib graphs embedded in html as images

options:
  -h, --help            show this help message and exit
  -f PATH, --gamedata PATH
                        gamedata directory path
  --head TEXT           head text

Examples: graph_tool.py -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" --head "Clear Sky - NPC and weapons" > "NPC_and_weapons.htm"
```

Examples of `hit_fraction` and `k_hit` for Clear Sky:

![NPC hit_fraction](https://github.com/stalker-tools/real_weapons_mod_clear_sky/blob/main/media/npc_hit_fraction.png)
![Ammo k_hit](https://github.com/stalker-tools/real_weapons_mod_clear_sky/blob/main/media/ammo_k_hit.png)

* **tree_tool.py** help:
```sh
python tree_tool.py -h
usage: tree_tool.py [-h] -f PATH [-e ENGINE] [-s STYLE] [--head TEXT]

X-ray .ltx file parser. Out format: dot (default) and rendered dot embedded in html as image.
Use different layout engines: https://www.graphviz.org/docs/layouts/

options:
  -h, --help            show this help message and exit
  -f PATH, --gamedata PATH
                        gamedata directory path
  -e ENGINE, --engine ENGINE
                        dot layout engine: circo, dot, neato (default)
  -s STYLE, --style STYLE
                        style: l - light, d - dark (default)
  --head TEXT           head text for html output

Examples:
tree_tool.py -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" --head "Clear Sky .ltx files tree" > "ltx_tree_cs.htm"
tree_tool.py -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" -ecirco --head "Clear Sky .ltx files tree" > "ltx_tree_cs.htm"
tree_tool.py -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" > "ltx_tree_cs.dot"
tree_tool.py -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" -sl > "ltx_tree_cs.dot"
```
 
Example of .ltx files tree for Clear Sky:
* Dot file [ltx_tree.dot](https://github.com/stalker-tools/real_weapons_mod_clear_sky/blob/main/media/ltx_tree.dot)
* Image (neato layout engine) ![Image](https://github.com/stalker-tools/real_weapons_mod_clear_sky/blob/main/media/ltx_tree_neato.png)

UI for interactive dot file view: `xdot -fneato ltx_tree.dot`
