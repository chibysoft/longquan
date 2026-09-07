"""L4 H5s: A5-on-stamp teleport + armed entry attempt.

H5r: A5 at (8,4) moved cursor to (8,9). Probe whether that is a portal,
whether stamp/gate opens, and whether ritual/entry works afterward.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_l4_arming_probe import _climb_to_l4, _plan_to_pickup, _gate_walk
from tools.ls20_l4_h5_arming_probe import _exec_path, _walk_to, _try_stamp
from tools.ls20_l4_h5e_diff_probe import _plane_diff, _snap

REPORT = ROOT / "docs" / "ls20_l4_h5s_a5_stamp.md"


def main() -> int:
    sess = OnlineSession(_api_key())
    log = []
    try:
        sess.open(tags=["ls20_l4_h5s"])
        frame, meta = _climb_to_l4(sess)
        p_pu, _ = _plan_to_pickup(frame)
        if p_pu:
            frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")

        # get to (8,4) without going through (7,5) eject if possible
        p, _ = _walk_to(frame, (8, 4))
        if p is None:
            log.append({"tag": "FAIL", "why": "no path to (8,4)"})
        else:
            frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to_84")
        log.append({"tag": "at_84", "snap": _snap(frame), "gate": _gate_walk(frame)})
        print("at", ls20.init(frame).cursor, "stamp9", _gate_walk(frame)["stamp_c9"])

        before = frame
        bs = _snap(before)
        resp = sess.action(5)
        frame, meta = resp["frame"], resp
        as_ = _snap(frame)
        dlt = _plane_diff(before, frame, limit=30)
        row = {
            "tag": "A5", "before": bs, "after": as_,
            "diff_n": dlt["n"], "trans": dlt["transitions"],
            "levels": int(meta.get("levels_completed") or 0),
            "gate": _gate_walk(frame),
        }
        log.append(row)
        print(
            f"A5: {bs['cursor']} -> {as_['cursor']} "
            f"gate_u={as_['gate_in_walk_u']} stamp9={as_['stamp_c9']} "
            f"n={dlt['n']} trans={dlt['transitions']}"
        )

        # If teleported to (8,9), try UP repeatedly (maybe climb shaft)
        cur = ls20.init(frame).cursor
        if cur[1] >= 8:
            for i in range(8):
                before = frame
                resp = sess.action(DIR_TO_ACTION[(0, -1)])
                frame, meta = resp["frame"], resp
                got = ls20.init(frame).cursor
                dlt = _plane_diff(before, frame, limit=15)
                log.append({
                    "tag": "UP", "i": i, "cursor": got,
                    "gate_u": _gate_walk(frame)["gate_in_walk_u"],
                    "stamp9": _gate_walk(frame)["stamp_c9"],
                    "n": dlt["n"], "trans": dlt["transitions"],
                    "levels": int(meta.get("levels_completed") or 0),
                })
                print(f"  UP{i}: {got} gate_u={_gate_walk(frame)['gate_in_walk_u']} n={dlt['n']}")
                if got == before and dlt["n"] <= 2:
                    break
                if int(meta.get("levels_completed") or 0) >= 4:
                    break

        # try enter gate from (2,1)
        p, _ = _walk_to(frame, (2, 1))
        if p is not None:
            frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to_21")
            for name, d in [("L", (-1, 0)), ("U", (0, -1)), ("D", (0, 1))]:
                before = frame
                resp = sess.action(DIR_TO_ACTION[d])
                frame, meta = resp["frame"], resp
                gw = _gate_walk(frame)
                log.append({
                    "tag": f"gate_{name}", "cursor": ls20.init(frame).cursor,
                    "gate": gw,
                    "levels": int(meta.get("levels_completed") or 0),
                    "diff": _plane_diff(before, frame, limit=10),
                })
                print(
                    f"  gate {name}: cur={ls20.init(frame).cursor} "
                    f"gate_u={gw['gate_in_walk_u']} lv={meta.get('levels_completed')}"
                )
                if int(meta.get("levels_completed") or 0) >= 4:
                    break

        # last resort: try_stamp
        if int(meta.get("levels_completed") or 0) < 4:
            frame, meta, ok = _try_stamp(sess, frame, meta, log, "stamp")
            log.append({"tag": "try_stamp", "ok": ok})

        lv = int(meta.get("levels_completed") or 0)
        verdict = "PASS" if lv >= 4 else "NO_ARMING"
        log.append({"tag": "RESULT", "verdict": verdict, "levels": lv})
        REPORT.write_text(
            f"# L4 H5s A5-on-stamp\n\n> {verdict}\n\n"
            + "\n".join(f"- `{r}`" for r in log) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {REPORT} {verdict}")
        return 0 if verdict == "PASS" else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
