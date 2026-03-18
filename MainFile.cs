using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.Modding;

namespace DemoMod;

// [ModInitializer] tells the STS2 mod loader to call Initialize() when loading this mod.
// The class must inherit from Godot's Node and be declared partial (Godot SDK requirement).
[ModInitializer(nameof(Initialize))]
public partial class MainFile : Node
{
    public const string ModId = "DemoMod";

    // The game's built-in logger — output appears in the game's log file and debug console.
    public static MegaCrit.Sts2.Core.Logging.Logger Logger { get; } =
        new(ModId, MegaCrit.Sts2.Core.Logging.LogType.Generic);

    public static void Initialize()
    {
        new Harmony(ModId).PatchAll();
        Logger.Info("DemoMod loaded — drawing 2 extra cards per turn.");
    }
}
