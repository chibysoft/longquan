"""L4 H5g: legend-LEFT at (2,1), then ACTION5, then enter gate / stamp.

Also try ACTION5-only control at (2,1).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_l4_arming_probe import _climb_to_l4, _plan_to_pickup
from tools.ls20_l4_h5_arming_probe import _exec_path, _try_stamp, _walk_to
from tools.ls20_l4_h5e_diff_probe import _plane_diff, _snap

REPORT = ROOT / "docs" / "ls20_l4_h5g_left_a5_probe.md"


def _a5(sess, frame, meta, log, tag):
    before = frame
    bs = _snap(before)
    resp = sess.action(5)  # interact — not in DIR map
    frame, meta = resp["frame"], resp
    as_ = _snap(frame)
    diff = _plane_diff(before, frame, limit=100)
    log.append({
        "tag": tag,
        "before": bs,
        "after": as_,
        "diff_n": diff["n"],
        "transitions": diff["transitions"],
        "levels": int(meta.get("levels_completed") or 0),
    })
    print(f"  A5: n={diff['n']} trans={diff['transitions']} "
          f"c0 {bs['c0']}->{as_['c0']} gate_u={as_['gate_in_walk_u']} "
          f"lv={log[-1]['levels']}")
    return frame, meta


def run_variant(sess, *, do_left: bool, do_a5: bool, name: str) -> dict:
    log = []
    frame, meta = _climb_to_l4(sess)
    log.append({"tag": "l4", "variant": name, "snap": _snap(frame)})
    p_pu, _ = _plan_to_pickup(frame)
    if p_pu:
        frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")
    p, _ = _walk_to(frame, (2, 1))
    if p is None:
        return {"verdict": "NO_21", "log": log, "name": name}
    frame, meta, cleared = _exec_path(sess, frame, meta, p, log, "to21")
    if cleared:
        return {"verdict": "PASS_WALK", "log": log, "name": name}
    if ls20.init(frame).cursor != (2, 1):
        return {"verdict": "MISS_21", "log": log, "name": name}

    if do_left:
        before = frame
        bs = _snap(before)
        resp = sess.action(DIR_TO_ACTION[(-1, 0)])
        frame, meta = resp["frame"], resp
        as_ = _snap(frame)
        diff = _plane_diff(before, frame, limit=40)
        log.append({"tag": "left", "diff_n": diff["n"], "transitions": diff["transitions"],
                    "after": as_, "levels": int(meta.get("levels_completed") or 0)})
        print(f"  LEFT: n={diff['n']} trans={diff['transitions']} c0={as_['c0']}")

    if do_a5:
        frame, meta = _a5(sess, frame, meta, log, "a5")

    if int(meta.get("levels_completed") or 0) >= 4:
        return {"verdict": "PASS_EARLY", "log": log, "name": name}

    # try LEFT into gate
    if ls20.init(frame).cursor == (2, 1):
        before = frame
        resp = sess.action(DIR_TO_ACTION[(-1, 0)])
        frame, meta = resp["frame"], resp
        as_ = _snap(frame)
        log.append({"tag": "enter_left", "after": as_,
                    "levels": int(meta.get("levels_completed") or 0),
                    "diff_n": _plane_diff(before, frame, limit=20)["n"]})
        print(f"  enter LEFT: {as_['cursor']} gate_u={as_['gate_in_walk_u']} "
              f"lv={log[-1]['levels']}")
        if int(meta.get("levels_completed") or 0) >= 4:
            return {"verdict": "PASS_ENTER", "log": log, "name": name}

    frame, meta, ok = _try_stamp(sess, frame, meta, log, "stamp")
    return {
        "verdict": "PASS" if ok else "FAIL",
        "log": log,
        "name": name,
        "final": _snap(frame),
    }


def main() -> int:
    key = _api_key()
    variants = [
        ("left_a5", True, True),
        ("a5_only", False, True),
        ("left_only", True, False),  # already know FAIL but keep legend state for stamp
    ]
    results = []
    for name, do_left, do_a5 in variants:
        sess = OnlineSession(key)
        try:
            sess.open(tags=[f"ls20_l4_h5g_{name}"])
            print(f"=== {name} ===")
            r = run_variant(sess, do_left=do_left, do_a5=do_a5, name=name)
            results.append(r)
            print(f"verdict={r['verdict']}")
            if "PASS" in r["verdict"]:
                break
        finally:
            sess.close()

    lines = ["# L4 H5g LEFT + ACTION5\n"]
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
