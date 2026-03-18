using Godot;
using MegaCrit.Sts2.Core.Nodes.Screens.GameOverScreen;

namespace DemoMod.Handlers;

public static class GameOverHandler
{
    public static double Handle(NGameOverScreen screen)
    {
        if (!GodotObject.IsInstanceValid(screen)) return 0;

        // Try main menu button first (appears after continue animation)
        var mainMenuBtn = AutoSlayHelpers.FindFirst<NReturnToMainMenuButton>(screen);
        if (mainMenuBtn != null && mainMenuBtn.Visible && mainMenuBtn.IsEnabled)
        {
            MainFile.Logger.Info("[AutoSlay] Clicking return to main menu");
            mainMenuBtn.ForceClick();
            return 2.0;
        }

        // Try continue button
        var continueBtn = AutoSlayHelpers.FindFirst<NGameOverContinueButton>(screen);
        if (continueBtn?.IsEnabled == true)
        {
            MainFile.Logger.Info("[AutoSlay] Clicking game over continue");
            continueBtn.ForceClick();
            return 2.0;
        }

        // Waiting for animation
        return 1.0;
    }
}
