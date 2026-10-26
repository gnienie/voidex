# Voidex

Voidex is a Windows desktop app for checking Fabric mod compatibility and installing optimization mods for Minecraft Java Edition.

## Version 2.1 improvements
- Dark, cleaner interface with a Voidex avatar and Windows executable icon.
- Retrieves the official Minecraft release list from Mojang at startup.
- Supports releases from Minecraft 1.16.5 through the newest release returned by Mojang; snapshots are excluded.
- Checks each listed mod against Modrinth's Fabric compatibility data for the selected version.
- Downloads compatible JAR files only from Modrinth's CDN.
- Installs Fabric using minecraft-launcher-lib.
- Remembers the game directory, Minecraft version, and mod selections.
- Keeps a manifest to distinguish files managed by Voidex from existing files.
- Performs network requests in background threads so the interface remains responsive.

Voidex cannot guarantee an FPS increase; results depend on the PC, game version, installed mods, and settings.

## Run from source
1. Install Python 3.12 (64-bit) on Windows.
2. Run install_requirements.bat.
3. Run py -3.12 voidex.py.

## Build the EXE
Double-click build_windows.bat. The executable is created at dist\Voidex.exe.

## Folder selection
Voidex tries to detect the standard Minecraft folder or a common TLauncher game folder. Check the path before installing. For separate instances, use Browse to select that instance's game directory.

Mods are installed into the selected folder's mods directory. Install Fabric for the same Minecraft version before launching with Fabric.

## Notes
- Only release versions are displayed; snapshots are excluded.
- Availability is based on the current Modrinth API response, so not every mod is available for every Minecraft version.
- Existing JAR files not managed by Voidex are not overwritten.
- Voidex downloads mod files; it does not execute downloaded JARs itself.
