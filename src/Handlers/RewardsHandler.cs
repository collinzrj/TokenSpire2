using System.Collections.Generic;
using System.Linq;
using Godot;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.Rewards;
using MegaCrit.Sts2.Core.Nodes.Screens;
using MegaCrit.Sts2.Core.Nodes.Screens.Overlays;
using MegaCrit.Sts2.Core.Rewards;
using MegaCrit.Sts2.Core.Runs;

namespace TokenSpire2.Handlers;

public static class RewardsHandler
{
    private static readonly HashSet<ulong> _triedRewards = new();

    public static void ClearTried() => _triedRewards.Clear();

    public static double Handle(NRewardsScreen screen)
    {
        if (!GodotObject.IsInstanceValid(screen)) return 0;

        // Skip potion rewards if no open slots (like original)
        bool hasPotionSlots = false;
        var runState = RunManager.Instance?.DebugOnlyGetState();
        if (runState != null)
        {
            var player = LocalContext.GetMe(runState);
            hasPotionSlots = player?.HasOpenPotionSlots ?? false;
        }

        var allBtns = AutoSlayHelpers.FindAll<NRewardButton>(screen);
        var btn = allBtns.FirstOrDefault(b =>
            b.IsEnabled
            && !_triedRewards.Contains(b.GetInstanceId())
            && (b.Reward is not PotionReward || hasPotionSlots));

        if (btn != null)
        {
            MainFile.Logger.Info($"[AutoSlay] Clicking reward button: {btn.Reward?.GetType().Name ?? "unknown"} (enabled={allBtns.Count(b => b.IsEnabled)}, tried={_triedRewards.Count})");
            _triedRewards.Add(btn.GetInstanceId());
            btn.ForceClick();
            return 1.0;
        }

        var proceed = AutoSlayHelpers.FindFirst<NProceedButton>(screen);
        if (proceed?.IsEnabled == true)
        {
            _triedRewards.Clear();
            proceed.ForceClick();
            return 1.0;
        }

        // Proceed stuck — force remove
        MainFile.Logger.Info("[AutoSlay] Proceed stuck, force-removing rewards overlay");
        _triedRewards.Clear();
        NOverlayStack.Instance?.Remove(screen);
        return 1.0;
    }
}
