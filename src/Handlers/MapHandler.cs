using System.Linq;
using MegaCrit.Sts2.Core.Nodes.Screens.Map;

namespace TokenSpire2.Handlers;

public static class MapHandler
{
    public static double Handle(NMapScreen mapScreen, System.Random rng)
    {
        var points = AutoSlayHelpers.FindAll<NMapPoint>(mapScreen)
            .Where(p => p.IsEnabled)
            .ToList();

        MainFile.Logger.Info($"[AutoSlay] Map open, {points.Count} enabled point(s)");

        if (points.Count > 0)
        {
            var point = points[rng.Next(points.Count)];
            MainFile.Logger.Info($"[AutoSlay] Selecting map point at ({point.Point.coord.row},{point.Point.coord.col})");
            mapScreen.OnMapPointSelectedLocally(point);
        }

        return 2.0;
    }
}
