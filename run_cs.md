# Run Clear Sky on Linux/Wine for Ubuntu 22.10

## 1. Tested hardware and OS info

## 1.1. Hardware info
```sh
cat /proc/cpuinfo|grep name|uniq
model name      : AMD Ryzen 5 PRO 5650G with Radeon Graphics
```

## 1.2. OS info
```sh
uname -a
Linux ubuntu-workstation 5.19.0-46-generic #47-Ubuntu SMP PREEMPT_DYNAMIC Fri Jun 16 13:30:11 UTC 2023 x86_64 x86_64 x86_64 GNU/Linux

lsb_release -a
No LSB modules are available.
Distributor ID: Ubuntu
Description:    Ubuntu 22.10
Release:        22.10
Codename:       kinetic
```

## 2. OS software installation

### 2.1. Install OpenGL and videocard driver AMD for i386 architecture.
```sh
sudo apt install libglx-mesa0:i386 libgl1:i386
sudo apt install libvulkan1:i386

# Packages list from apt history:
libglx-mesa0:i386 (22.2.5-0ubuntu0.1, automatic), libglx0:i386 (1.5.0-1, automatic), libgl1-mesa-dri:i386 (22.2.5-0ubuntu0.1, automatic), libxcb-glx0:i386 (1.15-1, automatic), libgl1:i386 (1.5.0-1)
libvulkan1:i386 (1.3.224.0-1), mesa-vulkan-drivers:i386 (22.2.5-0ubuntu0.1, automatic), libxcb-randr0:i386 (1.15-1, automatic)
```

Check OpenGL:
```sh
glxinfo|grep vers
server glx version string: 1.4
client glx version string: 1.4
GLX version: 1.4
    Max core profile version: 4.6
    Max compat profile version: 4.6
    Max GLES1 profile version: 1.1
    Max GLES[23] profile version: 3.2
OpenGL core profile version string: 4.6 (Core Profile) Mesa 22.2.5
OpenGL core profile shading language version string: 4.60
OpenGL version string: 4.6 (Compatibility Profile) Mesa 22.2.5
OpenGL shading language version string: 4.60
OpenGL ES profile version string: OpenGL ES 3.2 Mesa 22.2.5
OpenGL ES profile shading language version string: OpenGL ES GLSL ES 3.20
    GL_ANDROID_extension_pack_es31a, GL_ANGLE_pack_reverse_row_order,
    GL_EXT_shader_group_vote, GL_EXT_shader_implicit_conversions,
```

### 2.2. Install [Wine](https://wiki.winehq.org/Ubuntu) for i386 architecture. Check wine:
```sh
wine --version
wine-8.0.1
```
### 2.3 Create wine prefix

For example, `clear_sky`. Prefix path `$HOME/.local/share/wineprefixes/clear_sky`

### 2.4. Install [Winetricks](https://wiki.winehq.org/Winetricks)

Check installed dlls:
```sh
env WINEPREFIX=$HOME/.local/share/wineprefixes/clear_sky winetricks list-installed
Using winetricks 20220411 - sha256sum: a4952b40c48d104eb4bcb5319743c95ae68b404661957a134974ae4e1dc79b34 with wine-8.0.1 and WINEARCH=win32
d3dx9
d3dx9_31
d3dx10
d3dx10_43
d3dcompiler_47
d3dcompiler_43
```

## 3. Clear Sky installation and running

Game path: `"$HOME/.wine/drive_c/Program Files (x86)/clear_sky`

```sh
env WINEPREFIX=$HOME/.local/share/wineprefixes/clear_sky env LANG=ru_RU.CP1251 env LC_ALL="ru_RU.CP1251" wine ./setup.exe
env WINEPREFIX=$HOME/.local/share/wineprefixes/clear_sky env LANG=ru_RU.CP1251 env LC_ALL="ru_RU.CP1251" wine ./Redist/DirectX/DXSETUP.exe
env WINEPREFIX=$HOME/.local/share/wineprefixes/clear_sky wine ./bin/xrEngine.exe
```
