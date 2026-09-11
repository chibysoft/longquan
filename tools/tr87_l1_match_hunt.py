"""tr87 L1: extract 5 bottom glyph signatures; probe ACTION1/2 periods;
compare to upper targets; BFS-ish match hunt for levels↑.

tags=["tr87_recon"]
"""
from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.tr87_recon_probe import Sess, plane  # noqa: E402

OUT = ROOT / "tests/fixtures/tr87_l1_match_hunt.json"

# five selection slots by color0 x0
SLOTS_X0 = (15, 22, 29, 36, 43)
GLYPH_Y0, GLYPH_Y1 = 52, 56  # interior rows that flip (exclusive end 57)
GLYPH_W = 5  # x0 .. x0+4


def color0_x0(g):
    xs = [int(x) for y, x in np.argwhere(g == 0)]
    if not xs:
        return None
    return min(xs)


def slot_index(g):
    x0 = color0_x0(g)
    if x0 is None:
        return None
    # nearest SLOTS_X0
    return int(np.argmin([abs(x0 - s) for s in SLOTS_X0]))


def glyph_at(g, slot_i):
    x0 = SLOTS_X0[slot_i]
    patch = g[GLYPH_Y0:GLYPH_Y1 + 1, x0:x0 + GLYPH_W]
    # normalize: map to tuple of ints
    return tuple(int(v) for v in patch.ravel())


def all_glyphs(g):
    return [glyph_at(g, i) for i in range(5)]


def glyph_ascii(sig):
    a = np.array(sig, dtype=int).reshape((GLYPH_Y1 - GLYPH_Y0 + 1, GLYPH_W))
    chars = {5: "5", 7: "7", 10: "a", 0: ".", 3: " "}
    return ["".join(chars.get(int(v), str(int(v))[-1]) for v in row) for row in a]


def upper_glyphs(g):
    """Find 7x7-ish icons in upper area: color10 frames with 5/7 fill.
    Sample known rows from first frame: y4-10, 13-19, 22-28; pairs at x12 and x36-ish.
    """
    # From ascii: tiles start around x12 and x33/36, rows at 4,13,22
    starts = []
    for y0 in (4, 13, 22):
        for x0 in (12, 22, 33, 43):
            # require color10 border-ish at corners
            if int(g[y0, x0]) == 10 and int(g[y0 + 6, x0 + 6]) == 10:
                starts.append((x0, y0))
    out = []
    for x0, y0 in starts:
        # interior often y0+1..y0+5, x0+1..x0+5
        patch = g[y0 + 1:y0 + 6, x0 + 1:x0 + 6]
        sig = tuple(int(v) for v in patch.ravel())
        out.append({"x0": x0, "y0": y0, "sig": sig, "ascii": glyph_ascii(sig)})
    return out


def go(sess, n):
    return sess.action(f"ACTION{n}")


def move_to_slot(sess, g, target_i):
    """Use 3/4 to reach target slot index. Max 8 steps."""
    for _ in range(8):
        cur = slot_index(g)
        if cur == target_i:
            return g, True
        # 4 increases index (with wrap), 3 decreases
        if cur is None:
            return g, False
        # choose shorter direction on ring of 5
        d_fwd = (target_i - cur) % 5  # via ACTION4
        d_bwd = (cur - target_i) % 5  # via ACTION3
        if d_fwd <= d_bwd:
            d = go(sess, 4)
        else:
            d = go(sess, 3)
        g = plane(d["frame"])
    return g, slot_index(g) == target_i


