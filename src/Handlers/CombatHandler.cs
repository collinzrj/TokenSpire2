using System.Collections.Generic;
using System.Linq;
using Godot;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Runs;

namespace DemoMod.Handlers;

public static class CombatHandler
{
    private static bool _hpBoosted;
    private static bool _potionsUsed;
    private static readonly HashSet<CardModel> _attemptedCards = new();

    public static void OnCombatEnded()
    {
        _hpBoosted = false;
        _potionsUsed = false;
        _attemptedCards.Clear();
    }

    public static void OnNonPlayPhase()
    {
        _attemptedCards.Clear();
    }

    public static void BoostHpIfNeeded()
    {
        if (_hpBoosted) return;
        var runState = RunManager.Instance?.DebugOnlyGetState();
        var player = runState != null ? LocalContext.GetMe(runState) : null;
        if (player?.Creature == null) return;

        player.Creature.SetMaxHpInternal(9999);
        player.Creature.SetCurrentHpInternal(9999);
        MainFile.Logger.Info("[AutoSlay] Boosted player HP to 9999.");
        _hpBoosted = true;
    }

    public static void UsePotionsIfNeeded(System.Random rng)
    {
        if (_potionsUsed) return;
        var cm = CombatManager.Instance;
        if (cm == null || !cm.IsInProgress || !cm.IsPlayPhase) return;

        var runState = RunManager.Instance?.DebugOnlyGetState();
        var player = runState != null ? LocalContext.GetMe(runState) : null;
        if (player == null) return;

        var potions = player.Potions.ToList();
        if (potions.Count == 0) { _potionsUsed = true; return; }

        var combatState = player.Creature.CombatState;

        foreach (var potion in potions)
        {
            if (!cm.IsPlayPhase || !cm.IsInProgress) break;

            Creature? target = PotionHelper.GetTarget(potion, combatState, rng);
            if (target == null && potion.TargetType.IsSingleTarget())
            {
                MainFile.Logger.Info($"[AutoSlay] Skipping potion {potion.Id.Entry}: no valid target");
                continue;
            }

            MainFile.Logger.Info($"[AutoSlay] Using potion: {potion.Id.Entry}");
            potion.EnqueueManualUse(target);
        }
        _potionsUsed = true;
    }

    public static double PlayOneCard(CombatManager cm, System.Random rng)
    {
        var runState = RunManager.Instance?.DebugOnlyGetState();
        var player = runState != null ? LocalContext.GetMe(runState) : null;
        if (player == null) return 0;

        var playable = PileType.Hand.GetPile(player).Cards
            .Where(c => !_attemptedCards.Contains(c) && c.CanPlay(out _, out _))
            .ToList();

        if (playable.Count == 0)
        {
            if (cm.IsPlayPhase && cm.IsInProgress)
            {
                _attemptedCards.Clear();
                PlayerCmd.EndTurn(player, canBackOut: false);
                return 0.5;
            }
            return 0;
        }

        var card = playable[rng.Next(playable.Count)];
        _attemptedCards.Add(card);

        Creature? target = null;
        if (card.TargetType == TargetType.AnyEnemy)
        {
            var enemies = card.CombatState?.HittableEnemies.ToList() ?? new List<Creature>();
            if (enemies.Count > 0) target = enemies[rng.Next(enemies.Count)];
        }

        card.TryManualPlay(target);
        return 0.4;
    }

}
