"""L4 H5n: dual-pickup order then bump gate at (2,1).

Variants:
  pu1_pu2 — top pickup then bottom (6,10) then (2,1)+LEFT+enter attempt
  pu2_pu1 — bottom first then top then gate
  both_gate — eat both then armed-stamp plan
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.match import mover_bbox_from_cursor
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import _ov, _energy_bfs, MAX_FUEL
from tools.ls20_l4_arming_probe import _climb_to_l4, _fuel0, _plan_armed_stamp_only
from tools.ls20_l4_h5_arming_probe import _exec_path, _try_stamp, _walk_to
from tools.ls20_l4_h5e_diff_probe import _plane_diff, _snap

REPORT = ROOT / "docs" / "ls20_l4_h5n_dual_pickup_probe.md"


def _plan_to_specific_pickup(frame, target_bbox):
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    wu = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, wu)
    pickups = ls20.energy_pickups(frame)
    fuel0 = _fuel0(frame)

    def at(cell, _f, _p):
        return _ov(mover_bbox_from_cursor(cell, offset), target_bbox) > 0

    p, c, f, pm = _energy_bfs(
        state.cursor, fuel0, 0, wu, pickups, offset, at, warps,
    )
    return p, c


def _eat_pickup(sess, frame, meta, log, which: str):
    """which: 'top' = min y pickup, 'bot' = max y pickup."""
    pickups = ls20.energy_pickups(frame)
    if not pickups:
        log.append({"tag": "no_pickups"})
        return frame, meta, False
    pickups = sorted(pickups, key=lambda b: b[1])
    pb = pickups[0] if which == "top" else pickups[-1]
    p, _ = _plan_to_specific_pickup(frame, pb)
    if p is None:
        # fallback: cell (6,10) for bot
        if which == "bot":
            p, _ = _walk_to(frame, (6, 10))
        if p is None:
            log.append({"tag": "pu_unreach", "which": which, "bbox": pb})
            return frame, meta, False
    before = _snap(frame)
    # may need warp for bot: ensure path works; if starts fail, go via (8,4)
    frame, meta, cleared = _exec_path(sess, frame, meta, p, log, f"pu_{which}")
    after = _snap(frame)
    log.append({
        "tag": "ate", "which": which, "bbox": pb,
        "ui_before": before["ui"], "ui_after": after["ui"],
        "c11_before": before["c11"], "c11_after": after["c11"],
        "cursor": after["cursor"],
    })
    print(f"  ate {which}: ui {before['ui']}->{after['ui']} "
          f"c11 {before['c11']}->{after['c11']} at {after['cursor']}")
    return frame, meta, cleared


def _gate_bump(sess, frame, meta, log):
    p, _ = _walk_to(frame, (2, 1))
    if p is None:
        log.append({"tag": "no_21"})
        return frame, meta, False
    frame, meta, cleared = _exec_path(sess, frame, meta, p, log, "to21")
    if cleared:
        return frame, meta, True
    if ls20.init(frame).cursor != (2, 1):
        log.append({"tag": "miss21", "cursor": ls20.init(frame).cursor})
        return frame, meta, False
    before = frame
    bs = _snap(before)
    resp = sess.action(DIR_TO_ACTION[(-1, 0)])
    frame, meta = resp["frame"], resp
    as_ = _snap(frame)
    d = _plane_diff(before, frame, limit=10)
    log.append({
        "tag": "bump",
        "c0b": bs["c0"], "c0a": as_["c0"],
        "gate_u": as_["gate_in_walk_u"],
        "n": d["n"], "trans": d["transitions"],
        "levels": int(meta.get("levels_completed") or 0),
    })
    print(f"  bump: c0 {bs['c0']}->{as_['c0']} gate_u={as_['gate_in_walk_u']} "
          f"n={d['n']}")
    # try enter again
    resp = sess.action(DIR_TO_ACTION[(-1, 0)])
    frame, meta = resp["frame"], resp
    as2 = _snap(frame)
    lv = int(meta.get("levels_completed") or 0)
    log.append({"tag": "enter", "cursor": as2["cursor"], "gate_u": as2["gate_in_walk_u"],
                "levels": lv})
    if lv >= 4:
        return frame, meta, True
    frame, meta, ok = _try_stamp(sess, frame, meta, log, "stamp")
    return frame, meta, ok


def run_variant(name: str, order: list[str]) -> dict:
    sess = OnlineSession(_api_key())
    log = []
    try:
        sess.open(tags=[f"ls20_l4_h5n_{name}"])
        frame, meta = _climb_to_l4(sess)
        log.append({"tag": "l4", "snap": _snap(frame)})
        print(f"=== {name} order={order} ===")
        for which in order:
            frame, meta, cleared = _eat_pickup(sess, frame, meta, log, which)
            if cleared:
                return {"name": name, "verdict": "PASS_ON_PICKUP", "log": log}
        frame, meta, ok = _gate_bump(sess, frame, meta, log)
        return {
            "name": name,
            "verdict": "PASS" if ok else "FAIL",
            "log": log,
            "final": _snap(frame),
        }
    finally:
        sess.close()


def main() -> int:
    variants = [
        ("pu1_pu2", ["top", "bot"]),
        ("pu2_pu1", ["bot", "top"]),
    ]
    results = []
    for name, order in variants:
        r = run_variant(name, order)
        results.append(r)
        print(f"verdict={r['verdict']}")
        if "PASS" in r["verdict"]:
            break
    lines = ["# L4 H5n dual pickup\n"]
    for r in results:
        lines.append(f"## `{r['name']}` → **{r['verdict']}**\n")
        for row in r["log"]:
            lines.append(f"- `{row}`")
        lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("wrote", REPORT)
    return 0 if any("PASS" in r["verdict"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
