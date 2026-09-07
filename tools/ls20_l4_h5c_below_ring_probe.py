"""L4 H5c: approach the ring from BELOW via vertical warp (8,4)->(8,9).

Prior probes proved the upper approach to (6,5)/(6,6) is sealed by portals.
From (8,9) the lower chamber reaches (6,8)/(6,9)/(6,10) (pickup2). Try:
  1. stand on (6,9)/(6,8), pulse U/L/R/D, watch ring/legend diffs
  2. if ring dissolves (c9/c14/stamp_c9 change), armed-stamp without ritual
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_l4_arming_probe import (
    _climb_to_l4,
    _gate_walk,
    _plan_to_pickup,
)
from tools.ls20_l4_h5_arming_probe import _exec_path, _try_stamp, _walk_to

REPORT = ROOT / "docs" / "ls20_l4_h5c_below_ring_probe.md"
FIXTURE = ROOT / "tests" / "fixtures" / "ls20_l4_frame_below_ring.json"


def _counts(frame):
    g = ls20._plane(frame)
    return {
        "c9": int((g == 9).sum()),
        "c12": int((g == 12).sum()),
        "c14": int((g == 14).sum()),
        "c0": int((g == 0).sum()),
        "c8": int((g == 8).sum()),
        "stamp_c9": _gate_walk(frame)["stamp_c9"],
        "gate_u": _gate_walk(frame)["gate_in_walk_u"],
        "unlock": _gate_walk(frame)["unlock_cands"],
    }


def _ring_patch(frame):
    g = ls20._plane(frame)
    return g[30:35, 33:40].tolist()


def main() -> int:
    key = _api_key()
    if not key:
        raise RuntimeError("no key")
    sess = OnlineSession(key)
    log = []
    try:
        sess.open(tags=["ls20_l4_h5c_below"])
        frame, meta = _climb_to_l4(sess)
        log.append({"tag": "l4", "counts": _counts(frame), "ring": _ring_patch(frame)})

        p_pu, _ = _plan_to_pickup(frame)
        if p_pu:
            frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")

        p, _ = _walk_to(frame, (8, 4))
        if p is None:
            log.append({"tag": "RESULT", "verdict": "NO_84"})
            return 1
        frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to_84")
        frame, meta, _ = _exec_path(sess, frame, meta, [(0, 1)], log, "warp")
        log.append({"tag": "landed", "cursor": ls20.init(frame).cursor,
                    "counts": _counts(frame)})
        print(f"landed {log[-1]}")

        # go to (6,9) — adjacent below-ring corridor
        for target in ((6, 9), (6, 8), (6, 10)):
            p, _ = _walk_to(frame, target)
            if p is None:
                log.append({"tag": "skip", "target": target})
                continue
            frame, meta, cleared = _exec_path(sess, frame, meta, p, log, f"to_{target}")
            if cleared:
                log.append({"tag": "RESULT", "verdict": "PASS_ON_WALK", "levels": 4})
                break
            cur = ls20.init(frame).cursor
            log.append({"tag": "at", "want": target, "cursor": cur,
                        "counts": _counts(frame), "ring": _ring_patch(frame)})
            print(f"at {cur} counts={log[-1]['counts']}")
            if cur != target:
                continue
            # pulse four dirs
            for d in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                before = ls20.init(frame).cursor
                before_c = _counts(frame)
                before_ring = _ring_patch(frame)
                resp = sess.action(DIR_TO_ACTION[d])
                frame, meta = resp["frame"], resp
                after = ls20.init(frame).cursor
                after_c = _counts(frame)
                after_ring = _ring_patch(frame)
                changed = before_c != after_c or before_ring != after_ring
                row = {
                    "tag": "pulse", "from": target, "dir": d,
                    "before": before, "after": after,
                    "counts_before": before_c, "counts_after": after_c,
                    "ring_changed": before_ring != after_ring,
                    "levels": int(meta.get("levels_completed") or 0),
                }
                log.append(row)
                print(f"  pulse {d}: {before}->{after} changed={changed} "
                      f"ring_chg={row['ring_changed']} c9 {before_c['c9']}->{after_c['c9']}")
                if int(meta.get("levels_completed") or 0) >= 4:
                    log.append({"tag": "RESULT", "verdict": "PASS_ON_PULSE"})
                    break
                if after_c.get("gate_u") or after_c["stamp_c9"] != before_c["stamp_c9"] \
                        or after_c["c14"] != before_c["c14"] or row["ring_changed"]:
                    log.append({"tag": "EFFECT", "detail": row})
                    print("  *** EFFECT DETECTED ***")
                    # try stamp immediately
                    frame, meta, ok = _try_stamp(sess, frame, meta, log, "effect")
                    log.append({"tag": "RESULT",
                                "verdict": "PASS_AFTER_EFFECT" if ok else "EFFECT_NO_CLEAR"})
                    REPORT.write_text(
                        "# L4 H5c below-ring\n\n" + "\n".join(f"- `{r}`" for r in log),
                        encoding="utf-8",
                    )
                    return 0 if ok else 1
                # if we moved away from target, break pulse loop and re-seek next target
                if after != target:
                    break
            else:
                continue
            break

        # final stamp attempt from wherever we are
        g = ls20._plane(frame)
        FIXTURE.write_text(json.dumps({"frame": g.tolist(),
                                       "levels": int(meta.get("levels_completed") or 0),
                                       "cursor": ls20.init(frame).cursor}),
                           encoding="utf-8")
        frame, meta, ok = _try_stamp(sess, frame, meta, log, "final")
        verdict = "PASS" if ok else "NO_EFFECT_FAIL"
        log.append({"tag": "RESULT", "verdict": verdict, "counts": _counts(frame)})
        REPORT.write_text(
            f"# L4 H5c below-ring\n\n> verdict: **{verdict}**\n\n"
            + "\n".join(f"- `{r}`" for r in log) + "\n",
            encoding="utf-8",
        )
        print(f"verdict={verdict} wrote {REPORT}")
        return 0 if ok else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
