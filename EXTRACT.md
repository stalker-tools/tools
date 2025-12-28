# 3.1 .db/.xdb files extraction

## 1. Batch extraction

As .db/.xdb files is container with filesystem, export process include definition of latest version of extracted file.
This utility works with **latest** files version only. For low-level access to .db/.xdb files use `DBReader.py` command-line utility, see [3. Low-level .db/.xdb files information](#3-low-level-dbxdb-files-information).

Command-line interface of export utility consists of common part and sub-commands:
- common part:
  - game root path (_-g \<PATH\>_), default: current path
  - .db/.xdb version (_-t \<VER\>_), one of: _2947ru_, _2947ww_, _xdb_; there is another option values but not tested; see [1.3.1 common help](#131-common-help)
  - verbose (_-v_, _-vv_), default: minimum verbose
- sub-commands
  - extract (e) - main feature: extraction gamedata files from .db/.xdb files; see [1.1 Common use](#11-common-use)
  - diff (d) - game developer feature: unified diff of text files between: .db/.xdb files and _gamedata_ OS pathl see [2. Diff sub-command](#2-diff-sub-command)
  - info (i) - game developer feature: show dump of gamedata files paths from .db/.xdb; see [1.2.2 Show gamedata files paths <ins>info</ins> sub-command](#122-show-gamedata-files-paths-info-sub-command), [1.3.4 <ins>info</ins> sub-command help](#134-info-sub-command-help)

This allows to users more flexible way of using features. And for developers - more structured view of codebase and more rich functionality.

Most command-line options has name and short name. For example: .db/.xdb version: (_--version_) and (_-t_). Be free to use compact-way or meaningful-way. Note, short name of _--version_ option is not _-v_ because _-v_ is short name for verbore option. Thereby verbore option has widely used and has historical reason.

Export do not overwrite files by default. Use (_-r_) option of export sub-command to enable overwrite.

Export order of gamedata files is sorted and grouped by .db/.xdb file name.

### 1.1 Common use

#### 1.1.1 Extract <ins>all</ins> files to _gamedata_ sub-folder:
```sh
python paths.py -g ".../S.T.A.L.K.E.R" -t 2947ru e
```
Use _-g_ option to set game root path (with gamedata.db* files).

See help:
- common help: `python paths.py -h`
- _extract_ sub-command help: `python paths.py e -h`

#### 1.1.2 Extract <ins>all</ins> files to _gamedata-extracted_ sub-folder with verbose (use _-vv_):
```sh
python paths.py -vv -g ".../S.T.A.L.K.E.R" -t 2947ru e -e "gamedata-extracted"
Load all .db/.xdb files to define latest version of gamedata files
game path:     .../S.T.A.L.K.E.R
gamedata path: .../S.T.A.L.K.E.R/gamedata
Load .db/.xdb file  1: gamedata.db0
Load .db/.xdb file  2: gamedata.db1
Load .db/.xdb file  3: gamedata.db2
Load .db/.xdb file  4: gamedata.db3
Load .db/.xdb file  5: gamedata.db4
Load .db/.xdb file  6: gamedata.db5
Load .db/.xdb file  7: gamedata.db6
Load .db/.xdb file  8: gamedata.db7
Load .db/.xdb file  9: gamedata.db8
Load .db/.xdb file 10: gamedata.db9
Load .db/.xdb file 11: gamedata.dba
Load .db/.xdb file 12: gamedata.dbb
Load .db/.xdb file 13: gamedata.dbc
Load .db/.xdb file 14: gamedata.dbd
extract path: .../S.T.A.L.K.E.R/gamedata-extracted
    1 gamedata.db0 skip exist ai\alife\anomalydetectprobability.efd
    2 gamedata.db0 extract ai\alife\anomalyinteractprobability.efd
25684 gamedata.db8 extract textures\wpn\wpn_zink_svd.dds
...
Total files: check 25684, write 25683, skip 1, text encoding utf-8, line separator: '\n' (hex: 0a)
```
It is possible extract files to whatever path: use _-e_ with absolute path.

And lower the verbose level (_-v_) to show only **extract** files.

### 1.2 Developer use

#### 1.2.1 Extract <ins>text files</ins> to _gamedata-extracted_ sub-folder with verbose:
```sh
python paths.py -vv -f "*.ltx" "*.xml" "*.script" -g ".../S.T.A.L.K.E.R" -t 2947ru e -e "gamedata-extracted"
```
Use _-f_ to set one or more file path pattern to export. Unix shell-style wildcards: _*_, _?_, _[seq]_, _[!seq]_.
Example for media files _.ogg_ and _.dds_: _-f "*.ogg" "*.dds"_

##### 1.2.1.1 Working with text files <ins>encoding</ins>:

Extraction process includes very useful thing for text files: **automation encoding and line separator conversion** for used OS.
So, I hope we can't see encoding mess in text files anymore. Please, learn and edit text files with pleasure on youre own OS.

##### 1.2.1.2 Disable text files automation conversion:

To disable text files conversion use (_--encoding raw_):
```sh
python paths.py -f "*.ltx" "*.xml" "*.script" -g ".../S.T.A.L.K.E.R" -t 2947ru e --encoding raw
```

##### 1.2.1.3 Usage example of extraction <ins>text files</ins>

Example extraction of all text files (_.ltx_, _.xml_, _.script_) and verbose (use _-vv_) to _gamedata-extracted_ sub-folder:
```sh
python paths.py -vv -f "*.ltx" "*.xml" "*.script" -g "S.T.A.L.K.E.R" -t 2947ru e -e "S.T.A.L.K.E.R/gamedata-extracted"
Load all .db/.xdb files to define latest version of gamedata files
game path:     .../S.T.A.L.K.E.R
gamedata path: .../S.T.A.L.K.E.R/gamedata
Load .db/.xdb file  1: gamedata.db0
Load .db/.xdb file  2: gamedata.db1
Load .db/.xdb file  3: gamedata.db2
Load .db/.xdb file  4: gamedata.db3
Load .db/.xdb file  5: gamedata.db4
Load .db/.xdb file  6: gamedata.db5
Load .db/.xdb file  7: gamedata.db6
Load .db/.xdb file  8: gamedata.db7
Load .db/.xdb file  9: gamedata.db8
Load .db/.xdb file 10: gamedata.db9
Load .db/.xdb file 11: gamedata.dba
Load .db/.xdb file 12: gamedata.dbb
Load .db/.xdb file 13: gamedata.dbc
Load .db/.xdb file 14: gamedata.dbd
extract path: .../S.T.A.L.K.E.R/gamedata-extracted
    1 gamedata.db0 extract config\character_desc_general.xml
    2 gamedata.db0 extract levels\l01_escape\level.ltx
...
 1367 gamedata.db7 extract textures\textures.ltx
```

To overwrite existing files with exported files use _-r_:
```sh
python paths.py -v -f "*.ltx" "*.xml" "*.script" -g ".../S.T.A.L.K.E.R" -t 2947ru e -e "gamedata-extracted" -r
```

#### 1.2.2 Show gamedata files paths <ins>info</ins> sub-command:

It can be helpful to list file paths and .db/.xdb file names sources. And it can be used in automation.

Show _.ltx_ files as table (human-readable format):
```sh
python paths.py -vv -f "*.ltx" -g ".../S.T.A.L.K.E.R" -t 2947ru i --table
    1 gamedata.dbb config\_prefetch.ltx
    2 gamedata.dbb config\alife.ltx
...
  522 gamedata.db7 textures\textures.ltx
```
To get machine-readable format remove _--table_ option.

The same but swaps file names:
```sh
python paths.py -vv -f "*.ltx" -g ".../S.T.A.L.K.E.R" -t 2947ru i --table --reverse
    1 config\_prefetch.ltx gamedata.dbb
    2 config\alife.ltx gamedata.dbb
...
  522 textures\textures.ltx gamedata.db7
```

### 1.3 Command-line utility help

#### 1.3.1 common help:
```sh
python paths.py -h
sage: paths.py [-h] [-g PATH] [--exclude-db-files FILE_NAME|PATTERN [FILE_NAME|PATTERN ...]] [-t VER] [-f FILE|PATTERN [FILE|PATTERN ...]] [-d PATH] [-v] {extract,e,diff,d,info,i} ...

Odyssey/Stalker Xray game file paths tool.

Used to extract files from .db/.xdb files to gamedata or whatever place: see extract sub-command -d option.
Be free to filter extracted files: see extract sub-command -f option examples below; get help: paths.py e -h
And filter .db/.xdb files: see --exclude-db-files option.
Note: while extraction gamedata files is sorted by paths and grouped by .db/.dbx file name.

positional arguments:
  {extract,e,diff,d,info,i}
                        sub-commands:
    extract (e)         extract files from .db/.xdb files
    diff (d)            compare text files from two medias: .db/.xdb files and gamedata files; output format is unified_diff: ---, +++, @@
    info (i)            show info about files from .db/.xdb files

options:
  -h, --help            show this help message and exit
  -g PATH, --gamepath PATH
                        game path that contains .db/.xdb files and optional gamedata folder
  --exclude-db-files FILE_NAME|PATTERN [FILE_NAME|PATTERN ...]
                        game path that contains .db/.xdb files and optional gamedata folder; Unix shell-style wildcards: *, ?, [seq], [!seq]
  -t VER, --version VER
                        .db/.xdb files version; usually 2947ru/2947ww for SoC, xdb for CS and CP; one of: 11xx, 2215, 2945, 2947ru, 2947ww, xdb
  -f FILE|PATTERN [FILE|PATTERN ...], --filter FILE|PATTERN [FILE|PATTERN ...]
                        filter gamedata files by name use Unix shell-style wildcards: *, ?, [seq], [!seq]
  -d PATH, --gamedata PATH
                        gamedata path; used to diff sub-command; default: gamedata
  -v                    verbose mode: 0..; examples: -v, -vv

Examples:

1. Extract gamedata files from .db/.xdb files

        Extract all gamedata files from all .db/.xdb files to gamedata sub-folder:
paths.py -g "S.T.A.L.K.E.R" -t 2947ru e

        The same to whatever place:
paths.py -g "S.T.A.L.K.E.R" -t 2947ru e -e "path to extract"

        Extract filtered (from ai\alife\ folder) gamedata files from all .db/.xdb files:
paths.py -f "ai\alife\*" -g "S.T.A.L.K.E.R" -t 2947ru e

        The same with all .ltx files:
paths.py -f "*.ltx" -g "S.T.A.L.K.E.R" -t 2947ru e

        Extract all gamedata files from filtered .db/.xdb files:
paths.py --exclude-db-files "gamedata.db0" "gamedata.db1" -g "S.T.A.L.K.E.R" -t 2947ru e
paths.py --exclude-db-files "gamedata.db[012]" "gamedata.dbd" -g "S.T.A.L.K.E.R" -t 2947ru e

        Be free to debug command-line use -vv and --dummy:
paths.py -vv -f "ai\alife\*" -g "S.T.A.L.K.E.R" -t 2947ru e --dummy

        Create mirror of all gamedata files (.db/.xdb and gamedata sub-path) to another location for debug purposes:
paths.py -g "S.T.A.L.K.E.R" -t 2947ru e --include-gamedata -e "path to extract"
This is a way to find out what an X-ray engine see all game data files.

2. Show info about gamedata files from .db/.xdb files

        Show files info as machine-readable format:
paths.py -g "S.T.A.L.K.E.R" -t 2947ru i

        Show files info as human-readable format (and *.ltx files filter):
paths.py -f "*.ltx" -g "S.T.A.L.K.E.R" -t 2947ru i --table
```

#### 1.3.2 <ins>extract</ins> sub-command help:
```sh
python paths.py e -h
usage: paths.py extract [-h] [-e PATH] [-r] [--include-gamedata] [--encoding ENCODING] [-m]

options:
  -h, --help            show this help message and exit
  -e PATH, --extract-path PATH
                        destination path to extract files; default: gamedata
  -r, --replace         replace existing files
  --include-gamedata    include files from gamedata sub-path to extract; used to copy of all gamedata files (.db/.xdb and gamedata sub-path) to another location for debug purposes; default: false
  --encoding ENCODING   extract text files encoding to convert to; text files: .ltx, .xml, .script; to binary copy of text files use "raw" encoding; default: utf-8
  -m, --dummy           dummy run: do not write files; used for command-line options debugging
```

#### 1.3.3 <ins>diff</ins> sub-command help:
```sh
python paths.py d -h
usage: paths.py diff [-h] [--encoding ENCODING]

options:
  -h, --help           show this help message and exit
  --encoding ENCODING  .db/.xdb text files encoding to convert to; text files: .ltx, .xml, .script; to binary copy of text files use "raw" encoding; default: utf-8
```

#### 1.3.4 <ins>info</ins> sub-command help:
```sh
python paths.py i -h
usage: paths.py info [-h] [--paths] [--table] [--reverse]

options:
  -h, --help  show this help message and exit
  --paths     show paths
  --table     human-readable format
  --reverse   output gamedata file path first
```

## 2. Diff sub-command

### 2.1 Diff for text files

It possible to compare text files from two sources: .db/.xdb and gamedata path. This is very handy for developers.
Comparing does with take into account an encoding and lines separator of used OS.

Output format is [unified diff](https://www.gnu.org/software/diffutils/manual/html_node/Unified-Format.html):
- header with two file names: --- and +++
- hunks: @@ -[old file line info] +[new file line info] @@
- files lines:
  - (space) unchanged line
  - (+) line was added
  - (-) line was removed

#### 2.1.1 Compare text files from: .db/.xdb and _gamedata_ sub-path:
```sh
python paths.py -v -f "*.ltx" "*.xml" "*.script" -g ".../S.T.A.L.K.E.R" -t 2947ru d
```
Use (_-vv_) to increase verbose: show all text files paths.

#### 2.1.2 Compare text files from: .db/.xdb and _gamedata-extracted_ sub-path

For example, all text files extracted to _gamedata-extracted_ path.

Then add empty line to beginning in file _scripts\.script_ to get diff sub-command output:
```sh
python paths.py -vv -f "*.ltx" "*.xml" "*.script" -g ".../S.T.A.L.K.E.R" -d "gamedata-extracted" -t 2947ru d
--- gamedata.dbb:scripts\.script
+++           OS:scripts\.script
@@ -1,3 +1,4 @@
+
 schemes = {} -- соответствие схем модулям
 stypes = {} -- типы схем
 
Total files: compared 1367, modified 1, os missing 0
```
It is possible compare files to whatever path: use _-d_ with absolute path.

## 3. Low-level .db/.xdb files information

As .db/.xdb file is files container what is organized into filesystem with folders tree.
And there is number of .db/.xdb files. One gamedata file can be located into multiple .db/.xdb files.
So tools for showing such multiple versions of file is wanted. For this purpose use particular _--last_ option with _gamedata_ sub-command.

Be free to use two different practice:

### 3.1 Overall view of gamedata files from all .db files. This is usual for working with latest gamedata file version.

For example, show latest version of X-ray Lua files as table (human-readable output):
```sh
python DBReader.py -f "gamedata.db*" -t 2947ru g -l -n -g "*xr_*.script"
    1 scripts\xr_abuse.script           gamedata.dbb
    2 scripts\xr_actions_id.script      gamedata.dbb
...
```

By the way, remove -_n_ option in previous example to get machine-readable output:
```sh
python DBReader.py -f "gamedata.db*" -t 2947ru g -l -g "*xr_*.script"
scripts\xr_abuse.script gamedata.dbb
scripts\xr_actions_id.script gamedata.dbb
...
```

One more example, show latest version of _.dds_ image files table (human-readable output):
```sh
python DBReader.py -f "gamedata.db*" -t 2947ru g -l -n -g "*.dds"
    1 levels\l01_escape\build_details.dds                                gamedata.db0
...
   74 levels\l04u_labx18\lmap#1_2.dds                                    gamedata.db1
...
 5306 textures\wpn\wpn_zink_svd.dds                                      gamedata.db8
```

### 3.2 Split gamedata files by .db files. Here is possible to track gamedata files versions by .db files.

For example, show all versions of X-ray Lua files by .db/.xdb files (key-values list):

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
Here is three versions of _scripts\xr_abuse.script_ file in .db files: _gamedata.db4_, _gamedata.dba_ and latest version in _gamedata.dbb_.

## 4. Low-level command-line interface

### 4.1 `DBReader.py` help:
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

### 4.2 `DBReader.py` **gamedata** sub-command help:
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

### 4.3 `DBReader.py` **files** sub-command help:
```sh
python DBReader.py f -h
usage: DBReader.py files [-h] [--table] [--header]

options:
  -h, --help  show this help message and exit
  --table     show files as table format
  --header    treat file as header chunk binary dump file
```

### 4.4 `DBReader.py` **info** sub-command help:
```sh
python DBReader.py i -h
usage: DBReader.py info [-h]

options:
  -h, --help  show this help message and exit
```

### 4.5 `DBReader.py` **dump** sub-command help:
```sh
python DBReader.py d -h
usage: DBReader.py dump [-h] [-i NUMBER] [--header]

options:
  -h, --help  show this help message and exit
  -i NUMBER   print chunk by index: 0..
  --header    print header chunk
```

## 5. Low-level command-line examples

### 5.1 **gamedata** files count overall for .db/.xdb files

#### 5.1.1 count <ins>all</ins> **gamedata** files:
```sh
python DBReader.py -f "gamedata.db*" -t 2947ru g -c
25684
```

#### 5.1.2 count <ins>all .script</ins> **gamedata** files:
```sh
python DBReader.py -f "gamedata.db*" -t 2947ru g -c -g "*.script"
442
```

### 5.2 **gamedata** files count by .db/.xdb files separatelly

#### 5.2.1 <ins>all</ins> **gamedata** files count:
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

#### 5.2.2 <ins>all _.script_</ins> **gamedata** files count:
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

#### 5.2.3 <ins>one _scripts\stalker_generic.script_</ins> **gamedata** file count:
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
Here we see three versions of file. Latest version in <ins>gamedata.dbb</ins> file.
To get .db/.xdb file with file latest version use (_--last_) option.

## 6. Examples for development purposes

### 6.1 **files** listing in .db/.xdb file:
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

### 6.2 chunks <ins>info</ins> in .db/.xdb file:
```sh
python DBReader.py -f "gamedata.dbd" -t 2947ru i
0 Chunk type=DB_CHUNK_DATA(0) offset=8 size=100_788 
1 Chunk type=DB_CHUNK_HEADER(1) offset=100_804 size=210 compressed
```

### 6.3 chunk <ins>dump</ins> (raw data) from .db/.xdb file to binary file:
```sh
python DBReader.py -f "gamedata.dbd" -t 2947ru d --head > "gamedata.dbd.header.bin"
```

### 6.4 chunk <ins>dump</ins> (raw data) from .db/.xdb file as human-readable format (_-v_ option using):
```sh
python DBReader.py -v -f "gamedata.dbd" -t 2947ru d --head > "gamedata.dbd.header.bin"
File: gamedata.dbd
Chunk type=DB_CHUNK_HEADER(1) offset=100_804 size=210 compressed
b"\xder\xc3I\xf1j\xf5\xb6\xa3Z\xeb\x87\xa3\xc3\x94\x02\xf4\x85J8\xbe\xac\x1a6/k\x9c\x11\xe6\xa5\xd2\xab\x01\xa4\x1a\x98\xc2#\x1b\xdd+i6\xcb\xdb\xd0=\xb0\xc3\xbb\xd6,\xa4\xce\xf5\xb4\xbe\x12\x0b\x9e\xeet\xfcA\\&\x82P\x12\xb3\xa1\xa6Q\x08\xb8\x0f!\x0f\xab\xd4\xaaWl\xc6\x9b,\x14/\xe7k\xb1\xe7\x86\xc5z\xb1C\xc9\x19\x11\xb4D>\xb3\x95\xc3r\xc5r5\xcfh\xb3\xffW\xbd&WH=\x1a\x9b\xb4F\xd0}R\xabg-\xc2\x88\xe3u\x8eW\x02\xe5\xc0\x99l_i\x99\x05my\x89\xd6f||zt\xb4pk\xec\x03\x0e\x8b\x88\xecf\x0e\xc5\x94\xa25\xa4+\x02Nb\xde\xbeJ\xf9\xbf\xe5NI\xa2\xf3\xd5\x0ce\x8d\xd9\x9c\xad\x1b\x1b_\x81\xd0'6\xd8\xe7.\xe5o\xcf\xbd\x03}T\xa5\xa1"
```
