using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Runs;

namespace TokenSpire2.Llm;

public static class RunSummaryLogger
{
    private static bool _logged;
    private static string? _lastRunStats;

    /// <summary>High-level stats from the last completed run, for injection into reflection prompt.</summary>
    public static string? LastRunStats => _lastRunStats;

    public static void Reset()
    {
        _logged = false;
        // Don't clear _lastRunStats here — it's needed until reflection is done
    }

    public static void TryLog(LlmClient? llm)
    {
        if (_logged) return;
        _logged = true;

        try
        {
            var runState = RunManager.Instance?.DebugOnlyGetState();
            if (runState == null) return;

            var history = RunManager.Instance.History;
            var player = LocalContext.GetMe(runState);

            bool win = runState.CurrentRoom?.IsVictoryRoom ?? false;
            if (history != null) win = history.Win;

            var summary = new RunSummary
            {
                Timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"),
                Model = llm?.Model ?? "none",
                Result = win ? "victory" : "defeat",
                Seed = runState.Rng?.StringSeed ?? "",
                AscensionLevel = runState.AscensionLevel,
                Floor = runState.TotalFloor,
                Character = player?.Character?.Id.Entry ?? "Unknown",
                Hp = player != null ? $"{player.Creature.CurrentHp}/{player.Creature.MaxHp}" : "?",
                Gold = player?.Gold ?? 0,
                Deck = player?.Deck?.Cards?.Select(c => c.Id.Entry).ToList() ?? new List<string>(),
                Relics = player?.Relics?.Select(r => r.Id.Entry).ToList() ?? new List<string>(),
                Potions = player?.Potions?.Where(p => !p.IsQueued).Select(p => p.Id.Entry).ToList() ?? new List<string>(),
            };

            if (history != null)
            {
                summary.RunTimeSeconds = history.RunTime;
                if (history.KilledByEncounter != MegaCrit.Sts2.Core.Models.ModelId.none)
                    summary.KilledBy = history.KilledByEncounter.Entry;
                else if (history.KilledByEvent != MegaCrit.Sts2.Core.Models.ModelId.none)
                    summary.KilledBy = history.KilledByEvent.Entry;
            }

            // Use same session path as LLM log, but with .json extension
            string path;
            if (llm?.LogPath != null)
            {
                path = Path.ChangeExtension(llm.LogPath, ".json");
            }
            else
            {
                var asmDir = Path.GetDirectoryName(
                    System.Reflection.Assembly.GetExecutingAssembly().Location) ?? ".";
                path = Path.Combine(asmDir, $"run_summary_{DateTime.Now:yyyyMMdd_HHmmss}.json");
            }

            // Append to existing file if multiple runs in one session
            var runs = new List<RunSummary>();
            if (File.Exists(path))
            {
                try
                {
                    var existing = File.ReadAllText(path);
                    var parsed = JsonSerializer.Deserialize<List<RunSummary>>(existing);
                    if (parsed != null) runs = parsed;
                }
                catch { /* start fresh if corrupt */ }
            }
            runs.Add(summary);

            var json = JsonSerializer.Serialize(runs, new JsonSerializerOptions
            {
                WriteIndented = true,
                DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
            });
            File.WriteAllText(path, json);
            MainFile.Logger.Info($"[AutoSlay] Run summary saved to {path}");

            // Build human-readable stats for the reflection prompt
            var sb = new System.Text.StringBuilder();
            sb.AppendLine($"Result: {summary.Result} | Floor: {summary.Floor} | HP: {summary.Hp} | Gold: {summary.Gold}");
            sb.AppendLine($"Character: {summary.Character} | Ascension: {summary.AscensionLevel}");
            if (!string.IsNullOrEmpty(summary.KilledBy))
                sb.AppendLine($"Killed by: {summary.KilledBy}");
            sb.AppendLine($"Run time: {TimeSpan.FromSeconds(summary.RunTimeSeconds):mm\\:ss}");
            sb.AppendLine($"Final deck ({summary.Deck.Count}): {string.Join(", ", summary.Deck)}");
            sb.AppendLine($"Relics: {string.Join(", ", summary.Relics)}");
            if (summary.Potions.Count > 0)
                sb.AppendLine($"Unused potions: {string.Join(", ", summary.Potions)}");
            _lastRunStats = sb.ToString();
        }
        catch (Exception ex)
        {
            MainFile.Logger.Info($"[AutoSlay] Failed to save run summary: {ex.Message}");
        }
    }

    private class RunSummary
    {
        [JsonPropertyName("timestamp")]
        public string Timestamp { get; set; } = "";

        [JsonPropertyName("model")]
        public string Model { get; set; } = "";

        [JsonPropertyName("result")]
        public string Result { get; set; } = "";

        [JsonPropertyName("seed")]
        public string Seed { get; set; } = "";

        [JsonPropertyName("character")]
        public string Character { get; set; } = "";

        [JsonPropertyName("ascension_level")]
        public int AscensionLevel { get; set; }

        [JsonPropertyName("floor")]
        public int Floor { get; set; }

        [JsonPropertyName("hp")]
        public string Hp { get; set; } = "";

        [JsonPropertyName("gold")]
        public int Gold { get; set; }

        [JsonPropertyName("run_time_seconds")]
        public float RunTimeSeconds { get; set; }

        [JsonPropertyName("killed_by")]
        public string? KilledBy { get; set; }

        [JsonPropertyName("deck")]
        public List<string> Deck { get; set; } = new();

        [JsonPropertyName("relics")]
        public List<string> Relics { get; set; } = new();

        [JsonPropertyName("potions")]
        public List<string> Potions { get; set; } = new();
    }
}
