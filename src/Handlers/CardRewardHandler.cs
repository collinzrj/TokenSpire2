using Godot;
using MegaCrit.Sts2.Core.Nodes.Cards.Holders;
using MegaCrit.Sts2.Core.Nodes.Screens.CardSelection;

namespace DemoMod.Handlers;

public static class CardRewardHandler
{
    public static double Handle(NCardRewardSelectionScreen screen, System.Random rng)
    {
        if (!GodotObject.IsInstanceValid(screen)) return 0;
        var holders = AutoSlayHelpers.FindAll<NCardHolder>(screen);
        if (holders.Count == 0) return 0.5;
        var pick = holders[rng.Next(holders.Count)];
        pick.EmitSignal(NCardHolder.SignalName.Pressed, pick);
        return 1.5;
    }
}
