"""L4 H5o: soft-reset cycle — drain fuel without pickups; inspect gate after respawn."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.state import DIRS
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import _step_cell
from tools.ls20_l4_arming_probe import _climb_to_l4
from tools.ls20_l4_h5_arming_probe import _exec_path, _try_stamp, _walk_to
from tools.ls20_l4_h5e_diff_probe import _snap

REPORT = ROOT / "docs" / "ls20_l4_h5o_softreset_probe.md"


def _patrol_step(frame):
    """Pick a legal unarmed step that prefers unexplored / DOWN-RIGHT bias."""
    off = ls20.grid_offset(frame)
    wu = ls20.build_walkable(frame, off, armed=False)
    warps = ls20.detect_warps(frame, off, wu)
    cur = ls20.init(frame).cursor
    # prefer order that wanders: R, D, L, U
    for d in ((1, 0), (0, 1), (-1, 0), (0, -1)):
        nxt = _step_cell(cur, d, wu, warps)
        if nxt is not None and nxt != cur:
            return d
    return None


def main() -> int:
    sess = OnlineSession(_api_key())
    log = []
    try:
        sess.open(tags=["ls20_l4_h5o"])
        frame, meta = _climb_to_l4(sess)
        start = _snap(frame)
        log.append({"tag": "l4", "snap": start})
        print(f"start ui={start['ui']} mover={start['mover']} gate_u={start['gate_in_walk_u']}")

        soft = False
        for i in range(1, 50):
            d = _patrol_step(frame)
            if d is None:
                log.append({"tag": "stuck", "i": i, "snap": _snap(frame)})
                print(f"stuck at i={i}")
                break
            before = _snap(frame)
            resp = sess.action(DIR_TO_ACTION[d])
            frame, meta = resp["frame"], resp
            after = _snap(frame)
            lv = int(meta.get("levels_completed") or 0)
            # soft-reset heuristics
            mover_jump = (
                before["mover"] is not None and after["mover"] is not None
                and abs(before["mover"][1] - after["mover"][1]) >= 20
            )
            ui_jump = after["ui"] - before["ui"] >= 20
            layers = getattr(__import__("numpy").asarray(frame), "ndim", 2)
            row = {
                "i": i, "dir": d, "ui": after["ui"], "cursor": after["cursor"],
                "mover": after["mover"], "gate_u": after["gate_in_walk_u"],
                "c11": after["c11"], "levels": lv,
                "mover_jump": mover_jump, "ui_jump": ui_jump,
            }
            if i <= 5 or i % 5 == 0 or mover_jump or ui_jump or after["gate_in_walk_u"] or lv >= 4:
                log.append({"tag": "step", **row})
                print(
                    f"  #{i} ui={after['ui']} cursor={after['cursor']} "
                    f"gate_u={after['gate_in_walk_u']} jump={mover_jump}/{ui_jump}"
                )
            if lv >= 4:
                log.append({"tag": "RESULT", "verdict": "PASS"})
                break
            if mover_jump or (ui_jump and after["cursor"] == (10, 1)):
                soft = True
                log.append({"tag": "soft_reset", **row, "snap": after})
                print(f"SOFT RESET? {row}")
                break
            if after["ui"] <= 8 and i > 10:
                # nearly empty — keep going a bit
                pass
        else:
            log.append({"tag": "no_soft", "final": _snap(frame)})

        # after patrol / soft: try stamp
        snap = _snap(frame)
        log.append({"tag": "pre_stamp", "snap": snap, "soft": soft})
        print(f"pre_stamp gate_u={snap['gate_in_walk_u']} ui={snap['ui']} soft={soft}")
        # bump gate too
        p, _ = _walk_to(frame, (2, 1))
        if p:
            frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to21")
            if ls20.init(frame).cursor == (2, 1):
                resp = sess.action(DIR_TO_ACTION[(-1, 0)])
                frame, meta = resp["frame"], resp
                log.append({"tag": "bump", "snap": _snap(frame)})
        frame, meta, ok = _try_stamp(sess, frame, meta, log, "stamp")
        log.append({"tag": "RESULT", "verdict": "PASS" if ok else "FAIL", "soft": soft})
        REPORT.write_text(
            "# L4 H5o soft-reset\n\n" + "\n".join(f"- `{r}`" for r in log) + "\n",
            encoding="utf-8",
        )
        print("wrote", REPORT, log[-1])
        return 0 if ok else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
