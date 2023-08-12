# Stalker xray tools

This python cross-platform command-line tools used for analysis and editing of gamedata `.ltx` files. Developed and tested on Linux/Wine.

## Unpack gamedata

All game resources packed to several files. So, this files need unpack in new `gamedata` folder.
To pack/unpack use `converter.exe` (for example, from bardak converter_25aug2008).

### Unpack Clear Sky

```sh
GAME_PATH="$HOME/.wine/drive_c/Program Files (x86)/clear_sky/"
CONVERTER_PATH="converter.exe"

find "$GAME_PATH""resources" -type f -exec echo -e "\nEXTRACT: ""{}" \; -exec wine "$CONVERTER_PATH" -unpack -xdb "{}" -dir "$GAME_PATH""gamedata" \;

find "$GAME_PATH""patches" -type f -exec echo -e "\nEXTRACT: ""{}" \; -exec wine "$CONVERTER_PATH" -unpack -xdb "{}" -dir "$GAME_PATH""gamedata" \;
```

## .ltx files analysis tool

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

## Analysis examples for Clear Sky

### Ammunition

Show power of bullets:
```sh
python ltx_tool.py -l k_hit -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata/configs/weapons"
orig/configs/weapons/weapons.ltx [ammo_9x18_fmj] k_hit = 1.38
orig/configs/weapons/weapons.ltx [ammo_9x18_pbp] k_hit = 1.86
orig/configs/weapons/weapons.ltx [ammo_9x18_pmm] k_hit = 1.86
orig/configs/weapons/weapons.ltx [ammo_9x19_fmj] k_hit = 1.64
orig/configs/weapons/weapons.ltx [ammo_9x19_pbp] k_hit = 1.68
orig/configs/weapons/weapons.ltx [ammo_11.43x23_fmj] k_hit = 1.68
orig/configs/weapons/weapons.ltx [ammo_11.43x23_hydro] k_hit = 2.05
orig/configs/weapons/weapons.ltx [ammo_5.45x39_fmj] k_hit = 4.85
orig/configs/weapons/weapons.ltx [ammo_5.45x39_ap] k_hit = 4.67
orig/configs/weapons/weapons.ltx [ammo_5.56x45_ss190] k_hit = 5.5
orig/configs/weapons/weapons.ltx [ammo_5.56x45_ap] k_hit = 5.28
orig/configs/weapons/weapons.ltx [ammo_pkm_100] k_hit = 1
orig/configs/weapons/weapons.ltx [ammo_7.62x54_7h1] k_hit = 11.17
orig/configs/weapons/weapons.ltx [ammo_7.62x54_ap] k_hit = 11.17
orig/configs/weapons/weapons.ltx [ammo_7.62x54_7h14] k_hit = 11.17
orig/configs/weapons/weapons.ltx [ammo_223_fmj] k_hit = 1
orig/configs/weapons/weapons.ltx [ammo_gauss] k_hit = 1
orig/configs/weapons/weapons.ltx [ammo_9x39_pab9] k_hit = 2.72
orig/configs/weapons/weapons.ltx [ammo_9x39_ap] k_hit = 2.32
orig/configs/weapons/weapons.ltx [ammo_9x39_sp5] k_hit = 2.32
orig/configs/weapons/weapons.ltx [ammo_12x70_buck] k_hit = 0.3
orig/configs/weapons/weapons.ltx [ammo_12x76_zhekan] k_hit = 1
orig/configs/weapons/weapons.ltx [ammo_12x76_dart] k_hit = 1
orig/configs/weapons/weapons.ltx [ammo_og-7b] k_hit = 1
orig/configs/weapons/weapons.ltx [ammo_vog-25p] k_hit = 1
orig/configs/weapons/weapons.ltx [ammo_vog-25] k_hit = 1
orig/configs/weapons/weapons.ltx [ammo_m209] k_hit = 1
```

More complex filter for pbp ammunition only:
```sh
python ltx_tool.py -s ammo*pbp -l impair -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata/configs"
configs/weapons/weapons.ltx [ammo_9x18_pbp] impair = 1.22
configs/weapons/weapons.ltx [ammo_9x19_pbp] impair = 1.22
```

### Actor and NPC

