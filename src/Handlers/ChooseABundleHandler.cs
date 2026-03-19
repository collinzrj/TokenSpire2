using Godot;
using MegaCrit.Sts2.Core.Nodes.Cards;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.Screens.CardSelection;

namespace TokenSpire2.Handlers;

public static class ChooseABundleHandler
{
    public static double Handle(NChooseABundleSelectionScreen screen, System.Random rng)
    {
        if (!GodotObject.IsInstanceValid(screen)) return 0;

        // If confirm is visible and enabled, click it (bundle already selected)
        var confirm = AutoSlayHelpers.FindFirst<NConfirmButton>(screen);
        if (confirm?.IsEnabled == true)
        {
            MainFile.Logger.Info("[AutoSlay] Confirming bundle selection");
            confirm.ForceClick();
            return 1.0;
        }

        // Select a random bundle
        var bundles = AutoSlayHelpers.FindAll<NCardBundle>(screen);
        if (bundles.Count == 0) return 0.5;

        var pick = bundles[rng.Next(bundles.Count)];
        MainFile.Logger.Info("[AutoSlay] Selecting card bundle");
        pick.Hitbox?.ForceClick();
        return 0.5;
    }
}
