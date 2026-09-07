"""L4 H5ab: exact cursor path from recording (manual dirs).

Recording i97..110:
  (9,1)-(8,1)-(7,1)-(7,2)-(7,3)-(7,4)-(6,4)-DOWN_warp-(10,5)
  -(10,6)-(9,6)-(8,6)-UP-(8,5)-?-(6,6)
Then oscillate (6,6)/(6,5), leave, stamp (1,1).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_l4_arming_probe import _climb_to_l4, _gate_walk, _plan_to_pickup
from tools.ls20_l4_h5_arming_probe import _exec_path
from tools.ls20_l4_h5e_diff_probe import _plane_diff, _snap

REPORT = ROOT / "docs" / "ls20_l4_h5ab_rec_path.md"

# Absolute action ids: 1=U 2=D 3=L 4=R
# From cursors: deltas mapped carefully
PATH_TO_86 = [
    # (9,1) start after fuel may differ — we navigate relative from climb+fuel
]
# Explicit from known recording after being at (9,1):
# L L D D D L  then D(warp) D L L
SEQ_FROM_91 = [
    (3, "L_to_81"),
    (3, "L_to_71"),
    (2, "D_to_72"),
    (2, "D_to_73"),
    (2, "D_to_74"),
    (3, "L_to_64"),
    (2, "D_warp_105"),
    (2, "D_to_106"),
    (3, "L_to_96"),
    (3, "L_to_86"),
    (1, "U_to_85"),
]


def _safe(sess, aid):
    for i in range(4):
        try:
            return sess.action(aid)
        except Exception:
            time.sleep(0.5 * (i + 1))
    return sess.action(aid)


def _go(sess, frame, meta, log, aid, tag):
    before = frame
    resp = _safe(sess, aid)
    frame, meta = resp["frame"], resp
    off = ls20.grid_offset(frame)
    wu = ls20.build_walkable(frame, off, armed=False)
    wa = ls20.build_walkable(frame, off, armed=True)
    gw = _gate_walk(frame)
    dlt = _plane_diff(before, frame, limit=20)
    row = {
        "tag": tag,
        "aid": aid,
        "from": ls20.init(before).cursor,
        "to": ls20.init(frame).cursor,
        "gate_u": gw["gate_in_walk_u"],
        "armed_only": sorted(wa - wu),
        "ui": ls20.ui_energy(frame),
        "levels": int(meta.get("levels_completed") or 0),
        "n": dlt["n"],
        "trans": dlt["transitions"],
    }
    log.append(row)
    print(
        f"  {tag}: {row['from']}-> {row['to']} gate_u={row['gate_u']} "
        f"armed={row['armed_only']} n={row['n']}"
    )
    return frame, meta


def main() -> int:
    sess = OnlineSession(_api_key())
    log = []
    try:
        sess.open(tags=["ls20_l4_h5ab"])
        frame, meta = _climb_to_l4(sess)
        # match recording start-ish at top; eat one pickup
        p_pu, _ = _plan_to_pickup(frame)
        if p_pu:
            frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")

        # move to (9,1) if not there
        cur = ls20.init(frame).cursor
        log.append({"tag": "start", "cursor": cur, "snap": _snap(frame)})
        print("start", cur)
        # crude: if at top row, walk to (9,1)
        from collections import deque
        from longquan.interactive.state import DIRS
        from tools.ls20_seated_clear_full import _step_cell

        def geo(frame, target):
            st = ls20.init(frame)
            off = ls20.grid_offset(frame)
            wu = ls20.build_walkable(frame, off, armed=False)
            warps = ls20.detect_warps(frame, off, wu)
            if st.cursor == target:
                return []
            q = deque([(st.cursor, [])])
            seen = {st.cursor}
            while q:
                c, path = q.popleft()
                if len(path) > 40:
                    continue
                for d in DIRS:
                    n = _step_cell(c, d, wu, warps)
                    if n is None or n in seen:
                        continue
                    np = path + [d]
                    if n == target:
                        return np
                    seen.add(n)
                    q.append((n, np))
            return None

        p = geo(frame, (9, 1))
        if p is not None:
            frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to_91")
        print("at", ls20.init(frame).cursor)

        for aid, tag in SEQ_FROM_91:
            frame, meta = _go(sess, frame, meta, log, aid, tag)
            if int(meta.get("levels_completed") or 0) >= 4:
                break
            if ls20.init(frame).cursor in ((6, 6), (6, 5)):
                print("HIT RING early")
                break

        # if at (8,5), try each dir to enter ring
        if ls20.init(frame).cursor == (8, 5):
            for aid, name in [(3, "L"), (1, "U"), (2, "D"), (4, "R"), (5, "A5")]:
                frame, meta = _go(sess, frame, meta, log, aid, f"85_{name}")
                if ls20.init(frame).cursor in ((6, 6), (6, 5)):
                    print("ENTERED", ls20.init(frame).cursor)
                    break
                # return to 85 if possible
                if ls20.init(frame).cursor != (8, 5):
                    # try reverse briefly
                    break

        # oscillate if on ring
        for i in range(8):
            cur = ls20.init(frame).cursor
            if cur == (6, 6):
                frame, meta = _go(sess, frame, meta, log, 1, f"oscU_{i}")  # UP to 65?
            elif cur == (6, 5):
                frame, meta = _go(sess, frame, meta, log, 2, f"oscD_{i}")
            else:
                break
            if _gate_walk(frame)["gate_in_walk_u"]:
                print("GATE OPEN")
                break
            if int(meta.get("levels_completed") or 0) >= 4:
                break

        # approach gate
        if int(meta.get("levels_completed") or 0) < 4:
            p = geo(frame, (2, 1))
            if p is not None:
                frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to_21")
                frame, meta = _go(sess, frame, meta, log, 3, "LEFT_gate")

        lv = int(meta.get("levels_completed") or 0)
        verdict = "PASS" if lv >= 4 else "NO_CLEAR"
        log.append({"tag": "RESULT", "verdict": verdict, "levels": lv,
                    "final_cursor": ls20.init(frame).cursor,
                    "gate": _gate_walk(frame),
                    "snap": _snap(frame)})
        REPORT.write_text(
            f"# L4 H5ab recording path\n\n> {verdict}\n\n"
            + "\n".join(f"- `{r}`" for r in log) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {REPORT} {verdict} at={ls20.init(frame).cursor}")
        return 0 if verdict == "PASS" else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
