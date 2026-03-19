using System.Linq;
using System.Threading.Tasks;
using Godot;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Nodes.Screens.Shops;

namespace TokenSpire2.Handlers;

public static class ShopHandler
{
    public static async Task HandleAsync(NMerchantRoom room, System.Random rng)
    {
        if (!GodotObject.IsInstanceValid(room)) return;
        room.OpenInventory();
        await Task.Delay(500);

        int attempts = 0;
        while (attempts++ < 50 && GodotObject.IsInstanceValid(room))
        {
            var slots = room.Inventory.GetAllSlots()
                .Where(s => s is not NMerchantCardRemoval
                         && s.Entry.IsStocked
                         && s.Entry.EnoughGold)
                .ToList();
            if (slots.Count == 0) break;

            await slots[rng.Next(slots.Count)].Entry.OnTryPurchaseWrapper(
                room.Inventory.Inventory);
            await Task.Delay(300);
        }

        if (!GodotObject.IsInstanceValid(room)) return;
        AutoSlayHelpers.FindFirst<NBackButton>(room)?.ForceClick();
        await Task.Delay(300);
        if (GodotObject.IsInstanceValid(room))
            room.ProceedButton?.ForceClick();
    }
}
