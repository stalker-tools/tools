# Stalker Xray tools

The software consists of two parts:
- Analysis tools for Xray game engine. Used by traditional X-ray game developers:
  - .ltx/.xml/.script game logic modifications;
  - .ogg/.dds/.ogf/.omf/.anm/.ppe game media modifications.
- Hybrid game engine: Xray (.exe with Lua scripts) + Odyssey (Python with web interface). For a new featured, new kind of game developers that free of capabilities of X-ray engine.

## Table of contents:

### [1. Brief introduction](#1-brief-introduction-1)
- #### [1.1 Stalker Tools specific features](#11-stalker-tools-specific-features)
- #### [1.2 Little intro](#12-little-intro)
- #### [1.3 .db/.xdb extract tool](#13-dbxdb-extract-tool-1)
- #### [1.4 Gamedata analysis tools](#14-gamedata-analysis-tools-1)
- #### [1.5 Hybrid game engine](#15-hybrid-game-engine-1)
### [2. Installation](#2-installation-1)
- #### [2.1 Windows instructions](#21-windows-instructions-1)
- #### [2.2 Linux instructions](#22-linux-instructions-1)
### 3. Usage
- #### [3.1 .db/.xdb files extraction](EXTRACT.md)
- #### [3.2 .ltx files analysis tool](ANALYSIS_LTX.md)

# 1. Brief introduction

Odyssey/Stalker Xray tools is a cross-platform Python-based tools.

It build with reach media visualizing features in mind, like .html files for infographics and .csv table files for .ltx batch editing.

Tools authors strong believe that it helps to game developers to save time and speed-up development process.

Since X-ray game engine was reached good 3D capabilities. Along with exciting the main idea of ​​the game. Authors of this tools houps to help reach a next level, new kind of game scenario.

## 1.1 Stalker Tools specific features

This repo introduces a __new concept__ for mod authors that consists of two main workflow stages: prepare, compile.

### 1.1.1 Prepare stage: prepare sources for new mod

  Misc gamedata files
  - Collect files to gamedata souces path according gamedata-based paths.
  - Create new files.

  Section (.ltx) parameters (numericals and localization text) for .ltx files: ammo, weapons, outfits e.t.c.
  - Collect and edit .ltx sections and/or .ltx files.

  Inventory images
  - Collect and edit .ltx items images as .png separate files. So each inventory item has own .png file with .ltx section name.
    Example: for .ltx [antirad] section: anirad.png.
    Besides, each .ltx inventory item section has grid coordinates for texture .dds as parameters:
	  inv_grid_x, inv_grid_y, inv_grid_width, inv_grid_height.

### 1.1.2 Compilation stage: compile new mod from new mod sources

  Misc gamedata files
  - Import files to new mod gamedata path.

  Section (.ltx) parameters.
  - Import all .csv tables files to .ltx files.

  Inventory images:
  - Import all .png files into one full-size .dds texture according to .ltx inventory grid: x, y, w, h.

### 1.1.3 Forkflow for Prepare stage

  Misc gamedata files
  - Copy files from another mod to gamedata souces path according gamedata-based paths.
    Be kind to gather another mod authors info and show it.
  - Create/edit files by text editor or multimedia editors, examples:
    VS Code for text, Audacity for audio, blender-xray for X-ray graphics, GIMP for .dds and .png images.
  - For 3D objects.
    Copy .ogf files, copy textures .dds files (see .ogf file by hex editor for texture file path and name).
    Add textures to [specification] section of "textures/textures.ltx" file.

  Section (.ltx) parameters.
  - Collect new from another mod and edit existing .ltx files.
    If .ltx file or .ltx section does not exists: create them by text editor. Use latin symbols only.
    Use table-based editor:
	  Export .ltx sections names by rows (first column) and their parameters names by columns (first row) to .csv files.
	  See help for "csv" subcommand.
      Be free to use "--kind" filter to automatically gather of .ltx sections. Or set .ltx file path and sections names.

  Inventory images.
  - Collect new from another mod and edit existing items images as .png separate files.
    Use icons utility to import images from another mod .dds file. See help for "e" subcommand.
  - Select free inventory grid cells for new items.
    Export one full-size .dds to marked image file: grid with cells coordinates. See "-E" option for "inv" subcommand.
  - Edit .ltx files to set .ltx items inventory grid coordinates (and textures names if changed).
    If .ltx file or .ltx section does not exists: create them by text editor. Use latin symbols only.
    Use table-based editor: export .ltx sections to .csv files. See help for "csv" subcommand.

