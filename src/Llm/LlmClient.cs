using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Threading.Tasks;

namespace TokenSpire2.Llm;

public class LlmClient
{
    private readonly HttpClient _http;
    private readonly string _endpoint;
    private readonly string _model;
    private readonly bool _thinking;
    private readonly int _thinkingBudget;
    private readonly List<Message> _history = new();
    private readonly List<List<Message>> _allRuns = new();
    private readonly string _logPath;
    private readonly string _memoryPath;
    private readonly string _historyPath;
    private string _memory = "";

    public string LogPath => _logPath;
    public string Model => _model;
    public string Memory => _memory;

    public LlmClient(LlmConfig config)
    {
        _http = new HttpClient();
        _http.DefaultRequestHeaders.Add("Authorization", $"Bearer {config.Key}");
        _http.Timeout = TimeSpan.FromSeconds(120);

        var url = config.Url.TrimEnd('/');
        if (!url.EndsWith("/chat/completions"))
            url += "/chat/completions";
        _endpoint = url;
        _model = config.Model;
        _thinking = config.Thinking;
        _thinkingBudget = config.ThinkingBudget;

        // Set up files next to mod DLL — memory file uses same timestamp as log
        var asmDir = Path.GetDirectoryName(
            System.Reflection.Assembly.GetExecutingAssembly().Location) ?? ".";
        var ts = DateTime.Now.ToString("yyyyMMdd_HHmmss");
        _logPath = Path.Combine(asmDir, $"llm_log_{ts}.txt");
        _memoryPath = Path.Combine(asmDir, $"llm_memory_{ts}.md");
        _historyPath = Path.Combine(asmDir, $"llm_history_{ts}.json");

        LogToFile($"\n=== LLM Session Started {DateTime.Now:yyyy-MM-dd HH:mm:ss} ===");
        LogToFile($"Endpoint: {_endpoint}");
        LogToFile($"Model: {_model}");
        LogToFile($"Memory: {_memoryPath}");
        LogToFile($"\n[SYSTEM PROMPT]\n{BuildSystemPrompt()}\n");
    }

    public int MessageCount => _history.Count;

    /// <summary>Archive current run's conversation and clear history for next run.</summary>
    public void ResetForNewRun()
    {
        if (_history.Count > 0)
        {
            _allRuns.Add(new List<Message>(_history));
            SaveHistory();
        }
        _history.Clear();
        LogToFile($"\n=== New Run — History Cleared ({DateTime.Now:HH:mm:ss}) ===");
        if (!string.IsNullOrEmpty(_memory))
            LogToFile($"[MEMORY CARRIED OVER]\n{_memory}");
        MainFile.Logger.Info($"[AutoSlay/LLM] Conversation reset for new run ({(_memory.Length > 0 ? "with" : "no")} memory)");
    }

    private static readonly JsonSerializerOptions _jsonOpts = new()
    {
        WriteIndented = true,
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
        DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull
    };

    private void SaveHistory()
    {
        try
        {
            var data = SerializeAllRuns();
            File.WriteAllText(_historyPath, JsonSerializer.Serialize(data, _jsonOpts));
            MainFile.Logger.Info($"[AutoSlay/LLM] History saved ({_allRuns.Count} runs) to {_historyPath}");
        }
        catch (Exception ex)
        {
            MainFile.Logger.Info($"[AutoSlay/LLM] Failed to save history: {ex.Message}");
        }
    }

    private void SaveLive()
    {
        try
        {
            var data = SerializeAllRuns();
            // Append current (in-progress) run
            data.Add(SerializeRun(_history));
            File.WriteAllText(_historyPath, JsonSerializer.Serialize(data, _jsonOpts));
        }
        catch { /* ignore — live updates are best-effort */ }
    }

    private List<object> SerializeAllRuns()
    {
        var data = new List<object>();
        foreach (var run in _allRuns)
            data.Add(SerializeRun(run));
        return data;
    }

    private static object SerializeRun(List<Message> messages)
    {
        var msgs = new List<object>();
        foreach (var msg in messages)
        {
            msgs.Add(new
            {
                role = msg.role,
                content = msg.content,
                thinking = msg.thinking,
                context = msg.context,
                timestamp = msg.timestamp
            });
        }
        return new { messages = msgs };
    }

    /// <summary>Save reflection/lessons as memory for future runs.</summary>
    public void SaveMemory(string text)
    {
        _memory = text;
        try
        {
            File.WriteAllText(_memoryPath, $"# LLM Memory\nUpdated: {DateTime.Now:yyyy-MM-dd HH:mm:ss}\n\n{text}\n");
            LogToFile($"[MEMORY SAVED]\n{text}");
            MainFile.Logger.Info("[AutoSlay/LLM] Memory saved to file");
        }
        catch (Exception ex)
        {
            MainFile.Logger.Info($"[AutoSlay/LLM] Failed to save memory: {ex.Message}");
        }
    }