def main():
    key = _api_key()
    sess = Sess(key)
    out = {}
    try:
        sess.open()
        d = sess.reset()
        g = plane(d["frame"])

        # ---- glyph catalog ----
        print("\n## bottom glyphs @ reset")
        bottom = all_glyphs(g)
        for i, sig in enumerate(bottom):
            print(f"  slot{i} x0={SLOTS_X0[i]}")
            for line in glyph_ascii(sig):
                print("   ", line)
        upper = upper_glyphs(g)
        print(f"\n## upper glyphs n={len(upper)}")
        for u in upper:
            print(f"  @({u['x0']},{u['y0']})")
            for line in u["ascii"]:
                print("   ", line)

        # match any bottom == any upper?
        matches = []
        for i, b in enumerate(bottom):
            for u in upper:
                if b == u["sig"]:
                    matches.append({"slot": i, "upper": (u["x0"], u["y0"])})
        print("exact matches reset:", matches)
        out["reset_matches"] = matches
        out["bottom_reset"] = [glyph_ascii(s) for s in bottom]
        out["upper"] = [{"x0": u["x0"], "y0": u["y0"], "ascii": u["ascii"]} for u in upper]

        # ---- period of ACTION1/2 on slot 0 ----
        print("\n## periods on slot0")
        periods = {}
        for flip in (1, 2):
            d = sess.reset()
            g = plane(d["frame"])
            start = glyph_at(g, 0)
            seen = {start: 0}
            seq = [start]
            for step in range(1, 12):
                d = go(sess, flip)
                g = plane(d["frame"])
                sig = glyph_at(g, 0)
                seq.append(sig)
                if sig in seen:
                    periods[flip] = {"period": step - seen[sig], "first": seen[sig], "steps": step}
                    print(f"  ACT{flip} period={periods[flip]}")
                    break
                seen[sig] = step
            else:
                periods[flip] = {"period": None, "unique": len(seen)}
                print(f"  ACT{flip} no period in 12, unique={len(seen)}")
            periods[flip]["ascii_cycle"] = [glyph_ascii(s) for s in seq[:6]]
        out["periods"] = periods

        # ---- 1 then 2 interaction ----
        print("\n## 1/2 algebra on slot0")
        d = sess.reset()
        g = plane(d["frame"])
        s0 = glyph_at(g, 0)
        d = go(sess, 1)
        g = plane(d["frame"])
        s1 = glyph_at(g, 0)
        d = go(sess, 2)
        g = plane(d["frame"])
        s12 = glyph_at(g, 0)
        d = sess.reset()
        g = plane(d["frame"])
        d = go(sess, 2)
        g = plane(d["frame"])
        s2 = glyph_at(g, 0)
        d = go(sess, 1)
        g = plane(d["frame"])
        s21 = glyph_at(g, 0)
        algebra = {
            "1_changes": s1 != s0,
            "2_changes": s2 != s0,
            "12_eq_0": s12 == s0,
            "21_eq_0": s21 == s0,
            "12_eq_21": s12 == s21,
            "1_eq_2": s1 == s2,
        }
        print(" ", algebra)
        out["algebra"] = algebra

        # ---- try match each bottom glyph to nearest upper by applying 1/2 ----
        print("\n## per-slot transform to match any upper")
        d = sess.reset()
        g0 = plane(d["frame"])
        upper_sigs = [u["sig"] for u in upper_glyphs(g0)]
        plan = []
        for si in range(5):
            # BFS on glyph state with ops 1,2 depth<=4
            d = sess.reset()
            g = plane(d["frame"])
            g, ok = move_to_slot(sess, g, si)
            start = glyph_at(g, si)
            q = deque([(start, [])])
            seen = {start}
            found = None
            # we need live transforms — simulate by actually pressing from reset each time is expensive;
            # instead explore from current by cloning via reset+replay
            # cheaper: from this slot, try sequences of 1/2 up to len 4
            seqs = [[]]
            for L in range(1, 5):
                news = []
                for base in list(seqs):
                    news.append(base + [1])
                    news.append(base + [2])
                seqs += news
            # unique preserve order
            uniq = []
            seen_t = set()
            for seq in seqs:
                t = tuple(seq)
                if t not in seen_t:
                    seen_t.add(t)
                    uniq.append(seq)
            for seq in uniq:
                d = sess.reset()
                g = plane(d["frame"])
                g, ok = move_to_slot(sess, g, si)
                for a in seq:
                    d = go(sess, a)
                    g = plane(d["frame"])
                sig = glyph_at(g, si)
                if sig in upper_sigs:
                    uidx = upper_sigs.index(sig)
                    found = {"slot": si, "seq": seq, "upper": upper[uidx] if uidx < len(upper) else uidx}
                    break
            print(f"  slot{si} found={found}")
            plan.append(found)
        out["per_slot_match_plan"] = plan

        # ---- if we have a full plan, execute and check levels ----
        print("\n## execute combined plan")
        d = sess.reset()
        g = plane(d["frame"])
        lv0 = d.get("levels_completed")
        full_seq = []
        for si, p in enumerate(plan):
            if not p:
                continue
            # move to slot
            g, ok = move_to_slot(sess, g, si)
            # record moves — approximate by reading slot and pressing
            # re-do properly from tracking
        # cleaner replay from scratch
        d = sess.reset()
        g = plane(d["frame"])
        actions = []
        for si, p in enumerate(plan):
            if not p:
                continue
            # navigate
            for _ in range(8):
                if slot_index(g) == si:
                    break
                cur = slot_index(g)
                d_fwd = (si - cur) % 5
                d_bwd = (cur - si) % 5
                a = 4 if d_fwd <= d_bwd else 3
                d = go(sess, a)
                g = plane(d["frame"])
                actions.append(a)
            for a in p["seq"]:
                d = go(sess, a)
                g = plane(d["frame"])
                actions.append(a)
        lv1 = d.get("levels_completed")
        bottom_after = [glyph_ascii(s) for s in all_glyphs(g)]
        print(f"  actions={actions} lv {lv0}->{lv1}")
        print(f"  bottom after:")
        for i, lines in enumerate(bottom_after):
            print(f"   slot{i}")
            for line in lines:
                print("    ", line)
        out["combined"] = {
            "actions": actions,
            "lv0": lv0,
            "lv1": lv1,
            "bottom_after": bottom_after,
        }
        if int(lv1 or 0) > int(lv0 or 0):
            print("*** CLEAR")
            (ROOT / "tests/fixtures/tr87_l1_clear_frame.json").write_text(
                json.dumps({"frame": d["frame"], "levels": lv1, "actions": actions}, indent=2),
                encoding="utf-8",
            )

        # ---- also try: make all 5 bottom match the FIVE upper from one row ----
        # Row y=4 has tiles at x12,22,33,43 — only 4. Row pairs: left pair and right pair.
        # Looking at layout: 4 icons per row × 3 rows = 12 upper; bottom has 5.
        # Maybe bottom matches a specific sequence of 5 from somewhere else.
        # Compare bottom strip as whole to something.

        reading = "L1_CLEAR" if int(lv1 or 0) > int(lv0 or 0) else "MATCH_PARTIAL"
        out["reading"] = reading
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("READING:", reading)
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
