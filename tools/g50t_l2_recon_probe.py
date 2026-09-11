"""g50t L2: capture post-transition frame; identify actor; hunt levels 1→2."""
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
L2_FRAME = ROOT / "tests/fixtures/g50t_l2_frame_live.json"
L2_CLEAR = ROOT / "tests/fixtures/g50t_l2_clear_attempt.json"
OUT = ROOT / "tests/fixtures/g50t_l2_recon_probe.json"

L1_SEQ = [4] * 5 + [5] + [2] * 10 + [4] * 6


def H(key, j=False):
    h = {"X-API-Key": key, "Accept": "application/json"}
    if j:
        h["Content-Type"] = "application/json"
    return h


def plane(d):
    a = np.asarray(d["frame"], dtype=np.int64)
    return a[0] if a.ndim == 3 else a


def hist(g):
    return {int(k): int(v) for k, v in zip(*np.unique(g, return_counts=True))}


def ccs(g, colors, y0=1, y1=63, min_n=1, max_n=10**9):
    if isinstance(colors, int):
        colors = {colors}
    else:
        colors = set(colors)
    H_, W = g.shape
    seen = np.zeros_like(g, dtype=bool)
    out = []
    for y in range(y0, min(y1, H_)):
        for x in range(W):
            c = int(g[y, x])
            if seen[y, x] or c not in colors:
                continue
            stack = [(x, y)]
            seen[y, x] = True
            cells = []
            while stack:
                cx, cy = stack.pop()
                cells.append((cx, cy, int(g[cy, cx])))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if (
                        0 <= nx < W
                        and y0 <= ny < min(y1, H_)
                        and not seen[ny, nx]
                        and int(g[ny, nx]) in colors
                    ):
                        seen[ny, nx] = True
                        stack.append((nx, ny))
            if min_n <= len(cells) <= max_n:
                xs = [t[0] for t in cells]
                ys = [t[1] for t in cells]
                out.append({
                    "n": len(cells),
                    "cx": round(sum(xs) / len(xs), 2),
                    "cy": round(sum(ys) / len(ys), 2),
                    "box": [min(xs), min(ys), max(xs), max(ys)],
                    "cols": dict(Counter(t[2] for t in cells)),
                })
    out.sort(key=lambda b: (b["cy"], b["cx"]))
    return out


def e8(g):
    ys, xs = np.where(g[1:63] == 8)
    if len(xs) == 0:
        return {"n": 0}
    ys = ys + 1
    return {
        "n": int(len(xs)),
        "xmin": int(xs.min()),
        "xmax": int(xs.max()),
        "ymin": int(ys.min()),
        "ymax": int(ys.max()),
        "shaft_L": int(np.sum(g[38:43, 14:19] == 8)),
    }


def body_ndiff(a, b):
    return int(np.sum(a[1:63] != b[1:63]))


def body_hist(a, b):
    m = a[1:63] != b[1:63]
    ys, xs = np.where(m)
    hist_ = Counter()
    for y, x in zip(ys.tolist(), xs.tolist()):
        hist_[(int(a[y + 1, x]), int(b[y + 1, x]))] += 1
    return {f"{u}->{v}": n for (u, v), n in hist_.most_common(20)}


def ascii_preview(g):
    chars = {0: ".", 1: "1", 2: "2", 5: "5", 8: "8", 9: "9"}
    lines = []
    for y in range(g.shape[0]):
        row = "".join(chars.get(int(g[y, x]), "?") for x in range(g.shape[1]))
        if any(ch not in ". " for ch in row):
            lines.append(f"{y:02d}|{row}")
    return lines


def track_movers(g0, g1, colors=(2, 9), min_n=8, max_n=40):
    movers = []
    for c in colors:
        a = ccs(g0, c, 7, 62, min_n, max_n)
        b = ccs(g1, c, 7, 62, min_n, max_n)
        used = set()
        for ca in a:
            best = None
            best_d = 1e9
            for i, cb in enumerate(b):
                if i in used or ca["n"] != cb["n"]:
                    continue
                d = abs(ca["cx"] - cb["cx"]) + abs(ca["cy"] - cb["cy"])
                if d < best_d:
                    best_d = d
                    best = (i, cb)
            if best and best_d > 0.01:
                i, cb = best
                used.add(i)
                movers.append({
                    "color": c,
                    "n": ca["n"],
                    "from": ca,
                    "to": cb,
                    "dx": round(cb["cx"] - ca["cx"], 2),
                    "dy": round(cb["cy"] - ca["cy"], 2),
                })
    movers.sort(key=lambda m: -(abs(m["dx"]) + abs(m["dy"])))
    return movers


