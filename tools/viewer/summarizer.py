"""LLM-based thinking summarizer."""

import json
import urllib.request


class LLMSummarizer:
    SYSTEM_PROMPT = "你是一个正在直播玩游戏的AI主播，用幽默吐槽的口吻总结自己的思考过程。只总结新增内容，不要重复。每次限20token。直接输出，不加前缀"

    def __init__(self, api_url: str, api_key: str, model: str):
        url = api_url.rstrip("/")
        if not url.endswith("/chat/completions"):
            url += "/chat/completions"
        self.endpoint = url
        self.api_key = api_key
        self.model = model

    def call(self, user_content: str) -> str | None:
        request_body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": 30,
            "stream": True,
            "enable_thinking": False,
        }
        if "openrouter" in self.endpoint:
            del request_body["enable_thinking"]
            request_body["reasoning"] = {"enabled": False}

        body = json.dumps(request_body).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint, data=body,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        try:
            result = ""
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
            if "data: " in raw:
                for line in raw.split("\n"):
                    line = line.strip()
                    if not line.startswith("data: "):
                        continue
                    if line[6:].strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(line[6:])
                        token = chunk["choices"][0].get("delta", {}).get("content", "")
                        if token:
                            result += token
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
            else:
                data = json.loads(raw)
                result = data["choices"][0]["message"]["content"]
            print(f"[Summarizer] -> {result}")
            return result
        except Exception as e:
            import traceback
            print(f"[Summarizer] Error: {e}")
            traceback.print_exc()
            return None
