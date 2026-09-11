"""tr87 L1: online 7x7 torus scan on slot3×slot4 after fixing 0/1 to left top7.

tags=["tr87_recon"]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.tr87_recon_probe import Sess, plane  # noqa: E402

OUT = ROOT / "tests/fixtures/tr87_l1_torus34.json"
SLOTS = (15, 22, 29, 36, 43)


def bg(g, si):
    x0 = SLOTS[si]
    return tuple(int(v) for v in g[52:57, x0 : x0 + 5].ravel())


def sel(g):
    xs = [int(x) for y, x in np.argwhere(g == 0)]
    if not xs:
        return None
    return int(np.argmin([abs(min(xs) - s) for s in SLOTS]))


def move(sess, g, ti):
    acts = []
    for _ in range(8):
        cur = sel(g)
        if cur == ti:
            return g, acts, True
        a = 4 if (ti - cur) % 5 <= (cur - ti) % 5 else 3
        d = sess.action(f"ACTION{a}")
        g = plane(d["frame"])
        acts.append(a)
    return g, acts, False


def go(sess, g, a):
    d = sess.action(f"ACTION{a}")
    return plane(d["frame"]), d


def main():
    sess = Sess(_api_key())
    out = {}
    try:
        sess.open()
        d = sess.reset()
        g = plane(d["frame"])
        t04 = tuple(int(v) for v in g[5:10, 23:28].ravel())
        t13 = tuple(int(v) for v in g[14:19, 23:28].ravel())

        # Build base: slot0 -> t04, slot1 -> t13
        d = sess.reset()
        g = plane(d["frame"])
        lv0 = d.get("levels_completed")
        actions = []

        # slot0 ACT1 until match (max 7)
        for n in range(8):
            if bg(g, 0) == t04:
                break
            g, d = go(sess, g, 1)
            actions.append(1)
        assert bg(g, 0) == t04, "slot0 fail"

        g, nav, _ = move(sess, g, 1)
        actions.extend(nav)
        for n in range(8):
            if bg(g, 1) == t13:
                break
            # try ACT2 first direction from couple_hunt
            g, d = go(sess, g, 2)
            actions.append(2)
        if bg(g, 1) != t13:
            # undo-ish: reset path with ACT1
            d = sess.reset()
            g = plane(d["frame"])
            actions = []
            for _ in range(8):
                if bg(g, 0) == t04:
                    break
                g, d = go(sess, g, 1)
                actions.append(1)
            g, nav, _ = move(sess, g, 1)
            actions.extend(nav)
            for _ in range(8):
                if bg(g, 1) == t13:
                    break
                g, d = go(sess, g, 1)
                actions.append(1)
        assert bg(g, 1) == t13, "slot1 fail"
        print("base ok", "nact", len(actions), "lv", d.get("levels_completed"))
        base_actions = list(actions)

        # Torus on 3 x 4
        d = sess.reset()
        g = plane(d["frame"])
        for a in base_actions:
            g, d = go(sess, g, a)
        # ensure on slot3
        g, nav, _ = move(sess, g, 3)
        cleared = False
        hit = None
        scanned = 0
        for i3 in range(7):
            # at slot3, phase i3 (0=after base)
            g, nav4, _ = move(sess, g, 4)
            for i4 in range(7):
                scanned += 1
                lv = d.get("levels_completed")
                if int(lv or 0) > int(lv0 or 0):
                    cleared = True
                    hit = {"i3": i3, "i4": i4, "lv": lv}
                    print("*** CLEAR", hit)
                    (ROOT / "tests/fixtures/tr87_l1_clear_frame.json").write_text(
                        json.dumps({"frame": d["frame"], "levels": lv, "i3": i3, "i4": i4}, indent=2),
                        encoding="utf-8",
                    )
                    break
                g, d = go(sess, g, 1)  # advance slot4
            if cleared:
                break
            # back to slot3, advance
            g, _, _ = move(sess, g, 3)
            g, d = go(sess, g, 1)
            if scanned % 7 == 0:
                print(f"  scanned {scanned}")
        print("torus scanned", scanned, "cleared", cleared)

        # Also torus slot2 x slot3 with 0/1 fixed, 4 left alone
        if not cleared:
            print("\n## torus slot2 x slot3")
            d = sess.reset()
            g = plane(d["frame"])
            for a in base_actions:
                g, d = go(sess, g, a)
            g, _, _ = move(sess, g, 2)
            scanned2 = 0
            for i2 in range(7):
                g, _, _ = move(sess, g, 3)
                for i3 in range(7):
                    scanned2 += 1
                    lv = d.get("levels_completed")
                    if int(lv or 0) > int(lv0 or 0):
                        cleared = True
                        hit = {"i2": i2, "i3": i3, "lv": lv}
                        print("*** CLEAR", hit)
                        break
                    g, d = go(sess, g, 1)
                if cleared:
                    break
                g, _, _ = move(sess, g, 2)
                g, d = go(sess, g, 1)
            print("torus23 scanned", scanned2, "cleared", cleared)

        # Full-ish: with 0/1 fixed, scan slot2 for all 7 and check levels alone
        if not cleared:
            print("\n## slot2 alone cycle")
            d = sess.reset()
            g = plane(d["frame"])
            for a in base_actions:
                g, d = go(sess, g, a)
            g, _, _ = move(sess, g, 2)
            for i2 in range(8):
                lv = d.get("levels_completed")
                print(f"  i2={i2} lv={lv}")
                if int(lv or 0) > int(lv0 or 0):
                    cleared = True
                    hit = {"i2": i2, "lv": lv}
                    break
                g, d = go(sess, g, 1)

        out.update(
            {
                "base_actions": base_actions,
                "cleared": cleared,
                "hit": hit,
                "reading": "L1_CLEAR" if cleared else "TORUS_EMPTY",
            }
        )
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("READING:", out["reading"])
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
