"""vc33 L1: online RESET → save initial live frame fixture.

Closed-book: frames + API only. No engine source. No moves.
Independent scorecard tags: ["vc33_recon"].

Usage:
  python tools/vc33_l1_frame_grab.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, _api_key  # noqa: E402

GAME = "vc33"
TAGS = ["vc33_recon"]
FIXTURE = ROOT / "tests" / "fixtures" / "vc33_l1_frame_live.json"


def _headers(key: str, json_body: bool = False) -> dict:
    h = {"X-API-Key": key, "Accept": "application/json"}
    if json_body:
        h["Content-Type"] = "application/json"
    return h


def main() -> int:
    key = _api_key()
    if not key:
        raise RuntimeError("ARC_API_KEY not found")

    s = requests.Session()

    r = s.post(
        f"{BASE}/api/scorecard/open",
        headers=_headers(key, True),
        json={"tags": TAGS},
        timeout=20,
    )
    r.raise_for_status()
    card_id = r.json()["card_id"]
    print("card_id", card_id, "tags", TAGS)

    try:
        r = s.get(f"{BASE}/api/games/{GAME}", headers=_headers(key), timeout=20)
        r.raise_for_status()
        game_desc = r.json()
        game_id = game_desc["game_id"]
        print("game_id", game_id)
        print("game_desc", {k: v for k, v in game_desc.items() if k != "frame"})

        r = s.post(
            f"{BASE}/api/cmd/RESET",
            headers=_headers(key, True),
            json={"card_id": card_id, "game_id": game_id},
            timeout=30,
        )
        r.raise_for_status()
        reset = r.json()

        frame = reset.get("frame")
        arr = np.asarray(frame, dtype=np.int64)
        meta = {
            "levels_completed": reset.get("levels_completed"),
            "state": reset.get("state"),
            "available_actions": reset.get("available_actions"),
            "win_levels": reset.get("win_levels"),
        }
        flat = arr.reshape(-1)
        hist = {int(k): int(v) for k, v in Counter(flat.tolist()).items()}

        print("RESET keys", sorted(reset.keys()))
        print("meta", meta)
        print("frame_shape", list(arr.shape))
        print("color_hist", dict(sorted(hist.items())))

        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "game_id": game_id,
            "card_id": card_id,
            "tags": TAGS,
            "game_desc": {k: game_desc[k] for k in game_desc if k != "frame"},
            "frame": arr.tolist(),
            "available_actions": meta["available_actions"],
            "state": meta["state"],
            "levels_completed": meta["levels_completed"],
            "win_levels": meta["win_levels"],
            "frame_shape": list(arr.shape),
            "color_hist": dict(sorted(hist.items())),
            "reset_keys": sorted(reset.keys()),
        }
        FIXTURE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print("saved", FIXTURE)
        return 0
    finally:
        try:
            s.post(
                f"{BASE}/api/scorecard/close",
                headers=_headers(key, True),
                json={"card_id": card_id},
                timeout=15,
            )
        except Exception as e:
            print("close warn:", e)


if __name__ == "__main__":
    raise SystemExit(main())
