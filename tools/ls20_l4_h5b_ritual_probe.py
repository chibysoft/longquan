"""L4 H5b: c0+UDD ritual, and near-gate UDD then enter.

Also records (7,5) eject rule: any action -> (7,1) then apply (live-probed).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import RITUAL, _step_cell
from tools.ls20_l4_arming_probe import (
    _climb_to_l4,
    _gate_walk,
    _plan_armed_stamp_only,
    _plan_to_pickup,
)
from tools.ls20_l4_h5_arming_probe import (
    _c0_contact_cell,
    _exec_path,
    _try_stamp,
    _walk_to,
)

REPORT = ROOT / "docs" / "ls20_l4_h5b_ritual_probe.md"


def _exec_ritual(sess, frame, meta, log, tag, ritual=None):
    ritual = list(ritual or RITUAL)
    cur = ls20.init(frame).cursor
    log.append({"tag": f"{tag}_ritual_start", "cursor": cur, "ritual": ritual})
    for i, a in enumerate(ritual, 1):
        before = ls20.init(frame).cursor
        resp = sess.action(DIR_TO_ACTION[a])
        frame, meta = resp["frame"], resp
        after = ls20.init(frame).cursor
        log.append({
            "tag": f"{tag}_ritual", "step": i, "action": DIR_TO_ACTION[a],
            "before": before, "after": after,
            "moved": before != after,
            "levels": int(meta.get("levels_completed") or 0),
            "ui": ls20.ui_energy(frame),
        })
        print(f"  ritual {a}: {before}->{after}")
    return frame, meta


def variant_c0_udd(sess, frame, meta, log):
    p_pu, _ = _plan_to_pickup(frame)
    if p_pu:
        frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")
    hits = _c0_contact_cell(frame)
    log.append({"tag": "c0_hits", "hits": hits})
    if not hits:
        return frame, meta, "C0UDD_NO_HIT"
    p, _ = _walk_to(frame, hits[0])
    if p is None:
        return frame, meta, "C0UDD_UNREACHABLE"
    frame, meta, cleared = _exec_path(sess, frame, meta, p, log, "to_c0")
    if cleared:
        return frame, meta, "C0UDD_PASS_CONTACT"
    log.append({"tag": "c0_at", "cursor": ls20.init(frame).cursor,
                "snap": _gate_walk(frame)})
    frame, meta = _exec_ritual(sess, frame, meta, log, "c0")
    log.append({"tag": "post_ritual_snap", "snap": _gate_walk(frame)})
    frame, meta, ok = _try_stamp(sess, frame, meta, log, "c0udd")
    return frame, meta, "C0UDD_PASS" if ok else "C0UDD_FAIL"


def variant_gate_udd(sess, frame, meta, log):
    """Unarmed walk to (2,1) beside gate, UDD, then try LEFT into (1,1) / stamp plan."""
    p_pu, _ = _plan_to_pickup(frame)
    if p_pu:
        frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")
    # (2,1) reached in bare variant
    p, _ = _walk_to(frame, (2, 1))
    if p is None:
        return frame, meta, "GATEUDD_UNREACHABLE_21"
    frame, meta, cleared = _exec_path(sess, frame, meta, p, log, "to_21")
    if cleared:
        return frame, meta, "GATEUDD_PASS_WALK"
    log.append({"tag": "at_21", "cursor": ls20.init(frame).cursor,
                "snap": _gate_walk(frame)})
    frame, meta = _exec_ritual(sess, frame, meta, log, "gate")
    log.append({"tag": "post_gate_ritual", "cursor": ls20.init(frame).cursor,
                "snap": _gate_walk(frame)})
    # explicit LEFT into gate
    before = ls20.init(frame).cursor
    resp = sess.action(DIR_TO_ACTION[(-1, 0)])
    frame, meta = resp["frame"], resp
    after = ls20.init(frame).cursor
    lv = int(meta.get("levels_completed") or 0)
    log.append({"tag": "gate_left", "before": before, "after": after, "levels": lv,
                "snap": _gate_walk(frame)})
    print(f"  LEFT into gate: {before}->{after} lv={lv}")
    if lv >= 4:
        return frame, meta, "GATEUDD_PASS_LEFT"
    frame, meta, ok = _try_stamp(sess, frame, meta, log, "gateudd")
    return frame, meta, "GATEUDD_PASS" if ok else "GATEUDD_FAIL"


def variant_c0_then_gate_udd(sess, frame, meta, log):
    """Contact c0, UDD there, walk to (2,1), try enter gate."""
    p_pu, _ = _plan_to_pickup(frame)
    if p_pu:
        frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")
    hits = _c0_contact_cell(frame)
    if not hits:
        return frame, meta, "COMBO_NO_C0"
    p, _ = _walk_to(frame, hits[0])
    if p is None:
        return frame, meta, "COMBO_C0_UNREACH"
    frame, meta, cleared = _exec_path(sess, frame, meta, p, log, "to_c0")
    if cleared:
        return frame, meta, "COMBO_PASS_C0"
    frame, meta = _exec_ritual(sess, frame, meta, log, "combo_c0")
    p2, _ = _walk_to(frame, (2, 1), armed=True)  # try armed topology after ritual
    if p2 is None:
        p2, _ = _walk_to(frame, (2, 1), armed=False)
    if p2 is None:
        log.append({"tag": "combo_no_path_21", "snap": _gate_walk(frame)})
        frame, meta, ok = _try_stamp(sess, frame, meta, log, "combo")
        return frame, meta, "COMBO_PASS" if ok else "COMBO_FAIL_NO21"
    frame, meta, cleared = _exec_path(sess, frame, meta, p2, log, "to_21")
    if cleared:
        return frame, meta, "COMBO_PASS_WALK"
    before = ls20.init(frame).cursor
    resp = sess.action(DIR_TO_ACTION[(-1, 0)])
    frame, meta = resp["frame"], resp
    after = ls20.init(frame).cursor
    lv = int(meta.get("levels_completed") or 0)
    log.append({"tag": "combo_left", "before": before, "after": after, "levels": lv,
                "snap": _gate_walk(frame)})
    print(f"  combo LEFT: {before}->{after} lv={lv}")
    if lv >= 4:
        return frame, meta, "COMBO_PASS_LEFT"
    frame, meta, ok = _try_stamp(sess, frame, meta, log, "combo")
    return frame, meta, "COMBO_PASS" if ok else "COMBO_FAIL"


VARIANTS = {
    "c0_udd": variant_c0_udd,
    "gate_udd": variant_gate_udd,
    "combo": variant_c0_then_gate_udd,
}


def run_one(variant: str) -> dict:
    key = _api_key()
    if not key:
        raise RuntimeError("no key")
    sess = OnlineSession(key)
    log = []
    try:
        sess.open(tags=[f"ls20_l4_h5b_{variant}"])
        frame, meta = _climb_to_l4(sess)
        log.append({"tag": "l4_start", "snap": _gate_walk(frame),
                    "levels": int(meta.get("levels_completed") or 0)})
        print(f"=== {variant} ===")
        frame, meta, verdict = VARIANTS[variant](sess, frame, meta, log)
        log.append({"tag": "RESULT", "verdict": verdict,
                    "levels": int(meta.get("levels_completed") or 0),
                    "snap": _gate_walk(frame)})
        print(f"verdict={verdict}")
        return {"variant": variant, "verdict": verdict, "log": log}
    finally:
        sess.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=list(VARIANTS) + ["all"], default="all")
    args = ap.parse_args()
    variants = list(VARIANTS) if args.variant == "all" else [args.variant]
    if args.variant == "all":
        variants = ["c0_udd", "gate_udd", "combo"]
    results = []
    for v in variants:
        results.append(run_one(v))
        if "PASS" in results[-1]["verdict"]:
            break
    lines = ["# ls20 L4 H5b ritual probe", ""]
    for r in results:
        lines.append(f"## `{r['variant']}` → **{r['verdict']}**\n")
        for row in r["log"]:
            lines.append(f"- `{row}`")
        lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {REPORT}")
    return 0 if any("PASS" in r["verdict"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
