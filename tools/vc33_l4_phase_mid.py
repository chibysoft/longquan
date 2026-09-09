"""L4: kill c12 then env-phase climb; ceiling mid-click; left-arm→click mid."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l2_probe import body_changes, body_ndiff  # noqa: E402
from tools.vc33_l3_probe import Sess, pads_sorted, plane  # noqa: E402
from tools.vc33_l4_pad_map import components, enter_l4, sprite, summarize  # noqa: E402

CHARS = {0: ".", 1: "1", 3: " ", 4: "B", 5: "#", 11: "A", 12: "C"}
OUT = ROOT / "tests/fixtures/vc33_l4_phase_mid.json"


def dump(g, y0=34, y1=52, x0=15, x1=40):
    for y in range(y0, y1 + 1):
        row = "".join(CHARS.get(int(g[y, x]), str(int(g[y, x]))[-1]) for x in range(x0, x1 + 1))
        print(f"{y:02d}|{row}")


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP", e)
        return None


def pad(sess, d, g, x0, tag=""):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    g0, s0 = g, sprite(g)
    d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
    if d2 is None:
        return d, g, 0.0, 0.0
    g2 = plane(d2["frame"])
    s1 = sprite(g2)
    dx = (s1["body"]["cx"] - s0["body"]["cx"]) if s0 and s1 else 0.0
    dy = (s1["body"]["cy"] - s0["body"]["cy"]) if s0 and s1 else 0.0
    nd = body_ndiff(g0, g2)
    print(
        f"{tag}x{x0} nd={nd} Δ=({dx},{dy}) cy={s1['body']['cy'] if s1 else None} "
        f"h12={int((g2==12).sum())} lv={d2.get('levels_completed')}"
    )
    return d2, g2, dx, dy


def gap_tops(g):
    out = {}
    for x in (24, 25, 26, 27, 28, 29, 30):
        ys = [y for y in range(34, 56) if int(g[y, x]) == 0]
        out[x] = (min(ys) if ys else None, ys[:8])
    return out


def mid_gap0(g):
    return [(x, y) for x in (24, 25, 26) for y in range(34, 46) if int(g[y, x]) == 0]


def to_bay1(sess, hop=39):
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    while int((g == 12).sum()) == 0:
        d, g, _, _ = pad(sess, d, g, 15, "s ")
    c = components(g, 12, 1, 80)[0]
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    g = plane(d2["frame"]); d = d2
    d, g, _, _ = pad(sess, d, g, hop, f"h{hop} ")
    return d, g


def try_clear(sess, d, g, out):
    if int(d.get("levels_completed") or 0) < 4:
        return d, g, False
    print("CLEAR", d.get("levels_completed"))
    (ROOT / "tests/fixtures/vc33_l4_clear_frame.json").write_text(
        json.dumps({"frame": d["frame"], "levels": d.get("levels_completed")}, indent=2),
        encoding="utf-8",
    )
    d1 = sess.action("ACTION1")
    (ROOT / "tests/fixtures/vc33_l5_frame_live.json").write_text(
        json.dumps({"frame": d1["frame"], "levels": d1.get("levels_completed")}, indent=2),
        encoding="utf-8",
    )
    out["cleared"] = True
    return d, g, True


def main():
    key = _api_key()
    sess = Sess(key)
    out = {"trials": []}
    try:
        sess.open()

        # A: hop, kill12, env sequences at cy48, climb; watch gap tops
        print("\n==== A kill12 env phase climb ====")
        for env_seq in (
            [39, 45, 51, 57],
            [57, 51, 45, 39],
            [39, 39, 45, 45],
            [45],
            [51],
        ):
            d, g = to_bay1(sess, 39)
            d, g, _, _ = pad(sess, d, g, 15, "kill ")  # cy48, c12 clear
            print(f"seq={env_seq} pre-env tops={gap_tops(g)}")
            for e in env_seq:
                d, g, dx, dy = pad(sess, d, g, e, f"e{e} ")
                print(f"  after{e} tops={gap_tops(g)} mid0={mid_gap0(g)} nd flips?")
            # climb to ceiling
            for i in range(5):
                d, g, _, dy = pad(sess, d, g, 15, f"up{i} ")
                m0 = mid_gap0(g)
                print(f"  climb cy={sprite(g)['body']['cy']} tops={gap_tops(g)} mid0={m0}")
                if m0 or any(c["cx"] > 20 for c in components(g, 12, 1, 80)):
                    print("HIT", m0, components(g, 12, 1, 80))
                    dump(g)
                    out["trials"].append({"seq": env_seq, "hit": True, "mid0": m0})
                    break
                if abs(dy) < 0.1:
                    out["trials"].append({
                        "seq": env_seq,
                        "ceil_tops": gap_tops(g),
                        "mid0": mid_gap0(g),
                        "cy": sprite(g)["body"]["cy"],
                    })
                    break
            d, g, done = try_clear(sess, d, g, out)
            if done:
                break
            # early stop if we found any mid0 across seqs
            if out["trials"] and out["trials"][-1].get("hit"):
                break

        if out.get("cleared"):
            OUT.write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
            return

        # B: at ceiling click mid interface
        print("\n==== B ceiling mid clicks ====")
        d, g = to_bay1(sess, 39)
        for i in range(5):
            d, g, _, dy = pad(sess, d, g, 15, "Bu ")
            if abs(dy) < 0.1:
                break
        print("ceiling", sprite(g))
        dump(g)
        mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20][0]
        clicks = []
        # accent-mid interface + mid cells + gap cells
        for x, y in [
            (24, 44), (25, 44), (26, 44), (26, 45), (26, 46),
            (27, 44), (27, 45), (28, 40), (28, 34), (28, 45),
            (23, 44), (23, 45), (30, 44), (30, 45),
        ]:
            g0 = g
            d2 = click(sess, x, y)
            if d2 is None:
                break
            g2 = plane(d2["frame"])
            nd = body_ndiff(g0, g2)
            if nd:
                print(f"click({x},{y}) nd={nd} ch={body_changes(g0,g2)} lv={d2.get('levels_completed')}")
                clicks.append({"xy": [x, y], "ch": body_changes(g0, g2)})
                g = g2; d = d2
                if mid_gap0(g) or any(c["cx"] > 20 for c in components(g, 12, 1, 80)):
                    print("B HIT")
                    dump(g)
            else:
                print(f"click({x},{y}) noop")
        out["ceiling_clicks"] = clicks
        d, g, done = try_clear(sess, d, g, out)
        if done:
            OUT.write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
            return

        # C: from left, arm then click MID (not pad)
        print("\n==== C arm left then click mid ====")
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        while int((g == 12).sum()) == 0:
            d, g, _, _ = pad(sess, d, g, 15, "Cs ")
        left = components(g, 12, 1, 80)[0]
        mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20][0]
        d2 = click(sess, round(left["cx"]), round(left["cy"]))
        g = plane(d2["frame"]); d = d2
        print("armed", sprite(g))
        g0, s0 = g, sprite(g)
        d2 = click(sess, round(mid["cx"]), round(mid["cy"]))
        g = plane(d2["frame"]); d = d2
        s1 = sprite(g)
        print(
            f"click mid Δ=({s1['body']['cx']-s0['body']['cx']},{s1['body']['cy']-s0['body']['cy']}) "
            f"ch={body_changes(g0,g)} h12={int((g==12).sum())} lv={d.get('levels_completed')}"
        )
        dump(g, 28, 56, 0, 55)
        out["arm_mid"] = {
            "dx": s1["body"]["cx"] - s0["body"]["cx"],
            "dy": s1["body"]["cy"] - s0["body"]["cy"],
            "sprite": s1,
            "levels": d.get("levels_completed"),
        }
        # if hopped into/past mid, pursue
        if abs(out["arm_mid"]["dx"]) > 0.1:
            for i in range(15):
                if int(d.get("levels_completed") or 0) >= 4:
                    break
                moved = False
                # prefer gate clicks
                for c in components(g, 12, 1, 80):
                    d2 = click(sess, round(c["cx"]), round(c["cy"]))
                    if d2:
                        g2 = plane(d2["frame"])
                        if body_ndiff(g, g2) or sprite(g2)["body"]["cx"] != sprite(g)["body"]["cx"]:
                            g = g2; d = d2
                            print("gated", sprite(g))
                            moved = True
                            break
                if moved:
                    continue
                for x0 in (15, 9, 39, 45, 51, 57):
                    d, g, dx, dy = pad(sess, d, g, x0, "Cn ")
                    if abs(dx) + abs(dy) > 0.1:
                        moved = True
                        break
                if not moved:
                    break
            try_clear(sess, d, g, out)

        # D: bay1 with c12, click mid (charged hop toward mid?)
        print("\n==== D bay1 c12 click mid ====")
        d, g = to_bay1(sess, 39)
        print("bay1 c12", int((g == 12).sum()), sprite(g))
        # re-arm left
        left = [c for c in components(g, 12, 1, 80) if c["cx"] < 20]
        if left:
            d2 = click(sess, round(left[0]["cx"]), round(left[0]["cy"]))
            g = plane(d2["frame"]); d = d2
            print("rearmed", body_changes)
        mid = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
        if mid:
            g0, s0 = g, sprite(g)
            d2 = click(sess, round(mid[0]["cx"]), round(mid[0]["cy"]))
            g = plane(d2["frame"]); d = d2
            s1 = sprite(g)
            print(
                f"D mid Δ=({s1['body']['cx']-s0['body']['cx']},{s1['body']['cy']-s0['body']['cy']}) "
                f"ch={body_changes(g0,g)} lv={d.get('levels_completed')}"
            )
            dump(g, 28, 56, 0, 55)
            out["bay1_mid"] = {
                "dx": s1["body"]["cx"] - s0["body"]["cx"],
                "dy": s1["body"]["cy"] - s0["body"]["cy"],
                "levels": d.get("levels_completed"),
            }
            try_clear(sess, d, g, out)

        OUT.write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
        print("wrote", OUT, "lv", d.get("levels_completed"))
    finally:
        sess.close()


if __name__ == "__main__":
    main()
