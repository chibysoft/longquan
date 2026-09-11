"""g50t L4: careful buffer-flush D from y40 cells; watch land on y46.

Also dump c2 after 5228 visit; try (28,40) D with settle. tags=["g50t_recon"]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from collections import deque

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
)

OUT = ROOT / "tests/fixtures/g50t_l4_y40_down.json"
TO_3434 = [1, 1, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2]
TO_BOTTOM = [1, 1, 1, 1, 1, 1, 2, 2, 4, 1, 1, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2]
TO_TIP2 = TO_BOTTOM + [3, 3, 3, 3, 3, 1]
TIP1_LEAVE = TO_3434 + [4, 4, 3, 3]
L3_WEST_CLEAR = TO_TIP2 + [3, 3, 1, 1, 1, 1, 1, 4, 4, 1, 1, 1]
TIP_A5 = [2, 2, 2, 4, 2, 5, 5]
TIP_LEAVE = [2, 2, 2, 4, 2, 1, 1]
TO_1040 = [3, 3, 1, 1, 3, 3, 3, 2, 2, 2, 2, 2, 2]


def p(*a, **k):
    print(*a, **k, flush=True)


def einfo(g):
    e = dict(e8(g))
    ys, xs = np.where(g == 8)
    if len(xs):
        e.update(xmin=int(xs.min()), xmax=int(xs.max()), ymin=int(ys.min()), ymax=int(ys.max()))
    return e


def comps(g, val):
    mask = g == val
    vis = np.zeros_like(mask)
    out = []
    for y in range(64):
        for x in range(64):
            if not mask[y, x] or vis[y, x]:
                continue
            q = deque([(y, x)])
            vis[y, x] = True
            pts = []
            while q:
                cy, cx = q.popleft()
                pts.append((cy, cx))
                for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < 64 and 0 <= nx < 64 and mask[ny, nx] and not vis[ny, nx]:
                        vis[ny, nx] = True
                        q.append((ny, nx))
            out.append(
                (
                    len(pts),
                    round(float(np.mean([pt[1] for pt in pts])), 1),
                    round(float(np.mean([pt[0] for pt in pts])), 1),
                )
            )
    return sorted(out, reverse=True)


def cell(g, x, y):
    sub = g[max(0, int(y) - 2) : int(y) + 3, max(0, int(x) - 2) : int(x) + 3]
    return {
        "n5": int((sub == 5).sum()),
        "n15": int((sub == 15).sum()),
        "n0": int((sub == 0).sum()),
        "n8": int((sub == 8).sum()),
        "n9": int((sub == 9).sum()),
    }


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
    p("opened", gid)
    nact = [0]
    results = []

    def reset():
        return s.post(
            f"{BASE}/api/cmd/RESET",
            headers=H(key, True),
            json={"card_id": card, "game_id": gid},
            timeout=30,
        ).json()

    def act(guid, aid):
        nact[0] += 1
        d = s.post(
            f"{BASE}/api/cmd/ACTION{aid}",
            headers=H(key, True),
            json={"game_id": gid, "guid": guid},
            timeout=30,
        ).json()
        if "guid" not in d:
            p("  FAIL", nact[0], {k: d.get(k) for k in d if k != "frame"})
        return d

    def play(guid, g, prev, seq, stop_lv=None, quiet=True):
        d = {"guid": guid}
        for a_ in seq:
            d = act(guid, a_)
            if "guid" not in d:
                return guid, g, prev, d, False, True
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if not quiet:
                p(" ", a_, (prev["cx"], prev["cy"]) if prev else None, "e8", e8(g)["n"])
            lv = d.get("levels_completed") or 0
            if stop_lv is not None and lv >= stop_lv:
                return guid, g, prev, d, True, False
            if lv > 3:
                return guid, g, prev, d, True, False
        return guid, g, prev, d, False, False

    def boot_1040():
        d = reset()
        nact[0] = 0
        guid = d["guid"]
        g = plane(d)
        prev = None
        guid, g, prev, d, ok, dead = play(guid, g, prev, L1_SEQ + [2] * 4 + [4] * 8, stop_lv=1)
        d = act(guid, 3)
        guid, g, prev = d["guid"], plane(d), actor(plane(d), prev)
        guid, g, prev, d, ok, dead = play(guid, g, prev, TO_2840 + L2_ROUTE, stop_lv=2)
        d = act(guid, 3)
        guid, g, prev = d["guid"], plane(d), actor(plane(d), prev)
        guid, g, prev, d, ok, dead = play(guid, g, prev, TO_3434 + [4, 4, 5, 5])
        if (d.get("levels_completed") or 0) < 3 and not dead:
            guid, g, prev, d, ok, dead = play(guid, g, prev, TO_3434 + [4, 4, 3, 3])
        guid, g, prev, d, ok, dead = play(guid, g, prev, TO_TIP2 + [5, 5])
        if (d.get("levels_completed") or 0) < 3 and not dead:
            guid, g, prev, d, ok, dead = play(guid, g, prev, TIP1_LEAVE)
            guid, g, prev, d, ok, dead = play(guid, g, prev, L3_WEST_CLEAR, stop_lv=3)
        d = act(guid, 4)
        guid, g, prev = d["guid"], plane(d), actor(plane(d), None)
        guid, g, prev, d, ok, dead = play(guid, g, prev, TIP_A5 + TIP_LEAVE, quiet=False)
        guid, g, prev, d, ok, dead = play(guid, g, prev, TO_1040, quiet=False)
        ok = e8(g)["n"] == 36 and abs(prev["cx"] - 10) < 1 and abs(prev["cy"] - 40) < 1
        p("at1040", ok, (prev["cx"], prev["cy"]), einfo(g), "c2", comps(g, 2)[:4])
        return guid, g, prev, d, ok

    def flush(guid, g, prev, n=2):
        """Send noop-ish: repeat last direction by U then back — use L L if facing dead end.
        Better: send same action that is blocked to clear pending.
        From known pos, send U then D to settle if U works, else L R.
        """
        pos0 = (prev["cx"], prev["cy"])
        for a_ in (1, 2, 1, 2):
            d = act(guid, a_)
            if "guid" not in d:
                return guid, g, prev, d
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            if (prev["cx"], prev["cy"]) == pos0 and a_ == 2:
                # bounced back — flushed
                break
        # force return to pos0
        for _ in range(4):
            if (prev["cx"], prev["cy"]) == pos0:
                break
            x, y = prev["cx"], prev["cy"]
            tx, ty = pos0
            a_ = 4 if tx > x else 3 if tx < x else (2 if ty > y else 1)
            d = act(guid, a_)
            if "guid" not in d:
                break
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        p("  flushed", (prev["cx"], prev["cy"]))
        return guid, g, prev, d

    # Test D from each x on y40
    for name, prep in [
        ("x10", []),
        ("x16", [4, 4]),
        ("x22", [4, 4, 4, 4]),
        ("x28", [4, 4, 4, 4, 4, 4]),
    ]:
        p(f"## D from {name}")
        guid, g, prev, d, ok = boot_1040()
        if not ok:
            results.append({"name": name, "ok": False})
            continue
        for a_ in prep:
            d = act(guid, a_)
            if "guid" not in d:
                break
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
        guid, g, prev, d = flush(guid, g, prev)
        pos = (prev["cx"], prev["cy"])
        p("  settled", pos, cell(g, pos[0], pos[1]))
        # pure D D D
        for i in range(3):
            before = (prev["cx"], prev["cy"])
            d = act(guid, 2)
            if "guid" not in d:
                break
            guid = d["guid"]
            g = plane(d)
            prev = actor(g, prev)
            pos = (prev["cx"], prev["cy"])
            p("  D", i, before, "->", pos, cell(g, pos[0], pos[1]), "lv", d.get("levels_completed"))
            if pos[1] > 40:
                p("  *** CROSSED y40", pos)
                # push to goal
                for a_ in [2, 2, 3, 3, 3, 2, 3, 1, 2]:
                    d = act(guid, a_)
                    if "guid" not in d:
                        break
                    guid = d["guid"]
                    g = plane(d)
                    prev = actor(g, prev)
                    p("  +", a_, (prev["cx"], prev["cy"]), "lv", d.get("levels_completed"))
                    if (d.get("levels_completed") or 0) > 3:
                        p("  *** CLEAR")
                        break
                break
            if (d.get("levels_completed") or 0) > 3:
                break
        results.append(
            {
                "name": name,
                "final": (prev["cx"], prev["cy"]),
                "lv": d.get("levels_completed"),
                "c2": comps(g, 2)[:4],
            }
        )
        if (d.get("levels_completed") or 0) > 3:
            break

    # After 5228 visit, check c2 for new markers
    if (d.get("levels_completed") or 0) <= 3:
        p("## 5228 then c2 scan")
        guid, g, prev, d, ok = boot_1040()
        if ok:
            # back to top then rightcol
            seq = [1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 2, 2, 2, 2]
            # better from 1040: U to top, R... actually from 10,40 U to 10,10 R to 28 then path
            seq = [1, 1, 1, 1, 1, 4, 4, 4, 2, 4, 1, 1, 4, 4, 2, 2, 2, 2]
            for a_ in seq:
                d = act(guid, a_)
                if "guid" not in d:
                    break
                guid = d["guid"]
                g = plane(d)
                prev = actor(g, prev)
            p("  at", (prev["cx"], prev["cy"]), "c2", comps(g, 2)[:6], "c15", int((g == 15).sum()))

    out = {"results": results, "nact": nact[0], "cleared": any((r.get("lv") or 0) > 3 for r in results)}
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    p("READING", out)
    s.post(f"{BASE}/api/scorecard/close", headers=H(key, True), json={"card_id": card}, timeout=15)


if __name__ == "__main__":
    main()
