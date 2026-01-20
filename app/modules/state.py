from __future__ import annotations

import json
import os
from typing import Dict


def build_state_path(state_dir: str) -> str:
    return os.path.join(state_dir, "state.json")


def get_state(state_dir: str) -> Dict:
    path = build_state_path(state_dir)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state_dir: str, state: Dict) -> None:
    os.makedirs(state_dir, exist_ok=True)
    path = build_state_path(state_dir)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    os.replace(tmp, path)
