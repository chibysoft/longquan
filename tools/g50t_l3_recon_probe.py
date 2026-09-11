"""g50t L3 recon: enter via L1+L2 clear, dump frame, map shrinks, hunt levels 2→3.

tags=["g50t_recon"]
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import BASE, _api_key  # noqa: E402

TAGS = ["g50t_recon"]
OUT_FRAME = ROOT / "tests/fixtures/g50t_l3_frame_live.json"
OUT = ROOT / "tests/fixtures/g50t_l3_recon_probe.json"

# Proven L1 clear (from _g50t_l2_clear_v2)
L1_SEQ = [4] * 5 + [5] + [2] * 10 + [4] * 6
# L2 path pieces from clear_v2
TO_2240 = [3, 3, 5, 2, 2, 2, 2, 2, 3, 3, 3, 3, 1, 1, 1, 3, 3]
TO_2840 = list(TO_2240) + [5, 1] + [2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 1, 1, 1]
L2_ROUTE = (
    [2, 2, 2, 4, 4, 4, 4, 1, 1, 1, 1, 1, 1, 1, 1, 3, 3, 3, 3, 3, 3, 3, 3, 2, 2, 4, 4, 4]
)


def H(key, j=False):
    h = {"X-API-Key": key, "Accept": "application/json"}
    if j:
        h["Content-Type"] = "application/json"
    return h


def plane(d):
    a = np.asarray(d["frame"], dtype=np.int64)
    return a[0] if a.ndim == 3 else a


def p(*a, **k):
    print(*a, **k, flush=True)


def actor(g, prev=None):
    H_, W = g.shape
    seen = np.zeros_like(g, dtype=bool)
    cands = []
    for y in range(7, 56):
        for x in range(W):
            if seen[y, x] or int(g[y, x]) != 9:
                continue
            stack = [(x, y)]
            seen[y, x] = True
            cells = []
            while stack:
                cx, cy = stack.pop()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < W and 7 <= ny < 56 and not seen[ny, nx] and int(g[ny, nx]) == 9:
                        seen[ny, nx] = True
                        stack.append((nx, ny))
            if len(cells) == 24:
                xs = [c[0] for c in cells]
                ys = [c[1] for c in cells]
                cands.append({
                    "n": 24,
                    "cx": round(sum(xs) / 24, 2),
                    "cy": round(sum(ys) / 24, 2),
                    "box": [min(xs), min(ys), max(xs), max(ys)],
                })
    if not cands:
        return None
    if prev:
        return min(cands, key=lambda b: abs(b["cx"] - prev["cx"]) + abs(b["cy"] - prev["cy"]))
    return max(cands, key=lambda b: b["cy"] * 0 + b["cx"])  # prefer rightish spawn


def comps9(g, exclude_actor_box=None):
    """Other color9 blobs (goals), not the 24-ring actor."""
    H_, W = g.shape
    seen = np.zeros_like(g, dtype=bool)
    out = []
    for y in range(1, 63):
        for x in range(W):
            if seen[y, x] or int(g[y, x]) != 9:
                continue
            stack = [(x, y)]
            seen[y, x] = True
            cells = []
            while stack:
                cx, cy = stack.pop()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < W and 1 <= ny < 63 and not seen[ny, nx] and int(g[ny, nx]) == 9:
                        seen[ny, nx] = True
                        stack.append((nx, ny))
            if len(cells) == 24:
                continue  # actor
            if len(cells) < 4:
                continue
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            out.append({
                "n": len(cells),
                "cx": round(sum(xs) / len(cells), 2),
                "cy": round(sum(ys) / len(cells), 2),
                "box": [min(xs), min(ys), max(xs), max(ys)],
            })
    out.sort(key=lambda b: (b["cy"], b["cx"]))
    return out


def e8(g):
    return {
        "n": int(np.sum(g[1:63] == 8)),
        "bbox": None if int(np.sum(g[1:63] == 8)) == 0 else [
            int(np.min(np.where(g[1:63] == 8)[1])),
            int(np.min(np.where(g[1:63] == 8)[0]) + 1),
            int(np.max(np.where(g[1:63] == 8)[1])),
            int(np.max(np.where(g[1:63] == 8)[0]) + 1),
        ],
    }


def color8_tips(g):
    """Candidate shrink pads: color8 cells adjacent to floor color5 with room for actor."""
    tips = []
    ys, xs = np.where(g[1:63] == 8)
    ys = ys + 1
    seen = set()
    for y, x in zip(ys.tolist(), xs.tolist()):
        # look for 5-neighbor
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nx, ny = x + dx, y + dy
            if 1 <= ny < 63 and 0 <= nx < 64 and int(g[ny, nx]) == 5:
                # snap to 6-grid near this floor cell
                for sx in range(max(2, nx - 2), min(62, nx + 3)):
                    for sy in range(max(8, ny - 2), min(55, ny + 3)):
                        if (sx + sy) % 2:  # loose
                            pass
                        key = (sx - sx % 6, sy - sy % 6)  # rough
                # just record 8-cell itself as tip coord (center-ish)
                key = (x, y)
                if key not in seen:
                    seen.add(key)
                    tips.append({"x": x, "y": y})
    return tips[:40]


def floor_grid(g):
    """Walkable centers on 6-step lattice where 5x5 ring fits on color5."""
    pts = []
    for cy in range(10, 55, 6):
        for cx in range(10, 55, 6):
            patch = g[cy - 2 : cy + 3, cx - 2 : cx + 3]
            if patch.shape != (5, 5):
                continue
            # ring cells should be placeable: interior can be anything, ring positions need 5 or 9
            # simpler: majority of 5x5 is 5
            if int(np.sum(patch == 5)) >= 15:
                pts.append((cx, cy))
    return pts


def body_ndiff(a, b):
    return int(np.sum(a[1:63] != b[1:63]))


def ascii_map(g, act=None, step=2):
    chars = {0: ".", 1: "1", 2: "2", 5: " ", 8: "#", 9: "@"}
    lines = []
    for y in range(0, 64, step):
        row = []
        for x in range(0, 64, step):
            v = int(g[y, x])
            row.append(chars.get(v, str(v)[-1]))
        lines.append(f"{y:02d}|" + "".join(row) + "|")
    return lines


def main():
    key = _api_key()
    s = requests.Session()
    card = s.post(
        f"{BASE}/api/scorecard/open", headers=H(key, True), json={"tags": TAGS}, timeout=30
    ).json()["card_id"]
    gid = s.get(f"{BASE}/api/games/g50t", headers=H(key), timeout=20).json()["game_id"]
    p("opened g50t", gid, "card", card)

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

    out = {"tags": TAGS, "game_id": gid}

    # ---- enter L2 then clear to levels>=2, then transition to true L3 ----
    d = reset()
    guid = d["guid"]
    g = plane(d)
    prev = None
    log = []

    def run_seq(seq, tag, stop_lv=None):
        nonlocal guid, g, prev
        for i, a_ in enumerate(seq):
            d2 = act(guid, a_)
            guid = d2["guid"]
            g2 = plane(d2)
            a = actor(g2, prev)
            row = {
                "tag": tag,
                "i": i,
                "a": a_,
                "actor": a,
                "e8": e8(g2),
                "lv": d2.get("levels_completed"),
                "b": body_ndiff(g, g2),
            }
            log.append(row)
            g, prev = g2, a
            if stop_lv is not None and (d2.get("levels_completed") or 0) >= stop_lv:
                return d2
        return d2

    p("## L1 clear")
    d = run_seq(L1_SEQ + [2] * 4 + [4] * 8, "l1", stop_lv=1)
    p("  lv", d.get("levels_completed"), "actor", prev, "e8", e8(g))
    # transition into true L2
    d = run_seq([3], "l1_to_l2")
    p("  after transition actor", prev, "e8", e8(g), "hist", dict(Counter(g.ravel().tolist())))

    p("## L2 clear")
    d = run_seq(TO_2840 + L2_ROUTE, "l2", stop_lv=2)
    p("  lv", d.get("levels_completed"), "actor", prev, "e8", e8(g))
    if (d.get("levels_completed") or 0) < 2:
        p("FAIL enter L2 clear — abort")
        out["reading"] = "L2_CLEAR_FAIL"
        out["log"] = log[-30:]
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)
        return

    # L2 clear frame may still be L2 end — transition to true L3
    g_before = g.copy()
    hist_before = dict(Counter(g.ravel().tolist()))
    d = run_seq([3], "l2_to_l3")
    g_l3 = g
    hist_l3 = dict(Counter(g_l3.ravel().tolist()))
    a0 = actor(g_l3)
    goals = comps9(g_l3)
    e0 = e8(g_l3)
    p("## L3 start")
    p("  body_ndiff from L2-end", body_ndiff(g_before, g_l3))
    p("  hist", hist_l3)
    p("  actor", a0)
    p("  goals", goals)
    p("  e8", e0)
    p("  acts", d.get("available_actions"))

    # save frame
    OUT_FRAME.write_text(
        json.dumps(
            {
                "summary": {
                    "hist": hist_l3,
                    "levels_completed": d.get("levels_completed"),
                    "win_levels": d.get("win_levels"),
                    "available_actions": d.get("available_actions"),
                    "actor": a0,
                    "goals": goals,
                    "e8": e0,
                    "body_ndiff_from_l2_end": body_ndiff(g_before, g_l3),
                },
                "preview_lines": ascii_map(g_l3),
                "frame": g_l3.tolist(),
                "meta": {"game_id": gid, "tags": TAGS, "card_id": card},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    p("wrote", OUT_FRAME)

    # print ascii preview (compact)
    for line in ascii_map(g_l3)[4:30]:
        p(line)

    # ---- direction probe from spawn (flush buffer) ----
    p("## dir probe from L3 spawn")
    dir_rows = []
    for name, seq in [
        ("flush_U", [1, 1]),
        ("flush_D", [2, 2]),
        ("flush_L", [3, 3]),
        ("flush_R", [4, 4]),
    ]:
        # re-enter L3 each time
        d = reset()
        guid = d["guid"]
        g = plane(d)
        prev = None
        run_seq(L1_SEQ + [2] * 4 + [4] * 8, "l1", stop_lv=1)
        run_seq([3], "t2")
        run_seq(TO_2840 + L2_ROUTE, "l2", stop_lv=2)
        run_seq([3], "t3")
        a_before = actor(g)
        e_before = e8(g)
        d2 = run_seq(seq, name)
        a_after = actor(g)
        row = {
            "name": name,
            "before": a_before,
            "after": a_after,
            "e8_before": e_before,
            "e8_after": e8(g),
            "lv": d2.get("levels_completed"),
            "b": body_ndiff,
        }
        # fix body
        row["moved"] = None if not (a_before and a_after) else {
            "dx": round(a_after["cx"] - a_before["cx"], 2),
            "dy": round(a_after["cy"] - a_before["cy"], 2),
        }
        p(" ", name, row["moved"], "e8", row["e8_after"], "lv", row["lv"])
        dir_rows.append(row)

    # ---- BFS-ish explore on 6-grid for a while, watch e8 drops and levels ----
    p("## shallow explore (budget 80) watching e8/levels")
    d = reset()
    guid = d["guid"]
    g = plane(d)
    prev = None
    run_seq(L1_SEQ + [2] * 4 + [4] * 8, "l1", stop_lv=1)
    run_seq([3], "t2")
    run_seq(TO_2840 + L2_ROUTE, "l2", stop_lv=2)
    run_seq([3], "t3")
    start_lv = d.get("levels_completed") if False else 2
    # get current
    a = actor(g)
    e_start = e8(g)["n"]
    p("  start", a, "e8n", e_start)

    # try standing on nearby color8 by walking toward e8 bbox center
    explore_log = []
    # sequence hunts: spiral / toward each goal / toward e8
    hunts = []
    if goals:
        for gi, goal in enumerate(goals[:3]):
            # naive: move toward goal with buffered dirs
            seq = []
            # we'll execute online with greedy
            hunts.append(("goal" + str(gi), goal))

    # Online greedy toward first goal + sample A5 when e8 changes underfoot
    if goals:
        target = goals[0]
    else:
        target = {"cx": 28, "cy": 28}

    cleared = False
    actions_l3 = []
    for step in range(60):
        a = actor(g, prev)
        if not a:
            p("  lost actor")
            break
        # underfoot: check if standing near color8
        cx, cy = int(round(a["cx"])), int(round(a["cy"]))
        under8 = int(np.sum(g[cy - 2 : cy + 3, cx - 2 : cx + 3] == 8))
        e_now = e8(g)["n"]
        # choose dir toward target
        dx = target["cx"] - a["cx"]
        dy = target["cy"] - a["cy"]
        if abs(dx) >= abs(dy):
            aid = 4 if dx > 0 else 3
        else:
            aid = 2 if dy > 0 else 1
        # if on 8, try A5 once
        if under8 >= 3 and step % 7 == 3:
            aid = 5
        d2 = act(guid, aid)
        guid = d2["guid"]
        g2 = plane(d2)
        a2 = actor(g2, a)
        row = {
            "step": step,
            "a": aid,
            "actor": a2,
            "under8": under8,
            "e8n": e8(g2)["n"],
            "lv": d2.get("levels_completed"),
            "b": body_ndiff(g, g2),
        }
        explore_log.append(row)
        actions_l3.append(aid)
        if step % 10 == 0:
            p(f"  step{step} A{aid}", a2, "e8", row["e8n"], "u8", under8, "lv", row["lv"])
        g, prev = g2, a2
        if (d2.get("levels_completed") or 0) > 2:
            cleared = True
            p("*** L3 CLEAR")
            (ROOT / "tests/fixtures/g50t_l3_clear_attempt.json").write_text(
                json.dumps(
                    {
                        "cleared": True,
                        "l3_actions": actions_l3,
                        "final": row,
                        "log": explore_log,
                    },
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )
            break
        # retarget if e8 dropped a lot — maybe open corridors
        if e_now - row["e8n"] >= 10:
            p("  shrink event", e_now, "->", row["e8n"], "at", a2)

    out.update(
        {
            "l3_summary": {
                "hist": hist_l3,
                "actor": a0,
                "goals": goals,
                "e8": e0,
                "body_ndiff_from_l2_end": body_ndiff(g_before, g_l3),
            },
            "dir_probe": dir_rows,
            "explore": explore_log[-20:],
            "cleared": cleared,
            "reading": "L3_CLEAR" if cleared else "L3_PARTIAL",
        }
    )
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING:", out["reading"])
    p("wrote", OUT)
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
