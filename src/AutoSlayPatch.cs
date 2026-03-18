using HarmonyLib;
using MegaCrit.Sts2.Core.Nodes;

namespace DemoMod;

// Attach AutoSlayNode to the game tree when NGame is ready.
// AutoSlayNode._Ready() checks --autoslay and disables itself if not present.
[HarmonyPatch(typeof(NGame), "_Ready")]
public static class AttachAutoSlayNodePatch
{
    static void Postfix(NGame __instance)
    {
        var node = new AutoSlayNode();
        node.Name = "AutoSlayNode";
        __instance.AddChild(node);
    }
}
