"""File discovery and config loading."""

import glob
import json
import os
import sys

DEFAULT_MOD_PATHS = [
    os.path.expandvars(r"%ProgramFiles(x86)%\..\SteamLibrary\steamapps\common\Slay the Spire 2\mods\TokenSpire2"),
    os.path.expandvars(r"D:\SteamLibrary\steamapps\common\Slay the Spire 2\mods\TokenSpire2"),
    os.path.expandvars(r"C:\Program Files (x86)\Steam\steamapps\common\Slay the Spire 2\mods\TokenSpire2"),
    os.path.expanduser("~/Library/Application Support/Steam/steamapps/common/Slay the Spire 2/mods/TokenSpire2"),
]


def find_latest_history(base_dir: str) -> str | None:
    pattern = os.path.join(base_dir, "llm_history_*.json")
    files = glob.glob(pattern)
    return max(files, key=os.path.getmtime) if files else None


def find_json_file(explicit_path: str | None) -> tuple[str | None, str | None]:
    if explicit_path and os.path.isfile(explicit_path):
        return explicit_path, os.path.dirname(explicit_path)
    if explicit_path and os.path.isdir(explicit_path):
        f = find_latest_history(explicit_path)
        return (f, explicit_path) if f else (None, explicit_path)
    for mod_path in DEFAULT_MOD_PATHS:
        if os.path.isdir(mod_path):
            f = find_latest_history(mod_path)
            return (f, mod_path) if f else (None, mod_path)
    print("Error: Could not find mod folder or JSON file.")
    sys.exit(1)


def load_llm_config(watch_dir: str | None) -> dict | None:
    if not watch_dir:
        return None
    config_path = os.path.join(watch_dir, "llm_config.json")
    if not os.path.isfile(config_path):
        return None
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def enriched_path_for(history_path: str) -> str:
    d, name = os.path.split(history_path)
    return os.path.join(d, name.replace("llm_history_", "llm_enriched_"))