Show NPC `hit_fraction`:
```sh
python ltx_tool.py -l hit_fraction -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata/configs/creatures"
configs/creatures/damages.ltx [stalker_hero_1] hit_fraction = 0.1
configs/creatures/damages.ltx [stalker_lesnik_1] hit_fraction = 0.1
configs/creatures/damages.ltx [stalker_bandit_1] hit_fraction = 1.5
configs/creatures/damages.ltx [stalker_bandit_2] hit_fraction = 1.25
configs/creatures/damages.ltx [stalker_bandit_3] hit_fraction = 0.8
configs/creatures/damages.ltx [stalker_bandit_4] hit_fraction = 0.6
configs/creatures/damages.ltx [stalker_dolg_1] hit_fraction = 1.2
configs/creatures/damages.ltx [stalker_dolg_2] hit_fraction = 1.0
configs/creatures/damages.ltx [stalker_dolg_3] hit_fraction = 0.8
configs/creatures/damages.ltx [stalker_dolg_4] hit_fraction = 0.6
configs/creatures/damages.ltx [stalker_freedom_1] hit_fraction = 1.2
configs/creatures/damages.ltx [stalker_freedom_2] hit_fraction = 1.0
configs/creatures/damages.ltx [stalker_freedom_3] hit_fraction = 0.8
configs/creatures/damages.ltx [stalker_freedom_4] hit_fraction = 0.6
configs/creatures/damages.ltx [stalker_merc_1] hit_fraction = 1.2
configs/creatures/damages.ltx [stalker_merc_2] hit_fraction = 1.0
configs/creatures/damages.ltx [stalker_merc_3] hit_fraction = 0.8
configs/creatures/damages.ltx [stalker_merc_4] hit_fraction = 0.6
configs/creatures/damages.ltx [stalker_monolith_1] hit_fraction = 1.2
configs/creatures/damages.ltx [stalker_monolith_2] hit_fraction = 1.0
configs/creatures/damages.ltx [stalker_monolith_3] hit_fraction = 0.8
configs/creatures/damages.ltx [stalker_monolith_4] hit_fraction = 0.6
configs/creatures/damages.ltx [stalker_nebo_1] hit_fraction = 1.2
configs/creatures/damages.ltx [stalker_nebo_2] hit_fraction = 1.0
configs/creatures/damages.ltx [stalker_nebo_3] hit_fraction = 0.8
configs/creatures/damages.ltx [stalker_neutral_1] hit_fraction = 1.2
configs/creatures/damages.ltx [stalker_neutral_2] hit_fraction = 1.0
configs/creatures/damages.ltx [stalker_neutral_3] hit_fraction = 0.8
configs/creatures/damages.ltx [stalker_neutral_4] hit_fraction = 0.6
configs/creatures/damages.ltx [stalker_oon_1] hit_fraction = 0.3
configs/creatures/damages.ltx [stalker_oon_2] hit_fraction = 0.3
configs/creatures/damages.ltx [stalker_soldier_1] hit_fraction = 1.2
configs/creatures/damages.ltx [stalker_soldier_2] hit_fraction = 1.0
configs/creatures/damages.ltx [stalker_soldier_3] hit_fraction = 0.8
configs/creatures/damages.ltx [stalker_soldier_4] hit_fraction = 0.6
configs/creatures/damages.ltx [stalker_zombied_1] hit_fraction = 0.3
configs/creatures/damages.ltx [stalker_zombied_2] hit_fraction = 0.25
configs/creatures/damages.ltx [stalker_zombied_3] hit_fraction = 0.2
configs/creatures/damages.ltx [stalker_zombied_4] hit_fraction = 0.15
```

Set `hit_fraction = 1.2` for all first-level NPC exept zombie, bandits, hero, lesnik and oon:
```sh
python ./ltx_tool.py -m " 1.2" -s stalker_[^z^b^h^l^o]*_1 -l hit_fraction -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata/configs"
```

Show actor and mutants `ph_collision_damage_factor`:
```sh
python ltx_tool.py -l *_damage_* -f "$HOME/.wine/drive_c/Program Files (x86)/clear_sky/gamedata/configs/creatures"
configs/creatures/actor.ltx [actor] ph_collision_damage_factor = 1.0
configs/creatures/m_zombie.ltx [m_zombie_e] ph_collision_damage_factor = 0.1
configs/creatures/m_rat.ltx [m_rat_e] ph_collision_damage_factor = 0.1
configs/creatures/m_cat.ltx [m_cat_e] ph_collision_damage_factor = 0.1
configs/creatures/m_poltergeist.ltx [m_poltergeist_e] ph_collision_damage_factor = 0.1
configs/creatures/m_stalker.ltx [stalker] ph_collision_damage_factor = 0.1
configs/creatures/m_chimera.ltx [m_chimera_e] ph_collision_damage_factor = 0.1
configs/creatures/m_pseudodog.ltx [m_pseudodog_e] ph_collision_damage_factor = 0.1
configs/creatures/m_bloodsucker.ltx [m_bloodsucker_e] ph_collision_damage_factor = 0.1
configs/creatures/m_bloodsucker.ltx [bloodsucker_jumper_deadly] ph_collision_damage_factor = 0.0
configs/creatures/m_boar.ltx [m_boar_e] ph_collision_damage_factor = 0.1
configs/creatures/m_tushkano.ltx [m_tushkano_e] ph_collision_damage_factor = 0.1
configs/creatures/m_dog.ltx [m_dog_e] ph_collision_damage_factor = 0.1
configs/creatures/m_fracture.ltx [m_fracture_e] ph_collision_damage_factor = 0.1
configs/creatures/m_flesh.ltx [m_flesh_e] ph_collision_damage_factor = 0.1
configs/creatures/m_burer.ltx [m_burer_e] ph_collision_damage_factor = 0.1
configs/creatures/m_snork.ltx [m_snork_e] ph_collision_damage_factor = 0.1
configs/creatures/m_controller.ltx [m_controller_e] ph_collision_damage_factor = 0.1
configs/creatures/m_giant.ltx [m_gigant_e] ph_collision_damage_factor = 0.1
```
