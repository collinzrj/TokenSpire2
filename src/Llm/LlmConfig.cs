using System.IO;
using System.Text.Json;

namespace TokenSpire2.Llm;

public class LlmConfig
{
    public string Url { get; set; } = "";
    public string Key { get; set; } = "";
    public string Model { get; set; } = "gpt-4o";
    public string Lang { get; set; } = "zh";

    public static LlmConfig? Load()
    {
        // Look for config file next to mod DLL
        var asmDir = Path.GetDirectoryName(
            System.Reflection.Assembly.GetExecutingAssembly().Location);
        string? path = asmDir != null ? Path.Combine(asmDir, "llm_config.json") : null;

        if (string.IsNullOrEmpty(path) || !File.Exists(path))
            return null;

        try
        {
            var json = File.ReadAllText(path);
            var config = JsonSerializer.Deserialize<LlmConfig>(json, new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true
            });
            if (config == null || string.IsNullOrEmpty(config.Url) || string.IsNullOrEmpty(config.Key))
                return null;
            PromptStrings.Language = config.Lang?.ToLower() == "en" ? PromptLang.En : PromptLang.Zh;
            MainFile.Logger.Info($"[AutoSlay] LLM config loaded from {path}, model={config.Model}, lang={config.Lang}");
            return config;
        }
        catch (System.Exception ex)
        {
            MainFile.Logger.Info($"[AutoSlay] Failed to load LLM config: {ex.Message}");
            return null;
        }
    }
}
