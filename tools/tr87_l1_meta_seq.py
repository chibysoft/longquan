"""tr87 L1: watch available_actions / meta while dialing; try sequence from top reading.

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

OUT = ROOT / "tests/fixtures/tr87_l1_meta_seq.json"
SLOTS = (15, 22, 29, 36, 43)


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


def meta_snip(d):
    keys = [
        "levels_completed",
        "win_levels",
        "state",
        "available_actions",
        "score",
        "full_reset",
        "action_count",
        "steps",
    ]
    return {k: d.get(k) for k in keys if k in d or True}


def main():
    sess = Sess(_api_key())
    out = {"samples": []}
    try:
        sess.open()
        d = sess.reset()
        print("RESET keys:", sorted(d.keys()))
        print("RESET meta:", {k: d.get(k) for k in d if k != "frame"})
        out["reset_keys"] = sorted(d.keys())
        out["reset_meta"] = {k: d.get(k) for k in d if k != "frame"}

        g = plane(d["frame"])
        # Dial each slot through one ACT1 and record meta
        for si in range(5):
            d = sess.reset()
            g = plane(d["frame"])
            g, _, _ = move(sess, g, si)
            for step in range(3):
                d = sess.action("ACTION1")
                g = plane(d["frame"])
                snip = {
                    "slot": si,
                    "step": step,
                    "levels": d.get("levels_completed"),
                    "state": d.get("state"),
                    "acts": d.get("available_actions"),
                    "sel": sel(g),
                }
                # any extra non-frame fields
                extra = {k: d[k] for k in d if k not in ("frame", "guid", "game_id") and k not in snip}
                snip["extra_keys"] = sorted(extra.keys())
                out["samples"].append(snip)
                print(snip)

        # Try sequences inspired by top layout reading order:
        # Row-major over pairs: maybe action pattern from ink counts mod 4 + 1
        d = sess.reset()
        g = plane(d["frame"])
        ink_seq = []
        for y0 in (4, 13, 22):
            for x0 in (22, 46):
                patch = g[y0 + 1 : y0 + 6, x0 + 1 : x0 + 6]
                ink_seq.append(int((patch == 7).sum()))
        print("top7 ink counts", ink_seq)
        act_seq = [((c % 4) + 1) for c in ink_seq]
        print("try act_seq", act_seq)
        d = sess.reset()
        lv0 = d.get("levels_completed")
        for a in act_seq:
            d = sess.action(f"ACTION{a}")
        print("ink-mod seq lv", lv0, "->", d.get("levels_completed"))

        # try: 1,2 alternating while walking slots 0..4 twice
        trials = [
            ("walk_flip1", [4, 1, 4, 1, 4, 1, 4, 1, 4, 1]),
            ("walk_flip2", [4, 2, 4, 2, 4, 2, 4, 2, 4, 2]),
            ("all1_then_walk", [1, 1, 1, 1, 1, 1, 1, 4, 4, 4, 4]),
            ("spiral", [1, 4, 2, 4, 1, 4, 2, 4, 1]),
            ("only3x5", [3, 3, 3, 3, 3]),
            ("only4x5", [4, 4, 4, 4, 4]),
            ("121212", [1, 2, 1, 2, 1, 2, 1, 2]),
            ("12341234", [1, 2, 3, 4, 1, 2, 3, 4]),
            ("43214321", [4, 3, 2, 1, 4, 3, 2, 1]),
            # set every slot +1 then check: nav pattern
            ("each_slot_one_1", [1, 4, 1, 4, 1, 4, 1, 4, 1]),
        ]
        results = []
        for name, seq in trials:
            d = sess.reset()
            lv0 = d.get("levels_completed")
            for a in seq:
                d = sess.action(f"ACTION{a}")
            lv1 = d.get("levels_completed")
            cleared = int(lv1 or 0) > int(lv0 or 0)
            print(f"  {name}: lv {lv0}->{lv1} clear={cleared}")
            results.append({"name": name, "seq": seq, "lv0": lv0, "lv1": lv1, "cleared": cleared})
            if cleared:
                (ROOT / "tests/fixtures/tr87_l1_clear_frame.json").write_text(
                    json.dumps({"frame": d["frame"], "levels": lv1, "seq": seq, "name": name}, indent=2),
                    encoding="utf-8",
                )
                break
        out["trials"] = results

        # Deeper: for each slot, apply n flips where n = index of matching top7 in cycle
        # (already know slot0 needs 2 for top7(22,4), slot1 needs ... for (22,13))
        # Then press a candidate 'submit' — but only 1-4 exist. Maybe double-tap same?
        # Or navigate to a slot and press both 1 and 2 (=noop) as submit?
        print("\n## after aligning slot0+1 to left top7, try submit-ish")
        d = sess.reset()
        g = plane(d["frame"])
        lv0 = d.get("levels_completed")
        actions = []
        # slot0: 2x ACT1 from earlier
        for a in [1, 1]:
            d = sess.action(f"ACTION{a}")
            g = plane(d["frame"])
            actions.append(a)
        # move to slot1
        g, nav, _ = move(sess, g, 1)
        actions.extend(nav)
        # slot1: from couple_hunt, steps=-1 means 1x ACT2
        d = sess.action("ACTION2")
        g = plane(d["frame"])
        actions.append(2)
        # try various endings
        endings = [
            [],
            [1, 2],
            [2, 1],
            [3],
            [4],
            [3, 4],
            [4, 3],
            [1],
            [2],
            [1, 1, 1, 1, 1, 1, 1],  # full period
        ]
        end_results = []
        base = list(actions)
        for end in endings:
            d = sess.reset()
            g = plane(d["frame"])
            for a in base + end:
                d = sess.action(f"ACTION{a}")
                g = plane(d["frame"])
            lv1 = d.get("levels_completed")
            print(f"  end={end} lv {lv0}->{lv1}")
            end_results.append({"end": end, "lv1": lv1})
            if int(lv1 or 0) > int(lv0 or 0):
                print("CLEAR")
                break
        out["align_submit"] = {"base": base, "ends": end_results}

        out["reading"] = (
            "L1_CLEAR"
            if any(r.get("cleared") for r in results)
            or any(int(e.get("lv1") or 0) > int(lv0 or 0) for e in end_results)
            else "META_PARTIAL"
        )
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("READING:", out["reading"])
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
