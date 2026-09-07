"""L4: full-plane diffs at gate-adjacent (2,1) + pickup2/color8 arming tries.

Phase A: climb to L4, walk to (2,1), for each ACTION1-4 record before/after
         plane diff (value changes + counts). Look for arming signatures
         (stamp_c9 drop, legend flip, new walk_u on gate, etc.).

Phase B: from fresh L4 (same session after RESET+climb is expensive — do B
         as separate --phase). Warp to lower chamber, touch pickup2 (6,10)
         and color8 cells, then armed-stamp.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.match import mover_bbox_from_cursor, carrying_bbox_from_cursor
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_l4_arming_probe import _climb_to_l4, _gate_walk, _plan_to_pickup
from tools.ls20_l4_h5_arming_probe import _exec_path, _try_stamp, _walk_to

REPORT = ROOT / "docs" / "ls20_l4_h5e_diff_probe.md"
DIFF_JSON = ROOT / "tests" / "fixtures" / "ls20_l4_gate21_diffs.json"


def _plane_diff(before, after, limit: int = 80):
    b = ls20._plane(before)
    a = ls20._plane(after)
    ys, xs = np.where(b != a)
    changes = []
    for i in range(min(limit, len(xs))):
        x, y = int(xs[i]), int(ys[i])
        changes.append({"x": x, "y": y, "from": int(b[y, x]), "to": int(a[y, x])})
    # count transitions
    trans = {}
    for i in range(len(xs)):
        x, y = int(xs[i]), int(ys[i])
        key = (int(b[y, x]), int(a[y, x]))
        trans[key] = trans.get(key, 0) + 1
    return {
        "n": int(len(xs)),
        "transitions": {f"{a_}->{b_}": c for (a_, b_), c in sorted(trans.items())},
        "samples": changes,
    }


def _snap(frame):
    g = ls20._plane(frame)
    s = _gate_walk(frame)
    return {
        **s,
        "c9": int((g == 9).sum()),
        "c12": int((g == 12).sum()),
        "c14": int((g == 14).sum()),
        "c0": int((g == 0).sum()),
        "c8": int((g == 8).sum()),
        "c11": int((g == 11).sum()),
        "ui": ls20.ui_energy(frame),
        "cursor": ls20.init(frame).cursor,
        "mover": ls20.locate_mover(frame),
    }


def phase_a_diff(sess) -> dict:
    log = []
    frame, meta = _climb_to_l4(sess)
    log.append({"tag": "l4", "snap": _snap(frame)})
    p_pu, _ = _plan_to_pickup(frame)
    if p_pu:
        frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")
    p, _ = _walk_to(frame, (2, 1))
    if p is None:
        return {"verdict": "UNREACHABLE_21", "log": log}
    frame, meta, cleared = _exec_path(sess, frame, meta, p, log, "to21")
    if cleared:
        return {"verdict": "PASS_WALK", "log": log}
    if ls20.init(frame).cursor != (2, 1):
        log.append({"tag": "miss21", "cursor": ls20.init(frame).cursor})
        return {"verdict": "MISS_21", "log": log}

    diffs = []
    # For each dir: snapshot, act, snapshot, then UNDO by inverse if possible
    # Since we can't undo easily, re-path to (2,1) after each action.
    for d, name in (
        ((0, -1), "UP"),
        ((0, 1), "DOWN"),
        ((-1, 0), "LEFT"),
        ((1, 0), "RIGHT"),
    ):
        if ls20.init(frame).cursor != (2, 1):
            p, _ = _walk_to(frame, (2, 1))
            if not p:
                log.append({"tag": "repath_fail", "dir": name})
                break
            frame, meta, _ = _exec_path(sess, frame, meta, p, log, f"re21_{name}")
        before_f = frame
        before_s = _snap(before_f)
        resp = sess.action(DIR_TO_ACTION[d])
        frame, meta = resp["frame"], resp
        after_s = _snap(frame)
        diff = _plane_diff(before_f, frame)
        row = {
            "dir": name,
            "action": DIR_TO_ACTION[d],
            "before": before_s,
            "after": after_s,
            "diff": diff,
            "levels": int(meta.get("levels_completed") or 0),
        }
        diffs.append(row)
        log.append({"tag": "diff", "dir": name, "n": diff["n"],
                    "transitions": diff["transitions"],
                    "cursor": after_s["cursor"],
                    "gate_u": after_s["gate_in_walk_u"],
                    "stamp_c9": after_s["stamp_c9"],
                    "c9": after_s["c9"], "c14": after_s["c14"]})
        print(f"  {name}: n_diff={diff['n']} trans={diff['transitions']} "
              f"cursor {before_s['cursor']}->{after_s['cursor']} "
              f"gate_u={after_s['gate_in_walk_u']} stamp9={after_s['stamp_c9']}")
        if int(meta.get("levels_completed") or 0) >= 4:
            return {"verdict": "PASS", "log": log, "diffs": diffs}

    DIFF_JSON.write_text(json.dumps({"diffs": diffs}, indent=2), encoding="utf-8")
    # after diffs, try stamp from wherever
    frame, meta, ok = _try_stamp(sess, frame, meta, log, "after_diff")
    return {
        "verdict": "PASS" if ok else "DIFF_DONE_NO_CLEAR",
        "log": log,
        "diffs": diffs,
    }


def _c8_cells(frame):
    g = ls20._plane(frame)
    off = ls20.grid_offset(frame)
    wu = ls20.build_walkable(frame, off, armed=False)
    hits = []
    for cell in sorted(wu):
        for fn in (mover_bbox_from_cursor, carrying_bbox_from_cursor):
            x0, y0, x1, y1 = fn(cell, off)
            if np.any(g[y0 : y1 + 1, x0 : x1 + 1] == 8):
                hits.append(cell)
                break
    return hits


def phase_b_pickup2(sess) -> dict:
    log = []
    frame, meta = _climb_to_l4(sess)
    log.append({"tag": "l4", "snap": _snap(frame)})
    p_pu, _ = _plan_to_pickup(frame)
    if p_pu:
        frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")
    # warp down
    p, _ = _walk_to(frame, (8, 4))
    if p is None:
        return {"verdict": "NO_84", "log": log}
    frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to84")
    before = ls20.init(frame).cursor
    frame, meta, _ = _exec_path(sess, frame, meta, [(0, 1)], log, "warp")
    log.append({"tag": "land", "before": before, "after": ls20.init(frame).cursor,
                "snap": _snap(frame)})

    # pickup2 cell (6,10)
    for target, tag in (((6, 10), "pu2"),):
        p, _ = _walk_to(frame, target)
        if p is None:
            log.append({"tag": "unreachable", "target": target})
            continue
        before_s = _snap(frame)
        frame, meta, cleared = _exec_path(sess, frame, meta, p, log, f"to_{tag}")
        after_s = _snap(frame)
        diff = {"n": -1}
        # compare counts
        log.append({
            "tag": f"at_{tag}",
            "cursor": ls20.init(frame).cursor,
            "before_c11": before_s["c11"], "after_c11": after_s["c11"],
            "before_ui": before_s["ui"], "after_ui": after_s["ui"],
            "snap": after_s,
        })
        print(f"  {tag} at {after_s['cursor']} ui {before_s['ui']}->{after_s['ui']} "
              f"c11 {before_s['c11']}->{after_s['c11']}")
        if cleared:
            return {"verdict": "PASS_PU2", "log": log}

    # color8 cells
    c8 = _c8_cells(frame)
    log.append({"tag": "c8_hits", "hits": c8})
    print("c8 hits", c8)
    for cell in c8[:3]:
        p, _ = _walk_to(frame, cell)
        if p is None:
            continue
        before_s = _snap(frame)
        frame, meta, cleared = _exec_path(sess, frame, meta, p, log, f"c8_{cell}")
        after_s = _snap(frame)
        log.append({"tag": "at_c8", "cell": cell, "cursor": after_s["cursor"],
                    "snap": after_s,
                    "delta_c8": after_s["c8"] - before_s["c8"],
                    "delta_c9": after_s["c9"] - before_s["c9"]})
        print(f"  c8 {cell}: snap gate_u={after_s['gate_in_walk_u']} "
              f"stamp9={after_s['stamp_c9']}")
        if cleared:
            return {"verdict": "PASS_C8", "log": log}

    frame, meta, ok = _try_stamp(sess, frame, meta, log, "b_stamp")
    return {"verdict": "PASS" if ok else "B_NO_CLEAR", "log": log}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("a", "b", "all"), default="all")
    args = ap.parse_args()
    key = _api_key()
    if not key:
        raise RuntimeError("no key")

    results = []
    phases = ["a", "b"] if args.phase == "all" else [args.phase]
    for ph in phases:
        sess = OnlineSession(key)
        try:
            sess.open(tags=[f"ls20_l4_h5e_{ph}"])
            print(f"=== phase {ph} ===")
            if ph == "a":
                r = phase_a_diff(sess)
            else:
                r = phase_b_pickup2(sess)
            r["phase"] = ph
            results.append(r)
            print(f"verdict={r['verdict']}")
            if "PASS" in r["verdict"]:
                break
        finally:
            sess.close()

    lines = ["# ls20 L4 H5e gate-diff + pickup2/c8", ""]
    for r in results:
        lines.append(f"## phase `{r['phase']}` → **{r['verdict']}**\n")
        for row in r.get("log", []):
            lines.append(f"- `{row}`")
        lines.append("")
        if r.get("diffs"):
            lines.append("### diff summary\n")
            for d in r["diffs"]:
                lines.append(
                    f"- **{d['dir']}**: n={d['diff']['n']} "
                    f"trans=`{d['diff']['transitions']}` "
                    f"cursor {d['before']['cursor']}→{d['after']['cursor']}"
                )
            lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("wrote", REPORT)
    return 0 if any("PASS" in r["verdict"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
