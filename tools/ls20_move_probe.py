"""Probe ls20 move step-length: how many pixels does the cursor move per action.

Pure-requests, no arc_agi/arcengine dependency (their .venv is Windows-layout).
Protocol reverse-engineered from arc_agi/remote_wrapper.py + base.py
(design-time only, not runtime input to any learner).

CRITICAL: the server sets a GAMESESSION cookie on /api/scorecard/open which the
subsequent /api/cmd/* calls require (else RESET returns 400 "game not found").
We therefore use a single requests.Session for the whole probe.

Usage:
  python3 tools/ls20_move_probe.py            # probe all 4 directions
  python3 tools/ls20_move_probe.py ACTION1    # probe one direction
"""
from __future__ import annotations

import sys
import os

import requests
import numpy as np

BASE = os.environ.get("ARC_BASE_URL", "https://three.arcprize.org")
ENV = "/sessions/nice-inspiring-edison/mnt/Projects/ARC-AGI-3-Agents/.env"


def _key() -> str:
    for p in (ENV, ".env", "../.env"):
        if os.path.exists(p):
            for line in open(p):
                line = line.strip()
                if line.startswith("ARC_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return os.environ.get("ARC_API_KEY", "")


def _plane(frame):
    a = np.asarray(frame, dtype=np.int8)
    return a[0] if a.ndim == 3 else a


def _bbox(grid, colors):
    ys, xs = np.where(np.isin(grid, colors))
    if len(xs) == 0:
        return None
    return (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))


def main() -> int:
    key = _key()
    s = requests.Session()

    # open a scorecard (sets GAMESESSION cookie)
    r = s.post(f"{BASE}/api/scorecard/open",
               headers={"X-API-Key": key, "Accept": "application/json"},
               json={"tags": ["move_probe"]}, timeout=15)
    r.raise_for_status()
    card_id = r.json()["card_id"]

    # full game_id (with version) from metadata
    r = s.get(f"{BASE}/api/games/ls20", headers={"X-Api-Key": key}, timeout=15)
    r.raise_for_status()
    game_id = r.json()["game_id"]

    actions = ["ACTION1", "ACTION2", "ACTION3", "ACTION4"]
    if len(sys.argv) > 1:
        actions = [sys.argv[1].upper()]

    print(f"base={BASE} game={game_id}")
    for action in actions:
        # reset -> fresh frame + guid
        r = s.post(f"{BASE}/api/cmd/RESET",
                   headers={"X-Api-Key": key, "Content-Type": "application/json"},
                   json={"card_id": card_id, "game_id": game_id}, timeout=15)
        r.raise_for_status()
        before = r.json()
        guid = before["guid"]
        bg = _plane(before["frame"])

        # step the action
        r = s.post(f"{BASE}/api/cmd/{action}",
                   headers={"X-Api-Key": key, "Content-Type": "application/json"},
                   json={"game_id": game_id, "guid": guid}, timeout=15)
        r.raise_for_status()
        after = r.json()
        ag = _plane(after["frame"])

        # cursor = color 0 (body) + 1 (outline); slot marker = 12
        b0 = _bbox(bg, [0, 1])
        a0 = _bbox(ag, [0, 1])
        b12 = _bbox(bg, [12])
        a12 = _bbox(ag, [12])
        changed = int(np.count_nonzero(bg != ag))
        # unique colors present in each frame
        uniq_b = sorted(set(int(v) for v in np.unique(bg)))
        uniq_a = sorted(set(int(v) for v in np.unique(ag)))
        print(f"\n{action}:")
        print(f"  frame shape={bg.shape}")
        print(f"  cursor(0/1) before={b0} after={a0}")
        print(f"  slot(12)    before={b12} after={a12}")
        print(f"  changed_pixels={changed}")
        print(f"  colors before={uniq_b}")
        print(f"  colors after ={uniq_a}")
        print(f"  levels={before.get('levels_completed')}->{after.get('levels_completed')} state={after.get('state')}")

    # close scorecard
    s.post(f"{BASE}/api/scorecard/close",
           headers={"X-API-Key": key, "Accept": "application/json"},
           json={"card_id": card_id}, timeout=15)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
