# Stalker Xray tools

The software consists of two parts:
- Analysis tools for Xray game engine.
- Hybrid game engine: Xray (.exe with Lua scripts) + Odyssey (Python with web interface).

## Table of contents:

### [Brief introduction](#extract-tool)
- #### [Extract tool](#extract-tool)
- #### [Gamedata analysis tools](#gamedata-analysis-tools)
- #### [Hybrid game engine](#hybrid-game-engine)
### [Installation](#installation)
- #### [Windows instructions](#windows-instructions)
- #### [Linux instructions](#linux-instructions)
### [Usage](#usage)
- #### [.db files extract](#db-files-extract)
- #### [Extract command-line interface](#extract-command-line-interface)
- #### [Extract command-line examples](#extract-command-line-examples)
- #### [.ltx files analysis tool](#ltx-files-analysis-tool)

# Brief introduction

## Extract tool

Cross-platform command-line _.db, .xdb, .xrp, .xp_ files extract tool.

This ability allows to game developers working with gamedata without nessesarity extracting of .db files.

See comman-line help: [.db files extract](#db-files-extract).

And also be free to Python-way analysis of .db files content - game files/folders structure - just import `XRReader` class from `DBReader.py`. See `DBReader.py:main()` function code for usage examples.

## Gamedata analysis tools

This python cross-platform command-line tools used for analysis of gamedata Xray config files:
- .ltx sections
- .xml localization
- .dds icons with .xml configs
- game.graph

And Xray gameplay files:
- fsgame.ltx
- .sav save

Most useful utility for mod autor/publisher is `graph_tool.py`. Just see generated `.html` brochure example: [Clear Sky + SGM 3.10 + Real Weapons.html](https://html-preview.github.io/?url=https://github.com/stalker-tools/real_weapons_mod_clear_sky/blob/main/media/Clear%20Sky%20%2B%20SGM%203.10%20%2B%20Real%20Weapons.html)

This brochure genarated by this line:
```sh
python graph_tool.py -tb -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky_real_weapons_mod/gamedata/" --head "Clear Sky + SGM 3.10 + Real Weapons" > "Clear Sky + SGM 3.10 + Real Weapons.html"
```

Developed and tested on Linux/Wine.

## Hybrid game engine

This is cross-platform combination of following game engines:
- Xray game engine: .exe and .dll files with Lua scripts and config files, it cross-platform via Wine.
- Odyssey game engine: event-driven game logic with web interface, it cross-platform via Python.

Web interface allow involve mobile devices into game process. And can be used by game modification developers to increase game immersion thru device profiles: radio and PDA.

For example, play audio on radio with talks and radio interference according to gameplay.
And also provide offline access to game thru saved PDA states on smartphone. So player can see much more gameplay information such as fiction texts, photos, videos. That helps understand main idea of screenplay and deep into details if player wants.

Finally, nowadays AI allows game designers create multimedia content and this hybrid engine provide simply way to use it.

Tested on Firefox and Chrome on Ubuntu and Android.

# Installation

Dependencies:
| Python | Graphviz |
|--------|----------|
| ![Python](https://www.python.org/static/img/python-logo.png) | ![Graphviz](https://graphviz.org/Resources/app.png) |

Python packages installation:
```sh
pip3 install -r requirements.txt
```

### Windows instructions

Download and install Python version 3.12 and abow. For example:
[Python 3.12.4](https://www.python.org/downloads/release/python-3124/)

Download and install [Graphviz 11.0.0](https://graphviz.org/download/#windows)

### Linux instructions

Installation instruction: [Graphviz](https://graphviz.org/download/#linux)

Ubuntu:
```sh
sudo apt-get update
sudo apt-get install graphviz
```

OpenSUSE:
```sh
sudo zypper refresh
sudo zypper install graphviz
```

# Usage

## .db files extract

<a name="db-files-extract"></a>

As .db file is files container what is organized into filesystem with folders tree. And there is number of .db files. One gamedata file can be located into multiple .db files. So tools for showing such multiple versions of file is wanted. For this purpose use particular `--last` option with `gamedata` sub-command.

Be free to use two different practice:
- Overall view of gamedata files from all .db files. This is usual for working with latest gamedata file version.

For example, show latest version of X-ray Lua files as table (human-readable output):
```sh
python DBReader.py -f "gamedata.db*" -t 2947ru g -l -n -g "*xr_*.script"
    1 scripts\xr_abuse.script           gamedata.dbb
    2 scripts\xr_actions_id.script      gamedata.dbb
...
```

By the way, remove `-n` option in previous example to get machine-readable output:
```sh
python DBReader.py -f "gamedata.db*" -t 2947ru g -l -g "*xr_*.script"
scripts\xr_abuse.script gamedata.dbb
scripts\xr_actions_id.script gamedata.dbb
...
```

One more example, show latest version of .dds image files table (human-readable output):
```sh
python DBReader.py -f "gamedata.db*" -t 2947ru g -l -n -g "*.dds"
    1 levels\l01_escape\build_details.dds                                gamedata.db0
...
   74 levels\l04u_labx18\lmap#1_2.dds                                    gamedata.db1
...
 5306 textures\wpn\wpn_zink_svd.dds                                      gamedata.db8
```

- Split gamedata files by .db files. Here is possible to track gamedata files versions by .db files.

For example, show all versions of X-ray Lua files by .db files (key-values list):

```ssh
python DBReader.py -f "gamedata.db*" -t 2947ru g -s -g "*xr_*.script"
        gamedata.db0
        gamedata.db1
        gamedata.db2
        gamedata.db3
        gamedata.db4
scripts\xr_abuse.script
...
        gamedata.db5
        gamedata.db6
        gamedata.db7
        gamedata.db8
        gamedata.db9
        gamedata.dba
scripts\xr_abuse.script
        gamedata.dbb
scripts\xr_abuse.script
        gamedata.dbc
scripts\xr_motivator.script
        gamedata.dbd
```
Here is three versions of `scripts\xr_abuse.script` file in .db files: `gamedata.db4`, `gamedata.dba` and latest version in `gamedata.dbb`.


## Extract command-line interface

1. `DBReader.py` help:
```sh
usage: DBReader.py [-h] -f PATH [-t TYPE] [-v] {gamedata,g,files,f,info,i,dump,d} ...

DBReader test

positional arguments:
  {gamedata,g,files,f,info,i,dump,d}
                        sub-commands:
    gamedata (g)        gamedata .db files manipulations
    files (f)           show files info
    info (i)            dump chunks info
    dump (d)            dump chunks raw data

options:
  -h, --help            show this help message and exit
  -f PATH               .db file path
  -t TYPE               .db file type; one of: 11xx, 2215, 2945, 2947ru, 2947ww, xdb
  -v                    verbose mode

Examples:

1. Overal gamedata files

1.1 Gamedata overall in all .db files

        Show all files in all .db game files:
DBReader.py -f "gamedata.db*" -t 2947ru g

        Show .script files (Unix shell pattern) in selected .db game files (GLOB pattern):
DBReader.py -f "gamedata.db[04]" -t 2947ru g -g "*.script"

        Show latest version files from all .db game files:
DBReader.py -f "gamedata.db*" -t 2947ru g -l -g "*dialog*.script"

        Count files in all .db game files:
DBReader.py -f "gamedata.db*" -t 2947ru g -c

1.2 Gamedata separated by .db files

        Count files by .db game files:
DBReader.py -f "gamedata.db*" -t 2947ru g -s -c

        Count .script files by .db game files:
DBReader.py -f "gamedata.db*" -t 2947ru g -s -c -g "*.script"

2. One .db file

        Show files info (names only):
DBReader.py -f gamedata.dbd" -t 2947ru f

        Show files info as table format:
DBReader.py -f gamedata.dbd" -t 2947ru f --table

3. Examples for development purposes

        Show files info from unscrambled header chunk binary file:
DBReader.py -f "gamedata.dbd.header-unscrambled.bin" -t 2947ru f --header

        Show chunks info:
DBReader.py -f "gamedata.dbd" -t 2947ru i

        Dump raw header chunk to binary file:
DBReader.py -f "gamedata.dbd" -t 2947ru d --head > "gamedata.dbd.header.bin"

        Dump raw chunk (by index) to binary file:
DBReader.py -f "gamedata.dbd" -t 2947ru d -i 1 > "gamedata.dbd.chunk-1.bin"
```

2. `DBReader.py` **gamedata** sub-command help:
```sh
python DBReader.py g -h
usage: DBReader.py gamedata [-h] [-g PATTERN] [-s] [-n] [-c] [-l]

options:
  -h, --help            show this help message and exit
  -g PATTERN, --filter PATTERN
                        filter files by name use Unix shell-style wildcards: *, ?, [seq], [!seq]
  -s, --split           show files by .db files
  -n, --number          show number the files
  -c, --count           count files
  -l, --last            show .db file of latest version of file
```

3. `DBReader.py` **files** sub-command help:
```sh
python DBReader.py f -h
usage: DBReader.py files [-h] [--table] [--header]

options:
  -h, --help  show this help message and exit
  --table     show files as table format
  --header    treat file as header chunk binary dump file
```

4. `DBReader.py` **info** sub-command help:
```sh
python DBReader.py i -h
usage: DBReader.py info [-h]

options:
  -h, --help  show this help message and exit
```

5. `DBReader.py` **dump** sub-command help:
```sh
python DBReader.py d -h
usage: DBReader.py dump [-h] [-i NUMBER] [--header]

options:
  -h, --help  show this help message and exit
  -i NUMBER   print chunk by index: 0..
  --header    print header chunk
```

## Extract command-line examples

### **gamedata** files count overall for .db files:

1.1.1 count all **gamedata** files:
```sh
python DBReader.py -f "gamedata.db*" -t 2947ru g -c
25684
```

1.1.2 count all .script **gamedata** files:
```sh
python DBReader.py -f "gamedata.db*" -t 2947ru g -c -g "*.script"
442
```

### **gamedata** files count by .db files:

1.2.1 all **gamedata** files count:
```sh
python DBReader.py -f "gamedata.db*" -t 2947ru g -s -n -c
01 gamedata.db0  1195
02 gamedata.db1   413
03 gamedata.db2   200
04 gamedata.db3   300
05 gamedata.db4 14800
06 gamedata.db5  3459
07 gamedata.db6   170
08 gamedata.db7  2570
09 gamedata.db8  1035
10 gamedata.db9  1473
11 gamedata.dba  1526
12 gamedata.dbb  1547
13 gamedata.dbc    11
14 gamedata.dbd     6
```

1.2.2 .script **gamedata** files count:
```sh
python DBReader.py -f "gamedata.db*" -t 2947ru g -s -n -c -g "*.script"
01 gamedata.db0     2
02 gamedata.db1     0
03 gamedata.db2     0
04 gamedata.db3     0
05 gamedata.db4   440
06 gamedata.db5     0
07 gamedata.db6     0
08 gamedata.db7     0
09 gamedata.db8     0
10 gamedata.db9     0
11 gamedata.dba   441
12 gamedata.dbb   441
13 gamedata.dbc     6
14 gamedata.dbd     3
```

1.2.3 `scripts\stalker_generic.script` **gamedata** file count:
```sh
python DBReader.py -f "gamedata.db*" -t 2947ru g -s -g "scripts\stalker_generic.script"
        gamedata.db0
        gamedata.db1
        gamedata.db2
        gamedata.db3
        gamedata.db4
scripts\stalker_generic.script
        gamedata.db5
        gamedata.db6
        gamedata.db7
        gamedata.db8
        gamedata.db9
        gamedata.dba
scripts\stalker_generic.script
        gamedata.dbb
scripts\stalker_generic.script
        gamedata.dbc
        gamedata.dbd
```
Here we see three versions of file. Latest version in `gamedata.dbb` file. To get .db file with file latest version use `--last` option.

## examples for development purposes

2. **files** listing in .db file:
```sh
python DBReader.py -f "gamedata.dbd" -t 2947ru f --table
Type Offset  Compressed    CRC       Size    Name
D 0x00000000         0 0x00000000         0 config\
D 0x00000000         0 0x00000000         0 config\mp\
D 0x00000000         0 0x00000000         0 config\mp\weapons_mp\
D 0x00000000         0 0x00000000         0 config\ui\
D 0x00000000         0 0x00000000         0 scripts\
F 0x00000008    57_567 0xa5c60df5    57_567 config\mp\weapons_mp\weapons_mp.ltx
F 0x0000e0e7     7_311 0xce9244d4     7_311 config\ui\ui_mm_mp_tabclient.xml
F 0x0000fd76    10_286 0xf1855d14    10_286 config\ui\ui_mm_mp_taboptions.xml
F 0x000125a4     2_811 0x720eb5bd     2_811 scripts\ui_mm_mp_join.script
F 0x0001309f     6_567 0x6efd782e     6_567 scripts\ui_mm_mp_options.script
F 0x00014a46    16_246 0x36410070    16_246 scripts\ui_mp_main.script
```

3. chunks **info** in .db file:
```sh
python DBReader.py -f "gamedata.dbd" -t 2947ru i
0 Chunk type=DB_CHUNK_DATA(0) offset=8 size=100_788 
1 Chunk type=DB_CHUNK_HEADER(1) offset=100_804 size=210 compressed
```

4.1 chunk **dump** (raw data) from .db file to binary file:
```sh
python DBReader.py -f "gamedata.dbd" -t 2947ru d --head > "gamedata.dbd.header.bin"
```

4.2 chunk **dump** (raw data) from .db file as human-readable format (`-v` option using):
```sh
python DBReader.py -v -f "gamedata.dbd" -t 2947ru d --head > "gamedata.dbd.header.bin"
File: gamedata.dbd
Chunk type=DB_CHUNK_HEADER(1) offset=100_804 size=210 compressed
b"\xder\xc3I\xf1j\xf5\xb6\xa3Z\xeb\x87\xa3\xc3\x94\x02\xf4\x85J8\xbe\xac\x1a6/k\x9c\x11\xe6\xa5\xd2\xab\x01\xa4\x1a\x98\xc2#\x1b\xdd+i6\xcb\xdb\xd0=\xb0\xc3\xbb\xd6,\xa4\xce\xf5\xb4\xbe\x12\x0b\x9e\xeet\xfcA\\&\x82P\x12\xb3\xa1\xa6Q\x08\xb8\x0f!\x0f\xab\xd4\xaaWl\xc6\x9b,\x14/\xe7k\xb1\xe7\x86\xc5z\xb1C\xc9\x19\x11\xb4D>\xb3\x95\xc3r\xc5r5\xcfh\xb3\xffW\xbd&WH=\x1a\x9b\xb4F\xd0}R\xabg-\xc2\x88\xe3u\x8eW\x02\xe5\xc0\x99l_i\x99\x05my\x89\xd6f||zt\xb4pk\xec\x03\x0e\x8b\x88\xecf\x0e\xc5\x94\xa25\xa4+\x02Nb\xde\xbeJ\xf9\xbf\xe5NI\xa2\xf3\xd5\x0ce\x8d\xd9\x9c\xad\x1b\x1b_\x81\xd0'6\xd8\xe7.\xe5o\xcf\xbd\x03}T\xa5\xa1"
```

# .ltx files analysis tool

Command-line tools is 100% python, so it has wide usage as cross-platform.
* `ltx_tool.py` for **text**-based view/edit and has .ltx-specific filters capabilities.
  
  You can search _.ltx_ files for entire _gamedata/config_ path and see found data inline: `file.ltx [section] lvalue=rvalue`. And then set filtered _rvalue_ at once.
  
  This utility can be handle to _gamempay designers_.
* `graph_tool.py` for **graph**-based view and has .ltx-specific filters capabilities. Out format: matplotlib graphs embedded in html as images.

  You can open _.html_ file in _any browser_ and see collected info from _.ltx_ files as bar graphs for ammo/weapens and NPC to discover gameplay balance.

  This utility can be handle to _gamempay designers_.

* `profiles_tool.py` for **table**-based view of game profiles (Actor and NPC) with dialogs with localization and has profile-specific filters capabilities. Out formats: html, html with dot digraphs embedded in html as svg, csv table.

  You can open _.html_ file in _any browser_ and search text for NPC names, bio or dialog phrases, `give_info/has_info` variables and `precondition/action` script functions names.

  This utility can be handle to _game dialog designers_ and _game testers_.
* `task_tool.py` for **table**-based view of game tasks with localization. Out formats: html table, csv table.

  You can open _.cvs_ file in LibreOffice Calc or _.html_ file in _any browser_ and search text for Actor tasks and rewards.

  This utility can be handle to _gameplay designers_ and _game testers_.
* `dialog_tool.py` for **graph**-based view of game dialogs with localization and has dialog-specific filters capabilities. Out format: dot digraphs embedded in html as svg (or images - see help).

  So you can open _.html_ file in _any browser_ and search text for phrases, `give_info/has_info` variables and `precondition/action` script functions names. And you can filter by xml dialog files, phrases and variables/script names (see help).

  This utility can be handle to _game dialog designers_ and _game testers_.
  
* `tree_tool.py` for **graph**-based view and has .ltx-specific import tree representation capabilities. Out format: [graphviz dot](https://www.graphviz.org/) and dot embedded in html as image. See available dot [layouts](https://www.graphviz.org/docs/layouts/).

  This utility can be handle to _system game designers_.

### Tools usage examples

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

---
---
* **graph_tool.py** help:
```sh
python graph_tool.py -h
usage: graph_tool.py [-h] -f PATH [-l LANG] [--head TEXT] [-s STYLE] [-t TYPE]

X-ray .ltx file parser. Out format: matplotlib graphs embedded in html as images

options:
  -h, --help            show this help message and exit
  -f PATH, --gamedata PATH
                        gamedata directory path
  -l LANG, --localization LANG
                        localization language (see gamedata/configs/text path): rus (default), cz, hg, pol
  --head TEXT           head text
  -s STYLE, --style STYLE
                        style: l - light, d - dark (default)
  -t TYPE, --type TYPE  type: a - analyse (default), b - brochure

Examples: ./graph_tool.py -tb -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" --head "Clear Sky" > "ClearSky_brochure.htm"
```

Example to generate mod brochure **.html** file:
```sh
python graph_tool.py -tb -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky_real_weapons_mod/gamedata/" --head "Clear Sky + SGM 3.10 + Real Weapons" > "Clear Sky + SGM 3.10 + Real Weapons.html"
```
See brochure example: [Clear Sky + SGM 3.10 + Real Weapons.html](https://html-preview.github.io/?url=https://github.com/stalker-tools/real_weapons_mod_clear_sky/blob/main/media/Clear%20Sky%20%2B%20SGM%203.10%20%2B%20Real%20Weapons.html)

Example to generate mod analysis **.html** file:
```sh
python graph_tool.py -ta -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky_real_weapons_mod/gamedata/" --head "Clear Sky + SGM 3.10 + Real Weapons" > "Clear Sky + SGM 3.10 + Real Weapons - analysis.html"
```

---
---
* **profiles_tool.py** help:
```sh
python profiles_tool.py -h
usage: profiles_tool.py [-h] [-v] -f PATH [-l LANG] [-e ENGINE] [-s STYLE] [-o OUT_FORMAT] [--sort-field NAME] [--head TEXT]

X-ray dialog xml file parser. Dialogs xml file names reads from system.ltx file.
Out format: html with dialog phrases digraphs embedded as images.
Use different layout engines: https://www.graphviz.org/docs/layouts/

options:
  -h, --help            show this help message and exit
  -v                    increase information verbosity: show phrase id
  -f PATH, --gamedata PATH
                        gamedata directory path
  -l LANG, --localization LANG
                        localization language (see gamedata/configs/text path): rus (default), cz, hg, pol
  -e ENGINE, --engine ENGINE
                        dot layout engine: circo, dot (default), neato
  -s STYLE, --style STYLE
                        style: l - light, d - dark (default)
  -o OUT_FORMAT, --output-format OUT_FORMAT
                        output format: h - html table (default), d - html table + svg dialogs, c - csv table
  --sort-field NAME     sort field name: id (default), name, class, community, reputation, bio
  --head TEXT           head text for html output

Examples:
profiles_tool.py -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" --head "Clear Sky 1.5.10 profiles" > "profiles.html"
profiles_tool.py -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" -od -sl > "profiles with dialogs light theme.html"
profiles_tool.py -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" --sort-field name --head "Clear Sky 1.5.10 profiles" > "profiles.html"
profiles_tool.py -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" --sort-field name -oc" > "profiles.csv"
```

Example of profiles table for Clear Sky Sigerous Mod [profiles - Sigerous Mod.csv](https://github.com/stalker-tools/real_weapons_mod_clear_sky/blob/main/media/profiles%20-%20Sigerous%20Mod.csv)

---
---
* **task_tool.py** help:
```sh
python task_tool.py -h
usage: task_tool.py [-h] [-v] -f PATH [-l LANG] [-o OUT_FORMAT] [--sort-field NAME] [--head TEXT]

X-ray task_manager.ltx file parser.
Out format: table.

options:
  -h, --help            show this help message and exit
  -v                    increase information verbosity: show phrase id
  -f PATH, --gamedata PATH
                        gamedata directory path
  -l LANG, --localization LANG
                        localization language (see gamedata/configs/text path): rus (default), cz, hg, pol
  -o OUT_FORMAT, --output-format OUT_FORMAT
                        output format: h - html table (default), c - csv table
  --sort-field NAME     sort field name: name (default)
  --head TEXT           head text for html output

Examples:
task_tool.py -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" --head "Clear Sky 1.5.10 tasks" > "tasks.html"
task_tool.py -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" --sort-field name --head "Clear Sky 1.5.10 tasks" > "tasks.html"
task_tool.py -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" --sort-field name -oc" > "tasks.csv"
```

Example of profiles table for Clear Sky Sigerous Mod [tasks - Sigerous Mod.csv](https://github.com/stalker-tools/real_weapons_mod_clear_sky/blob/main/media/tasks%20-%20Sigerous%20Mod.csv)

---
---
* **dialog_tool.py** help:
```sh
python dialog_tool.py -h
usage: dialog_tool.py [-h] [-v] -f PATH [-l LANG] [-d DIALOG_FILE [DIALOG_FILE ...]] [-i IDS [IDS ...]] [-p TEXT [TEXT ...]] [-a NAMES [NAMES ...]] [-e ENGINE] [-s STYLE] [-g IMG_FORMAT] [--head TEXT]

X-ray dialog xml file parser. Dialogs xml file names reads from system.ltx file.
Out format: html with dialog phrases digraphs embedded as images.
Use different layout engines: https://www.graphviz.org/docs/layouts/

options:
  -h, --help            show this help message and exit
  -v                    increase information verbosity: show phrase id
  -f PATH, --gamedata PATH
                        gamedata directory path
  -l LANG, --localization LANG
                        localization language (see gamedata/configs/text path): rus (default), cz, hg, pol
  -d DIALOG_FILE [DIALOG_FILE ...], --dialog-files DIALOG_FILE [DIALOG_FILE ...]
                        filter: dialog file names; see system.ltx [dialogs]
  -i IDS [IDS ...], --dialog-ids IDS [IDS ...]
                        filter: dialogs ids; regexp, escaped symbols: ^$()[]?!; see configs/gameplay/dialog*.xml
  -p TEXT [TEXT ...], --phrases TEXT [TEXT ...]
                        filter: phrase text; regexp, escaped symbols: ^$()[]?!; see configs/gameplay/dialog*.xml
  -a NAMES [NAMES ...], --automation NAMES [NAMES ...]
                        filter of names: variables, script functions; regexp, escaped symbols: ^$()[]?!
  -e ENGINE, --engine ENGINE
                        dot layout engine: circo, dot (default), neato
  -s STYLE, --style STYLE
                        style: l - light, d - dark (default)
  -g IMG_FORMAT, --graph-format IMG_FORMAT
                        digraph image format: s - svg (default), p - png
  --head TEXT           head text for html output

Examples:
dialog_tool.py -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" --head "Clear Sky 1.5.10 dialogs" > "dialogs.html"
dialog_tool.py -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" -sl > "dialogs light theme.html"
dialog_tool.py -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" -i "*hello*" "*barman*" --head "Clear Sky 1.5.10 dialogs" > "dialogs id hello or barman.html"
dialog_tool.py -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" -p "*сигнал*" "*шрам*" --head "Clear Sky 1.5.10 dialogs" > "dialogs text filtered.html"
dialog_tool.py -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata" -a "*not_in_dolg" "agru_open_story_door" --head "Clear Sky 1.5.10 dialogs" > "dialogs variable and function names filtered.html"
```

Example of dialog digraphs for Clear Sky:
* Join dialog to "Duty" ![Image](https://github.com/stalker-tools/real_weapons_mod_clear_sky/blob/main/media/agr_leader_join_duty.png?raw=true)
* Join dialog to "Freedom" ![Image](https://github.com/stalker-tools/real_weapons_mod_clear_sky/blob/main/media/val_freedom_leader_join_main.png?raw=true)

---
---
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
* Image (neato layout engine) ![Image](https://github.com/stalker-tools/real_weapons_mod_clear_sky/blob/main/media/ltx_tree_neato.png?raw=true)

UI for interactive dot file view: `xdot -fneato ltx_tree.dot`
