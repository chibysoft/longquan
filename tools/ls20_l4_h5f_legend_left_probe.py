"""L4 H5f: at (2,1) fire LEFT (legend 5->0), then immediately enter gate.

Do NOT move RIGHT afterwards (that restored 0->5 in H5e).
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
from tools.ls20_l4_arming_probe import _climb_to_l4, _gate_walk, _plan_to_pickup
from tools.ls20_l4_h5_arming_probe import _exec_path, _try_stamp, _walk_to
from tools.ls20_l4_h5e_diff_probe import _plane_diff, _snap

REPORT = ROOT / "docs" / "ls20_l4_h5f_legend_left_probe.md"
FIXTURE = ROOT / "tests" / "fixtures" / "ls20_l4_frame_after_legend_left.json"


def main() -> int:
    sess = OnlineSession(_api_key())
    log = []
    try:
        sess.open(tags=["ls20_l4_h5f"])
        frame, meta = _climb_to_l4(sess)
        log.append({"tag": "l4", "snap": _snap(frame)})

        p_pu, _ = _plan_to_pickup(frame)
        if p_pu:
            frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")

        p, _ = _walk_to(frame, (2, 1))
        if p is None:
            log.append({"tag": "RESULT", "verdict": "NO_21"})
            return 1
        frame, meta, cleared = _exec_path(sess, frame, meta, p, log, "to21")
        if cleared:
            log.append({"tag": "RESULT", "verdict": "PASS_WALK"})
            return 0
        if ls20.init(frame).cursor != (2, 1):
            log.append({"tag": "RESULT", "verdict": "MISS_21",
                        "cursor": ls20.init(frame).cursor})
            return 1

        before = frame
        before_s = _snap(before)
        # LEFT — expected legend 5->0
        resp = sess.action(DIR_TO_ACTION[(-1, 0)])
        frame, meta = resp["frame"], resp
        after_s = _snap(frame)
        diff = _plane_diff(before, frame, limit=120)
        log.append({
            "tag": "left",
            "before": before_s,
            "after": after_s,
            "diff_n": diff["n"],
            "transitions": diff["transitions"],
            "levels": int(meta.get("levels_completed") or 0),
        })
        print(f"LEFT: n={diff['n']} trans={diff['transitions']}")
        print(f"  c0 {before_s['c0']}->{after_s['c0']} gate_u={after_s['gate_in_walk_u']} "
              f"stamp9={after_s['stamp_c9']} unlock={after_s['unlock_cands']}")

        g = ls20._plane(frame)
        FIXTURE.write_text(
            json.dumps({
                "frame": g.tolist(),
                "levels": int(meta.get("levels_completed") or 0),
                "cursor": ls20.init(frame).cursor,
                "snap": after_s,
                "diff": diff,
            }),
            encoding="utf-8",
        )

        if int(meta.get("levels_completed") or 0) >= 4:
            log.append({"tag": "RESULT", "verdict": "PASS_ON_LEFT"})
            REPORT.write_text("# H5f\n\n" + "\n".join(f"- `{r}`" for r in log), encoding="utf-8")
            return 0

        # Immediately try LEFT again into gate (still at 2,1 if blocked)
        cur = ls20.init(frame).cursor
        print(f"cursor after LEFT: {cur}")
        if cur == (2, 1):
            before2 = frame
            resp = sess.action(DIR_TO_ACTION[(-1, 0)])
            frame, meta = resp["frame"], resp
            s2 = _snap(frame)
            d2 = _plane_diff(before2, frame, limit=40)
            log.append({
                "tag": "left2_into_gate",
                "before_cursor": cur,
                "after": s2,
                "diff_n": d2["n"],
                "transitions": d2["transitions"],
                "levels": int(meta.get("levels_completed") or 0),
            })
            print(f"LEFT2: cursor {cur}->{s2['cursor']} n={d2['n']} "
                  f"trans={d2['transitions']} gate_u={s2['gate_in_walk_u']} "
                  f"lv={log[-1]['levels']}")
            if int(meta.get("levels_completed") or 0) >= 4:
                log.append({"tag": "RESULT", "verdict": "PASS_LEFT2"})
                REPORT.write_text("# H5f\n\n" + "\n".join(f"- `{r}`" for r in log), encoding="utf-8")
                return 0

        # armed stamp plan without undoing legend
        frame, meta, ok = _try_stamp(sess, frame, meta, log, "stamp")
        # if stamp path includes RIGHT that undoes legend, log final snap
        log.append({"tag": "RESULT", "verdict": "PASS" if ok else "FAIL",
                    "final": _snap(frame)})
        print("stamp", ok, "final", log[-1]["final"])

        REPORT.write_text(
            f"# L4 H5f legend-LEFT then gate\n\n> verdict: **{log[-1]['verdict']}**\n\n"
            + "\n".join(f"- `{r}`" for r in log) + "\n",
            encoding="utf-8",
        )
        print("wrote", REPORT)
        return 0 if ok else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
