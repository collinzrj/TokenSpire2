using System.Linq;
using Godot;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Nodes.Screens.TreasureRoomRelic;

namespace DemoMod.Handlers;

public static class TreasureRoomHandler
{
    private static bool _chestOpened;

    public static void Reset() => _chestOpened = false;

    public static double Handle(NTreasureRoom room)
    {
        if (!GodotObject.IsInstanceValid(room)) return 0;

        // Step 1: Open chest first (matching official AutoSlay flow)
        if (!_chestOpened)
        {
            var chest = room.GetNodeOrNull<NClickableControl>("Chest");
            if (chest != null && GodotObject.IsInstanceValid(chest) && chest.IsEnabled)
            {
                MainFile.Logger.Info("[AutoSlay] Opening chest");
                chest.ForceClick();
                _chestOpened = true;
                return 2.0;
            }
        }

        // Step 2: Pick up relics
        var relics = AutoSlayHelpers.FindAll<NTreasureRoomRelicHolder>(room)
            .Where(r => r.IsEnabled && r.Visible)
            .ToList();
        if (relics.Count > 0)
        {
            MainFile.Logger.Info($"[AutoSlay] Picking up relic ({relics.Count} available)");
            relics[0].ForceClick();
            return 1.0;
        }

        // Step 3: Proceed
        var proceed = room.ProceedButton;
        if (proceed?.IsEnabled == true)
        {
            MainFile.Logger.Info("[AutoSlay] Clicking treasure room proceed");
            proceed.ForceClick();
            _chestOpened = false;
            return 1.5;
        }

        MainFile.Logger.Info("[AutoSlay] Treasure room: waiting");
        return 0.5;
    }
}
