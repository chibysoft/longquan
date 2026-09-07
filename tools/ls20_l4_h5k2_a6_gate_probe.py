"""L4 H5k2: short — confirm flip only at (2,1), A6 gate clicks while flipped."""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_l4_arming_probe import _climb_to_l4, _plan_to_pickup
from tools.ls20_l4_h5_arming_probe import _exec_path, _try_stamp, _walk_to
from tools.ls20_l4_h5e_diff_probe import _plane_diff, _snap

REPORT = ROOT / "docs" / "ls20_l4_h5k2_a6_gate_probe.md"
CLICKS = [(9, 5), (10, 5), (11, 6), (12, 6), (11, 7), (10, 8), (13, 7)]


def _act(sess, *args, **kwargs):
    for attempt in range(3):
        try:
            return sess.action(*args, **kwargs)
        except Exception as e:
            print(f"  retry {attempt}: {e}")
            time.sleep(2 + attempt * 2)
    raise RuntimeError("action failed")


def main() -> int:
    sess = OnlineSession(_api_key())
    log = []
    try:
        sess.open(tags=["ls20_l4_h5k2"])
        frame, meta = _climb_to_l4(sess)
        p_pu, _ = _plan_to_pickup(frame)
        if p_pu:
            frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")

        # control: LEFT at (2,4) near stamp column but not gate-adjacent
        for cell in ((2, 4), (2, 1)):
            p, _ = _walk_to(frame, cell)
            if not p:
                log.append({"tag": "skip", "cell": cell})
                continue
            frame, meta, _ = _exec_path(sess, frame, meta, p, log, f"to_{cell}")
            if ls20.init(frame).cursor != cell:
                continue
            if _snap(frame)["c0"] > 40:
                resp = _act(sess, 5)
                frame, meta = resp["frame"], resp
            b = frame
            c0b = _snap(frame)["c0"]
            resp = _act(sess, DIR_TO_ACTION[(-1, 0)])
            frame, meta = resp["frame"], resp
            s = _snap(frame)
            d = _plane_diff(b, frame, limit=10)
            row = {"tag": "left", "cell": cell, "c0b": c0b, "c0a": s["c0"],
                   "flipped": s["c0"] - c0b >= 60, "n": d["n"],
                   "trans": d["transitions"]}
            log.append(row)
            print(f"LEFT@{cell}: c0 {c0b}->{s['c0']} flipped={row['flipped']}")
            if row["flipped"] and cell != (2, 1):
                resp = _act(sess, 5)
                frame, meta = resp["frame"], resp

        # ensure at (2,1) flipped
        if ls20.init(frame).cursor != (2, 1):
            p, _ = _walk_to(frame, (2, 1))
            frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to21")
        if _snap(frame)["c0"] < 40:
            resp = _act(sess, DIR_TO_ACTION[(-1, 0)])
            frame, meta = resp["frame"], resp
        print(f"ready flip c0={_snap(frame)['c0']} cursor={ls20.init(frame).cursor}")

        for x, y in CLICKS:
            if ls20.init(frame).cursor != (2, 1) or _snap(frame)["c0"] < 40:
                if ls20.init(frame).cursor != (2, 1):
                    p, _ = _walk_to(frame, (2, 1))
                    if p:
                        frame, meta, _ = _exec_path(sess, frame, meta, p, log, "re21")
                if _snap(frame)["c0"] < 40 and ls20.init(frame).cursor == (2, 1):
                    resp = _act(sess, DIR_TO_ACTION[(-1, 0)])
                    frame, meta = resp["frame"], resp
            b = frame
            c0b = _snap(frame)["c0"]
            resp = _act(sess, 6, x=x, y=y)
            frame, meta = resp["frame"], resp
            s = _snap(frame)
            d = _plane_diff(b, frame, limit=15)
            lv = int(meta.get("levels_completed") or 0)
            row = {"tag": "a6", "xy": (x, y), "c0b": c0b, "c0a": s["c0"],
                   "gate_u": s["gate_in_walk_u"], "n": d["n"],
                   "trans": d["transitions"], "levels": lv}
            log.append(row)
            print(f"A6({x},{y}): c0 {c0b}->{s['c0']} n={d['n']} gate_u={s['gate_in_walk_u']}")
            if lv >= 4:
                log.append({"tag": "RESULT", "verdict": "PASS"})
                break
        else:
            frame, meta, ok = _try_stamp(sess, frame, meta, log, "stamp")
            log.append({"tag": "RESULT", "verdict": "PASS" if ok else "FAIL"})

        REPORT.write_text(
            "# L4 H5k2\n\n" + "\n".join(f"- `{r}`" for r in log) + "\n",
            encoding="utf-8",
        )
        print("wrote", REPORT, log[-1])
        return 0 if "PASS" in str(log[-1]) else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
