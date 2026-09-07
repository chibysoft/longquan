"""L4 H5j: while legend-flipped at (2,1), pulse UP/DOWN/A5/A6-stamp — what preserves flip?"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_l4_arming_probe import _climb_to_l4, _plan_to_pickup
from tools.ls20_l4_h5_arming_probe import _exec_path, _walk_to
from tools.ls20_l4_h5e_diff_probe import _plane_diff, _snap

REPORT = ROOT / "docs" / "ls20_l4_h5j_flip_preserve_probe.md"


def main() -> int:
    sess = OnlineSession(_api_key())
    log = []
    try:
        sess.open(tags=["ls20_l4_h5j"])
        frame, meta = _climb_to_l4(sess)
        p_pu, _ = _plan_to_pickup(frame)
        if p_pu:
            frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")
        p, _ = _walk_to(frame, (2, 1))
        frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to21")

        def flip():
            nonlocal frame, meta
            # ensure unflipped then flip
            s = _snap(frame)
            if s["c0"] > 40:
                # already flipped
                return
            b = frame
            resp = sess.action(DIR_TO_ACTION[(-1, 0)])
            frame, meta = resp["frame"], resp
            d = _plane_diff(b, frame, limit=10)
            log.append({"tag": "flip", "n": d["n"], "c0": _snap(frame)["c0"]})
            print(f"flip c0={_snap(frame)['c0']}")

        def ensure_21():
            nonlocal frame, meta
            if ls20.init(frame).cursor == (2, 1):
                return True
            p, _ = _walk_to(frame, (2, 1))
            if not p:
                return False
            frame, meta, _ = _exec_path(sess, frame, meta, p, log, "re21")
            return ls20.init(frame).cursor == (2, 1)

        # pulses that should NOT leave via RIGHT
        tests = [
            ("UP", lambda: sess.action(DIR_TO_ACTION[(0, -1)])),
            ("DOWN", lambda: sess.action(DIR_TO_ACTION[(0, 1)])),
            ("LEFT", lambda: sess.action(DIR_TO_ACTION[(-1, 0)])),
            ("A5", lambda: sess.action(5)),
            ("A6stamp", lambda: sess.action(6, x=11, y=7)),
            ("A6leg", lambda: sess.action(6, x=5, y=57)),
        ]
        for name, fn in tests:
            if not ensure_21():
                log.append({"tag": "lost21", "name": name})
                break
            # restore if needed then flip fresh
            s = _snap(frame)
            if s["c0"] > 40:
                # reset flip with A5 if needed for clean test — except when testing A5
                pass
            else:
                flip()
            if _snap(frame)["c0"] < 40:
                flip()
            c0_before = _snap(frame)["c0"]
            b = frame
            resp = fn()
            frame, meta = resp["frame"], resp
            d = _plane_diff(b, frame, limit=30)
            s = _snap(frame)
            row = {
                "tag": "pulse", "name": name,
                "c0_before": c0_before, "c0_after": s["c0"],
                "cursor": s["cursor"], "gate_u": s["gate_in_walk_u"],
                "diff_n": d["n"], "transitions": d["transitions"],
                "levels": int(meta.get("levels_completed") or 0),
            }
            log.append(row)
            print(f"{name}: c0 {c0_before}->{s['c0']} cursor={s['cursor']} "
                  f"n={d['n']} trans={d['transitions']} gate_u={s['gate_in_walk_u']}")
            if int(meta.get("levels_completed") or 0) >= 4:
                log.append({"tag": "RESULT", "verdict": "PASS"})
                break
            # if unflipped and not at 21, repath+reflip next iter
            if s["c0"] < 40 and name != "A6leg":
                # try reflip at 21 for next
                pass

        REPORT.write_text(
            "# L4 H5j flip preserve\n\n" + "\n".join(f"- `{r}`" for r in log) + "\n",
            encoding="utf-8",
        )
        print("wrote", REPORT)
        return 0
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
