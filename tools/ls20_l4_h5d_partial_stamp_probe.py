"""L4: interact from (1,2) — unarmed partial stamp overlap (ov=5)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import RITUAL
from tools.ls20_l4_arming_probe import _climb_to_l4, _gate_walk, _plan_to_pickup
from tools.ls20_l4_h5_arming_probe import _exec_path, _try_stamp, _walk_to

REPORT = ROOT / "docs" / "ls20_l4_h5d_partial_stamp_probe.md"


def main() -> int:
    sess = OnlineSession(_api_key())
    log = []
    try:
        sess.open(tags=["ls20_l4_h5d"])
        frame, meta = _climb_to_l4(sess)
        p_pu, _ = _plan_to_pickup(frame)
        if p_pu:
            frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")
        p, _ = _walk_to(frame, (1, 2))
        if p is None:
            print("unreachable 1,2")
            return 1
        frame, meta, cleared = _exec_path(sess, frame, meta, p, log, "to12")
        if cleared:
            log.append({"tag": "RESULT", "verdict": "PASS_WALK"})
        else:
            cur = ls20.init(frame).cursor
            log.append({"tag": "at12", "cursor": cur, "snap": _gate_walk(frame)})
            print("at", cur, log[-1]["snap"])
            # pulse UDD + LEFT/RIGHT/UP/DOWN extras
            seq = list(RITUAL) + [(-1, 0), (1, 0), (0, -1), (0, 1)]
            for a in seq:
                before = ls20.init(frame).cursor
                bs = _gate_walk(frame)
                resp = sess.action(DIR_TO_ACTION[a])
                frame, meta = resp["frame"], resp
                after = ls20.init(frame).cursor
                as_ = _gate_walk(frame)
                lv = int(meta.get("levels_completed") or 0)
                row = {
                    "tag": "pulse", "action": DIR_TO_ACTION[a],
                    "before": before, "after": after,
                    "gate_u": as_["gate_in_walk_u"],
                    "stamp_c9": as_["stamp_c9"],
                    "levels": lv,
                }
                log.append(row)
                print(f"  {a}: {before}->{after} gate_u={as_['gate_in_walk_u']} "
                      f"c9={as_['stamp_c9']} lv={lv}")
                if lv >= 4:
                    log.append({"tag": "RESULT", "verdict": "PASS_PULSE"})
                    break
                # if returned to 1,2 continue; if drifted try continue pulses anyway
            else:
                # try enter gate from wherever
                before = ls20.init(frame).cursor
                if before == (2, 1) or before == (1, 2):
                    resp = sess.action(DIR_TO_ACTION[(-1, 0)])
                    frame, meta = resp["frame"], resp
                    log.append({"tag": "left", "before": before,
                                "after": ls20.init(frame).cursor,
                                "levels": int(meta.get("levels_completed") or 0),
                                "snap": _gate_walk(frame)})
                frame, meta, ok = _try_stamp(sess, frame, meta, log, "final")
                log.append({"tag": "RESULT", "verdict": "PASS" if ok else "FAIL"})
                print("final", ok)

        REPORT.write_text(
            "# L4 H5d partial stamp (1,2)\n\n" + "\n".join(f"- `{r}`" for r in log) + "\n",
            encoding="utf-8",
        )
        print("wrote", REPORT)
        return 0 if any("PASS" in str(r) for r in log) else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
