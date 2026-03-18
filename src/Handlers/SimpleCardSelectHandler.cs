using Godot;
using MegaCrit.Sts2.Core.Nodes.Cards;
using MegaCrit.Sts2.Core.Nodes.Cards.Holders;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.Screens.CardSelection;

namespace DemoMod.Handlers;

public static class SimpleCardSelectHandler
{
    private static int? _llmChoice;

    public static void SetLlmChoice(int choice) => _llmChoice = choice;
    public static bool HasPendingLlmChoice => _llmChoice.HasValue;

    public static double Handle(NSimpleCardSelectScreen screen, System.Random rng)
    {
        if (!GodotObject.IsInstanceValid(screen)) return 0;

        // If confirm is available, click it
        var confirm = screen.GetNodeOrNull<NConfirmButton>("%Confirm");
        if (confirm?.IsEnabled == true)
        {
            MainFile.Logger.Info("[AutoSlay] Clicking simple card select confirm");
            confirm.ForceClick();
            return 1.0;
        }

        var cards = AutoSlayHelpers.FindAll<NGridCardHolder>(screen);
        if (cards.Count == 0) return 0.5;

        NGridCardHolder pick;
        if (_llmChoice.HasValue && _llmChoice.Value >= 1 && _llmChoice.Value <= cards.Count)
        {
            pick = cards[_llmChoice.Value - 1];
            MainFile.Logger.Info($"[AutoSlay/LLM] Selecting card {_llmChoice.Value} in simple select ({cards.Count} available)");
            _llmChoice = null;
        }
        else
        {
            pick = cards[rng.Next(cards.Count)];
            MainFile.Logger.Info($"[AutoSlay] Selecting random card in simple select ({cards.Count} available)");
            _llmChoice = null;
        }

        var grid = AutoSlayHelpers.FindFirst<NCardGrid>(screen);
        if (grid != null)
        {
            MainFile.Logger.Info($"[AutoSlay] Emitting HolderPressed for {pick.CardModel?.Id.Entry ?? "?"}");
            grid.EmitSignal(NCardGrid.SignalName.HolderPressed, pick);
        }
        return 0.5;
    }
}
