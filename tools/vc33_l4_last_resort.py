"""L4 H59 (f) last resort: hidden colors / unseen UI / multi-click counters.

A) hist union across states — any color outside known set
B) full API response key/value watch (non-frame fields) across clicks
C) multi-click counters: same cell ×{2,3,5,8} on mid/gap/left12/dig/accent/c7
D) alternating rituals: mid↔gap, left12↔mid, dig↔mid
E) click every rare component (n<=16) at convert + ceiling states

Hit: novel color, levels>=4, acts!=[6], mid12, or non-frame field change
    that isn't guid churn alone.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l2_probe import body_changes, body_ndiff  # noqa: E402
from tools.vc33_l3_probe import Sess, pads_sorted, plane  # noqa: E402
from tools.vc33_l4_pad_map import components, enter_l4, gap11, sprite  # noqa: E402

OUT = ROOT / "tests/fixtures/vc33_l4_last_resort.json"
KNOWN = {0, 1, 3, 4, 5, 7, 9, 11, 12}
META_IGNORE = {"frame", "guid"}  # guid always churns


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP", e)
        return None


def pad(sess, g, x0):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    return click(sess, int(round(p["cx"])), int(round(p["cy"])))


def hist(g):
    return {int(k): int(v) for k, v in zip(*np.unique(g, return_counts=True))}


def novel(g):
    return {c: n for c, n in hist(g).items() if c not in KNOWN}


def meta(d):
    return {k: v for k, v in d.items() if k not in META_IGNORE}


def meta_diff(a, b):
    keys = set(a) | set(b)
    out = {}
    for k in keys:
        if a.get(k) != b.get(k):
            out[k] = {"from": a.get(k), "to": b.get(k)}
    return out


def mid_kind(g):
    if [c for c in components(g, 12, 1, 80) if c["cx"] > 20]:
        return 12
    if [c for c in components(g, 1, 4, 80) if c["cx"] > 20]:
        return 1
    return None


def left12(g):
    cs = [c for c in components(g, 12, 1, 80) if c["cx"] < 20]
    return cs[0] if cs else None


def setup_convert(sess):
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    for _ in range(8):
        if left12(g):
            break
        d2 = pad(sess, g, 15)
        if d2 is None:
            break
        g = plane(d2["frame"]); d = d2
    return d, g


def arm_hop_climb(sess, d, g):
    c = left12(g)
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    g = plane(d2["frame"]); d = d2
    d2 = pad(sess, g, 39)
    g = plane(d2["frame"]); d = d2
    d2 = pad(sess, g, 15)  # clear
    g = plane(d2["frame"]); d = d2
    for _ in range(6):
        cy0 = sprite(g)["body"]["cy"]
        d2 = pad(sess, g, 15)
        if d2 is None:
            break
        g2 = plane(d2["frame"])
        if abs(sprite(g2)["body"]["cy"] - cy0) < 0.1:
            return d2, g2
        g = g2; d = d2
    return d, g


def hit_check(d, g, label, hits):
    nov = novel(g)
    lv = int(d.get("levels_completed") or 0)
    acts = d.get("available_actions")
    mk = mid_kind(g)
    reasons = []
    if nov:
        reasons.append(f"novel {nov}")
    if lv >= 4:
        reasons.append(f"levels {lv}")
    if acts is not None and list(acts) != [6]:
        reasons.append(f"acts {acts}")
    if mk == 12:
        reasons.append("mid12")
    if reasons:
        print(f"*** HIT {label}: {reasons}")
        hits.append({"label": label, "reasons": reasons, "meta": meta(d), "hist": hist(g)})
        return True
    return False


def main():
    key = _api_key()
    sess = Sess(key)
    hits = []
    hist_union = Counter()
    meta_events = []
    click_logs = []
    try:
        sess.open()

        # ---- A: hist across states ----
        print("\n## A hist union across states")
        states = []

        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        states.append(("spawn", hist(g), novel(g), meta(d)))
        hit_check(d, g, "A/spawn", hits)

        d, g = setup_convert(sess)
        states.append(("convert", hist(g), novel(g), meta(d)))
        hit_check(d, g, "A/convert", hits)

        # armed
        c = left12(g)
        d2 = click(sess, round(c["cx"]), round(c["cy"]))
        g = plane(d2["frame"]); d = d2
        states.append(("armed", hist(g), novel(g), meta(d)))
        hit_check(d, g, "A/armed", hits)

        d2 = pad(sess, g, 39)
        g = plane(d2["frame"]); d = d2
        states.append(("bay1", hist(g), novel(g), meta(d)))
        hit_check(d, g, "A/bay1", hits)

        d, g = arm_hop_climb(sess, *setup_convert(sess))
        states.append(("ceil", hist(g), novel(g), meta(d)))
        hit_check(d, g, "A/ceil", hits)

        for name, h, nov, m in states:
            hist_union.update(h)
            print(f"  {name}: hist={h} novel={nov} acts={m.get('available_actions')} lv={m.get('levels_completed')}")
        odd_colors = sorted(c for c in hist_union if c not in KNOWN)
        print(f"  UNION odd colors: {odd_colors}")

        # ---- B+C: multi-click counters at convert (fresh) ----
        print("\n## B/C multi-click + meta watch @ convert")
        d, g = setup_convert(sess)
        m0 = meta(d)
        targets = []
        mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
        if mid:
            targets.append(("mid", round(mid[0]["cx"]), round(mid[0]["cy"])))
            targets.append(("midbot", mid[0]["x0"], mid[0]["y1"]))
        gp = gap11(g)
        if gp:
            targets.append(("gap", round(gp["cx"]), round(gp["cy"])))
        c12 = left12(g)
        if c12:
            targets.append(("left12", round(c12["cx"]), round(c12["cy"])))
        targets += [
            ("dig26_45", 26, 45),
            ("dig26_46", 26, 46),
            ("flank16_45", 16, 45),
            ("flank10_45", 10, 45),
            ("deep26_55", 26, 55),
        ]
        sp = sprite(g)
        if sp and sp["accent"]:
            targets.append(("accent", round(sp["accent"]["cx"]), round(sp["accent"]["cy"])))
        # c7 / UI row if present
        for c7 in components(g, 7, 1, 200)[:2]:
            targets.append(("c7", round(c7["cx"]), round(c7["cy"])))
        for c4ui in components(g, 4, 1, 200):
            if c4ui["y1"] <= 2:  # top UI turned 4
                targets.append(("ui4", round(c4ui["cx"]), round(c4ui["cy"])))
                break

        for name, x, y in targets:
            # fresh state for each target — re-setup if c12 lost
            if left12(g) is None and name != "c7":
                d, g = setup_convert(sess)
                m0 = meta(d)
            g_base = g.copy()
            m_base = meta(d)
            for n in range(1, 9):
                d2 = click(sess, x, y)
                if d2 is None:
                    click_logs.append({"target": name, "n": n, "http": True})
                    break
                g2 = plane(d2["frame"])
                md = meta_diff(m_base, meta(d2))
                nd = body_ndiff(g_base, g2)
                nov = novel(g2)
                # interesting if meta changes beyond levels/acts noise we know, or novel, or big nd without expected hop
                interesting_meta = {k: v for k, v in md.items() if k not in ("levels_completed",)}
                # after arm-like click left12 once, hop may happen on later — track
                row = {
                    "target": name,
                    "n": n,
                    "xy": (x, y),
                    "nd": nd,
                    "meta_diff": md,
                    "novel": nov,
                    "lv": d2.get("levels_completed"),
                    "acts": d2.get("available_actions"),
                    "mid": mid_kind(g2),
                    "h12": int((g2 == 12).sum()),
                }
                click_logs.append(row)
                if nov or (d2.get("levels_completed") or 0) >= 4 or (
                    d2.get("available_actions") and list(d2["available_actions"]) != [6]
                ):
                    print(f"*** HIT multi {name} n={n}", row)
                    hits.append({"label": f"C/{name}_x{n}", "row": row})
                elif interesting_meta and n >= 2:
                    # non-guid meta change on multi-click
                    print(f"  META {name} n={n} {interesting_meta} nd={nd}")
                    meta_events.append(row)
                elif nd and name not in ("left12",) and n >= 2:
                    # unexpected frame change on repeat click
                    ch = body_changes(g_base, g2)
                    print(f"  ND {name} n={n} nd={nd} ch={ch}")
                    meta_events.append({**row, "ch": ch})
                g = g2; d = d2
                m_base = meta(d2)  # cumulative from start of this target? use rolling
                # For counter detection: compare to state AFTER first click
                if n == 1:
                    g_base = g2.copy()
                    m_base = meta(d2)

        # ---- D: alternating rituals @ ceiling ----
        print("\n## D alternating rituals @ ceiling")
        d, g = setup_convert(sess)
        d, g = arm_hop_climb(sess, d, g)
        m0 = meta(d)
        mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
        gp = gap11(g)
        pairs = []
        if mid and gp:
            pairs.append(("mid_gap", [
                (round(mid[0]["cx"]), round(mid[0]["cy"])),
                (round(gp["cx"]), round(gp["cy"])),
            ]))
        if mid:
            pairs.append(("mid_dig", [
                (round(mid[0]["cx"]), round(mid[0]["cy"])),
                (26, 45),
            ]))
            pairs.append(("mid_beam", [
                (round(mid[0]["cx"]), round(mid[0]["cy"])),
                (28, 46),
            ]))
        for pname, pts in pairs:
            for i in range(8):
                x, y = pts[i % 2]
                d2 = click(sess, x, y)
                if d2 is None:
                    break
                g2 = plane(d2["frame"])
                md = meta_diff(meta(d), meta(d2))
                if hit_check(d2, g2, f"D/{pname}_{i}", hits):
                    break
                if md and list(md.keys()) != ["levels_completed"]:
                    print(f"  D META {pname}_{i} {md}")
                    meta_events.append({"label": f"D/{pname}_{i}", "meta_diff": md})
                g = g2; d = d2

        # ---- E: rare components @ convert ----
        print("\n## E rare components @ convert")
        d, g = setup_convert(sess)
        rares = []
        for color in sorted(hist(g)):
            for c in components(g, color, 1, 16):
                if c["n"] <= 16:
                    rares.append((color, c))
        print(f"  rare comps n={len(rares)}")
        # cap clicks
        for color, c in rares[:40]:
            d2 = click(sess, round(c["cx"]), round(c["cy"]))
            if d2 is None:
                continue
            g2 = plane(d2["frame"])
            nd = body_ndiff(g, g2)
            nov = novel(g2)
            if nov or (d2.get("levels_completed") or 0) >= 4:
                print(f"*** HIT rare c{color}", c, nov)
                hits.append({"label": f"E/c{color}", "comp": c, "novel": nov})
            elif nd:
                ch = body_changes(g, g2)
                # ignore pure env / sprite moves from accidental pad-ish
                if any(k for k in ch if k not in (
                    "3->0", "0->3", "3->4", "4->3", "3->11", "11->3", "4->11", "11->4",
                    "7->4", "4->7", "12->1", "1->12",
                )):
                    print(f"  rare odd ch c{color}@{c['cx']:.0f},{c['cy']:.0f} {ch}")
                    meta_events.append({"label": f"E/c{color}", "ch": ch})
            g = g2; d = d2
            if hit_check(d, g, f"E/c{color}", hits):
                break

        # ---- F: API keys dump once ----
        print("\n## F response keys")
        print("  keys", sorted(d.keys()))
        print("  meta", meta(d))

        reading = "LAST_RESORT_HIT" if hits else (
            "WEAK_META" if meta_events else "NO_LAST_RESORT"
        )
        out = {
            "reading": reading,
            "hits": hits,
            "odd_colors_union": odd_colors,
            "hist_states": [
                {"name": n, "hist": h, "novel": nov, "meta": m}
                for n, h, nov, m in states
            ],
            "meta_events_n": len(meta_events),
            "meta_events": meta_events[:40],
            "click_logs_interesting": [
                r for r in click_logs
                if r.get("novel") or r.get("http")
                or (r.get("nd") and r.get("n", 0) >= 2)
                or (r.get("meta_diff") and set(r["meta_diff"]) - {"levels_completed"})
            ][:60],
            "hypothesis": "H59 last resort hidden UI / novel color / multi-click",
        }
        print("\n## Summary")
        print("odd_colors", odd_colors)
        print("hits", len(hits), "meta_events", len(meta_events))
        print("READING:", reading)
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
