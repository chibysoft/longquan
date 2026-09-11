"""tr87 L1: verify OR/AND checksum solutions; dial non-trivial ones."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.tr87_recon_probe import Sess, plane  # noqa: E402

OUT = ROOT / "tests/fixtures/tr87_l1_or_and.json"
SLOTS = (15, 22, 29, 36, 43)


def p(*a, **k):
    print(*a, **k, flush=True)


def phases_to_actions(phases):
    actions, cur = [], 0
    for si, ph in enumerate(phases):
        df, db = (si - cur) % 5, (cur - si) % 5
        actions.extend([4] * df if df <= db else [3] * db)
        cur = si
        actions.extend([1] * int(ph))
    return actions


def main():
    g0 = np.asarray(
        json.loads((ROOT / "tests/fixtures/tr87_l1_frame_live.json").read_text(encoding="utf-8"))["frame"]
    )
    if g0.ndim == 3:
        g0 = g0[0]
    mids = [(g0[41:46, x0 : x0 + 5] == 10).astype(np.uint8).ravel() for x0 in (15, 22, 29, 36, 43)]
    mo = np.zeros(25, dtype=np.uint8)
    ma = np.ones(25, dtype=np.uint8)
    for m in mids:
        mo |= m
        ma &= m
    p("OR(mids) ink", int(mo.sum()), "".join(str(int(x)) for x in mo))
    p("AND(mids) ink", int(ma.sum()), "".join(str(int(x)) for x in ma))

    sess = Sess(_api_key())
    out = {}
    try:
        sess.open()
        bit_cycles = []
        for si in range(5):
            d = sess.reset()
            g = plane(d["frame"])
            xs = [int(x) for y, x in np.argwhere(g == 0)]
            cur = int(np.argmin([abs(min(xs) - s) for s in SLOTS]))
            while cur != si:
                a = 4 if (si - cur) % 5 <= (cur - si) % 5 else 3
                d = sess.action(f"ACTION{a}")
                g = plane(d["frame"])
                xs = [int(x) for y, x in np.argwhere(g == 0)]
                cur = int(np.argmin([abs(min(xs) - s) for s in SLOTS]))
            start = tuple(int(v) for v in g[52:57, SLOTS[si] : SLOTS[si] + 5].ravel())
            bc = [(np.array(start).reshape(5, 5) == 7).astype(np.uint8).ravel()]
            sig = start
            for _ in range(6):
                d = sess.action("ACTION1")
                g = plane(d["frame"])
                sig = tuple(int(v) for v in g[52:57, SLOTS[si] : SLOTS[si] + 5].ravel())
                if sig == start:
                    break
                bc.append((np.array(sig).reshape(5, 5) == 7).astype(np.uint8).ravel())
            bit_cycles.append(bc)

        n_or = n_and = 0
        or_ex, and_ex = [], []
        for ph in np.ndindex(7, 7, 7, 7, 7):
            acc = np.zeros(25, dtype=np.uint8)
            for si in range(5):
                acc |= bit_cycles[si][ph[si]]
            if np.array_equal(acc, mo):
                n_or += 1
                if len(or_ex) < 8:
                    or_ex.append(ph)
            acc = np.ones(25, dtype=np.uint8)
            for si in range(5):
                acc &= bit_cycles[si][ph[si]]
            if np.array_equal(acc, ma):
                n_and += 1
                if len(and_ex) < 8:
                    and_ex.append(ph)
        p("n_or", n_or, "ex", or_ex[:5])
        p("n_and", n_and, "ex", and_ex[:5])
        out["n_or"] = n_or
        out["n_and"] = n_and
        out["or_ex"] = [list(x) for x in or_ex]
        out["and_ex"] = [list(x) for x in and_ex]
        out["mo_ink"] = int(mo.sum())
        out["ma_ink"] = int(ma.sum())

        # dial up to 6 distinct non-trivial
        cands = []
        for ph in or_ex:
            if ph != (0, 0, 0, 0, 0):
                cands.append(("or", ph))
        for ph in and_ex:
            if ph != (0, 0, 0, 0, 0):
                cands.append(("and", ph))
        cands = cands[:8]

        results = []
        seen = set()
        cleared = False
        for name, ph in cands:
            if ph in seen:
                continue
            seen.add(ph)
            acts = phases_to_actions(ph)
            d = sess.reset()
            g = plane(d["frame"])
            for a in acts:
                d = sess.action(f"ACTION{a}")
                g = plane(d["frame"])
            lv = d.get("levels_completed")
            p(f"dial {name} {ph} lv={lv}")
            for a in [4] * 5:
                d = sess.action(f"ACTION{a}")
                g = plane(d["frame"])
            lv2 = d.get("levels_completed")
            p(f"  +lap lv={lv2}")
            results.append({"name": name, "ph": list(ph), "lv": lv, "lv_lap": lv2, "actions": acts})
            if int(lv or 0) > 0 or int(lv2 or 0) > 0:
                cleared = True
                (ROOT / "tests/fixtures/tr87_l1_clear_frame.json").write_text(
                    json.dumps(
                        {"frame": d["frame"], "levels": max(int(lv or 0), int(lv2 or 0)), "ph": list(ph)},
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                break

        # Also try: intersection of OR and AND solution sets
        and_set = set(and_ex)  # incomplete - need full intersection count
        n_both = 0
        both_ex = []
        for ph in np.ndindex(7, 7, 7, 7, 7):
            acc = np.zeros(25, dtype=np.uint8)
            for si in range(5):
                acc |= bit_cycles[si][ph[si]]
            if not np.array_equal(acc, mo):
                continue
            acc = np.ones(25, dtype=np.uint8)
            for si in range(5):
                acc &= bit_cycles[si][ph[si]]
            if np.array_equal(acc, ma):
                n_both += 1
                if len(both_ex) < 5:
                    both_ex.append(ph)
        p("n_both OR&AND", n_both, "ex", both_ex)
        out["n_both"] = n_both
        out["both_ex"] = [list(x) for x in both_ex]

        if not cleared and both_ex:
            for ph in both_ex[:3]:
                acts = phases_to_actions(ph)
                d = sess.reset()
                g = plane(d["frame"])
                for a in acts:
                    d = sess.action(f"ACTION{a}")
                    g = plane(d["frame"])
                lv = d.get("levels_completed")
                p(f"dial both {ph} lv={lv}")
                results.append({"name": "both", "ph": list(ph), "lv": lv, "actions": acts})
                if int(lv or 0) > 0:
                    cleared = True
                    break

        out["results"] = results
        out["reading"] = "L1_CLEAR" if cleared else "OR_AND_PARTIAL"
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        p("READING:", out["reading"])
        p("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
