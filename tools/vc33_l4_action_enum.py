"""L4: enumerate every action while left c12 is lit.

Setup: enter → sink convert → stop (c12 on, still bay0, cy≈51).
Fresh enter per action so charge/state is comparable.
Record: h12 kept? Δy/Δx? mid morph? levels? acts?
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l2_probe import body_changes, body_ndiff  # noqa: E402
from tools.vc33_l3_probe import Sess, pads_sorted, plane  # noqa: E402
from tools.vc33_l4_pad_map import components, enter_l4, gap11, sprite  # noqa: E402

OUT = ROOT / "tests/fixtures/vc33_l4_action_enum.json"


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP", e)
        return None


def pad_click(sess, g, x0):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    return click(sess, int(round(p["cx"])), int(round(p["cy"])))


def mid_info(g):
    m1 = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
    if m1:
        return {"kind": 1, "n": m1[0]["n"], "bbox": (m1[0]["x0"], m1[0]["y0"], m1[0]["x1"], m1[0]["y1"])}
    m12 = [c for c in components(g, 12, 1, 80) if c["cx"] > 20]
    if m12:
        return {"kind": 12, "n": m12[0]["n"], "bbox": (m12[0]["x0"], m12[0]["y0"], m12[0]["x1"], m12[0]["y1"])}
    return None


def left_h12(g):
    left = [c for c in components(g, 12, 1, 80) if c["cx"] < 20]
    return int((g == 12).sum()), bool(left)


def setup_c12_bay0(sess):
    """Enter L4, sink until left 1→12, do NOT arm/hop. Return d,g at cy≈51 c12 lit."""
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    for _ in range(8):
        if int((g == 12).sum()) > 0:
            break
        d2 = pad_click(sess, g, 15)
        if d2 is None:
            break
        g = plane(d2["frame"])
        d = d2
    h12, has_left = left_h12(g)
    sp = sprite(g)
    assert h12 > 0 and has_left, f"setup failed h12={h12} left={has_left} cy={sp}"
    return d, g


def setup_c12_bay1(sess):
    """Enter, convert, arm, hop39 → bay1 cy51 with c12 still lit (charge spent)."""
    d, g = setup_c12_bay0(sess)
    c = [x for x in components(g, 12, 1, 80) if x["cx"] < 20][0]
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    g = plane(d2["frame"]); d = d2
    d2 = pad_click(sess, g, 39)
    g = plane(d2["frame"]); d = d2
    h12, has_left = left_h12(g)
    sp = sprite(g)
    print(f"  bay1 setup cx={sp['body']['cx']} cy={sp['body']['cy']} h12={h12}")
    return d, g


def run_one(sess, label, setup_fn, action_fn):
    d, g = setup_fn(sess)
    sp0 = sprite(g)
    m0 = mid_info(g)
    gp0 = gap11(g)
    h12_0, _ = left_h12(g)
    lv0 = d.get("levels_completed")
    acts0 = d.get("available_actions")

    d2 = action_fn(sess, d, g)
    if d2 is None:
        return {
            "label": label,
            "ok": False,
            "http": True,
            "h12_keep": None,
        }
    g2 = plane(d2["frame"])
    sp1 = sprite(g2)
    m1 = mid_info(g2)
    gp1 = gap11(g2)
    h12_1, has_left = left_h12(g2)
    dx = (sp1["body"]["cx"] - sp0["body"]["cx"]) if sp0 and sp1 else 0
    dy = (sp1["body"]["cy"] - sp0["body"]["cy"]) if sp0 and sp1 else 0
    nd = body_ndiff(g, g2)
    ch = body_changes(g, g2) if nd else {}
    row = {
        "label": label,
        "ok": True,
        "h12_before": h12_0,
        "h12_after": h12_1,
        "h12_keep": h12_1 > 0 and has_left,
        "dx": dx,
        "dy": dy,
        "cy0": sp0["body"]["cy"] if sp0 else None,
        "cy1": sp1["body"]["cy"] if sp1 else None,
        "cx0": sp0["body"]["cx"] if sp0 else None,
        "cx1": sp1["body"]["cx"] if sp1 else None,
        "mid0": m0,
        "mid1": m1,
        "mid_ch": m0 != m1,
        "gap_ch": gp0 != gp1,
        "lv0": lv0,
        "lv1": d2.get("levels_completed"),
        "acts0": acts0,
        "acts1": d2.get("available_actions"),
        "nd": nd,
        "ch": ch,
    }
    keep = "KEEP" if row["h12_keep"] else "CLEAR"
    mid_r = "CHG" if row["mid_ch"] else "none"
    print(
        f"| {label:22s} | {keep:5s} | d=({dx:+.0f},{dy:+.0f}) cy {row['cy0']}->{row['cy1']} "
        f"| mid={mid_r} | h12 {h12_0}->{h12_1} | lv={row['lv1']} | ch={ch}"
    )
    return row


def summarize(rows):
    keep_up = [r for r in rows if r.get("h12_keep") and (r.get("dy") or 0) < -0.1]
    keep_any_y = [r for r in rows if r.get("h12_keep") and abs(r.get("dy") or 0) > 0.1]
    clear_up = [r for r in rows if r.get("ok") and not r.get("h12_keep") and (r.get("dy") or 0) < -0.1]
    mid_resp = [r for r in rows if r.get("mid_ch")]
    keep_hop = [
        r for r in rows
        if r.get("h12_keep") and abs(r.get("dx") or 0) > 0.1 and abs(r.get("dy") or 0) < 0.1
    ]
    summary = {
        "keep_and_up": [r["label"] for r in keep_up],
        "keep_and_any_dy": [r["label"] for r in keep_any_y],
        "keep_and_hop_flat": [r["label"] for r in keep_hop],
        "clear_and_up": [r["label"] for r in clear_up],
        "mid_response": [r["label"] for r in mid_resp],
        "n_rows": len(rows),
    }
    if summary["keep_and_up"]:
        reading = "FOUND_LOCK — exists action that keeps c12 AND raises cy"
    elif summary["clear_and_up"] and not summary["keep_and_up"]:
        reading = (
            "DUAL12_NOT_PRECONDITION_VIA_CLIMB — all upward moves clear c12; "
            "dual-12 climb path blocked"
        )
    else:
        reading = "NO_UP_WHILE_C12 — no upward move observed while c12 lit in tested states"
    return summary, reading


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--only",
        default="",
        help="comma labels to run only, e.g. bay1/click_gap; merge into existing OUT",
    )
    args = ap.parse_args()
    only = {x.strip() for x in args.only.split(",") if x.strip()}

    key = _api_key()
    sess = Sess(key)
    rows = []
    if only and OUT.exists():
        prev = json.loads(OUT.read_text(encoding="utf-8"))
        rows = [r for r in prev.get("rows", []) if r.get("label") not in only]
    elif (ROOT / "tests/fixtures/vc33_l4_action_enum.partial.json").exists() and only:
        rows = json.loads(
            (ROOT / "tests/fixtures/vc33_l4_action_enum.partial.json").read_text(encoding="utf-8")
        )
        rows = [r for r in rows if r.get("label") not in only]

    try:
        sess.open()

        def bay0(s):
            return setup_c12_bay0(s)

        def bay0_armed(s):
            d, g = setup_c12_bay0(s)
            c = [x for x in components(g, 12, 1, 80) if x["cx"] < 20][0]
            d2 = click(s, round(c["cx"]), round(c["cy"]))
            return d2, plane(d2["frame"])

        def bay1(s):
            return setup_c12_bay1(s)

        jobs = []

        # Bay0 unarmed
        for x0 in (9, 15, 39, 45, 51, 57):
            jobs.append((f"bay0/pad{x0}", bay0, lambda s, d, g, x0=x0: pad_click(s, g, x0)))
        jobs.append((
            "bay0/click_left12", bay0,
            lambda s, d, g: click(
                s,
                round([c for c in components(g, 12, 1, 80) if c["cx"] < 20][0]["cx"]),
                round([c for c in components(g, 12, 1, 80) if c["cx"] < 20][0]["cy"]),
            ),
        ))
        jobs.append((
            "bay0/click_mid", bay0,
            lambda s, d, g: click(
                s,
                round([c for c in components(g, 1, 4, 80) if c["cx"] > 20][0]["cx"]),
                round([c for c in components(g, 1, 4, 80) if c["cx"] > 20][0]["cy"]),
            ),
        ))
        jobs.append((
            "bay0/click_midbot", bay0,
            lambda s, d, g: (
                lambda m: click(s, m["x0"], m["y1"])
            )([c for c in components(g, 1, 4, 80) if c["cx"] > 20][0]),
        ))
        jobs.append((
            "bay0/click_gap", bay0,
            lambda s, d, g: click(s, round(gap11(g)["cx"]), round(gap11(g)["cy"])),
        ))
        jobs.append(("bay0/click_flank10_45", bay0, lambda s, d, g: click(s, 10, 45)))
        jobs.append(("bay0/click_flank16_45", bay0, lambda s, d, g: click(s, 16, 45)))

        # Armed
        for x0 in (9, 15, 39, 45, 51, 57):
            jobs.append((
                f"armed/pad{x0}", bay0_armed,
                lambda s, d, g, x0=x0: pad_click(s, g, x0),
            ))
        jobs.append((
            "armed/click_mid", bay0_armed,
            lambda s, d, g: click(
                s,
                round([c for c in components(g, 1, 4, 80) if c["cx"] > 20][0]["cx"]),
                round([c for c in components(g, 1, 4, 80) if c["cx"] > 20][0]["cy"]),
            ),
        ))
        jobs.append((
            "armed/click_left12_again", bay0_armed,
            lambda s, d, g: click(
                s,
                round([c for c in components(g, 12, 1, 80) if c["cx"] < 20][0]["cx"]),
                round([c for c in components(g, 12, 1, 80) if c["cx"] < 20][0]["cy"]),
            ),
        ))

        # Bay1
        for x0 in (9, 15, 39, 45, 51, 57):
            jobs.append((
                f"bay1/pad{x0}", bay1,
                lambda s, d, g, x0=x0: pad_click(s, g, x0),
            ))
        jobs.append((
            "bay1/click_mid", bay1,
            lambda s, d, g: click(
                s,
                round([c for c in components(g, 1, 4, 80) if c["cx"] > 20][0]["cx"]),
                round([c for c in components(g, 1, 4, 80) if c["cx"] > 20][0]["cy"]),
            ),
        ))
        jobs.append((
            "bay1/click_left12", bay1,
            lambda s, d, g: click(
                s,
                round([c for c in components(g, 12, 1, 80) if c["cx"] < 20][0]["cx"]),
                round([c for c in components(g, 12, 1, 80) if c["cx"] < 20][0]["cy"]),
            ),
        ))
        jobs.append((
            "bay1/click_gap", bay1,
            lambda s, d, g: click(s, round(gap11(g)["cx"]), round(gap11(g)["cy"])),
        ))

        for label, setup, fn in jobs:
            if only and label not in only:
                continue
            print(f"\n## run {label}")
            rows.append(run_one(sess, label, setup, fn))
            # incremental save
            summary, reading = summarize(rows)
            OUT.write_text(
                json.dumps({"rows": rows, "summary": summary, "reading": reading}, indent=2, default=str),
                encoding="utf-8",
            )

        summary, reading = summarize(rows)
        print("\n## Summary")
        print("keep_and_up:", summary["keep_and_up"])
        print("keep_and_any_dy:", summary["keep_and_any_dy"])
        print("keep_and_hop_flat:", summary["keep_and_hop_flat"])
        print("clear_and_up:", summary["clear_and_up"])
        print("mid_response:", summary["mid_response"])
        print("READING:", reading)
        OUT.write_text(
            json.dumps({"rows": rows, "summary": summary, "reading": reading}, indent=2, default=str),
            encoding="utf-8",
        )
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
