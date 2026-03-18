using System.Collections.Generic;
using System.Linq;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Models;

namespace DemoMod.Handlers;

/// <summary>
/// Potion target resolution matching the official CombatRoomHandler.GetPotionTarget logic.
/// </summary>
public static class PotionHelper
{
    public static Creature? GetTarget(PotionModel potion, CombatState? combatState, System.Random? rng = null)
    {
        if (combatState == null) return null;
        return potion.TargetType switch
        {
            TargetType.AnyEnemy => RandomEnemy(combatState, rng),
            TargetType.AnyAlly or TargetType.AnyPlayer or TargetType.Self =>
                combatState.PlayerCreatures.FirstOrDefault(c => c.IsAlive),
            _ => null,
        };
    }

    private static Creature? RandomEnemy(CombatState combatState, System.Random? rng)
    {
        var enemies = combatState.HittableEnemies.ToList();
        if (enemies.Count == 0) return null;
        return enemies[rng?.Next(enemies.Count) ?? 0];
    }
}
