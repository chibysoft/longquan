"""More post-S6044 chains seeking d14<25."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.r11l_l2_clear_probe import step_budget
from tools.r11l_l2_probe import ships
from tools._l3_posts6044_probe import boot_s6044
from tools._l3_savebud_probe import move14

GOAL14, GOAL15 = (55, 53), (34, 57)

CHAINS = [
    ("N6032_S6050", [("N", (60, 32)), ("S", (60, 50))]),
    ("N6032_S6048", [("N", (60, 32)), ("S", (60, 48))]),
    ("N6034_S6052", [("N", (60, 34)), ("S", (60, 52))]),
    ("N5838_S5850", [("N", (58, 38)), ("S", (58, 50))]),
    ("N5536_S5550", [("N", (55, 36)), ("S", (55, 50))]),
    ("N6038_S6046_S6050", [("N", (60, 38)), ("S", (60, 46)), ("S", (60, 50))]),
    ("N4844_S6050", [("N", (48, 44)), ("S", (60, 50))]),
    ("S5242_N6038", [("S", (52, 42)), ("N", (60, 38))]),
    ("N4232_S5550", [("N", (42, 32)), ("S", (55, 50))]),
    ("triple", [("N", (60, 38)), ("S", (60, 48)), ("N", (55, 40))]),
]


def main():
    hits = []
    for name, steps in CHAINS:
        print(f"\n===== {name} =====", flush=True)
        sess, data, ok = boot_s6044()
        if not ok:
            print("boot fail", flush=True)
            continue
        for who, tgt in steps:
            if step_budget(data["frame"]) < 2:
                print("budout", flush=True)
                break
            data, st = move14(sess, data, who, tgt)
            if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                print("DEAD", flush=True)
                break
            if st != "moved":
                print(f"SOFT {who}{tgt} {st}", flush=True)
                break
        if "frame" not in data:
            continue
        me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
        d14 = abs(me14["c"][0] - GOAL14[0]) + abs(me14["c"][1] - GOAL14[1])
        d15 = abs(me15["c"][0] - GOAL15[0]) + abs(me15["c"][1] - GOAL15[1])
        bud = step_budget(data["frame"])
        tag = "BEAT" if d14 < 25 else ("EQ25" if d14 == 25 else "")
        print(
            f"RESULT {tag} {name} ship={me14['c']} d14={d14} d15={d15} bud={bud}",
            flush=True,
        )
        hits.append((d14, -bud, name, me14["c"]))
    print("\n===== BEST =====", flush=True)
    for h in sorted(hits)[:8]:
        print(h, flush=True)


if __name__ == "__main__":
    main()