def main():
    key = _api_key()
    s = requests.Session()
    card = s.post(
        f"{BASE}/api/scorecard/open", headers=H(key, True), json={"tags": TAGS}, timeout=30
    ).json()["card_id"]
    gid = s.get(f"{BASE}/api/games/g50t", headers=H(key), timeout=20).json()["game_id"]
    print("card", card, gid)

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

    def clear_l1():
        d = reset()
        g = plane(d)
        guid = d["guid"]
        for aid in L1_SEQ + [2] * 4 + [4] * 8:
            d = act(guid, aid)
            guid = d["guid"]
            g = plane(d)
            if (d.get("levels_completed") or 0) >= 1:
                return guid, g, d
        raise RuntimeError("L1 clear failed")

    def enter_l2(enter_aid=1):
        """L1 clear frame is still L1-end; next action loads L2."""
        guid, g_end, d_end = clear_l1()
        d2 = act(guid, enter_aid)
        return d2["guid"], plane(d2), d2, g_end, d_end

    result = {"card": card, "game": gid}

    # --- Capture true L2 start ---
    guid, g, d, g_end, d_end = enter_l2(1)
    print("L1-end play9", ccs(g_end, 9, 7, 56, 15, 30)[:4])
    print("L1-end c2", ccs(g_end, 2, 1, 56, 1, 50)[:6])
    print("L2 hist", hist(g), "lv", d.get("levels_completed"), "acts", d.get("available_actions"))
    print("L2 c2", ccs(g, 2, 1, 62, 1, 80))
    print("L2 c9", ccs(g, 9, 1, 62, 1, 80)[:10])
    print("L2 e8", e8(g))
    print("transition body", body_ndiff(g_end, g), "hist", body_hist(g_end, g))

    payload = {
        "summary": {
            "levels_completed": d.get("levels_completed"),
            "win_levels": d.get("win_levels"),
            "state": d.get("state"),
            "available_actions": d.get("available_actions"),
            "shape": list(g.shape),
            "hist": hist(g),
            "c2": ccs(g, 2, 1, 62, 1, 80),
            "c9": ccs(g, 9, 1, 62, 1, 80),
            "e8": e8(g),
            "note": "Frame AFTER first post-L1 action (true L2 layout)",
            "enter_action": "ACTION1",
            "l1_end_hist": hist(g_end),
            "transition_body": body_ndiff(g_end, g),
        },
        "preview_lines": ascii_preview(g),
        "frame": d["frame"],
        "meta": {
            "levels_completed": d.get("levels_completed"),
            "win_levels": d.get("win_levels"),
            "available_actions": d.get("available_actions"),
            "state": d.get("state"),
            "game_id": gid,
            "card_id": card,
            "tags": TAGS,
        },
    }
    L2_FRAME.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    for line in payload["preview_lines"][:35]:
        print(line)

    # --- Directional tests tracking c2 and c9 movers ---
    dir_rows = []
    for aid in [1, 2, 3, 4, 5]:
        guid, g0, d0, _, _ = enter_l2(4)  # enter via RIGHT
        # flush: after enter, queue may be enter_aid; press aid twice
        d1 = act(guid, aid)
        guid = d1["guid"]
        g1 = plane(d1)
        d2 = act(guid, aid)
        guid = d2["guid"]
        g2 = plane(d2)
        movers = track_movers(g1, g2) or track_movers(g0, g1)
        row = {
            "action": f"ACTION{aid}",
            "enter": "A4",
            "body01": body_ndiff(g0, g1),
            "body12": body_ndiff(g1, g2),
            "movers_12": movers[:4],
            "c2_0": ccs(g0, 2, 7, 56, 8, 40),
            "c2_2": ccs(g2, 2, 7, 56, 8, 40),
            "c9_rings": [b for b in ccs(g2, 9, 7, 56, 15, 30)],
            "e8": e8(g2),
            "levels": d2.get("levels_completed"),
        }
        # label from best mover
        label = "NOMOVE"
        if movers:
            m = movers[0]
            dx, dy = m["dx"], m["dy"]
            if abs(dx) > abs(dy) and abs(dx) >= 0.5:
                label = "RIGHT" if dx > 0 else "LEFT"
            elif abs(dy) >= 0.5:
                label = "DOWN" if dy > 0 else "UP"
            row["best"] = m
        row["label"] = label
        dir_rows.append(row)
        print("DIR", aid, "b", row["body01"], row["body12"], label, row.get("best"))
    result["directions"] = dir_rows

    # Identify actor color from consistent movers
    actor_color = None
    for r in dir_rows:
        if r.get("best"):
            actor_color = r["best"]["color"]
            break
    print("actor_color guess", actor_color)

    def actor(g, color=actor_color):
        if color is None:
            # try c2 first then c9 ring
            for c in (2, 9):
                rings = ccs(g, c, 7, 56, 15, 40)
                if rings:
                    # prefer not the static mid n=19 if multiple
                    return min(rings, key=lambda b: (abs(b["n"] - 24), b["cy"], b["cx"]))
            return None
        rings = ccs(g, color, 7, 56, 8, 40)
        if not rings:
            return None
        return min(rings, key=lambda b: (abs(b["n"] - 24), b["cy"], b["cx"]))

    # --- Map walkable + snake interaction ---
    guid, g, d, _, _ = enter_l2(2)
    # flush enter with same dir
    d = act(guid, 2)
    guid = d["guid"]
    g = plane(d)
    a0 = actor(g)
    print("L2 actor after enter+D", a0, "e8", e8(g))

    # March each direction recording actor
    marches = {}
    for aid, name in [(4, "R"), (3, "L"), (2, "D"), (1, "U")]:
        guid, g, _, _, _ = enter_l2(aid)
        log = []
        for i in range(14):
            d = act(guid, aid)
            guid = d["guid"]
            g2 = plane(d)
            log.append({
                "i": i,
                "body": body_ndiff(g, g2),
                "actor": actor(g2),
                "movers": track_movers(g, g2)[:2],
                "e8": e8(g2),
                "levels": d.get("levels_completed"),
                "c2n": int(np.sum(g2 == 2)),
            })
            print(name, i, log[-1]["body"], log[-1]["actor"], log[-1]["e8"], "lv", log[-1]["levels"])
            g = g2
            if (d.get("levels_completed") or 0) >= 2:
                break
        marches[name] = log
    result["marches"] = {k: {"end": v[-1], "moves": [e for e in v if e["body"] > 20][:10], "len": len(v)} for k, v in marches.items()}

    # Find if stepping on 8 shrinks
    shrink_events = []
    for name, log in marches.items():
        prev_n = None
        for e in log:
            n = e["e8"].get("n", 0)
            if prev_n is not None and n < prev_n:
                shrink_events.append({"dir": name, "entry": e, "from": prev_n, "to": n})
            prev_n = n
    result["shrink_events"] = shrink_events
    print("shrink_events", shrink_events)

    # --- Clear attempts ---
    trials = {}

    def trial(name, seq_builder):
        guid, g, d, _, _ = enter_l2(4)
        # optional: seq_builder can use initial actor
        seq = seq_builder(actor(g), e8(g))
        log = []
        for i, aid in enumerate(seq):
            d = act(guid, aid)
            guid = d["guid"]
            g2 = plane(d)
            log.append({
                "i": i,
                "a": aid,
                "body": body_ndiff(g, g2),
                "actor": actor(g2),
                "e8": e8(g2),
                "levels": d.get("levels_completed"),
                "state": d.get("state"),
                "c2": ccs(g2, 2, 7, 56, 8, 40)[:3],
                "c9": [b for b in ccs(g2, 9, 7, 56, 15, 40)][:4],
            })
            g = g2
            if (d.get("levels_completed") or 0) >= 2:
                print(name, "CLEAR", log[-1])
                break
        print(name, "max", max(e["levels"] for e in log), "end", log[-1]["actor"], log[-1]["e8"])
        trials[name] = log
        return log

    # Explore based on marches — build open paths
    trial("R_A5_D_R", lambda a, e: [4] * 10 + [5] + [2] * 12 + [4] * 8 + [3] * 4)
    trial("D_R_D_R", lambda a, e: [2] * 10 + [4] * 10 + [2] * 8 + [4] * 8)
    trial("L_D_R", lambda a, e: [3] * 8 + [2] * 10 + [4] * 12)
    trial("U_R_D", lambda a, e: [1] * 6 + [4] * 10 + [2] * 12 + [4] * 6)
    trial("A5_clock", lambda a, e: [5] * 3 + [4] * 8 + [2] * 10 + [4] * 8)

    # If we know actor is c2 at some spawn, go toward south goal-like c9
    def greedy_seq(a, e):
        # just emit a long mixed exploration
        return [2, 2, 2, 4, 4, 4, 2, 2, 4, 4, 5, 2, 2, 2, 4, 4, 4, 4, 3, 3, 2, 2, 4, 4, 4, 2, 2, 2, 4, 4] * 2

    trial("mixed", greedy_seq)

    # Touch 8 clusters: from marches, if R hits shrink, latch A5
    if shrink_events:
        se = shrink_events[0]
        # approximate presses from that march
        trial("shrink_latch", lambda a, e: [4] * 12 + [5] + [2] * 14 + [4] * 10 + [3] * 4)

    cleared = any(max(e["levels"] for e in log) >= 2 for log in trials.values())
    result["cleared"] = cleared
    result["trials"] = {
        k: {
            "max_lv": max(e["levels"] for e in v),
            "end": v[-1],
            "len": len(v),
            "moved": [e for e in v if e["body"] > 20][:12],
        }
        for k, v in trials.items()
    }
    result["actor_color"] = actor_color
    result["l2_summary"] = payload["summary"]

    L2_CLEAR.write_text(json.dumps({
        "cleared": cleared,
        "actor_color": actor_color,
        "directions": dir_rows,
        "marches": result["marches"],
        "shrink_events": shrink_events,
        "trials": result["trials"],
        "raw_trials": trials,
    }, indent=2, default=str), encoding="utf-8")
    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print("CLEARED", cleared, "actor_color", actor_color)
    print("wrote", L2_FRAME, L2_CLEAR)

    s.post(
        f"{BASE}/api/scorecard/close",
        headers=H(key, True),
        json={"card_id": card},
        timeout=15,
    )


if __name__ == "__main__":
    main()
