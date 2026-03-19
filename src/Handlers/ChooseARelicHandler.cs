using Godot;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Screens;

namespace TokenSpire2.Handlers;

public static class ChooseARelicHandler
{
    public static double Handle(NChooseARelicSelection screen, System.Random rng)
    {
        if (!GodotObject.IsInstanceValid(screen)) return 0;
        var clickables = AutoSlayHelpers.FindAll<NClickableControl>(screen);
        if (clickables.Count == 0) return 0.5;

        var pick = clickables[rng.Next(clickables.Count)];
        MainFile.Logger.Info("[AutoSlay] Selecting relic");
        pick.ForceClick();
        return 1.0;
    }
}
