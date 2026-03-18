using System.Linq;
using Godot;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.RestSite;
using MegaCrit.Sts2.Core.Nodes.Rooms;

namespace DemoMod.Handlers;

public static class RestSiteHandler
{
    public static double Handle(NRestSiteRoom room, System.Random rng)
    {
        if (!GodotObject.IsInstanceValid(room)) return 0;

        // Check for proceed button (after choosing an option)
        var proceed = room.ProceedButton;
        if (proceed?.IsEnabled == true)
        {
            MainFile.Logger.Info("[AutoSlay] Clicking rest site proceed");
            proceed.ForceClick();
            return 1.5;
        }

        var btns = AutoSlayHelpers.FindAll<NRestSiteButton>(room)
            .Where(b => b.Option.IsEnabled)
            .ToList();
        if (btns.Count == 0) return 0.5;

        btns[rng.Next(btns.Count)].ForceClick();
        return 1.5;
    }
}
