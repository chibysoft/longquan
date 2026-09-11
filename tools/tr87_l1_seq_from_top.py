"""tr87 L1: mid-as-non-target — derive ACTION sequences from top pairs; also sort/multiset + hidden UI.

Hypotheses:
  H7  top 6 pairs encode an act sequence (ink/CC/hash/shape → 1..4); run len≤30
  H8  rearrange bottoms into sorted order by ink/CC/hash (or all-equal where alphabet allows)
  H9  pairwise: slot i ↔ top pair i (left-col / reading order)
  H10 hidden UI: color1@y63, hist, state, full_reset, action_input after varied acts

tags=["tr87_recon"]  ·  do NOT touch r11l/vc33
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.tr87_recon_probe import Sess, plane  # noqa: E402

OUT = ROOT / "tests/fixtures/tr87_l1_seq_from_top.json"
CLEAR = ROOT / "tests/fixtures/tr87_l1_clear_frame.json"
SLOTS = (15, 22, 29, 36, 43)
MID_X = (14, 21, 28, 35, 42)
# reading orders over 6 pairs (A_x, seven_x, y)
PAIR_LAYOUT = [
    (12, 22, 4),
    (36, 46, 4),
    (12, 22, 13),
    (36, 46, 13),
    (12, 22, 22),
    (36, 46, 22),
]
ORDERS = {
    "row_major": [0, 1, 2, 3, 4, 5],
    "col_left_then_right": [0, 2, 4, 1, 3, 5],
    "col_right_then_left": [1, 3, 5, 0, 2, 4],
    "zigzag": [0, 1, 3, 2, 4, 5],
    "bottom_up": [4, 5, 2, 3, 0, 1],
}


def bg(g, si):
    x0 = SLOTS[si]
    return tuple(int(v) for v in g[52:57, x0 : x0 + 5].ravel())


def all_b(g):
    return [bg(g, i) for i in range(5)]


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


def patch5(g, x0, y0, remap10=False):
    p = g[y0 + 1 : y0 + 6, x0 + 1 : x0 + 6].copy()
    if remap10:
        p = np.where(p == 10, 7, p)
    return p


def ink(p, color=7):
    return int((p == color).sum())


def n_cc(p, color=7):
    H, W = p.shape
    seen = np.zeros_like(p, dtype=bool)
    n = 0
    for y in range(H):
        for x in range(W):
            if seen[y, x] or int(p[y, x]) != color:
                continue
            n += 1
            stack = [(x, y)]
            seen[y, x] = True
            while stack:
                cx, cy = stack.pop()
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < W and 0 <= ny < H and not seen[ny, nx] and int(p[ny, nx]) == color:
                        seen[ny, nx] = True
                        stack.append((nx, ny))
    return n


def feats_pair(g, ax, sx, y0):
    A = patch5(g, ax, y0, remap10=True)
    S = patch5(g, sx, y0, remap10=False)
    Ad = patch5(g, ax, y0, remap10=False)
    return {
        "pos": (ax, sx, y0),
        "inkA7": ink(A, 7),
        "inkS7": ink(S, 7),
        "inkA10": ink(Ad, 10),
        "ccA": n_cc(A, 7),
        "ccS": n_cc(S, 7),
        "hamAS": int(np.sum(A != S)),
        "hashA": hash(tuple(int(v) for v in A.ravel())) & 0xFFFFFFFF,
        "hashS": hash(tuple(int(v) for v in S.ravel())) & 0xFFFFFFFF,
        "sigA": tuple(int(v) for v in A.ravel()),
        "sigS": tuple(int(v) for v in S.ravel()),
    }


def act_from(v, scheme="mod4"):
    if scheme == "mod4":
        return (int(v) % 4) + 1
    if scheme == "mod4_0":
        return (int(v) % 4)  # 0..3 then map — invalid; use clamp
    if scheme == "clamp14":
        return min(4, max(1, int(v)))
    if scheme == "parity12":
        return 1 if int(v) % 2 == 0 else 2
    if scheme == "parity34":
        return 3 if int(v) % 2 == 0 else 4
    if scheme == "bucket_ink":
        # ink typically 5..15ish → buckets
        v = int(v)
        if v <= 7:
            return 1
        if v <= 10:
            return 2
        if v <= 13:
            return 3
        return 4
    raise ValueError(scheme)


def hist(g):
    return {int(k): int(v) for k, v in zip(*np.unique(g, return_counts=True))}


def y63(g):
    return tuple(int(v) for v in g[63, :].ravel())


def meta_watch(d, g0_hist=None, g0_y63=None, g=None):
    m = {
        "levels": d.get("levels_completed"),
        "state": d.get("state"),
        "acts": d.get("available_actions"),
        "full_reset": d.get("full_reset"),
        "action_input": d.get("action_input"),
        "score": d.get("score"),
        "steps": d.get("steps"),
        "action_count": d.get("action_count"),
    }
    extra = sorted(k for k in d if k not in ("frame", "guid", "game_id"))
    m["keys"] = extra
    if g is not None:
        h = hist(g)
        m["hist"] = h
        m["y63"] = y63(g)
        if g0_hist is not None:
            m["hist_delta"] = {str(k): h.get(k, 0) - g0_hist.get(k, 0) for k in set(h) | set(g0_hist)}
        if g0_y63 is not None:
            m["y63_changed"] = y63(g) != g0_y63
            m["y63_n_diff"] = sum(a != b for a, b in zip(y63(g), g0_y63))
    return m


def run_seq(sess, seq, label, out_trials, watch=True):
    d = sess.reset()
    g = plane(d["frame"])
    h0, y0 = hist(g), y63(g)
    lv0 = d.get("levels_completed", 0)
    applied = []
    last_meta = None
    for a in seq:
        d = sess.action(f"ACTION{a}")
        g = plane(d["frame"])
        applied.append(a)
        lv = d.get("levels_completed", 0)
        if watch:
            last_meta = meta_watch(d, h0, y0, g)
        if lv is not None and lv > lv0:
            rec = {
                "label": label,
                "seq": applied,
                "levels": lv,
                "meta": last_meta,
            }
            out_trials.append(rec)
            CLEAR.write_text(
                json.dumps(
                    {
                        "label": label,
                        "seq": applied,
                        "levels_completed": lv,
                        "frame": d["frame"],
                        "meta": {k: d.get(k) for k in d if k != "frame"},
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            print("*** L1_CLEAR ***", label, applied, "lv", lv)
            return True, g, d
    rec = {
        "label": label,
        "seq": list(seq),
        "levels": d.get("levels_completed"),
        "meta": last_meta,
    }
    out_trials.append(rec)
    print(f"  {label}: lv={d.get('levels_completed')} len={len(seq)} y63Δ={last_meta and last_meta.get('y63_n_diff')}")
    return False, g, d


def collect_alpha(sess):
    """per slot: list of 7 glyph sigs via ACT1 from reset position."""
    alphas = []
    for si in range(5):
        d = sess.reset()
        g = plane(d["frame"])
        g, _, _ = move(sess, g, si)
        start = bg(g, si)
        seq = [start]
        for _ in range(8):
            d = sess.action("ACTION1")
            g = plane(d["frame"])
            sig = bg(g, si)
            if sig == start:
                break
            seq.append(sig)
        alphas.append(seq)
    return alphas


def dial_to(sess, g, si, target_sig, alpha_index):
    """From current, move to si and ACT1 until bg matches target (max 8)."""
    acts = []
    g, macts, ok = move(sess, g, si)
    acts.extend(macts)
    if not ok:
        return g, acts, False
    for _ in range(8):
        if bg(g, si) == target_sig:
            return g, acts, True
        d = sess.action("ACTION1")
        g = plane(d["frame"])
        acts.append(1)
    return g, acts, bg(g, si) == target_sig


def sort_bottoms(sess, alphas, key_fn, label, out_trials):
    """Try to permute/dial bottoms so key_fn(sig) is nondecreasing across slots.
    Only dial within each slot's alphabet; cannot truly permute glyphs across
    disjoint alphabets — we sort by choosing phase per slot to minimize
    inversions of key_fn among chosen glyphs.
    """
    d = sess.reset()
    g = plane(d["frame"])
    # greedy: for each slot pick glyph with key closest to a global sorted target
    keys_options = []
    for si, alpha in enumerate(alphas):
        keys_options.append([(key_fn(sig), sig) for sig in alpha])

    # target keys: sort all available keys, assign by slot order from global sorted multiset
    # Alternative: pick one glyph per slot minimizing sum of adjacent |Δkey|
    # Beam: choose phase for slot0..4 greedily left-to-right
    chosen = []
    prev = None
    for si in range(5):
        opts = keys_options[si]
        if prev is None:
            # pick median key
            opts_sorted = sorted(opts, key=lambda t: t[0])
            pick = opts_sorted[len(opts_sorted) // 2]
        else:
            pick = min(opts, key=lambda t: abs(t[0] - prev))
        chosen.append(pick[1])
        prev = pick[0]

    acts = []
    for si, tgt in enumerate(chosen):
        g, a, ok = dial_to(sess, g, si, tgt, None)
        acts.extend(a)
        if not ok:
            print(f"  {label}: dial fail slot{si}")
    d_last = sess.action("ACTION3")  # noop-ish nudge to refresh? actually moves sel
    g = plane(d_last["frame"])
    # undo that nudge conceptually — just check levels after dials
    # Re-check: levels on last dial response — we need last action response
    # Re-run cleanly recording last d
    d = sess.reset()
    g = plane(d["frame"])
    acts = []
    last_d = d
    for si, tgt in enumerate(chosen):
        g, a, ok = dial_to(sess, g, si, tgt, None)
        acts.extend(a)
        # get last response by doing nothing — store from dial: dial_to doesn't return d
    # one more ACT that doesn't change glyphs much: ACTION3 then ACTION4
    last_d = sess.action("ACTION4")
    g = plane(last_d["frame"])
    lv = last_d.get("levels_completed")
    rec = {
        "label": label,
        "seq": acts + [4],
        "chosen_keys": [key_fn(s) for s in chosen],
        "levels": lv,
    }
    out_trials.append(rec)
    print(f"  {label}: keys={rec['chosen_keys']} lv={lv} n_acts={len(acts)}")
    if lv and lv > 0:
        CLEAR.write_text(
            json.dumps(
                {
                    "label": label,
                    "seq": acts + [4],
                    "levels_completed": lv,
                    "frame": last_d["frame"],
                    "meta": {k: last_d.get(k) for k in last_d if k != "frame"},
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print("*** L1_CLEAR ***", label)
        return True
    return False


def all_equal_attempt(sess, alphas, label, out_trials):
    """Where alphabets intersect, try make as many slots equal as possible.
    slots 0,3,4 share alphabet — set all three to same glyph (each of 7).
    slot1,2 stay at reset or cycle.
    """
    shared = set(alphas[0]) & set(alphas[3]) & set(alphas[4])
    print(f"  shared 0/3/4 glyphs: {len(shared)}")
    for gi, target in enumerate(list(shared)[:7]):
        d = sess.reset()
        g = plane(d["frame"])
        acts = []
        last_d = d
        for si in (0, 3, 4):
            g, a, ok = dial_to(sess, g, si, target, None)
            acts.extend(a)
        last_d = sess.action("ACTION4")
        lv = last_d.get("levels_completed")
        rec = {"label": f"{label}_g{gi}", "seq": acts + [4], "levels": lv}
        out_trials.append(rec)
        print(f"  {label}_g{gi}: lv={lv}")
        if lv and lv > 0:
            CLEAR.write_text(
                json.dumps(
                    {
                        "label": rec["label"],
                        "seq": acts + [4],
                        "levels_completed": lv,
                        "frame": last_d["frame"],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            print("*** L1_CLEAR ***", rec["label"])
            return True
    return False


def pairwise_dial(sess, alphas, pairs_feats, mode, label, out_trials):
    """H9: relate slots to pairs.
    mode:
      left3: slots 0,1,2 dial toward left-col top7 (y 4,13,22) best ham in alphabet
      assign5: first 5 pairs' inkS7 mod → phase
      ink_match: dial each slot to alphabet glyph whose ink closest to pair[i].inkS7
    """
    d = sess.reset()
    g = plane(d["frame"])
    top7_left = [pairs_feats[i]["sigS"] for i in (0, 2, 4)]  # left col
    top7_all = [p["sigS"] for p in pairs_feats]

    targets = [None] * 5
    if mode == "left3_best":
        for si in range(3):
            tgt = top7_left[si]
            best = min(alphas[si], key=lambda s: int(np.sum(np.array(s) != np.array(tgt))))
            targets[si] = best
        for si in (3, 4):
            targets[si] = alphas[si][0]
    elif mode == "ink_to_pair":
        # pair i -> slot i for i<5; pair5 unused
        for si in range(5):
            want = pairs_feats[si]["inkS7"]
            best = min(alphas[si], key=lambda s: abs(ink(np.array(s).reshape(5, 5), 7) - want))
            targets[si] = best
    elif mode == "cc_to_pair":
        for si in range(5):
            want = pairs_feats[si]["ccS"]
            best = min(
                alphas[si],
                key=lambda s: abs(n_cc(np.array(s).reshape(5, 5), 7) - want),
            )
            targets[si] = best
    elif mode == "hash_phase":
        for si in range(5):
            phase = pairs_feats[si]["hashS"] % len(alphas[si])
            targets[si] = alphas[si][phase]
    else:
        raise ValueError(mode)

    acts = []
    for si, tgt in enumerate(targets):
        if tgt is None:
            continue
        g, a, ok = dial_to(sess, g, si, tgt, None)
        acts.extend(a)
    last_d = sess.action("ACTION4")
    lv = last_d.get("levels_completed")
    rec = {"label": label, "seq": acts + [4], "levels": lv, "mode": mode}
    out_trials.append(rec)
    print(f"  {label}: lv={lv} n_acts={len(acts)}")
    if lv and lv > 0:
        CLEAR.write_text(
            json.dumps(
                {"label": label, "seq": acts + [4], "levels_completed": lv, "frame": last_d["frame"]},
                indent=2,
            ),
            encoding="utf-8",
        )
        print("*** L1_CLEAR ***", label)
        return True
    return False


def main():
    sess = Sess(_api_key())
    out = {"trials": [], "pair_feats": [], "hidden": [], "alphas_n": [], "best_lv": 0}
    cleared = False
    try:
        sess.open()
        d = sess.reset()
        g = plane(d["frame"])
        print("RESET lv", d.get("levels_completed"), "keys", sorted(k for k in d if k != "frame"))

        pairs = [feats_pair(g, *lay) for lay in PAIR_LAYOUT]
        out["pair_feats"] = [
            {k: v for k, v in p.items() if k not in ("sigA", "sigS")} | {"sigA_ink": p["inkA7"], "sigS_ink": p["inkS7"]}
            for p in pairs
        ]
        for i, p in enumerate(pairs):
            print(
                f"pair{i} y={p['pos'][2]} inkA={p['inkA7']} inkS={p['inkS7']} "
                f"ccA={p['ccA']} ccS={p['ccS']} ham={p['hamAS']}"
            )

        # --- H10: hidden UI baseline + after single acts ---
        h0, y0 = hist(g), y63(g)
        out["hidden"].append({"tag": "reset", **meta_watch(d, h0, y0, g)})
        for a in (1, 2, 3, 4):
            d = sess.reset()
            g = plane(d["frame"])
            h0, y0 = hist(g), y63(g)
            d = sess.action(f"ACTION{a}")
            g = plane(d["frame"])
            m = meta_watch(d, h0, y0, g)
            out["hidden"].append({"tag": f"single_{a}", **m})
            print(f"H10 ACT{a}: histΔ={m.get('hist_delta')} y63Δ={m.get('y63_n_diff')} keys={m.get('keys')}")

        # longer churn then watch
        d = sess.reset()
        g = plane(d["frame"])
        h0, y0 = hist(g), y63(g)
        for a in [1, 1, 4, 1, 4, 2, 3, 1, 4, 1, 2, 3, 4, 1]:
            d = sess.action(f"ACTION{a}")
            g = plane(d["frame"])
        m = meta_watch(d, h0, y0, g)
        out["hidden"].append({"tag": "churn14", **m})
        print(f"H10 churn14: lv={m['levels']} histΔ={m.get('hist_delta')} y63Δ={m.get('y63_n_diff')}")

        # --- H7: sequences from top features ---
        print("\n=== H7 seq from top ===")
        feat_keys = ["inkS7", "inkA7", "ccS", "ccA", "hamAS", "hashS", "hashA"]
        schemes = ["mod4", "bucket_ink", "parity12", "parity34"]

        for order_name, order in ORDERS.items():
            for fk in feat_keys:
                for scheme in schemes:
                    if scheme.startswith("parity") and fk.startswith("hash"):
                        continue
                    if scheme == "bucket_ink" and fk not in ("inkS7", "inkA7", "hamAS"):
                        continue
                    seq = [act_from(pairs[i][fk], scheme) for i in order]
                    # also doubled / reverse / interleaved nav
                    variants = {
                        f"H7_{order_name}_{fk}_{scheme}": seq,
                        f"H7_{order_name}_{fk}_{scheme}_x2": seq + seq,
                        f"H7_{order_name}_{fk}_{scheme}_rev": list(reversed(seq)),
                        f"H7_{order_name}_{fk}_{scheme}_nav": sum([[a, 4] for a in seq], []),
                    }
                    # only run a subset to keep API budget: prefer row_major + col + ink/cc
                    if order_name not in ("row_major", "col_left_then_right") and scheme != "mod4":
                        continue
                    if order_name == "col_left_then_right" and fk not in ("inkS7", "ccS", "hamAS"):
                        continue
                    for lab, s in variants.items():
                        if "x2" in lab and order_name != "row_major":
                            continue
                        if "nav" in lab and scheme != "mod4":
                            continue
                        if "rev" in lab and fk not in ("inkS7", "hamAS"):
                            continue
                        ok, _, _ = run_seq(sess, s, lab, out["trials"], watch=False)
                        if ok:
                            cleared = True
                            break
                    if cleared:
                        break
                if cleared:
                    break
            if cleared:
                break

        # denser hand-crafted sequences from ink reading
        if not cleared:
            inkS = [pairs[i]["inkS7"] for i in range(6)]
            inkA = [pairs[i]["inkA7"] for i in range(6)]
            hamv = [pairs[i]["hamAS"] for i in range(6)]
            hand = {
                "H7_inkS_mod4_rm": [act_from(v, "mod4") for v in inkS],
                "H7_ink_diff_mod4": [act_from(abs(a - b), "mod4") for a, b in zip(inkA, inkS)],
                "H7_ham_mod4": [act_from(v, "mod4") for v in hamv],
                "H7_ccS_mod4": [act_from(pairs[i]["ccS"], "mod4") for i in range(6)],
                # repeat pattern to length ~24–30
                "H7_inkS_mod4_x4": [act_from(v, "mod4") for v in inkS] * 4,
                "H7_walk_slots_flip_by_ink": [],  # filled below
                "H7_1234_x6": [1, 2, 3, 4] * 6,
                "H7_11223344_x3": [1, 1, 2, 2, 3, 3, 4, 4] * 3,
                "H7_only1_x21": [1] * 21,
                "H7_slotwalk_1each": [1, 4] * 5 + [1, 4] * 5,
                "H7_full_cycle_each_slot": [1, 1, 1, 1, 1, 1, 1, 4] * 5,
            }
            # walk: for each pair in row order, do `inkS%4+1` then ACTION4
            seq_w = []
            for v in inkS:
                seq_w.append(act_from(v, "mod4"))
                seq_w.append(4)
            hand["H7_walk_slots_flip_by_ink"] = seq_w * 2

            # shape-class: cluster by unique sigS order of first appearance → class id
            class_ids = []
            seen = {}
            for p in pairs:
                s = p["sigS"]
                if s not in seen:
                    seen[s] = len(seen)
                class_ids.append(seen[s])
            hand["H7_shape_class_mod4"] = [act_from(c, "mod4") for c in class_ids]
            hand["H7_shape_class_mod4_x3"] = hand["H7_shape_class_mod4"] * 3
            out["shape_class_ids"] = class_ids

            for lab, s in hand.items():
                ok, _, _ = run_seq(sess, s, lab, out["trials"], watch=True)
                if ok:
                    cleared = True
                    break

        # --- collect alphabets for H8/H9 ---
        print("\n=== alphabets ===")
        alphas = collect_alpha(sess)
        out["alphas_n"] = [len(a) for a in alphas]
        print("alpha lens", out["alphas_n"])

        if not cleared:
            print("\n=== H8 sort / equal ===")

            def key_ink(sig):
                return ink(np.array(sig).reshape(5, 5), 7)

            def key_cc(sig):
                return n_cc(np.array(sig).reshape(5, 5), 7)

            def key_hash(sig):
                return hash(sig) & 0xFFFF

            for name, fn in (("ink", key_ink), ("cc", key_cc), ("hash", key_hash)):
                if sort_bottoms(sess, alphas, fn, f"H8_sort_{name}", out["trials"]):
                    cleared = True
                    break
            if not cleared:
                if all_equal_attempt(sess, alphas, "H8_equal034", out["trials"]):
                    cleared = True

        if not cleared:
            print("\n=== H9 pairwise ===")
            for mode in ("left3_best", "ink_to_pair", "cc_to_pair", "hash_phase"):
                if pairwise_dial(sess, alphas, pairs, mode, f"H9_{mode}", out["trials"]):
                    cleared = True
                    break

        # --- bonus: dial slot0 to dialable top7, slot1 to dialable, then seq from remaining pairs ---
        if not cleared:
            print("\n=== combo dial+seq ===")
            d = sess.reset()
            g = plane(d["frame"])
            # (22,4) on slots 0/2/3/4; (22,13) on slot1
            t04 = pairs[0]["sigS"]  # (22,4) left top — pair0 seven
            t13 = pairs[2]["sigS"]  # (22,13)
            acts = []
            for si, tgt in ((0, t04), (1, t13)):
                # only if in alphabet
                if tgt in alphas[si]:
                    g, a, ok = dial_to(sess, g, si, tgt, None)
                    acts.extend(a)
                    print(f"  dial slot{si} exact={ok}")
                else:
                    best = min(alphas[si], key=lambda s: int(np.sum(np.array(s) != np.array(tgt))))
                    g, a, ok = dial_to(sess, g, si, best, None)
                    acts.extend(a)
                    print(f"  dial slot{si} best-ham ok={ok}")
            # then append ink-derived seq
            tail = [act_from(pairs[i]["inkS7"], "mod4") for i in range(6)] * 2
            for a in tail:
                d = sess.action(f"ACTION{a}")
                acts.append(a)
                if d.get("levels_completed", 0) > 0:
                    cleared = True
                    CLEAR.write_text(
                        json.dumps(
                            {"label": "combo_dial01_inkseq", "seq": acts, "levels_completed": d["levels_completed"], "frame": d["frame"]},
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                    print("*** L1_CLEAR *** combo")
                    break
            out["trials"].append(
                {"label": "combo_dial01_inkseq", "seq": acts, "levels": d.get("levels_completed")}
            )
            print("  combo lv", d.get("levels_completed"))

        lvs = [t.get("levels") or 0 for t in out["trials"]]
        out["best_lv"] = max(lvs) if lvs else 0
        out["cleared"] = cleared
        out["n_trials"] = len(out["trials"])
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("\nDONE best_lv", out["best_lv"], "trials", out["n_trials"], "cleared", cleared, "->", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
