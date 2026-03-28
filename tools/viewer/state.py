"""Enriched state manager — merges game history with summaries and persists to disk.

Two-phase summarization per turn:
1. Scene description: when a new user query appears (no assistant response yet),
   immediately describe the game state for audio narration.
2. Decision summary: after the assistant response is finalized (content + cot),
   summarize the full thinking + decision.
"""

import json
import os
import threading
import time


def enriched_path_for(history_path: str) -> str:
    d, name = os.path.split(history_path)
    return os.path.join(d, name.replace("llm_history_", "llm_enriched_"))


class EnrichedState:
    """
    Enriched format per message pair:
        user:      { role, content, context, timestamp }
        assistant: { role, content, cot, scene, summary, context, timestamp }
            - scene: str | None — immediate scene description (phase 1)
            - summary: str | None — final decision summary (phase 2)
    """

    def __init__(self, summarizer=None):
        self._lock = threading.Lock()
        self._raw_json = ""
        self._current_path = ""
        self._enriched_path = ""
        self._enriched = []
        self._summarizer = summarizer
        # Track what we've processed: (run_idx, msg_idx) -> phase
        # phase: 0 = nothing, 1 = scene done, 2 = summary done
        self._phase = {}
        self._t_query: dict[tuple, float] = {}  # (ri, mi) -> wall time query detected

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
                self._phase = {}
                if os.path.isfile(self._enriched_path):
                    try:
                        with open(self._enriched_path, "r", encoding="utf-8") as f:
                            self._enriched = json.load(f)
                        # Restore phases from existing data
                        for ri, run in enumerate(self._enriched):
                            for mi, msg in enumerate(run.get("messages", [])):
                                if msg.get("summary"):
                                    self._phase[(ri, mi)] = 2
                                elif msg.get("scene"):
                                    self._phase[(ri, mi)] = 1
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
                        new_finished = msg.get("finished", False)
                        if new_finished and not dst_msgs[mi].get("finished"):
                            dst_msgs[mi]["finished"] = True
                            changed = True
                    else:
                        role = msg.get("role", "")
                        dst_msgs.append({
                            "role": role,
                            "content": msg.get("content", ""),
                            "cot": msg.get("thinking"),
                            "finished": msg.get("finished", False),
                            "scene": None,
                            "scene_history": None,
                            "summary": None,
                            "should_proceed": False,
                            "context": msg.get("context"),
                            "timestamp": msg.get("timestamp"),
                        })
                        if role == "assistant":
                            self._t_query[(ri, mi)] = time.time()
                            print(f"[Timing] R{ri+1}M{mi} query detected at {self._t_query[(ri, mi)]:.3f}")
                        changed = True

        if changed:
            self._persist()

    def process_pending(self):
        """Two-phase summarization: scene description, then decision summary."""
        if not self._summarizer:
            return

        with self._lock:
            target = None
            for ri in range(len(self._enriched) - 1, -1, -1):
                msgs = self._enriched[ri]["messages"]
                for mi in range(len(msgs) - 1, -1, -1):
                    msg = msgs[mi]
                    if msg["role"] != "assistant":
                        continue
                    phase = self._phase.get((ri, mi), 0)

                    if phase == 0:
                        # Phase 1: scene description — user query exists, assistant placeholder added
                        user_query = ""
                        if mi > 0 and msgs[mi - 1]["role"] == "user":
                            user_query = msgs[mi - 1]["content"]
                        if user_query:
                            target = ("scene", ri, mi, user_query, msg)
                            break

                    elif phase == 1 and msg.get("finished"):
                        # Phase 2: decision summary — response is finalized
                        user_query = ""
                        if mi > 0 and msgs[mi - 1]["role"] == "user":
                            user_query = msgs[mi - 1]["content"]
                        target = ("summary", ri, mi, user_query, msg)
                        break

                if target:
                    break

        if not target:
            return

        phase_name, ri, mi, user_query, msg = target

        if phase_name == "scene":
            t_query = self._t_query.get((ri, mi), time.time())
            print(f"[Timing] R{ri+1}M{mi} query→llm_start: {(time.time()-t_query)*1000:.0f} ms")
            print(f"[Summarizer] Scene for Run {ri+1} Msg {mi}")
            scene_text = self._summarizer.call_with_history(
                [],
                user_query,
                phase="scene"
            )
            if scene_text:
                t_scene_ready = time.time()
                print(f"[Timing] R{ri+1}M{mi} query→scene_ready: {(t_scene_ready-t_query)*1000:.0f} ms")
                # Store history: user query (with suffix already added by summarizer) + assistant scene
                from .summarizer import SCENE_SUFFIX
                history = [
                    {"role": "user", "content": user_query + SCENE_SUFFIX},
                    {"role": "assistant", "content": scene_text},
                ]
                with self._lock:
                    self._enriched[ri]["messages"][mi]["scene"] = scene_text
                    self._enriched[ri]["messages"][mi]["scene_history"] = history
                    self._enriched[ri]["messages"][mi]["scene_t"] = t_scene_ready
                    self._phase[(ri, mi)] = 1
                self._persist()
            else:
                with self._lock:
                    self._phase[(ri, mi)] = 1

        elif phase_name == "summary":
            print(f"[Summarizer] Summary for Run {ri+1} Msg {mi}")
            cot = msg.get("cot") or ""
            content = msg.get("content") or ""
            # Continue conversation from phase 1 (persisted in enriched file)
            history = msg.get("scene_history") or []
            summary_input = f"思考过程：\n{cot}\n\n最终决策：\n{content}"
            summary_text = self._summarizer.call_with_history(
                history,
                summary_input,
                phase="summary"
            )
            if summary_text:
                with self._lock:
                    self._enriched[ri]["messages"][mi]["summary"] = summary_text
                    self._phase[(ri, mi)] = 2
                self._persist()
            else:
                with self._lock:
                    self._phase[(ri, mi)] = 2

    def set_proceed(self, ri: int, mi: int):
        """Mark a specific assistant message as ready to proceed."""
        with self._lock:
            if ri < len(self._enriched):
                msgs = self._enriched[ri]["messages"]
                if mi < len(msgs):
                    msgs[mi]["should_proceed"] = True
                    print(f"[Proceed] Set should_proceed=True for Run {ri+1} Msg {mi}")
                else:
                    print(f"[Proceed] WARN: Msg {mi} out of range ({len(msgs)} msgs)")
            else:
                print(f"[Proceed] WARN: Run {ri} out of range ({len(self._enriched)} runs)")
        self._persist()
        # Verify
        with self._lock:
            if ri < len(self._enriched):
                val = self._enriched[ri]["messages"][mi].get("should_proceed")
                print(f"[Proceed] Verified: should_proceed={val}")

    def _persist(self):
        with self._lock:
            path = self._enriched_path
            if not path:
                return
            try:
                content = json.dumps(self._enriched, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[State] Serialize error: {e}")
                return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"[State] Persist error: {e}")
