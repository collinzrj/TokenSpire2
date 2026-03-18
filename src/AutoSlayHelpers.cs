using System.Collections.Generic;
using Godot;

namespace DemoMod;

public static class AutoSlayHelpers
{
    public static List<T> FindAll<T>(Node start) where T : Node
    {
        var result = new List<T>();
        FindAllRecursive(start, result);
        return result;
    }

    private static void FindAllRecursive<T>(Node node, List<T> found) where T : Node
    {
        if (!GodotObject.IsInstanceValid(node)) return;
        if (node is T item) found.Add(item);
        foreach (var child in node.GetChildren())
            FindAllRecursive(child, found);
    }

    public static T? FindFirst<T>(Node start) where T : Node
    {
        if (!GodotObject.IsInstanceValid(start)) return null;
        if (start is T result) return result;
        foreach (var child in start.GetChildren())
        {
            var found = FindFirst<T>(child);
            if (found != null) return found;
        }
        return null;
    }
}
