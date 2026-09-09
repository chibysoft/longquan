"""L4 H55 (a): cy≈51 + left c12 lit — multi-step PHASE primitives (no climb).

Each trial: fresh enter → convert to c12 @ cy≈51 → run a short sequence that
NEVER uses pad9/pad15 vertical intent after c12 (except accidental hop dy).
Watch: mid_kind, n4, levels, novel, h12 keep, local mid cells.

Families:
  U*  unarmed bay0: env parity then mid / flanks
  A*  arm then env then mid (may consume charge as hop)
  H*  arm+hop39 bay1 c12: env / rearm / mid / shuttle / flank
  M*  arm then mid-as-hop, then follow-ups
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l2_probe import body_changes, body_ndiff  # noqa: E402
from tools.vc33_l3_probe import Sess, pads_sorted, plane  # noqa: E402
from tools.vc33_l4_pad_map import components, enter_l4, gap11, sprite  # noqa: E402

OUT = ROOT / "tests/fixtures/vc33_l4_c12_phase.json"


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP", e)
        return None


def pad(sess, g, x0):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    return click(sess, int(round(p["cx"])), int(round(p["cy"])))


def left12(g):
    cs = [c for c in components(g, 12, 1, 80) if c["cx"] < 20]
    return cs[0] if cs else None


def mid_comp(g):
    m1 = [c for c in components(g, 1, 4, 80) if c["cx"] > 20]
    if m1:
        return {"kind": 1, **{k: m1[0][k] for k in ("n", "x0", "y0", "x1", "y1", "cx", "cy")}}
    m12 = [c for c in components(g, 12, 1, 80) if c["cx"] > 20]
    if m12:
        return {"kind": 12, **{k: m12[0][k] for k in ("n", "x0", "y0", "x1", "y1", "cx", "cy")}}
    return None


def n4_mid(g, mid):
    if not mid:
        return 0
    H, W = g.shape
    kind = mid["kind"]
    n = 0
    for y in range(mid["y0"], mid["y1"] + 1):
        for x in range(mid["x0"], mid["x1"] + 1):
            if int(g[y, x]) != kind:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H and int(g[ny, nx]) == 0:
                    n += 1
    return n


def snap(g, d):
    sp = sprite(g)
    mid = mid_comp(g)
    return {
        "lv": d.get("levels_completed"),
        "acts": d.get("available_actions"),
        "h12": int((g == 12).sum()),
        "left12": left12(g) is not None,
        "mid": mid,
        "n4": n4_mid(g, mid),
        "cy": sp["body"]["cy"] if sp else None,
        "cx": sp["body"]["cx"] if sp else None,
        "hist": dict(Counter(int(v) for v in g.ravel())),
        "gap": gap11(g),
    }


def sigs(before, after, g0, g1):
    out = []
    if after["mid"] and before["mid"]:
        if after["mid"]["kind"] != before["mid"]["kind"]:
            out.append(f"mid_kind {before['mid']['kind']}->{after['mid']['kind']}")
        bb0 = (before["mid"]["x0"], before["mid"]["y0"], before["mid"]["x1"], before["mid"]["y1"])
        bb1 = (after["mid"]["x0"], after["mid"]["y0"], after["mid"]["x1"], after["mid"]["y1"])
        if bb0 != bb1:
            out.append(f"mid_bbox {bb0}->{bb1}")
    if after["n4"] != before["n4"]:
        out.append(f"n4 {before['n4']}->{after['n4']}")
    if (after["lv"] or 0) > (before["lv"] or 0):
        out.append(f"levels {before['lv']}->{after['lv']}")
    if after["acts"] != before["acts"]:
        out.append(f"acts {before['acts']}->{after['acts']}")
    # novel excluding ordinary left-12 (already lit) — look for NEW colors
    nov = {c: n for c, n in after["hist"].items() if c not in before["hist"]}
    if nov:
        out.append(f"novel {nov}")
    if before["h12"] > 0 and after["h12"] == 0:
        out.append("h12_cleared")
    if before["gap"] != after["gap"]:
        out.append("gap_ch")
    mid = before["mid"] or after["mid"]
    if mid:
        local = []
        for y in range(max(0, mid["y0"] - 2), min(64, mid["y1"] + 4)):
            for x in range(max(0, mid["x0"] - 4), min(64, mid["x1"] + 5)):
                a, b = int(g0[y, x]), int(g1[y, x])
                if a != b and (a, b) not in (
                    (3, 0), (0, 3), (3, 4), (4, 3), (3, 11), (11, 3),
                    (4, 11), (11, 4), (4, 0), (0, 4), (11, 0), (0, 11),
                ):
                    local.append((x, y, a, b))
        if local:
            out.append(f"local_mid {local[:16]}")
    return out


def setup_c12_bay0(sess):
    ent = enter_l4(sess)
    d, g = ent["data"], ent["frame"]
    for _ in range(8):
        if left12(g):
            break
        d2 = pad(sess, g, 15)
        if d2 is None:
            break
        g = plane(d2["frame"]); d = d2
    assert left12(g), "no left c12"
    return d, g


def arm(sess, d, g):
    c = left12(g)
    d2 = click(sess, round(c["cx"]), round(c["cy"]))
    return d2, plane(d2["frame"])


def do_seq(sess, d, g, steps):
    """steps: list of ('pad', x0) | ('click', x, y) | ('mid',) | ('arm',) | ('left12',)"""
    log = []
    for st in steps:
        if st[0] == "pad":
            d2 = pad(sess, g, st[1])
        elif st[0] == "click":
            d2 = click(sess, st[1], st[2])
        elif st[0] == "mid":
            m = mid_comp(g)
            if not m:
                log.append({"step": st, "fail": "no mid"})
                break
            d2 = click(sess, round(m["cx"]), round(m["cy"]))
        elif st[0] == "arm" or st[0] == "left12":
            c = left12(g)
            if not c:
                log.append({"step": st, "fail": "no left12"})
                break
            d2 = click(sess, round(c["cx"]), round(c["cy"]))
        else:
            raise ValueError(st)
        if d2 is None:
            log.append({"step": st, "fail": "http"})
            break
        g = plane(d2["frame"]); d = d2
        sp = sprite(g)
        log.append({
            "step": st,
            "cy": sp["body"]["cy"] if sp else None,
            "cx": sp["body"]["cx"] if sp else None,
            "h12": int((g == 12).sum()),
            "mid_kind": mid_comp(g)["kind"] if mid_comp(g) else None,
            "lv": d.get("levels_completed"),
        })
    return d, g, log


def run_trial(sess, label, builder):
    """builder(sess) -> (d,g) starting state with c12; then returns steps list."""
    d, g = setup_c12_bay0(sess)
    before = snap(g, d)
    g0 = g.copy()
    steps = builder(sess, d, g)
    # builder may mutate — if it returns (d,g,steps) use that
    if isinstance(steps, tuple):
        d, g, steps = steps
        before = snap(g, d)
        g0 = g.copy()
    d2, g2, log = do_seq(sess, d, g, steps)
    after = snap(g2, d2)
    s = sigs(before, after, g0, g2)
    row = {
        "label": label,
        "sigs": s,
        "before": {k: before[k] for k in ("cy", "cx", "h12", "n4", "lv", "left12")},
        "after": {
            "cy": after["cy"], "cx": after["cx"], "h12": after["h12"],
            "n4": after["n4"], "lv": after["lv"], "left12": after["left12"],
            "mid_kind": after["mid"]["kind"] if after["mid"] else None,
        },
        "log": log,
        "nd": body_ndiff(g0, g2),
        "ch": body_changes(g0, g2) if body_ndiff(g0, g2) else {},
    }
    flag = "SIGNAL" if s else "none"
    hard = any(str(x).startswith("mid_kind") or str(x).startswith("levels") for x in s)
    print(
        f"| {label:36s} | {flag:6s} | cy {before['cy']}->{after['cy']} "
        f"cx {before['cx']}->{after['cx']} h12 {before['h12']}->{after['h12']} "
        f"n4={after['n4']} | {s}"
    )
    return row, hard


def main():
    key = _api_key()
    sess = Sess(key)
    rows = []
    hard = False
    try:
        sess.open()

        trials = []

        # --- Unarmed bay0 ---
        def U_env_mid(s, d, g):
            return [("pad", 39), ("pad", 45), ("pad", 51), ("pad", 57), ("mid",)]

        def U_env2_mid(s, d, g):
            # flip each env twice (parity back) then odd on 39
            steps = []
            for x0 in (39, 45, 51, 57):
                steps += [("pad", x0), ("pad", x0)]
            steps += [("pad", 39), ("mid",)]
            return steps

        def U_flanks(s, d, g):
            return [
                ("click", 25, 45), ("click", 31, 45), ("click", 26, 45),
                ("click", 26, 46), ("mid",), ("click", 28, 45),
            ]

        def U_double_arm_mid(s, d, g):
            return [("arm",), ("arm",), ("mid",)]

        trials += [
            ("U/env_then_mid", U_env_mid),
            ("U/env2_parity_mid", U_env2_mid),
            ("U/flanks_mid", U_flanks),
            ("U/double_arm_mid", U_double_arm_mid),
        ]

        # --- Arm then phase (bay0) ---
        def A_env_mid(s, d, g):
            d, g = arm(s, d, g)
            return d, g, [("pad", 39), ("pad", 45), ("mid",)]

        def A_mid_only(s, d, g):
            d, g = arm(s, d, g)
            return d, g, [("mid",)]

        def A_env_all_mid(s, d, g):
            d, g = arm(s, d, g)
            return d, g, [("pad", 39), ("pad", 45), ("pad", 51), ("pad", 57), ("mid",)]

        def A_gap_mid(s, d, g):
            d, g = arm(s, d, g)
            gp = gap11(g)
            return d, g, [("click", round(gp["cx"]), round(gp["cy"])), ("mid",)]

        trials += [
            ("A/arm_env_mid", A_env_mid),
            ("A/arm_mid", A_mid_only),
            ("A/arm_env_all_mid", A_env_all_mid),
            ("A/arm_gap_mid", A_gap_mid),
        ]

        # --- Hop to bay1 with c12, then phase ---
        def H_env_mid(s, d, g):
            d, g = arm(s, d, g)
            d2 = pad(s, g, 39)
            g = plane(d2["frame"]); d = d2
            return d, g, [("pad", 45), ("pad", 51), ("pad", 57), ("mid",)]

        def H_rearm_mid(s, d, g):
            d, g = arm(s, d, g)
            d2 = pad(s, g, 39)
            g = plane(d2["frame"]); d = d2
            return d, g, [("arm",), ("mid",)]

        def H_rearm_env_mid(s, d, g):
            d, g = arm(s, d, g)
            d2 = pad(s, g, 39)
            g = plane(d2["frame"]); d = d2
            return d, g, [("arm",), ("pad", 45), ("pad", 51), ("mid",)]

        def H_rearm_env_hop_mid(s, d, g):
            # rearm, env, hop with pad39 (back?), mid
            d, g = arm(s, d, g)
            d2 = pad(s, g, 39)
            g = plane(d2["frame"]); d = d2
            return d, g, [("arm",), ("pad", 45), ("pad", 39), ("mid",)]

        def H_shuttle_mid(s, d, g):
            # bay1 -> rearm -> hop back -> rearm -> hop east -> mid
            d, g = arm(s, d, g)
            d2 = pad(s, g, 39)
            g = plane(d2["frame"]); d = d2
            return d, g, [
                ("arm",), ("pad", 39),  # hop west?
                ("arm",), ("pad", 39),  # hop east
                ("mid",),
            ]

        def H_flanks(s, d, g):
            d, g = arm(s, d, g)
            d2 = pad(s, g, 39)
            g = plane(d2["frame"]); d = d2
            return d, g, [
                ("click", 25, 45), ("click", 31, 45), ("click", 26, 45),
                ("click", 26, 46), ("click", 28, 45), ("mid",),
            ]

        def H_rearm_flank_mid(s, d, g):
            d, g = arm(s, d, g)
            d2 = pad(s, g, 39)
            g = plane(d2["frame"]); d = d2
            return d, g, [("arm",), ("click", 25, 45), ("click", 26, 45), ("mid",)]

        trials += [
            ("H/bay1_env_mid", H_env_mid),
            ("H/bay1_rearm_mid", H_rearm_mid),
            ("H/bay1_rearm_env_mid", H_rearm_env_mid),
            ("H/bay1_rearm_env_hop_mid", H_rearm_env_hop_mid),
            ("H/shuttle_mid", H_shuttle_mid),
            ("H/bay1_flanks_mid", H_flanks),
            ("H/bay1_rearm_flank_mid", H_rearm_flank_mid),
        ]

        # --- Mid-as-hop then follow ---
        def M_mid_hop_env_mid(s, d, g):
            d, g = arm(s, d, g)
            return d, g, [("mid",), ("pad", 45), ("pad", 51), ("mid",)]

        def M_mid_hop_rearm_mid(s, d, g):
            d, g = arm(s, d, g)
            return d, g, [("mid",), ("arm",), ("mid",)]

        def M_mid_hop_flank(s, d, g):
            d, g = arm(s, d, g)
            return d, g, [("mid",), ("click", 25, 45), ("click", 26, 45), ("mid",)]

        trials += [
            ("M/midhop_env_mid", M_mid_hop_env_mid),
            ("M/midhop_rearm_mid", M_mid_hop_rearm_mid),
            ("M/midhop_flank", M_mid_hop_flank),
        ]

        for label, builder in trials:
            if hard:
                break
            row, hard = run_trial(sess, label, builder)
            rows.append(row)
            # incremental save
            OUT.write_text(
                json.dumps({"rows": rows, "partial": True}, indent=2, default=str),
                encoding="utf-8",
            )

        sig_rows = [r for r in rows if r.get("sigs")]
        hard_hit = any(
            any(str(x).startswith("mid_kind") or str(x).startswith("levels") for x in r.get("sigs", []))
            for r in rows
        )
        # phase-interesting: local_mid / n4 / acts without being mere hop+env
        interesting = [
            r["label"] for r in sig_rows
            if any(
                str(x).startswith(("mid_kind", "levels", "n4", "local_mid", "acts", "novel", "gap_ch"))
                for x in r["sigs"]
            )
        ]
        reading = (
            "PHASE_HIT" if hard_hit
            else ("WEAK_SIGNAL" if interesting else "NO_SIGNAL")
        )
        out = {
            "rows": rows,
            "n": len(rows),
            "signal_labels": [r["label"] for r in sig_rows],
            "interesting": interesting,
            "reading": reading,
            "hypothesis": "H55 cy51+c12 phase/multi-step (no climb)",
        }
        print("\n## Summary")
        print("signal_labels:", out["signal_labels"])
        print("interesting:", interesting)
        print("READING:", reading)
        OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print("wrote", OUT)
    finally:
        sess.close()


if __name__ == "__main__":
    main()
