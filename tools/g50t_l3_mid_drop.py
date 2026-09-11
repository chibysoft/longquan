"""g50t L3: drop from top mid-column toward goal (22,22); probe c11.

tags=["g50t_recon"]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import BASE, _api_key  # noqa: E402
from tools.g50t_l3_recon_probe import (  # noqa: E402
    L1_SEQ,
    TO_2840,
    L2_ROUTE,
    H,
    plane,
    actor,
    e8,
    comps9,
)

OUT = ROOT / "tests/fixtures/g50t_l3_mid_drop.json"


def p(*a, **k):
    print(*a, **k, flush=True)


def main():
    key = _api_key()
    s = requests.Session()
    card = s.post(
        f"{BASE}/api/scorecard/open",
        headers=H(key, True),
        json={"tags": ["g50t_recon"]},
        timeout=30,
    ).json()["card_id"]
    gid = s.get(f"{BASE}/api/games/g50t", headers=H(key), timeout=20).json()["game_id"]

    def reset():
        return s.post(
            f"{BASE}/api/cmd/RESET",
            headers=H(key, True),
            json={"card_id": card, "game_id": gid},
            timeout=30,
        ).json()

    def act(guid, aid):
        d = s.post(
            f"{BASE}/api/cmd/ACTION{aid}",
            headers=H(key, True),
            json={"game_id": gid, "guid": guid},
            timeout=30,
        ).json()
        if "guid" not in d:
            raise RuntimeError(str({k: d.get(k) for k in d if k != "frame"}))
        return d

    def enter_l3():
        d = reset()
        guid = d["guid"]
        g = plane(d)
        prev = None
        for a_ in L1_SEQ + [2] * 4 + [4] * 8:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if (d.get("levels_completed") or 0) >= 1:
                break
        d = act(guid, 3)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        for a_ in TO_2840 + L2_ROUTE:
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if (d.get("levels_completed") or 0) >= 2:
                break
        d = act(guid, 3)
        guid = d["guid"]
        g = plane(d)
        prev = actor(g, prev)
        return guid, g, prev

    def flush_to(guid, g, prev, target_x, target_y, limit=30):
        """Greedy buffered moves toward target."""
        log = []
        for _ in range(limit):
            if not prev:
                break
            cx, cy = prev["cx"], prev["cy"]
            if abs(cx - target_x) < 3 and abs(cy - target_y) < 3:
                break
            dx, dy = target_x - cx, target_y - cy
            if abs(dx) >= abs(dy) and abs(dx) >= 3:
                aid = 4 if dx > 0 else 3
            elif abs(dy) >= 3:
                aid = 2 if dy > 0 else 1
            else:
                break
            before = (cx, cy)
            d = act(guid, aid)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            d = act(guid, aid)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            after = (prev["cx"], prev["cy"]) if prev else None
            log.append({"a": aid, "from": before, "to": after, "lv": d.get("levels_completed"),
                        "e8": e8(g)["n"], "c11": int(np.sum(g == 11))})
            if after == before:
                # blocked; try alternate
                break
            if (d.get("levels_completed") or 0) > 2:
                return guid, g, prev, log, True
        return guid, g, prev, log, False

    out = {"drops": []}
    cleared = False

    # For each top x in {10,16,22,28,34,40,46,52}, go there then try D D D
    for tx in (10, 16, 22, 28, 34, 40, 46, 52):
        p(f"## to ({tx},10) then drop D")
        guid, g, prev = enter_l3()
        guid, g, prev, log1, ok = flush_to(guid, g, prev, tx, 10)
        p("  at", prev)
        if ok:
            cleared = True
            break
        # drop
        drop_log = []
        for i in range(6):
            d = act(guid, 2)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            d = act(guid, 2)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            row = {
                "i": i,
                "actor": prev,
                "e8": e8(g)["n"],
                "c11": int(np.sum(g == 11)),
                "lv": d.get("levels_completed"),
            }
            drop_log.append(row)
            p("  D", row["actor"], "e8", row["e8"], "c11", row["c11"], "lv", row["lv"])
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                p("*** CLEAR")
                (ROOT / "tests/fixtures/g50t_l3_clear_attempt.json").write_text(
                    json.dumps(
                        {"cleared": True, "via": f"drop_x{tx}", "log": log1 + drop_log},
                        indent=2,
                        default=str,
                    ),
                    encoding="utf-8",
                )
                break
            if not prev:
                break
            # stop if not moving down
            if i > 0 and drop_log[i]["actor"] and drop_log[i - 1]["actor"]:
                if drop_log[i]["actor"]["cy"] == drop_log[i - 1]["actor"]["cy"]:
                    p("  stuck vertically")
                    break
        out["drops"].append({"tx": tx, "top": log1[-1] if log1 else None, "drop": drop_log})
        if cleared:
            break

        # if landed near c11, try A5
        if prev:
            cx, cy = int(round(prev["cx"])), int(round(prev["cy"]))
            u11 = int(np.sum(g[cy - 2 : cy + 3, cx - 2 : cx + 3] == 11))
            u8 = int(np.sum(g[cy - 2 : cy + 3, cx - 2 : cx + 3] == 8))
            if u11 >= 2 or u8 >= 2:
                e0, c0 = e8(g)["n"], int(np.sum(g == 11))
                d = act(guid, 5)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
                d = act(guid, 5)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
                p(f"  A5 u8={u8} u11={u11} e8 {e0}->{e8(g)['n']} c11 {c0}->{int(np.sum(g==11))} lv={d.get('levels_completed')}")
                out["drops"][-1]["a5"] = {
                    "u8": u8,
                    "u11": u11,
                    "e8": [e0, e8(g)["n"]],
                    "c11": [c0, int(np.sum(g == 11))],
                    "lv": d.get("levels_completed"),
                    "actor": prev,
                }
                if (d.get("levels_completed") or 0) > 2:
                    cleared = True
                    break

    # Special: go to (22,10), D to (22,16), then L/R micro toward goal center, then D
    if not cleared:
        p("## precise approach (22,10)->D->nudge->D")
        guid, g, prev = enter_l3()
        guid, g, prev, _, _ = flush_to(guid, g, prev, 22, 10)
        p("  at top", prev)
        # one D flush
        for a_ in (2, 2):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        p("  after D", prev, "c11", int(np.sum(g == 11)))
        # try D again
        for a_ in (2, 2):
            d = act(guid, a_)
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        p("  after D2", prev, "lv", d.get("levels_completed"))
        # try L then D, R then D
        for name, pair in [("L", 3), ("R", 4)]:
            guid, g, prev = enter_l3()
            guid, g, prev, _, _ = flush_to(guid, g, prev, 22, 10)
            for a_ in (2, 2, pair, pair, 2, 2):
                d = act(guid, a_)
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
            p(f"  via {name}", prev, "lv", d.get("levels_completed"), "e8", e8(g)["n"])
            if (d.get("levels_completed") or 0) > 2:
                cleared = True
                p("*** CLEAR")
                break

    out["reading"] = "L3_CLEAR" if cleared else "L3_DROP_PARTIAL"
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    p("wrote", OUT)
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
