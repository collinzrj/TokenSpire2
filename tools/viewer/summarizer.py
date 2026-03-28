"""LLM-based two-phase summarizer for game narration."""

import json
import urllib.request

SCENE_SUFFIX = "\n\n---\n你是一个游戏AI主播，正在直播中思考下一步操作。用幽默吐槽的口吻分析当前局面，不要给出最终决策，保持悬念感。限50字，必须用中文。"
DECISION_SUFFIX = "\n\n---\n你是一个游戏AI主播。你刚才分析了局面，现在你已经进行思考并做出了决策。用幽默吐槽的口吻宣布你的操作并解释理由。限50字，必须用中文。"


class LLMSummarizer:
    def __init__(self, api_url: str, api_key: str, model: str):
        url = api_url.rstrip("/")
        if not url.endswith("/chat/completions"):
            url += "/chat/completions"
        self.endpoint = url
        self.api_key = api_key
        self.model = model

    def call(self, user_content: str) -> str | None:
        return self.call_with_history([], user_content)

    def call_with_history(self, history: list, user_content: str, phase: str = "scene") -> str | None:
        """
        Phase 1 (scene): messages = [user(query + SCENE_SUFFIX)]
        Phase 2 (summary): messages = [user(query + SCENE_SUFFIX), assistant(scene), user(cot+decision + DECISION_SUFFIX)]
        """
        suffix = DECISION_SUFFIX if phase == "summary" else SCENE_SUFFIX
        messages = list(history)
        messages.append({"role": "user", "content": user_content + suffix})

        request_body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 50,
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
            print(f"[Summarizer] request: {json.dumps(json.loads(body), ensure_ascii=False)}")
            print(f"[Summarizer] -> {result}")
            return result
        except Exception as e:
            import traceback
            print(f"[Summarizer] Error: {e}")
            traceback.print_exc()
            return None
