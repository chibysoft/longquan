"""L4 clear via ring approach (8,6) UP (8,5) LEFT (6,5) crush (6,6) then stamp."""
from __future__ import annotations

import sys
import time
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.state import DIRS
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_l4_arming_probe import _climb_to_l4, _gate_walk, _plan_to_pickup
from tools.ls20_l4_h5_arming_probe import _exec_path
from tools.ls20_l4_h5e_diff_probe import _snap
from tools.ls20_seated_clear_full import _step_cell, _plan_to_unlock

REPORT = ROOT / "docs" / "ls20_l4_h5ac_clear.md"


def _geo(frame, target, *, armed=False, limit=60):
    st = ls20.init(frame)
    off = ls20.grid_offset(frame)
    walk = ls20.build_walkable(frame, off, armed=armed)
    wu = ls20.build_walkable(frame, off, armed=False)
    warps = ls20.detect_warps(frame, off, wu)
    if st.cursor == target:
        return []
    q = deque([(st.cursor, [])])
    seen = {st.cursor}
    while q:
        c, path = q.popleft()
        if len(path) >= limit:
            continue
        for d in DIRS:
            n = _step_cell(c, d, walk, warps)
            if n is None or n in seen:
                continue
            np = path + [d]
            if n == target:
                return np
            seen.add(n)
            q.append((n, np))
    return None


def _safe(sess, aid):
    for _ in range(4):
        try:
            return sess.action(aid)
        except Exception:
            time.sleep(0.4)
    return sess.action(aid)


def main() -> int:
    sess = OnlineSession(_api_key())
    log = []
    try:
        sess.open(tags=["ls20_l4_h5ac"])
        frame, meta = _climb_to_l4(sess)
        p_pu, _ = _plan_to_pickup(frame)
        if p_pu:
            frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")

        # unlock via (6,6)
        p, dest, info = _plan_to_unlock(frame, (6, 6))
        log.append({"tag": "unlock_plan", "ok": p is not None, "dest": dest, "info": info})
        print("unlock_plan", p is not None, "len", None if p is None else len(p), info)
        if p is None:
            # fallback explicit
            for tgt in ((8, 6),):
                gp = _geo(frame, tgt)
                if gp is not None:
                    frame, meta, _ = _exec_path(sess, frame, meta, gp, log, f"to_{tgt}")
            for aid, tag in [(1, "UP85"), (3, "LEFT65"), (2, "DOWN66")]:
                resp = _safe(sess, aid)
                frame, meta = resp["frame"], resp
                log.append({"tag": tag, "cur": ls20.init(frame).cursor,
                            "gate": _gate_walk(frame)})
                print(tag, ls20.init(frame).cursor)
        else:
            frame, meta, cleared = _exec_path(sess, frame, meta, p, log, "unlock")
            if cleared:
                log.append({"tag": "RESULT", "verdict": "PASS_UNLOCK"})
                REPORT.write_text(
                    f"# L4 H5ac\n\nPASS\n\n" + "\n".join(f"- `{r}`" for r in log),
                    encoding="utf-8",
                )
                return 0

        # crush oscillate
        for i in range(4):
            cur = ls20.init(frame).cursor
            if cur == (6, 6):
                resp = _safe(sess, 1)
            elif cur == (6, 5):
                resp = _safe(sess, 2)
            else:
                break
            frame, meta = resp["frame"], resp
            log.append({"tag": f"osc{i}", "cur": ls20.init(frame).cursor,
                        "armed_only": sorted(
                            ls20.build_walkable(frame, ls20.grid_offset(frame), armed=True)
                            - ls20.build_walkable(frame, ls20.grid_offset(frame), armed=False)
                        ),
                        "levels": int(meta.get("levels_completed") or 0)})
            print("osc", ls20.init(frame).cursor, log[-1]["armed_only"])

        # armed walk to gate (1,1)
        p2 = _geo(frame, (1, 1), armed=True)
        log.append({"tag": "stamp_path", "ok": p2 is not None,
                    "len": None if p2 is None else len(p2),
                    "at": ls20.init(frame).cursor})
        print("stamp_path", p2 is not None, "len", None if p2 is None else len(p2))
        if p2 is not None:
            frame, meta, cleared = _exec_path(sess, frame, meta, p2, log, "stamp")
            if cleared or int(meta.get("levels_completed") or 0) >= 4:
                log.append({"tag": "RESULT", "verdict": "PASS"})
                REPORT.write_text(
                    "# L4 H5ac\n\n> PASS\n\n" + "\n".join(f"- `{r}`" for r in log) + "\n",
                    encoding="utf-8",
                )
                print("PASS")
                return 0

        # fallback (2,1) LEFT
        p3 = _geo(frame, (2, 1), armed=True) or _geo(frame, (2, 1), armed=False)
        if p3 is not None:
            frame, meta, _ = _exec_path(sess, frame, meta, p3, log, "to21")
            resp = _safe(sess, 3)
            frame, meta = resp["frame"], resp
            log.append({"tag": "LEFT", "cur": ls20.init(frame).cursor,
                        "levels": int(meta.get("levels_completed") or 0),
                        "gate": _gate_walk(frame)})
            print("LEFT", ls20.init(frame).cursor, meta.get("levels_completed"))

        lv = int(meta.get("levels_completed") or 0)
        verdict = "PASS" if lv >= 4 else "NO_CLEAR"
        log.append({"tag": "RESULT", "verdict": verdict, "levels": lv,
                    "snap": _snap(frame)})
        REPORT.write_text(
            f"# L4 H5ac\n\n> {verdict}\n\n" + "\n".join(f"- `{r}`" for r in log) + "\n",
            encoding="utf-8",
        )
        print(verdict)
        return 0 if verdict == "PASS" else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
