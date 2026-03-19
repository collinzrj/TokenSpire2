using System.Linq;
using Godot;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.Events.Custom.CrystalSphere;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Screens.Map;
using MegaCrit.Sts2.Core.Nodes.Screens.Overlays;

namespace TokenSpire2.Handlers;

public static class CrystalSphereHandler
{
    public static double Handle(NCrystalSphereScreen screen, System.Random rng)
    {
        if (!GodotObject.IsInstanceValid(screen)) return 0;

        // If a child overlay appeared on top, let the main loop handle it
        var topOverlay = NOverlayStack.Instance?.Peek();
        if (topOverlay != null && topOverlay != (IOverlayScreen)screen)
            return 0;

        // Try proceed button
        var proceed = screen.GetNodeOrNull<NProceedButton>("%ProceedButton");
        if (proceed?.IsEnabled == true)
        {
            MainFile.Logger.Info("[AutoSlay] Clicking Crystal Sphere proceed");
            proceed.ForceClick();

            // If map opened but screen lingers, force remove it (like original)
            if (NMapScreen.Instance?.IsOpen == true)
                NOverlayStack.Instance?.Remove(screen);

            return 1.0;
        }

        // Click a random hidden cell
        var cells = screen.GetNodeOrNull<Control>("%Cells");
        if (cells == null) return 0.5;

        var clickable = AutoSlayHelpers.FindAll<NCrystalSphereCell>(cells)
            .Where(c => c.Visible && c.Entity.IsHidden)
            .ToList();

        if (clickable.Count == 0)
        {
            MainFile.Logger.Info("[AutoSlay] No more hidden cells, waiting for proceed/rewards");
            return 0.5;
        }

        var pick = clickable[rng.Next(clickable.Count)];
        MainFile.Logger.Info($"[AutoSlay] Clicking crystal sphere cell, {clickable.Count} clickable remaining");
        pick.EmitSignal(NClickableControl.SignalName.Released, pick);
        return 0.5;
    }
}
