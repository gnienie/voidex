voidex — Modrinth-Only Fabric Mod Installer

FEATURES
- Downloads mod JAR files using the official Modrinth API and the download URLs returned by Modrinth.
- Only installs versions explicitly tagged for Minecraft 1.21.11 and Fabric.
- Defaults to %APPDATA%\.tlauncher\legacy\Minecraft\game\mods for the current Windows user.
- Lets you choose a different mods folder.
- Verifies SHA-1 checksums when Modrinth provides them.
- Skips projects without a compatible Modrinth release and reports them in the log.
- Does not include View Model Customizer (the hand-position adjustment mod).
- Never downloads mods from third-party sites.

BUILD voidex.exe
1. Install Python 3.11 or newer from the official Python website and make sure the Python launcher (py) is available.
2. Double-click build_voidex.bat.
3. The executable will be created at dist\voidex.exe.
4. You can copy voidex.exe anywhere. It automatically uses the current Windows user's APPDATA folder.

TLS CERTIFICATES
- API requests and mod downloads use the certifi CA bundle, included in the executable during the build.
- HTTPS certificate and hostname verification remain enabled. Do not disable verification if a certificate error persists; check the computer's date/time and network security software instead.

NOTES
- Your Minecraft installation must use Fabric for Minecraft 1.21.11. This installer does not install Minecraft, Java, or Fabric Loader.
- An internet connection is required to download mods.
- Some requested mods may not have a compatible Modrinth release for Minecraft 1.21.11; those mods are safely skipped.