    private string? _currentContext;

    public async Task<string> SendAsync(string userMessage, string? context = null)
    {
        _currentContext = context;
        _history.Add(new Message("user", userMessage, context: context, timestamp: DateTime.Now.ToString("o")));
        SaveLive();

        // Build messages array: system (with memory) + history
        var messages = new List<object>
        {
            new { role = "system", content = BuildSystemPrompt() }
        };
        foreach (var msg in _history)
            messages.Add(new { role = msg.role, content = msg.content });

        var requestBody = new Dictionary<string, object>
        {
            ["model"] = _model,
            ["messages"] = messages,
            ["stream"] = true,
        };
        ApplyReasoningParams(requestBody);

        var json = JsonSerializer.Serialize(requestBody);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        LogToFile($"\n--- Turn {_history.Count / 2} ({DateTime.Now:HH:mm:ss}) ---");
        LogToFile($"[USER]\n{userMessage}");
        MainFile.Logger.Info($"[AutoSlay/LLM] Sending request ({_history.Count} messages)...");

        var response = await _http.SendAsync(
            new HttpRequestMessage(HttpMethod.Post, _endpoint) { Content = content },
            HttpCompletionOption.ResponseHeadersRead).ConfigureAwait(false);

        if (!response.IsSuccessStatusCode)
        {
            var errorBody = await response.Content.ReadAsStringAsync().ConfigureAwait(false);
            MainFile.Logger.Info($"[AutoSlay/LLM] API error {response.StatusCode}: {errorBody}");
            LogToFile($"[ERROR] {response.StatusCode}: {errorBody}");
            _history.RemoveAt(_history.Count - 1);
            throw new Exception($"LLM API error: {response.StatusCode}");
        }

        // Read SSE stream on background thread to avoid blocking the game
        var assistantMessage = new StringBuilder();
        var thinkingContent = new StringBuilder();
        using var stream = await response.Content.ReadAsStreamAsync().ConfigureAwait(false);
        using var reader = new System.IO.StreamReader(stream);
        while (!reader.EndOfStream)
        {
            var line = await reader.ReadLineAsync().ConfigureAwait(false);
            if (line == null) break;
            if (!line.StartsWith("data: ")) continue;
            var data = line.Substring(6).Trim();
            if (data == "[DONE]") break;

            try
            {
                var chunk = JsonSerializer.Deserialize<JsonElement>(data);
                if (!chunk.TryGetProperty("choices", out var choices)) continue;
                foreach (var choice in choices.EnumerateArray())
                {
                    if (!choice.TryGetProperty("delta", out var delta)) continue;

                    // Reasoning content (thinking)
                    if (delta.TryGetProperty("reasoning", out var rp) && rp.ValueKind == JsonValueKind.String)
                        thinkingContent.Append(rp.GetString());
                    else if (delta.TryGetProperty("reasoning_content", out var rc) && rc.ValueKind == JsonValueKind.String)
                        thinkingContent.Append(rc.GetString());

                    // Main content
                    if (delta.TryGetProperty("content", out var cp) && cp.ValueKind == JsonValueKind.String)
                        assistantMessage.Append(cp.GetString());
                }
            }
            catch { /* skip malformed chunks */ }
        }

        var result = assistantMessage.ToString();
        var thinking = thinkingContent.ToString();
        _history.Add(new Message("assistant", result,
            thinking: string.IsNullOrEmpty(thinking) ? null : thinking,
            context: _currentContext,
            timestamp: DateTime.Now.ToString("o")));
        SaveLive();

        if (!string.IsNullOrEmpty(thinking))
            LogToFile($"[THINKING]\n{thinking}");
        LogToFile($"[ASSISTANT]\n{result}");
        MainFile.Logger.Info($"[AutoSlay/LLM] Response: {result.Replace("\n", " | ")}");
        return result;
    }

    private void ApplyReasoningParams(Dictionary<string, object> body)
    {
        if (_thinking)
        {
            body["reasoning"] = new { max_tokens = _thinkingBudget };
            // Claude needs Anthropic provider routing (Bedrock doesn't support thinking)
            var m = _model.ToLowerInvariant();
            if (m.Contains("claude") || m.Contains("anthropic"))
                body["provider"] = new { order = new[] { "Anthropic" } };
        }
        else
        {
            body["reasoning"] = new { enabled = false };
        }
    }

    private string BuildSystemPrompt()
    {
        var prompt = PromptStrings.Get("SystemPrompt");
        if (!string.IsNullOrEmpty(_memory))
            prompt += "\n\n=== YOUR MEMORY FILE ===\n" + _memory;
        return prompt;
    }

    private void LogToFile(string text)
    {
        try { File.AppendAllText(_logPath, text + "\n"); }
        catch { /* ignore file write errors */ }
    }

    public record Message(string role, string content, string? thinking = null, string? context = null, string? timestamp = null);
}