### 1.1.4 Forkflow for Compilation stage

  Misc gamedata files
  - Copy files to new mod gamedata path from gamedata souces path according gamedata-based paths.

  Section (.ltx) parameters.
  - Import all table .csv files. See "-i" option for "csv" subcommand.

  Inventory images.
  - Import all table .csv files for inventory grid coordinates. See "-i" option for "csv" subcommand.
  - Import all inventory images by this utility. See help for "inv" subcommand.

## 1.2 Little intro

Tools usage falls into two category:
- **Git repository usage**<br/>
  Clone all Python sources and use all functionality - command-line utilities and Python-way API (import statement).

- **Standalone tools**<br/>
  Python Zip Applications: one file ready-to-use for one main function.<br/>
  Just open [releases](https://github.com/stalker-tools/tools/releases/latest) page and download files.<br/>
  Note: You still need [install](#2-installation-1) Python and dependencies. And You still can use Python-way API import statement to use modules from Python Zip Applications.

  List of standalone tools:
  - db-extract<br/>
    extract .db/.xdb files to gamedata path with extracted files filters
  - stalker-brochure<br/>
    example: [Clear Sky + SGM 3.10 + Real Weapons](https://html-preview.github.io/?url=https://github.com/stalker-tools/real_weapons_mod_clear_sky/blob/main/media/Clear%20Sky%20%2B%20SGM%203.10%20%2B%20Real%20Weapons.html)
  - stalker-dialogs<br/>
    example: [CS: Join dialog to "Duty"](https://github.com/stalker-tools/real_weapons_mod_clear_sky/blob/main/media/agr_leader_join_duty.png?raw=true).
  - stalker-profiles<br/>
    examples: [SoC: profiles](https://github.com/stalker-tools/real_weapons_mod_clear_sky/blob/main/media/SoC.profiles.brochure.png?raw=true), [SoC: escape location: stalker-guide](https://github.com/stalker-tools/real_weapons_mod_clear_sky/blob/main/media/SoC.profiles.dialogs.png?raw=true).
  - stalker-tasks<br/>
    example: [tasks - Sigerous Mod.csv](https://github.com/stalker-tools/real_weapons_mod_clear_sky/blob/main/media/tasks%20-%20Sigerous%20Mod.csv)
  - stalker-maps<br/>
    see all game maps (levels) on single .html page

### Main features

- Direct working with packed .db/.xdb files without needs for gamedata extraction.
- Python-way API support:
  - .db/.xdb files;
  - config files: .ltx sections, .xml localization and game.graph;
  - saving the game .sav and fsgame.ltx.
- Analysis tools with visualize game files:
  - dialogue tool; out format: html with dialog phrases digraphs that embedded as svg or images.
In case of svg - dialogue phrases is text searchable: just open .html and use text search.
Use different layout engines, see: [graphviz layouts](https://www.graphviz.org/docs/layouts/).<br/>
See dialogs digraphs (.png) example: [CS: Join dialog to "Duty"](https://github.com/stalker-tools/real_weapons_mod_clear_sky/blob/main/media/agr_leader_join_duty.png?raw=true).<br/>
See installation for standalon utility: [2.2.5 stalker-dialogs instructions](#225-stalker-dialogs-stalker-profiles-instructions)
  - characters profiles tool; out formats: html (brochure), html + dialogs digraphs embedded in html as svg, csv table.<br/>
See profiles (.png) examples: [SoC: profiles](https://github.com/stalker-tools/real_weapons_mod_clear_sky/blob/main/media/SoC.profiles.brochure.png?raw=true), [SoC: escape location: stalker-guide](https://github.com/stalker-tools/real_weapons_mod_clear_sky/blob/main/media/SoC.profiles.dialogs.png?raw=true).
  - actor tasks tool; out format: table.<br/>
See tasks example: [tasks - Sigerous Mod.csv](https://github.com/stalker-tools/real_weapons_mod_clear_sky/blob/main/media/tasks%20-%20Sigerous%20Mod.csv)
  - maps tool; out format: html with embedded images.
- Tools to extract UI .dds icons sets.
- Tools for automatic brochure generation with rich infographics of game actors, suits, ammo, artifacts, food.
  - It can greatly helps gamers to involve into game action and choose gameplay.
  - Moreover, such brochure can help introduce audience with game developer.
  - Finally, that should people become a bit serious to game author. :)
  - See infographics .html example: [Clear Sky + SGM 3.10 + Real Weapons](https://html-preview.github.io/?url=https://github.com/stalker-tools/real_weapons_mod_clear_sky/blob/main/media/Clear%20Sky%20%2B%20SGM%203.10%20%2B%20Real%20Weapons.html)
  - See installation for standalon utility: [2.2.4 stalker-brochure instructions](#224-stalker-brochure-instructions)

Take a fact that tools is in developing process. And API may be changed.

## 1.3 .db/.xdb extract tool

At all, using scenarios involves two ways:

- Standalone command-line utility - ready-to-use for game enthusiasts. See: installation [2.2.3 db-extract instructions](#223-db-extract-instructions)
- Python-way API to access game resources as flexible as python can - for developers.


Command-line tool to extract _.db, .xdb, .xrp, .xp_ files. See help: `paths.py -h` and it sub-command `paths.py e -h`. Standalone tool: `db-extract`.<br/>
Of course there is _low-level_ command-line tool for analysis of .db/.xdb files content - game files/folders structure. See help: `DBReader.py -h` and it sub-commands.<br/>
This tool allows to game developers working with gamedata without nessesarity extracting of .db/.xdb files: 
Python-way API - just import `XRReader` class from `DBReader.py`. See [DBReader.py:main()](https://github.com/stalker-tools/tools/blob/0b7f1c134f875a457119ae87c7187c0d3708e0a6/DBReader.py#L262) function code for low-level usage examples.

See help: [3.1 .db/.xdb files extraction](EXTRACT.md).

## 1.4 Gamedata analysis tools

This command-line tools used for analysis of gamedata Xray config files:
- .ltx sections
- .xml localization
- .dds icons with .xml configs
- game.graph

And Xray gameplay files:
- root config fsgame.ltx
- saving the game .sav save

Most useful utility for mod autor/publisher is `graph_tool.py`, standalone tool: `stalker-brochure`.<br/>
Just see generated _.html_ brochure example: [Clear Sky + SGM 3.10 + Real Weapons.html](https://html-preview.github.io/?url=https://github.com/stalker-tools/real_weapons_mod_clear_sky/blob/main/media/Clear%20Sky%20%2B%20SGM%203.10%20%2B%20Real%20Weapons.html)<br/>
This brochure genarated by this line:
```sh
python graph_tool.py -g ".../S.T.A.L.K.E.R" -t 2947ru b > "Clear Sky + SGM 3.10 + Real Weapons.html"
```

One more exciting feature of `graph_tool.py` is **batch .ltx files editing**. Let imagine a game developer that wants real weapons in own game. This requires tens .ltx files modification with about ten parameters for each weapon and ammo. And holds all this information in mind with consistency requirements. Actually, it usual business process - use table-organized data representing way. Just gather all weapons and ammo info into .csv (comma separated values) tables files. For this - use `graph_tool.py` csv commands.

Example workflow to make real weapons and ammo (see [Real weapons and ammo parameters](https://github.com/stalker-tools/real_weapons_mod_clear_sky)):
- edit selected parameters for all weapons:
  - create _weapons.power.csv_ file with one line:
    ```[],hit_power,hit_impulse,fire_distance,bullet_speed,rpm,silencer_hit_power,silencer_hit_impulse,silencer_fire_distance,silencer_bullet_speed```
  - export selected parameters from .ltx files with _--kind_ filter:
    ```sh
    python graph_tool.py -g ".../S.T.A.L.K.E.R" -t 2947ru csv --kind weapons "weapons.power.csv"
    ```
  - edit .csv file in Your faworit software, for example LibreOffice Calc
  - import .csv file to .ltx files in _gamedata_ path:
    ```sh
    python graph_tool.py -g ".../S.T.A.L.K.E.R" -t 2947ru csv -i "weapons.power.csv"
    ```
- edit selected parameters for all ammo:
  - create _ammo.power.csv_ file with one line:
    ```[],k_dist,k_disp,k_hit,k_impulse,k_pierce,impair,buck_shot,inv_weight,box_size,cost```
  - export selected parameters from .ltx files with _--kind_ filter:
    ```sh
    python graph_tool.py -g ".../S.T.A.L.K.E.R" -t 2947ru csv --kind ammo "ammo.power.csv"
    ```
  - edit .csv file in Your faworit software, for example MS Office Excel
  - import .csv file to .ltx files in _gamedata_ path:
    ```sh
    python graph_tool.py -g ".../S.T.A.L.K.E.R" -t 2947ru csv -i "ammo.power.csv"
    ```

See help: [3.2 .ltx files analysis tool](ANALYSIS_LTX.md).

Developed and tested on Linux/Wine.

## 1.5 Hybrid game engine

This is cross-platform combination of following game engines:
- Xray game engine: .exe and .dll files with Lua scripts and config files, it cross-platform via Wine.
- Odyssey game engine: event-driven game logic with web interface, it cross-platform via Python.

Web interface allow involve mobile devices into game process. And can be used by game modification developers to increase game immersion thru device profiles: radio and PDA.

For example, play audio on radio with talks and radio interference according to gameplay.
And also provide offline access to game thru saved PDA states on smartphone. So player can see much more gameplay information such as fiction texts, photos, videos. That helps understand main idea of screenplay and deep into details if player wants.

Finally, nowadays AI allows game designers create multimedia content and this hybrid engine provide simply way to use it.

Tested on Firefox and Chrome on Ubuntu and Android.

# 2. Installation

### Dependencies:
| Python | LZO |
|--------|-----|
| ![Python](https://www.python.org/static/img/python-logo.png) | python-lzo |

### Analysis dependencies:
 Graphviz + pydot | plotly + kaleido | Pillow |
|-----------------|------------------|--------|
| ![Graphviz](https://graphviz.org/Resources/app.png) | ![plotly](https://plotly.github.io/documentation/all_static/images/graphing_library.svg) | ![Pillow](https://pillow.readthedocs.io/en/stable/_static/pillow-logo-dark-text.png) |

### 2.1 Windows instructions

#### 2.1.1. Download and install Python version 3.12 and abow. For example:
[Python 3.12.4](https://www.python.org/downloads/release/python-3124/)

#### 2.1.2 Download and install [Graphviz 11.0.0](https://graphviz.org/download/#windows)

#### 2.1.3 Install Python packages:
```sh
pip3 install -r requirements.txt
```

### 2.2 Linux instructions

#### 2.2.1 Install Graphviz, instruction: [Graphviz](https://graphviz.org/download/#linux)

- Ubuntu 24:

```sh
sudo apt-get update
sudo apt-get install graphviz
```

- OpenSUSE:
```sh
sudo zypper refresh
sudo zypper install graphviz
```

#### 2.2.2 Install Python packages:

```sh
pip3 install -r requirements.txt
```

#### 2.2.3 db-extract instructions

Also for **stalker-tasks**.

Download latest version: [db-extract](https://github.com/stalker-tools/tools/releases/latest).
Please, read release notes for using instructions.

Ubuntu 24:

- Install LZO development package: `apt install liblzo2-dev`
- Install LZO Python package:
  - for Python venv: `python3 -m pip install python-lzo`
  - for system Python: `apt install python3-lzo`
- Run: `+x ./db-extract`

#### 2.2.4 stalker-brochure instructions

Also for **stalker-maps**.

Download latest version: [stalker-brochure](https://github.com/stalker-tools/tools/releases/latest).
Please, read release notes for using instructions.

Ubuntu 24:

Install packages for [2.2.3 db-extract instructions](#223-db-extract-instructions)

- Install Python packages:
  - for Python venv: `python3 -m pip install plotly pillow`
  - for system Python: `apt install python3-plotly python3-pillow`
- Run: `+x ./stalker-brochure`

#### 2.2.5 stalker-dialogs, stalker-profiles instructions

Download latest version: [stalker-dialogs, stalker-profiles](https://github.com/stalker-tools/tools/releases/latest).
Please, read release notes for using instructions.

Ubuntu 24:

Install packages for [2.2.4 stalker-brochure instructions](#224-stalker-brochure-instructions)

- Install Python packages:
  - for Python venv: `python3 -m pip install pydot`
  - for system Python: `apt install python3-plotly pydot`
- Run: `+x ./stalker-dialogs`
- Run: `+x ./stalker-profiles`
