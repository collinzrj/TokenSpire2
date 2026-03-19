using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using TokenSpire2.Llm;
using MegaCrit.Sts2.Core.Entities.CardRewardAlternatives;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.TestSupport;

namespace TokenSpire2;

public class AutoSlayCardSelector : ICardSelector
{
    private readonly System.Random _rng;
    private readonly LlmClient? _llm;
    public bool IsPendingLlm { get; private set; }

    public AutoSlayCardSelector(System.Random rng, LlmClient? llm = null)
    {
        _rng = rng;
        _llm = llm;
    }

    public async Task<IEnumerable<CardModel>> GetSelectedCards(IEnumerable<CardModel> options, int minSelect, int maxSelect)
    {
        IsPendingLlm = true;
        try { return await GetSelectedCardsInner(options, minSelect, maxSelect); }
        finally { IsPendingLlm = false; }
    }

    private async Task<IEnumerable<CardModel>> GetSelectedCardsInner(IEnumerable<CardModel> options, int minSelect, int maxSelect)
    {
        var list = options.ToList();
        if (list.Count == 0)
            return Array.Empty<CardModel>();

        int count = Math.Min(maxSelect, list.Count);
        if (count < minSelect)
            count = Math.Min(minSelect, list.Count);

        if (_llm != null && list.Count > 1)
        {
            try
            {
                var sb = new StringBuilder();
                sb.AppendLine(Llm.PromptStrings.Get("SelectCards", count));
                bool inCombat = NCombatRoom.Instance != null;
                sb.AppendLine(inCombat
                    ? Llm.PromptStrings.Get("SelectCardsIntro", count)
                    : Llm.PromptStrings.Get("SelectCardsNonCombat", count));
                for (int i = 0; i < list.Count; i++)
                {
                    var card = list[i];
                    var cost = card.EnergyCost.CostsX ? "X" : card.EnergyCost.Canonical.ToString();
                    var desc = Llm.GameStateSerializer.SafeGetCardDescription(card);
                    sb.AppendLine($"  [{i + 1}] {card.Id.Entry} ({card.Type}, {cost} {Llm.PromptStrings.Get("Energy")}) — {desc}");
                }
                sb.AppendLine();
                sb.AppendLine(Llm.PromptStrings.Get("ReplyChooseCount", count));

                MainFile.Logger.Info($"[AutoSlay/LLM] Asking LLM for card selection ({list.Count} options, pick {count})");
                var response = await _llm.SendAsync(sb.ToString());

                var chosen = ParseChoices(response, list.Count, count);
                if (chosen.Count > 0)
                {
                    var result = chosen.Select(idx => list[idx - 1]).ToList();
                    MainFile.Logger.Info($"[AutoSlay/LLM] Card selection: {string.Join(", ", result.Select(c => c.Id.Entry))}");
                    return result;
                }
            }
            catch (Exception ex)
            {
                MainFile.Logger.Info($"[AutoSlay/LLM] Card selection failed: {ex.Message}, falling back to random");
            }
        }

        // Fallback: random
        for (int i = list.Count - 1; i > 0; i--)
        {
            int j = _rng.Next(i + 1);
            (list[i], list[j]) = (list[j], list[i]);
        }

        MainFile.Logger.Info($"[AutoSlay] Auto-selected {count} card(s) randomly");
        return list.Take(count);
    }

    private static List<int> ParseChoices(string response, int max, int needed)
    {
        var choices = new List<int>();
        foreach (var line in response.Split('\n'))
        {
            var trimmed = line.Trim().ToUpper();
            if (trimmed.StartsWith("CHOOSE") && trimmed.Length > 6)
            {
                if (int.TryParse(trimmed.Substring(6).Trim(), out int idx) && idx >= 1 && idx <= max)
                    choices.Add(idx);
            }
        }
        if (choices.Count >= needed)
            return choices.Take(needed).ToList();
        return choices;
    }

    public CardModel? GetSelectedCardReward(IReadOnlyList<CardCreationResult> options, IReadOnlyList<CardRewardAlternative> alternatives)
    {
        if (options.Count == 0) return null;
        return options[_rng.Next(options.Count)].Card;
    }
}
