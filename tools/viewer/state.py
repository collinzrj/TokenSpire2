"""Enriched state manager — merges game history with summaries and persists to disk."""

import json
import os
import threading

from .config import enriched_path_for


class EnrichedState:
    """
    Reads game history, enriches with summaries, persists to disk.

    Enriched format per assistant message:
        {
            "role": "assistant",
            "content": "PLAY 3 -> A ...",
            "cot": "raw thinking...",
            "summary": ["chunk1", "chunk2", ...],
            "context": "combat",
            "timestamp": "..."
        }
    """

    def __init__(self, summarizer=None):
        self._lock = threading.Lock()
        self._raw_json = ""
        self._current_path = ""
        self._enriched_path = ""
        self._enriched = []
        self._summarizer = summarizer
        self._sent_len = {}  # (run_idx, msg_idx) -> chars of cot already summarized

    def get_enriched_path(self) -> str:
        with self._lock:
            return self._enriched_path

    def update_from_file(self, path: str | None):
        if not path:
            return
        if path != self._current_path:
            with self._lock:
                self._current_path = path
                self._enriched_path = enriched_path_for(path)
                self._raw_json = ""
                self._sent_len = {}
                if os.path.isfile(self._enriched_path):
                    try:
                        with open(self._enriched_path, "r", encoding="utf-8") as f:
                            self._enriched = json.load(f)
                        for ri, run in enumerate(self._enriched):
                            for mi, msg in enumerate(run.get("messages", [])):
                                if msg.get("summary") and msg.get("cot"):
                                    self._sent_len[(ri, mi)] = len(msg["cot"])
                        print(f"[State] Loaded existing enriched file: {os.path.basename(self._enriched_path)}")
                    except Exception:
                        self._enriched = []
                else:
                    self._enriched = []
                print(f"[State] Watching: {os.path.basename(path)}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
        except (FileNotFoundError, PermissionError):
            return
        if raw == self._raw_json:
            return
        self._raw_json = raw
        try:
            game_data = json.loads(raw)
        except json.JSONDecodeError:
            return

        changed = False
        with self._lock:
            while len(self._enriched) < len(game_data):
                self._enriched.append({"messages": []})

            for ri, run in enumerate(game_data):
                src_msgs = run.get("messages", [])
                dst_msgs = self._enriched[ri]["messages"]

                for mi, msg in enumerate(src_msgs):
                    if mi < len(dst_msgs):
                        if dst_msgs[mi]["content"] != msg.get("content", ""):
                            dst_msgs[mi]["content"] = msg.get("content", "")
                            changed = True
                        new_cot = msg.get("thinking")
                        if dst_msgs[mi]["cot"] != new_cot:
                            dst_msgs[mi]["cot"] = new_cot
                            changed = True
                    else:
                        dst_msgs.append({
                            "role": msg.get("role", ""),
                            "content": msg.get("content", ""),
                            "cot": msg.get("thinking"),
                            "summary": [],
                            "context": msg.get("context"),
                            "timestamp": msg.get("timestamp"),
                        })
                        changed = True

        if changed:
            self._persist()

    def summarize_pending(self):
        if not self._summarizer:
            return

        with self._lock:
            target = None
            for ri in range(len(self._enriched) - 1, -1, -1):
                msgs = self._enriched[ri]["messages"]
                for mi in range(len(msgs) - 1, -1, -1):
                    msg = msgs[mi]
                    if msg["role"] != "assistant" or not msg.get("cot"):
                        continue
                    cot = msg["cot"]
                    sent = self._sent_len.get((ri, mi), 0)
                    # Once content is finalized, lock sent_len and skip
                    if msg.get("content") and sent > 0:
                        self._sent_len[(ri, mi)] = len(cot)
                        continue
                    if len(cot) > sent:
                        user_query = ""
                        if mi > 0 and msgs[mi - 1]["role"] == "user":
                            user_query = msgs[mi - 1]["content"]
                        target = (ri, mi, user_query, cot, sent)
                        break
                if target:
                    break

        if not target:
            return

        ri, mi, user_query, cot, sent_len = target
        new_cot = cot[sent_len:]
        print(f"[Summarizer] Run {ri+1} Msg {mi}: +{len(new_cot)} chars (total: {len(cot)})")

        chunk = self._summarizer.call(f"用户问题：\n{user_query}\n\n新增思考：\n{new_cot}")
        if chunk:
            with self._lock:
                summary_list = self._enriched[ri]["messages"][mi].get("summary")
                if not isinstance(summary_list, list):
                    summary_list = []
                    self._enriched[ri]["messages"][mi]["summary"] = summary_list
                summary_list.append(chunk)
                self._sent_len[(ri, mi)] = len(cot)
            self._persist()

    def _persist(self):
        """Atomic write: build full JSON string under lock, then write all at once."""
        with self._lock:
            path = self._enriched_path
            if not path:
                return
            try:
                content = json.dumps(self._enriched, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[State] Serialize error: {e}")
                return
        # Write to temp file then rename for atomicity
        tmp_path = path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, path)
        except Exception as e:
            print(f"[State] Persist error: {e}")
