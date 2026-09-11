"""tr87: enumerate ACTION1–4 from L1 RESET; record frame/levels/acts deltas.

tags=["tr87_recon"]. Fresh RESET per action.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.tr87_recon_probe import Sess, plane, summarize, ascii_preview  # noqa: E402
from tools.ls20_online_validate import _api_key  # noqa: E402

OUT = ROOT / "tests/fixtures/tr87_l1_action_enum.json"
TAGS = ["tr87_recon"]


def body_ndiff(a, b):
    return int(np.sum(a != b))


def body_changes(a, b):
    m = a != b
    ys, xs = np.where(m)
    hist = Counter()
    for y, x in zip(ys.tolist(), xs.tolist()):
        hist[(int(a[y, x]), int(b[y, x]))] += 1
    return {f"{a_}->{b_}": n for (a_, b_), n in hist.most_common(20)}


def main():
    key = _api_key()
    sess = Sess(key)
    rows = []
    try:
        sess.open()
        for act in (1, 2, 3, 4):
            d0 = sess.reset()
            g0 = plane(d0["frame"])
            s0 = summarize(g0, d0)
            name = f"ACTION{act}"
            d1 = sess.action(name)
            g1 = plane(d1["frame"])
            s1 = summarize(g1, d1)
            nd = body_ndiff(g0, g1)
            ch = body_changes(g0, g1) if nd else {}
            row = {
                "action": name,
                "nd": nd,
                "ch": ch,
                "lv0": d0.get("levels_completed"),
                "lv1": d1.get("levels_completed"),
                "acts0": d0.get("available_actions"),
                "acts1": d1.get("available_actions"),
                "state0": d0.get("state"),
                "state1": d1.get("state"),
                "hist0": s0["hist"],
                "hist1": s1["hist"],
                "preview1": ascii_preview(g1)[:24],
            }
            rows.append(row)
            print(
                f"| {name} | nd={nd} | lv {row['lv0']}->{row['lv1']} "
                f"| acts {row['acts0']}->{row['acts1']} | state {row['state1']} | ch={ch}"
            )
            for line in row["preview1"][:12]:
                print(" ", line)

        # also try 2-step: each pair ACTIONi then ACTIONj once (sample)
        print("\n## 2-step sample")
        for a, b in ((1, 2), (2, 1), (1, 1), (3, 4), (4, 3)):
            d0 = sess.reset()
            g0 = plane(d0["frame"])
            d1 = sess.action(f"ACTION{a}")
            g1 = plane(d1["frame"])
            d2 = sess.action(f"ACTION{b}")
            g2 = plane(d2["frame"])
            row = {
                "seq": [a, b],
                "nd01": body_ndiff(g0, g1),
                "nd12": body_ndiff(g1, g2),
                "nd02": body_ndiff(g0, g2),
                "ch02": body_changes(g0, g2) if body_ndiff(g0, g2) else {},
                "lv": d2.get("levels_completed"),
                "acts": d2.get("available_actions"),
                "state": d2.get("state"),
            }
            rows.append({"two_step": row})
            print(
                f"| {a}->{b} | nd01={row['nd01']} nd12={row['nd12']} nd02={row['nd02']} "
                f"| lv={row['lv']} acts={row['acts']} | ch02={row['ch02']}"
            )

        OUT.write_text(
            json.dumps({"tags": TAGS, "rows": rows}, indent=2, default=str),
            encoding="utf-8",
        )
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
