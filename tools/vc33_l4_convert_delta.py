"""L4: exact cell delta on left 1→12 convert frame."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l3_probe import Sess, pads_sorted, plane  # noqa: E402
from tools.vc33_l4_pad_map import components, enter_l4, sprite  # noqa: E402

OUT = ROOT / "tests/fixtures/vc33_l4_convert_delta.json"


def click(sess, x, y):
    return sess.click(int(x), int(y))


def pad(sess, d, g, x0):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
    return d2, plane(d2["frame"])


def main():
    key = _api_key()
    sess = Sess(key)
    try:
        sess.open()
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        d, g = pad(sess, d, g, 15)  # pre
        g_pre = g.copy()
        sp_pre = sprite(g_pre)
        d, g = pad(sess, d, g, 15)  # convert
        g_post = g
        sp_post = sprite(g_post)

        diff = np.argwhere(g_pre != g_post)
        cells = []
        for y, x in diff:
            cells.append({
                "x": int(x), "y": int(y),
                "a": int(g_pre[y, x]), "b": int(g_post[y, x]),
            })
        # summarize transitions
        from collections import Counter
        trans = Counter((c["a"], c["b"]) for c in cells)
        print("sprite pre", sp_pre)
        print("sprite post", sp_post)
        print("n_diff", len(cells))
        print("transitions", dict(trans))
        # show non-sprite-ish diffs (not 3↔4, 3↔11, 4↔3, 11↔3)
        interesting = [c for c in cells if (c["a"], c["b"]) not in ((3, 4), (4, 3), (3, 11), (11, 3), (4, 11), (11, 4))]
        print("interesting n", len(interesting))
        for c in interesting[:80]:
            print(f"  ({c['x']},{c['y']}) {c['a']}→{c['b']}")
        # focus y45 and window cols
        y45 = [c for c in cells if c["y"] == 45]
        print("y45 changes", y45)
        win = [c for c in cells if 12 <= c["x"] <= 14]
        print("window col changes n", len(win), "sample", win[:5])

        OUT.write_text(json.dumps({
            "transitions": {str(k): v for k, v in trans.items()},
            "interesting": interesting,
            "y45": y45,
            "sp_pre": sp_pre,
            "sp_post": sp_post,
        }, indent=2), encoding="utf-8")
        print("wrote", OUT, "lv", d.get("levels_completed"))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
