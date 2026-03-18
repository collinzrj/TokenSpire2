using System.Linq;
using Godot;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.Events;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;

namespace DemoMod.Handlers;

public static class EventRoomHandler
{
    public static double Handle(Node eventRoom, System.Random rng)
    {
        if (!GodotObject.IsInstanceValid(eventRoom)) return 0;

        // Look for proceed button first (some events have it after completion)
        var proceedBtn = AutoSlayHelpers.FindFirst<NProceedButton>(eventRoom);
        if (proceedBtn?.IsEnabled == true)
        {
            MainFile.Logger.Info("[AutoSlay] Clicking event proceed button");
            proceedBtn.ForceClick();
            return 1.0;
        }

        // Try unlocked event options
        var options = AutoSlayHelpers.FindAll<NEventOptionButton>(eventRoom)
            .Where(o => !o.Option.IsLocked)
            .ToList();

        if (options.Count > 0)
        {
            var pick = options[rng.Next(options.Count)];
            MainFile.Logger.Info("[AutoSlay] Selecting event option");
            pick.ForceClick();
            return 1.0;
        }

        // Try clicking dialogue hitbox (Ancient event)
        var dialogueBtn = eventRoom.GetNodeOrNull<NButton>("%DialogueHitbox");
        if (dialogueBtn != null && dialogueBtn.Visible && dialogueBtn.IsEnabled)
        {
            MainFile.Logger.Info("[AutoSlay] Clicking Ancient event dialogue");
            dialogueBtn.EmitSignal(NClickableControl.SignalName.Released, dialogueBtn);
            return 0.5;
        }

        return 0.5;
    }
}
