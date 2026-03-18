# STS2 Demo Mod

A minimal, well-commented mod for Slay the Spire 2 to learn how modding works.

## What it does

| Patch | Type | Visible effect |
|---|---|---|
| `LogShufflePatch` | Prefix | Writes a log line every time a card pile shuffles |
| `DemoIntentLabelPatch` | Postfix | Appends `[DEMO]` to multi-attack monster intent labels in combat |

## Prerequisites

1. **.NET 9 SDK** — https://dotnet.microsoft.com/download/dotnet/9.0
   Run `dotnet --version` to confirm.

2. **Slay the Spire 2** installed at
   `D:\SteamLibrary\steamapps\common\Slay the Spire 2`
   (If yours is elsewhere, edit `SteamAppsPath` in `DemoMod.csproj`.)

## Build & install

```bash
dotnet build
```

The build target `CopyToModsFolderOnBuild` automatically copies `DemoMod.dll`
and `DemoMod.json` into:

```
D:\SteamLibrary\steamapps\common\Slay the Spire 2\mods\DemoMod\
```

Start the game — the mod will be loaded automatically.

## Key concepts

### Mod entry point (`MainFile.cs`)
- The class inherits from Godot's `Node` and is marked `partial` (Godot SDK requirement).
- `[ModInitializer(nameof(Initialize))]` tells the game's mod loader which method to call.
- `harmony.PatchAll()` applies every `[HarmonyPatch]` class in the assembly at once.

### Harmony patch types (`src/ExamplePatches.cs`)
- **Prefix** — runs before the original method; return `false` to skip the original.
- **Postfix** — runs after the original method; use `ref __result` to change the return value.
- **Transpiler** — rewrites IL directly (see `FasterShufflePatch` in MintySpire2 for an example).

### Special Harmony parameter names
| Name | Meaning |
|---|---|
| `__instance` | The object the method was called on (`this`) |
| `__result` | The method's return value (declare `ref` to modify) |
| `__0`, `__1`, … | The original method's positional parameters |

### Mod manifest (`DemoMod.json`)
```json
{
  "has_pck": false,   // no Godot resource pack needed for pure C# mods
  "has_dll": true,    // a compiled C# assembly is required
  "dependencies": []  // list other mod IDs here if you depend on them
}
```

## Project structure

```
sts2_mod/
├── DemoMod.csproj      Project + build configuration
├── DemoMod.json        Mod manifest (read by the game's mod loader)
├── nuget.config        Keeps NuGet packages local to this folder
├── project.godot       Minimal Godot project config (required by Godot.NET.Sdk)
├── MainFile.cs         Mod entry point
└── src/
    └── ExamplePatches.cs   Two demo patches with comments
```
