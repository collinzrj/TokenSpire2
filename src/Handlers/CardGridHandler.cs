using Godot;
using MegaCrit.Sts2.Core.Nodes.Cards;
using MegaCrit.Sts2.Core.Nodes.Cards.Holders;
using MegaCrit.Sts2.Core.Nodes.CommonUi;

namespace TokenSpire2.Handlers;

/// <summary>
/// Handles two-phase card grid screens: DeckUpgrade, DeckTransform, DeckEnchant, DeckCardSelect.
/// Flow: select cards -> main confirm -> preview appears -> preview confirm -> screen closes.
/// Each call does one step, relying on the _Process tick loop to call again.
/// </summary>
public static class CardGridHandler
{
    // Known preview container node names across different screen types
    private static readonly string[] PreviewNames =
    {
        "%PreviewContainer",
        "%UpgradeSinglePreviewContainer",
        "%UpgradeMultiPreviewContainer",
        "%EnchantSinglePreviewContainer",
        "%EnchantMultiPreviewContainer",
    };

    private static int? _llmChoice;

    /// <summary>
    /// Set the LLM's chosen card index (1-based). Called before Handle() on the next tick.
    /// </summary>
    public static void SetLlmChoice(int choice) => _llmChoice = choice;

    /// <summary>
    /// Returns true if an LLM choice is pending (waiting to be applied by Handle()).
    /// </summary>
    public static bool HasPendingLlmChoice => _llmChoice.HasValue;

    public static double Handle(Node screen, System.Random rng)
    {
        if (!GodotObject.IsInstanceValid(screen)) return 0;

        // Phase 3: Preview visible — find and click the confirm inside it
        var visiblePreview = FindVisiblePreview(screen);
        if (visiblePreview != null)
        {
            var previewConfirm = visiblePreview.GetNodeOrNull<NConfirmButton>("Confirm")
                ?? visiblePreview.GetNodeOrNull<NConfirmButton>("%PreviewConfirm")
                ?? AutoSlayHelpers.FindFirst<NConfirmButton>(visiblePreview);
            if (previewConfirm?.IsEnabled == true)
            {
                MainFile.Logger.Info("[AutoSlay] Clicking preview confirm");
                previewConfirm.ForceClick();
                return 1.0;
            }
            // Preview visible but confirm not ready yet — wait
            return 0.3;
        }

        // Phase 2: Main confirm enabled (no preview yet) — click to trigger preview
        var mainConfirm = screen.GetNodeOrNull<NConfirmButton>("Confirm")
            ?? screen.GetNodeOrNull<NConfirmButton>("%Confirm");
        if (mainConfirm?.IsEnabled == true)
        {
            MainFile.Logger.Info("[AutoSlay] Clicking main confirm to show preview");
            mainConfirm.ForceClick();
            return 0.5;
        }

        // Phase 1: Select a card
        var cards = AutoSlayHelpers.FindAll<NGridCardHolder>(screen);
        if (cards.Count == 0) return 0.5;

        NGridCardHolder pick;
        if (_llmChoice.HasValue && _llmChoice.Value >= 1 && _llmChoice.Value <= cards.Count)
        {
            pick = cards[_llmChoice.Value - 1];
            MainFile.Logger.Info($"[AutoSlay/LLM] Selecting card {_llmChoice.Value} in grid ({cards.Count} available)");
            _llmChoice = null;
        }
        else
        {
            pick = cards[rng.Next(cards.Count)];
            MainFile.Logger.Info($"[AutoSlay] Selecting random card in grid ({cards.Count} available)");
            _llmChoice = null;
        }

        var grid = AutoSlayHelpers.FindFirst<NCardGrid>(screen);
        if (grid != null)
        {
            MainFile.Logger.Info($"[AutoSlay] Emitting HolderPressed for {pick.CardModel?.Id.Entry ?? "?"}");
            grid.EmitSignal(NCardGrid.SignalName.HolderPressed, pick);
        }
        return 0.3;
    }

    private static Control? FindVisiblePreview(Node screen)
    {
        foreach (var name in PreviewNames)
        {
            var container = screen.GetNodeOrNull<Control>(name);
            if (container?.Visible == true)
                return container;
        }
        return null;
    }
}
