"""L4 H5i: legend-LEFT flip, then c0 contact (keep flip), return to gate, enter."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_l4_arming_probe import _climb_to_l4, _plan_to_pickup
from tools.ls20_l4_h5_arming_probe import _c0_contact_cell, _exec_path, _try_stamp, _walk_to
from tools.ls20_l4_h5e_diff_probe import _plane_diff, _snap
from tools.ls20_seated_clear import RITUAL

REPORT = ROOT / "docs" / "ls20_l4_h5i_flip_c0_probe.md"


def main() -> int:
    sess = OnlineSession(_api_key())
    log = []
    try:
        sess.open(tags=["ls20_l4_h5i"])
        frame, meta = _climb_to_l4(sess)
        p_pu, _ = _plan_to_pickup(frame)
        if p_pu:
            frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")

        p, _ = _walk_to(frame, (2, 1))
        frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to21")
        before = frame
        resp = sess.action(DIR_TO_ACTION[(-1, 0)])
        frame, meta = resp["frame"], resp
        diff = _plane_diff(before, frame, limit=20)
        log.append({"tag": "flip", "diff_n": diff["n"], "transitions": diff["transitions"],
                    "c0": _snap(frame)["c0"]})
        print(f"flip n={diff['n']} c0={log[-1]['c0']}")

        # to c0 — avoid RIGHT-first paths that might restore? path may go RIGHT
        hits = _c0_contact_cell(frame)
        # After legend flip, palette y>=54 is full of color0 — ignore chrome.
        off = ls20.grid_offset(frame)
        hits = [
            c for c in hits
            if ls20.cursor_to_pixel(c, off)[1] < 54
        ]
        log.append({"tag": "c0_hits", "hits": hits, "c0_pre": _snap(frame)["c0"]})
        if not hits:
            log.append({"tag": "RESULT", "verdict": "NO_PLAYFIELD_C0"})
            REPORT.write_text(
                "# L4 H5i flip+c0\n\n" + "\n".join(f"- `{r}`" for r in log) + "\n",
                encoding="utf-8",
            )
            return 1
        p, _ = _walk_to(frame, hits[0])
        if p is None:
            log.append({"tag": "RESULT", "verdict": "C0_UNREACHABLE", "target": hits[0]})
            REPORT.write_text(
                "# L4 H5i flip+c0\n\n" + "\n".join(f"- `{r}`" for r in log) + "\n",
                encoding="utf-8",
            )
            return 1
        frame, meta, cleared = _exec_path(sess, frame, meta, p, log, "to_c0")
        snap = _snap(frame)
        log.append({"tag": "at_c0", "snap_c0": snap["c0"], "cursor": snap["cursor"],
                    "gate_u": snap["gate_in_walk_u"]})
        print(f"at c0 c0={snap['c0']} (want stay 85) cursor={snap['cursor']}")
        if cleared:
            log.append({"tag": "RESULT", "verdict": "PASS_C0"})
            return 0
        # optional mini ritual at c0
        for a in RITUAL:
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
        log.append({"tag": "after_udd", "snap": _snap(frame)})

        # return to (2,1) without undoing — check c0 count
        p, _ = _walk_to(frame, (2, 1))
        if p:
            frame, meta, _ = _exec_path(sess, frame, meta, p, log, "back21")
        snap = _snap(frame)
        log.append({"tag": "back21", "c0": snap["c0"], "cursor": snap["cursor"],
                    "gate_u": snap["gate_in_walk_u"]})
        print(f"back21 c0={snap['c0']} cursor={snap['cursor']} gate_u={snap['gate_in_walk_u']}")

        if snap["cursor"] == (2, 1):
            before = frame
            resp = sess.action(DIR_TO_ACTION[(-1, 0)])
            frame, meta = resp["frame"], resp
            as_ = _snap(frame)
            log.append({"tag": "enter", "after": as_,
                        "diff_n": _plane_diff(before, frame, limit=30)["n"],
                        "levels": int(meta.get("levels_completed") or 0)})
            print(f"enter {as_['cursor']} gate_u={as_['gate_in_walk_u']} "
                  f"lv={log[-1]['levels']} c0={as_['c0']}")

        frame, meta, ok = _try_stamp(sess, frame, meta, log, "stamp")
        log.append({"tag": "RESULT", "verdict": "PASS" if ok else "FAIL",
                    "final_c0": _snap(frame)["c0"]})
        REPORT.write_text(
            "# L4 H5i flip+c0\n\n" + "\n".join(f"- `{r}`" for r in log) + "\n",
            encoding="utf-8",
        )
        print("wrote", REPORT, log[-1])
        return 0 if ok else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
