"""tr87 L1: region diffs for ACTION1-4 (top/mid/bot). tags=["tr87_recon"]"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.tr87_recon_probe import Sess, plane  # noqa: E402

OUT = ROOT / "tests/fixtures/tr87_l1_region_diff.json"


def bbox_ch(a, b, mask=None):
    d = a != b
    if mask is not None:
        d = d & mask
    ys, xs = np.where(d)
    if len(ys) == 0:
        return None, {}
    ch = {}
    for y, x in zip(ys, xs):
        k = f"{int(a[y, x])}->{int(b[y, x])}"
        ch[k] = ch.get(k, 0) + 1
    return (int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max()), int(len(ys))), ch


def main():
    sess = Sess(_api_key())
    out = {"acts": {}, "slot2_act1": {}}
    try:
        sess.open()
        for act in (1, 2, 3, 4):
            d = sess.reset()
            g0 = plane(d["frame"])
            lv0 = d.get("levels_completed")
            d = sess.action(f"ACTION{act}")
            g1 = plane(d["frame"])
            entry = {"levels": [lv0, d.get("levels_completed")], "nd": int((g0 != g1).sum()), "regions": {}}
            for name, ys, ye in [("top", 0, 33), ("mid", 34, 47), ("bot", 48, 62)]:
                mask = np.zeros_like(g0, dtype=bool)
                mask[ys : ye + 1, :] = True
                bb, ch = bbox_ch(g0, g1, mask)
                entry["regions"][name] = {"bbox": bb, "ch": ch}
                print(f"ACT{act} {name}: bbox={bb} ch={ch}")
            print(f"  levels {lv0}->{d.get('levels_completed')} nd={entry['nd']}")
            out["acts"][str(act)] = entry

        print("--- on slot2 ACT1 ---")
        d = sess.reset()
        g0 = plane(d["frame"])
        for _ in range(2):
            d = sess.action("ACTION4")
            g0 = plane(d["frame"])
        xs = [int(x) for y, x in np.argwhere(g0 == 0)]
        print("sel x0", min(xs) if xs else None)
        before = g0.copy()
        d = sess.action("ACTION1")
        g1 = plane(d["frame"])
        for name, ys, ye in [("top", 0, 33), ("mid", 34, 47), ("bot", 48, 62)]:
            mask = np.zeros_like(g0, dtype=bool)
            mask[ys : ye + 1, :] = True
            bb, ch = bbox_ch(before, g1, mask)
            out["slot2_act1"][name] = {"bbox": bb, "ch": ch}
            print(f"  {name}: {bb} {ch}")

        # Extract top7 correctly at x22, x46
        d = sess.reset()
        g = plane(d["frame"])
        print("## top7 @22/46")
        top7 = []
        for y0 in (4, 13, 22):
            for x0 in (22, 46):
                patch = g[y0 + 1 : y0 + 6, x0 + 1 : x0 + 6]
                sig = tuple(int(v) for v in patch.ravel())
                asc = ["".join(str(int(v)) for v in row) for row in patch]
                top7.append({"x0": x0, "y0": y0, "ascii": asc})
                print(f"  @({x0},{y0})")
                for line in asc:
                    print("   ", line)
        out["top7"] = top7

        # Walk slot0 ACT1 cycle; which top7 appear?
        def bottom_glyph(gg, si, slots=(15, 22, 29, 36, 43)):
            x0 = slots[si]
            return tuple(int(v) for v in gg[52:57, x0 : x0 + 5].ravel())

        d = sess.reset()
        g = plane(d["frame"])
        start = bottom_glyph(g, 0)
        seen = {start: 0}
        seq = [start]
        for step in range(1, 10):
            d = sess.action("ACTION1")
            g = plane(d["frame"])
            sig = bottom_glyph(g, 0)
            seq.append(sig)
            if sig in seen:
                break
            seen[sig] = step
        set0 = set(seq)
        hits = []
        for t in top7:
            sig = tuple(int(c) for line in t["ascii"] for c in line)
            hits.append({"pos": (t["x0"], t["y0"]), "in_cycle": sig in set0})
        print("top7 in slot0 ACT1 cycle:", hits)
        out["top7_in_slot0_cycle"] = hits

        # Also: does any bottom reset glyph equal any top7?
        d = sess.reset()
        g = plane(d["frame"])
        bots = [bottom_glyph(g, i) for i in range(5)]
        for i, b in enumerate(bots):
            for t in top7:
                sig = tuple(int(c) for line in t["ascii"] for c in line)
                if b == sig:
                    print(f"RESET B{i} == top7@{t['x0']},{t['y0']}")

        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
