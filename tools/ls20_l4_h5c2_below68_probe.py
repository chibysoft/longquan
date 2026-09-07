"""L4: pulse four dirs from (6,8) after warping below the ring."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_l4_arming_probe import _climb_to_l4, _gate_walk, _plan_to_pickup
from tools.ls20_l4_h5_arming_probe import _exec_path, _try_stamp, _walk_to

REPORT = ROOT / "docs" / "ls20_l4_h5c2_below68_probe.md"


def counts(frame):
    g = ls20._plane(frame)
    snap = _gate_walk(frame)
    return {
        "c9": int((g == 9).sum()),
        "c14": int((g == 14).sum()),
        "c12": int((g == 12).sum()),
        "stamp_c9": snap["stamp_c9"],
        "gate_u": snap["gate_in_walk_u"],
        "unlock": snap["unlock_cands"],
        "ring": g[30:35, 33:40].tolist(),
    }


def main() -> int:
    sess = OnlineSession(_api_key())
    log = []
    try:
        sess.open(tags=["ls20_l4_h5c2"])
        frame, meta = _climb_to_l4(sess)
        p_pu, _ = _plan_to_pickup(frame)
        if p_pu:
            frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")
        p, _ = _walk_to(frame, (8, 4))
        frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to84")
        frame, meta, _ = _exec_path(sess, frame, meta, [(0, 1)], log, "warp")
        print("land", ls20.init(frame).cursor)

        for d in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            if ls20.init(frame).cursor != (6, 8):
                p, _ = _walk_to(frame, (6, 8))
                if p is None:
                    log.append({"tag": "no68", "cursor": ls20.init(frame).cursor})
                    print("cannot reach 68")
                    break
                frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to68")
            before = ls20.init(frame).cursor
            bc = counts(frame)
            resp = sess.action(DIR_TO_ACTION[d])
            frame, meta = resp["frame"], resp
            after = ls20.init(frame).cursor
            ac = counts(frame)
            changed = bc != ac
            row = {
                "tag": "pulse", "dir": d, "before": before, "after": after,
                "changed": changed, "before_c": {k: bc[k] for k in bc if k != "ring"},
                "after_c": {k: ac[k] for k in ac if k != "ring"},
                "ring_changed": bc["ring"] != ac["ring"],
                "levels": int(meta.get("levels_completed") or 0),
            }
            log.append(row)
            print(
                f"pulse {d}: {before}->{after} changed={changed} "
                f"c9 {bc['c9']}->{ac['c9']} c14 {bc['c14']}->{ac['c14']} "
                f"stamp9 {bc['stamp_c9']}->{ac['stamp_c9']} gate_u={ac['gate_u']}"
            )
            if int(meta.get("levels_completed") or 0) >= 4:
                log.append({"tag": "RESULT", "verdict": "PASS"})
                break
            if changed:
                print("EFFECT", row["after_c"])
                frame, meta, ok = _try_stamp(sess, frame, meta, log, "eff")
                log.append({"tag": "RESULT", "verdict": "PASS" if ok else "EFFECT_NO_CLEAR"})
                break
        else:
            frame, meta, ok = _try_stamp(sess, frame, meta, log, "final")
            log.append({"tag": "RESULT", "verdict": "PASS" if ok else "FAIL",
                        "final": counts(frame)})
            print("final", ok)

        REPORT.write_text(
            "# L4 H5c2 pulses from (6,8)\n\n" + "\n".join(f"- `{r}`" for r in log) + "\n",
            encoding="utf-8",
        )
        print("wrote", REPORT)
        return 0 if log and "PASS" in str(log[-1]) else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
