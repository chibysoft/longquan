"""L4 H41: park at left-convert (c12, cy≈51); NEVER climb / NEVER ±15 hop.

Knife (new): treat clear like L1/L2 x-overlap OR multi-gate/fingerprint while
parked — not paint-y45 / break-ceiling / morph-mid / east-hop.

Measure each click:
  - accent.x vs gap.x (overlap? dx)
  - pads_sorted y0/x0 relocation
  - full hist + novel color comps (1/12/other)
  - levels_completed

tags=["vc33_recon"]. Enter via enter_l4.
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
from tools.vc33_l2_probe import body_ndiff  # noqa: E402
from tools.vc33_l3_probe import Sess, pads_sorted, plane  # noqa: E402
from tools.vc33_l4_pad_map import (  # noqa: E402
    FIXTURE_L4_CLEAR,
    FIXTURE_L5,
    components,
    enter_l4,
    gap11,
    sprite,
)

OUT = ROOT / "tests/fixtures/vc33_l4_park_x.json"


def click(sess, x, y):
    try:
        return sess.click(int(x), int(y))
    except requests.HTTPError as e:
        print("HTTP", e)
        return None


def hist(g):
    return {int(k): int(v) for k, v in zip(*np.unique(g, return_counts=True))}


def pad_sig(g):
    return [(int(p["x0"]), int(p["y0"]), int(p["x1"]), int(p["y1"])) for p in pads_sorted(g)]


def x_metrics(g):
    sp = sprite(g)
    gp = gap11(g)
    if not sp or not sp.get("accent") or not gp:
        return None
    acc, body = sp["accent"], sp["body"]
    # interval overlap on x (L1/L2 style)
    ox0 = max(acc["x0"], gp["x0"])
    ox1 = min(acc["x1"], gp["x1"])
    overlap = ox1 >= ox0
    return {
        "body_cx": round(body["cx"], 2),
        "body_cy": round(body["cy"], 2),
        "body_y0": body["y0"],
        "acc_x0": acc["x0"],
        "acc_x1": acc["x1"],
        "acc_y0": acc["y0"],
        "acc_y1": acc["y1"],
        "gap_x0": gp["x0"],
        "gap_x1": gp["x1"],
        "gap_y0": gp["y0"],
        "gap_y1": gp["y1"],
        "dx_acc_to_gap": gp["x0"] - acc["x1"],  # >0 means gap is to the right
        "x_overlap": overlap,
        "y_overlap": not (acc["y1"] < gp["y0"] or acc["y0"] > gp["y1"]),
        "h12": int((g == 12).sum()),
        "c1n": len(components(g, 1, 1, 80)),
        "c12n": len(components(g, 12, 1, 80)),
        "c12": components(g, 12, 1, 80),
        "c1": components(g, 1, 1, 80),
        "pads": pad_sig(g),
        "hist": hist(g),
    }


def snap(d, g, tag, log, g_prev=None):
    m = x_metrics(g)
    nd = None if g_prev is None else int(body_ndiff(g_prev, g))
    row = {
        "tag": tag,
        "lv": d.get("levels_completed"),
        "acts": d.get("available_actions"),
        "nd": nd,
        **(m or {}),
    }
    # compact print
    if m:
        print(
            f"{tag} cy={m['body_cy']} accx={m['acc_x0']}-{m['acc_x1']} "
            f"gapx={m['gap_x0']}-{m['gap_x1']} dx={m['dx_acc_to_gap']} "
            f"xov={m['x_overlap']} h12={m['h12']} c12n={m['c12n']} "
            f"padsY={[p[1] for p in m['pads']]} nd={nd} lv={row['lv']}"
        )
    else:
        print(f"{tag} NO_SPRITE nd={nd} lv={row['lv']}")
    log.append(row)
    return row


def pad_click(sess, d, g, x0, tag, log):
    p = next(p for p in pads_sorted(g) if p["x0"] == x0)
    g0 = g
    d2 = click(sess, int(round(p["cx"])), int(round(p["cy"])))
    if d2 is None:
        return d, g
    g2 = plane(d2["frame"])
    snap(d2, g2, tag, log, g0)
    return d2, g2


def cell_click(sess, d, g, x, y, tag, log):
    g0 = g
    d2 = click(sess, x, y)
    if d2 is None:
        return d, g
    g2 = plane(d2["frame"])
    snap(d2, g2, tag, log, g0)
    return d2, g2


def hist_delta(h0, h1):
    keys = set(h0) | set(h1)
    return {k: h1.get(k, 0) - h0.get(k, 0) for k in keys if h1.get(k, 0) != h0.get(k, 0)}


def novel_colors(g, base_hist):
    h = hist(g)
    return sorted(set(h) - set(base_hist))


def main():
    key = _api_key()
    sess = Sess(key)
    log = []
    out = {"hypothesis": "H41", "log": log}
    try:
        sess.open()
        out["game_id"] = sess.game_id
        ent = enter_l4(sess)
        d, g = ent["data"], ent["frame"]
        snap(d, g, "enter", log)
        base_hist = hist(g)
        base_pads = pad_sig(g)
        out["base_hist"] = base_hist
        out["base_pads"] = base_pads

        # --- sink to left convert (pad15 ×2); stay cy≈51 ---
        d, g = pad_click(sess, d, g, 15, "pre_sink", log)
        d, g = pad_click(sess, d, g, 15, "convert", log)
        m = x_metrics(g)
        assert m and m["h12"] > 0, "expected left c12 after convert"
        assert m["body_cy"] >= 50, f"expected park cy≈51 got {m['body_cy']}"
        park_cy = m["body_cy"]
        out["park"] = m

        # --- §A: env spam at park (no arm → no hop); watch corridor / accent.x ---
        env_order = [39, 45, 51, 57, 39, 57, 45, 51, 39, 45, 51, 57] * 3  # 36
        for i, x0 in enumerate(env_order):
            d, g = pad_click(sess, d, g, x0, f"A_env{x0}_{i}", log)
            m = x_metrics(g)
            if m and (m["x_overlap"] or m["body_cy"] < park_cy - 1 or int(d.get("levels_completed") or 0) >= 4):
                print("*** EARLY SIGNAL ***", m)
                break

        # --- §B: click left c12 cells (arm?) then ONLY non-pad cells — avoid hop ---
        # do NOT click pads after arm
        c12s = components(g, 12, 1, 80)
        if c12s:
            w = c12s[0]
            for j, (x, y) in enumerate(
                [
                    (w["x0"], w["y0"]),
                    (w["x1"], w["y1"]),
                    (int(w["cx"]), int(w["cy"])),
                    (w["x0"], int(w["cy"])),
                    (w["x1"], int(w["cy"])),
                ]
            ):
                d, g = cell_click(sess, d, g, x, y, f"B_c12_{j}_{x}_{y}", log)

        # mid / gap / dig / accent / beam while possibly armed — still no pads
        gp = gap11(g)
        sp = sprite(g)
        targets = []
        for c in components(g, 1, 1, 80):
            if c["cx"] > 20:  # mid window
                targets += [
                    (int(c["cx"]), int(c["cy"]), "mid"),
                    (c["x0"], c["y1"], "mid_bl"),
                    (c["x1"], c["y1"], "mid_br"),
                    (c["x0"], c["y0"], "mid_tl"),
                ]
        if gp:
            targets += [
                (int(gp["cx"]), int(gp["cy"]), "gap"),
                (gp["x0"], gp["y0"], "gap_tl"),
                (gp["x1"], gp["y1"], "gap_br"),
            ]
        if sp and sp.get("accent"):
            a = sp["accent"]
            targets += [
                (int(a["cx"]), int(a["cy"]), "acc"),
                (a["x1"] + 1, int(a["cy"]), "acc_east"),
                (a["x0"] - 1, int(a["cy"]), "acc_west"),
            ]
            # dig cells below accent (color0)
            for x in range(a["x0"], a["x1"] + 1):
                y = a["y1"] + 1
                if 0 <= y < g.shape[0] and int(g[y, x]) == 0:
                    targets.append((x, y, "dig"))
                    break
        # beam color5 near mid
        for y in (46, 47):
            for x in (27, 28, 29):
                if int(g[y, x]) == 5:
                    targets.append((x, y, "beam"))
        # rare colors from hist
        for col in sorted(set(hist(g)) - {0, 3, 4, 5, 7, 9, 11, 12, 1}):
            comps = components(g, col, 1, 200)
            if comps:
                c = comps[0]
                targets.append((int(c["cx"]), int(c["cy"]), f"rare{col}"))

        for i, (x, y, lab) in enumerate(targets[:40]):
            d, g = cell_click(sess, d, g, x, y, f"B_{lab}_{i}_{x}_{y}", log)
            if int(d.get("levels_completed") or 0) >= 4:
                break

        # --- §C: more env + pad15 micro (stay sink-side; pad15 at park is further sink risk) ---
        # use ONLY env + pad9 once? pad9 at park after convert is UP (+3y) — FORBIDDEN (climb)
        # pad15 is further sink — allowed as long as we don't climb; may 12→1
        for i, x0 in enumerate([39, 45, 51, 57, 39, 45]):
            d, g = pad_click(sess, d, g, x0, f"C_env{x0}_{i}", log)

        # optional: one more convert cycle if extinguished — re-establish park without climb path
        m = x_metrics(g)
        if m and m["h12"] == 0 and m["body_cy"] < 53:
            # sink until convert or bottom
            for k in range(4):
                d, g = pad_click(sess, d, g, 15, f"C_resink_{k}", log)
                m = x_metrics(g)
                if m and m["h12"] > 0:
                    break

        # --- §D: fingerprint summary ---
        final = x_metrics(g)
        out["final"] = final
        out["lv"] = d.get("levels_completed")
        # pad relocation across log
        pad_changes = []
        prev = base_pads
        for row in log:
            if "pads" in row and row["pads"] != prev:
                pad_changes.append({"tag": row["tag"], "from": prev, "to": row["pads"]})
                prev = row["pads"]
        out["pad_relocations"] = pad_changes

        # accent.x1 max / min dx
        acc_x1s = [r["acc_x1"] for r in log if "acc_x1" in r]
        dxs = [r["dx_acc_to_gap"] for r in log if "dx_acc_to_gap" in r]
        xovs = [r for r in log if r.get("x_overlap")]
        out["acc_x1_range"] = [min(acc_x1s), max(acc_x1s)] if acc_x1s else None
        out["dx_range"] = [min(dxs), max(dxs)] if dxs else None
        out["any_x_overlap"] = bool(xovs)
        out["cy_range"] = (
            [min(r["body_cy"] for r in log if "body_cy" in r),
             max(r["body_cy"] for r in log if "body_cy" in r)]
            if any("body_cy" in r for r in log) else None
        )

        # hist deltas vs base at convert and final
        conv = next((r for r in log if r["tag"] == "convert"), None)
        out["hist_delta_convert"] = hist_delta(base_hist, conv["hist"]) if conv and "hist" in conv else None
        out["hist_delta_final"] = hist_delta(base_hist, final["hist"]) if final else None
        out["novel_final"] = novel_colors(g, base_hist) if final else None

        # component fingerprint: any new c1/c12 beyond left?
        c12_all = []
        for r in log:
            for c in r.get("c12") or []:
                c12_all.append((r["tag"], c))
        out["c12_sightings"] = c12_all
        mid12 = [s for s in c12_all if s[1]["cx"] > 20]
        out["any_mid12"] = bool(mid12)

        # hop detector: |Δcx|>=10 between consecutive
        hops = []
        prev_cx = None
        for r in log:
            if "body_cx" not in r:
                continue
            if prev_cx is not None and abs(r["body_cx"] - prev_cx) >= 10:
                hops.append({"tag": r["tag"], "from": prev_cx, "to": r["body_cx"]})
            prev_cx = r["body_cx"]
        out["hops_detected"] = hops

        print("\n=== H41 SUMMARY ===")
        print("lv", out["lv"], "acc_x1_range", out["acc_x1_range"], "dx_range", out["dx_range"])
        print("any_x_overlap", out["any_x_overlap"], "any_mid12", out["any_mid12"])
        print("pad_relocations", len(pad_changes), "hops", hops)
        print("hist_delta_final", out["hist_delta_final"], "novel", out["novel_final"])
        print("cy_range", out["cy_range"], "n_log", len(log))

        if int(out["lv"] or 0) >= 4:
            FIXTURE_L4_CLEAR.write_text(
                json.dumps({"game_id": sess.game_id, "frame": g.tolist(), "lv": out["lv"]}, indent=2),
                encoding="utf-8",
            )
            print("SAVED CLEAR", FIXTURE_L4_CLEAR)
            # try grab L5 if sync available
            try:
                d5 = sess.action("ACTION1")
                g5 = plane(d5["frame"])
                FIXTURE_L5.write_text(
                    json.dumps({
                        "game_id": sess.game_id,
                        "meta": {
                            "levels_completed": d5.get("levels_completed"),
                            "available_actions": d5.get("available_actions"),
                        },
                        "frame": g5.tolist(),
                    }, indent=2),
                    encoding="utf-8",
                )
                print("SAVED L5", FIXTURE_L5)
            except Exception as e:
                print("L5 grab fail", e)

    finally:
        sess.close()

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
