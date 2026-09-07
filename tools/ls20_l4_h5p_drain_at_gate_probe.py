"""L4 H5p: drain energy AT (2,1) via UP/DOWN no-ops until soft-reset."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_l4_arming_probe import _climb_to_l4
from tools.ls20_l4_h5_arming_probe import _exec_path, _try_stamp, _walk_to
from tools.ls20_l4_h5e_diff_probe import _snap

REPORT = ROOT / "docs" / "ls20_l4_h5p_drain_at_gate_probe.md"


def main() -> int:
    sess = OnlineSession(_api_key())
    log = []
    try:
        sess.open(tags=["ls20_l4_h5p"])
        frame, meta = _climb_to_l4(sess)
        # no pickup — want low reserve
        p, _ = _walk_to(frame, (2, 1))
        frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to21")
        s = _snap(frame)
        log.append({"tag": "at21", "snap": s})
        print(f"at21 ui={s['ui']} c0={s['c0']}")

        for i in range(1, 60):
            if ls20.init(frame).cursor != (2, 1):
                p, _ = _walk_to(frame, (2, 1))
                if p:
                    frame, meta, _ = _exec_path(sess, frame, meta, p, log, "re21")
            before = _snap(frame)
            # alternate UP/DOWN to burn fuel without leaving / flipping
            d = (0, -1) if i % 2 else (0, 1)
            resp = sess.action(DIR_TO_ACTION[d])
            frame, meta = resp["frame"], resp
            after = _snap(frame)
            lv = int(meta.get("levels_completed") or 0)
            ui_jump = after["ui"] - before["ui"] >= 20
            if i <= 3 or i % 5 == 0 or ui_jump or after["gate_in_walk_u"] or lv >= 4:
                log.append({
                    "tag": "burn", "i": i, "dir": d,
                    "ui": after["ui"], "c0": after["c0"],
                    "cursor": after["cursor"],
                    "gate_u": after["gate_in_walk_u"], "levels": lv,
                    "ui_jump": ui_jump,
                })
                print(f"  #{i} ui={after['ui']} c0={after['c0']} "
                      f"gate_u={after['gate_in_walk_u']} jump={ui_jump}")
            if lv >= 4:
                log.append({"tag": "RESULT", "verdict": "PASS"})
                break
            if ui_jump:
                log.append({"tag": "soft", "snap": after})
                print("SOFT at gate area", after)
                # try enter immediately
                if after["cursor"] == (2, 1) or True:
                    p, _ = _walk_to(frame, (2, 1))
                    if p:
                        frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to21b")
                    if ls20.init(frame).cursor == (2, 1):
                        resp = sess.action(DIR_TO_ACTION[(-1, 0)])
                        frame, meta = resp["frame"], resp
                        log.append({"tag": "post_soft_bump", "snap": _snap(frame)})
                frame, meta, ok = _try_stamp(sess, frame, meta, log, "stamp")
                log.append({"tag": "RESULT", "verdict": "PASS" if ok else "FAIL_AFTER_SOFT"})
                break
        else:
            frame, meta, ok = _try_stamp(sess, frame, meta, log, "stamp")
            log.append({"tag": "RESULT", "verdict": "PASS" if ok else "NO_SOFT"})

        REPORT.write_text(
            "# L4 H5p drain at gate\n\n" + "\n".join(f"- `{r}`" for r in log) + "\n",
            encoding="utf-8",
        )
        print("wrote", REPORT, log[-1])
        return 0 if "PASS" in str(log[-1].get("verdict")) else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
