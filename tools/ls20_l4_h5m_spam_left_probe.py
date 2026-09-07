"""L4 H5m: spam LEFT at (2,1) while flipped — drain energy / soft-reset?"""
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
from tools.ls20_l4_h5e_diff_probe import _snap

REPORT = ROOT / "docs" / "ls20_l4_h5m_spam_left_probe.md"


def main() -> int:
    sess = OnlineSession(_api_key())
    log = []
    try:
        sess.open(tags=["ls20_l4_h5m"])
        frame, meta = _climb_to_l4(sess)
        p, _ = _walk_to(frame, (2, 1))
        frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to21")
        resp = sess.action(DIR_TO_ACTION[(-1, 0)])
        frame, meta = resp["frame"], resp
        s = _snap(frame)
        log.append({"tag": "flipped", "c0": s["c0"], "ui": s["ui"]})
        print(f"flipped c0={s['c0']} ui={s['ui']}")

        for i in range(1, 40):
            before = s
            resp = sess.action(DIR_TO_ACTION[(-1, 0)])
            frame, meta = resp["frame"], resp
            s = _snap(frame)
            lv = int(meta.get("levels_completed") or 0)
            moved = s["cursor"] != before["cursor"]
            gate_u = s["gate_in_walk_u"]
            interesting = (
                i <= 3 or i % 5 == 0 or s["c0"] < 40 or moved or lv >= 4
                or s["ui"] != before["ui"] or gate_u
            )
            if interesting:
                log.append({
                    "tag": "spam", "i": i, "ui": s["ui"], "c0": s["c0"],
                    "cursor": s["cursor"], "gate_u": gate_u, "levels": lv,
                    "moved": moved, "mover": s["mover"],
                })
                print(
                    f"  #{i} ui={s['ui']} c0={s['c0']} gate_u={gate_u} "
                    f"cursor={s['cursor']} lv={lv}"
                )
            if lv >= 4:
                log.append({"tag": "RESULT", "verdict": "PASS"})
                break
            if s["c0"] < 40:
                log.append({"tag": "RESULT", "verdict": "UNFLIPPED", "i": i})
                break
            if s["cursor"] == (10, 1) and i > 5:
                log.append({"tag": "RESULT", "verdict": "SOFT_RESET", "i": i})
                break
        else:
            log.append({"tag": "RESULT", "verdict": "NO_CHANGE", "final": s})

        REPORT.write_text(
            "# L4 H5m spam LEFT\n\n" + "\n".join(f"- `{r}`" for r in log) + "\n",
            encoding="utf-8",
        )
        print("wrote", REPORT, log[-1])
        return 0 if log[-1].get("verdict") == "PASS" else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
