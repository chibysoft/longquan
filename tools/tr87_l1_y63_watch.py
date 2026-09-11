"""tr87 L1: dissect y63 color1→4 progress bar / hidden UI; hunt levels↑.

Observation from seq_from_top: after longer act sequences, hist shows color1↓
color4↑ and y63_n_diff grows. Single ACT after RESET often Δ=0.

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

OUT = ROOT / "tests/fixtures/tr87_l1_y63_watch.json"
CLEAR = ROOT / "tests/fixtures/tr87_l1_clear_frame.json"
SLOTS = (15, 22, 29, 36, 43)


def sel(g):
    xs = [int(x) for y, x in np.argwhere(g == 0)]
    if not xs:
        return None
    return int(np.argmin([abs(min(xs) - s) for s in SLOTS]))


def y63_row(g):
    return [int(v) for v in g[63, :].ravel()]


def y63_stats(g):
    row = np.asarray(y63_row(g))
    return {
        "n1": int((row == 1).sum()),
        "n4": int((row == 4).sum()),
        "other": {int(k): int(v) for k, v in zip(*np.unique(row, return_counts=True)) if int(k) not in (1, 4)},
        "first4": int(np.argmax(row == 4)) if (row == 4).any() else None,
        "last4": int(len(row) - 1 - np.argmax(row[::-1] == 4)) if (row == 4).any() else None,
        "run": "".join(str(int(v)) if v in (1, 4) else "X" for v in row),
    }


def bg(g, si):
    x0 = SLOTS[si]
    return tuple(int(v) for v in g[52:57, x0 : x0 + 5].ravel())


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


def snap(d, g, step, act):
    st = y63_stats(g)
    return {
        "step": step,
        "act": act,
        "lv": d.get("levels_completed"),
        "state": d.get("state"),
        "full_reset": d.get("full_reset"),
        "action_input": d.get("action_input"),
        "sel": sel(g),
        "n1": st["n1"],
        "n4": st["n4"],
        "first4": st["first4"],
        "last4": st["last4"],
        "run_head": st["run"][:20],
        "run_tail": st["run"][-20:],
    }


def run_trace(sess, seq, label):
    d = sess.reset()
    g = plane(d["frame"])
    trace = [snap(d, g, 0, None)]
    print(f"\n=== {label} reset n4={trace[0]['n4']} ===")
    for i, a in enumerate(seq, 1):
        d = sess.action(f"ACTION{a}")
        g = plane(d["frame"])
        s = snap(d, g, i, a)
        trace.append(s)
        if s["n4"] != trace[i - 1]["n4"] or s["lv"] != trace[i - 1]["lv"]:
            print(f"  step{i} ACT{a}: n4 {trace[i-1]['n4']}->{s['n4']} lv={s['lv']} sel={s['sel']} first4={s['first4']}")
        if s["lv"] and s["lv"] > 0:
            CLEAR.write_text(
                json.dumps(
                    {
                        "label": label,
                        "seq": seq[:i],
                        "levels_completed": s["lv"],
                        "frame": d["frame"],
                        "meta": {k: d.get(k) for k in d if k != "frame"},
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            print("*** L1_CLEAR ***", label, seq[:i])
            return trace, True, d
    print(f"  end n4={trace[-1]['n4']} lv={trace[-1]['lv']}")
    return trace, False, d


def main():
    sess = Sess(_api_key())
    out = {"traces": {}, "cleared": False, "findings": []}
    try:
        sess.open()

        # 1) Pure ACTION1 spam — does n4 grow every step?
        t, ok, _ = run_trace(sess, [1] * 64, "spam1_x64")
        out["traces"]["spam1_x64"] = t
        if ok:
            out["cleared"] = True

        # When does first color4 appear?
        first_hit = next((s for s in t if s["n4"] > 0), None)
        out["findings"].append({"spam1_first4": first_hit})
        print("spam1 first4 at", first_hit)

        # 2) Pure ACTION4 (nav only)
        if not out["cleared"]:
            t, ok, _ = run_trace(sess, [4] * 64, "spam4_x64")
            out["traces"]["spam4_x64"] = t
            out["findings"].append({"spam4_first4": next((s for s in t if s["n4"] > 0), None)})
            if ok:
                out["cleared"] = True

        # 3) Pure ACTION3
        if not out["cleared"]:
            t, ok, _ = run_trace(sess, [3] * 64, "spam3_x64")
            out["traces"]["spam3_x64"] = t
            out["findings"].append({"spam3_first4": next((s for s in t if s["n4"] > 0), None)})
            if ok:
                out["cleared"] = True

        # 4) Alternating 1/4
        if not out["cleared"]:
            t, ok, _ = run_trace(sess, [1, 4] * 32, "alt14_x64")
            out["traces"]["alt14_x64"] = t
            if ok:
                out["cleared"] = True

        # 5) Fill bar? keep going until n4==64 or lv↑ (cap 200)
        if not out["cleared"]:
            d = sess.reset()
            g = plane(d["frame"])
            seq = []
            trace = [snap(d, g, 0, None)]
            print("\n=== fill_to_64 with ACT1 ===")
            for i in range(1, 201):
                d = sess.action("ACTION1")
                g = plane(d["frame"])
                seq.append(1)
                s = snap(d, g, i, 1)
                trace.append(s)
                if i <= 5 or i % 10 == 0 or s["n4"] in (1, 32, 63, 64) or (s["lv"] or 0) > 0:
                    print(f"  i={i} n4={s['n4']} lv={s['lv']} first4={s['first4']} last4={s['last4']}")
                if (s["lv"] or 0) > 0:
                    out["cleared"] = True
                    CLEAR.write_text(
                        json.dumps({"label": "fill_act1", "seq": seq, "levels_completed": s["lv"], "frame": d["frame"]}, indent=2),
                        encoding="utf-8",
                    )
                    print("*** L1_CLEAR *** fill_act1")
                    break
                if s["n4"] >= 64:
                    print("  bar full n4=64 still lv", s["lv"])
                    break
            out["traces"]["fill_act1"] = [trace[0], *[s for s in trace if s["step"] in (1, 2, 3, 7, 14, 21, 32, 48, 63, 64) or s["n4"] in (0, 1, 32, 63, 64)]]
            out["findings"].append({"fill_act1_end": trace[-1], "n_steps": len(seq)})

        # 6) Does n4 track action_input / step count globally?
        # Compare: 7x ACT1 on slot0 vs 7x ACT1 after walking
        if not out["cleared"]:
            d = sess.reset()
            g = plane(d["frame"])
            # cycle one full period on each slot
            seq = []
            for si in range(5):
                g, macts, _ = move(sess, g, si)
                seq.extend(macts)
                for _ in range(7):
                    d = sess.action("ACTION1")
                    g = plane(d["frame"])
                    seq.append(1)
            s = snap(d, g, len(seq), 1)
            out["findings"].append({"full_period_all_slots": s, "n_acts": len(seq)})
            print(f"\nfull period all slots: n_acts={len(seq)} n4={s['n4']} lv={s['lv']}")
            if (s["lv"] or 0) > 0:
                out["cleared"] = True
                CLEAR.write_text(
                    json.dumps({"label": "full_period_all", "seq": seq, "levels_completed": s["lv"], "frame": d["frame"]}, indent=2),
                    encoding="utf-8",
                )

        # 7) action_input field — dump raw values along spam
        if not out["cleared"]:
            d = sess.reset()
            g = plane(d["frame"])
            ai_trace = []
            for i in range(20):
                d = sess.action("ACTION1")
                g = plane(d["frame"])
                ai_trace.append(
                    {
                        "i": i + 1,
                        "action_input": d.get("action_input"),
                        "n4": y63_stats(g)["n4"],
                        "keys": sorted(k for k in d if k != "frame"),
                    }
                )
            out["findings"].append({"action_input_trace": ai_trace})
            print("action_input sample", ai_trace[:5], "...", ai_trace[-1])

        # 8) Try fill with mixed acts that previously showed Δ — until n4 plateaus, then check
        # Also try: after n4 grows, do RESET? (full_reset flag)
        if not out["cleared"]:
            d = sess.reset()
            g = plane(d["frame"])
            for i in range(30):
                d = sess.action("ACTION1")
                g = plane(d["frame"])
            s = y63_stats(g)
            out["findings"].append({"before_soft_check": {"n4": s["n4"], "full_reset": d.get("full_reset"), "lv": d.get("levels_completed")}})
            print("after 30x1:", s["n4"], "full_reset", d.get("full_reset"))

        OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print("\nDONE cleared=", out["cleared"], "->", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
