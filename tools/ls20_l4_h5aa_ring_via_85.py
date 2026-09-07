"""L4 H5aa: reproduce recording path into ring via (8,6) UP → (8,5) → (6,6).

Then oscillate crush, approach gate (1,1), clear.
"""
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
from tools.ls20_l4_h5_arming_probe import _exec_path, _try_stamp
from tools.ls20_l4_h5e_diff_probe import _plane_diff, _snap
from tools.ls20_seated_clear_full import _step_cell

REPORT = ROOT / "docs" / "ls20_l4_h5aa_ring_via_85.md"


def _geo_path(frame, target, limit=60):
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
        if len(path) >= limit:
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


def _safe(sess, aid):
    for i in range(4):
        try:
            return sess.action(aid)
        except Exception:
            time.sleep(0.5 * (i + 1))
    return sess.action(aid)


def _act(sess, frame, meta, log, aid, tag):
    before = frame
    bg = _gate_walk(before)
    resp = _safe(sess, aid)
    frame, meta = resp["frame"], resp
    ag = _gate_walk(frame)
    dlt = _plane_diff(before, frame, limit=25)
    row = {
        "tag": tag,
        "aid": aid,
        "from": ls20.init(before).cursor,
        "to": ls20.init(frame).cursor,
        "gate_u": ag["gate_in_walk_u"],
        "unlock": ag["unlock_cands"],
        "armed_hint": ag.get("unlock_cands"),
        "stamp9": ag["stamp_c9"],
        "ui": ls20.ui_energy(frame),
        "levels": int(meta.get("levels_completed") or 0),
        "n": dlt["n"],
        "trans": dlt["transitions"],
    }
    # armed-only
    off = ls20.grid_offset(frame)
    wu = ls20.build_walkable(frame, off, armed=False)
    wa = ls20.build_walkable(frame, off, armed=True)
    row["armed_only"] = sorted(wa - wu)
    log.append(row)
    print(
        f"  {tag}: {row['from']} -A{aid}-> {row['to']} "
        f"gate_u={row['gate_u']} armed={row['armed_only']} "
        f"n={row['n']} lv={row['levels']}"
    )
    return frame, meta


def main() -> int:
    sess = OnlineSession(_api_key())
    log = []
    try:
        sess.open(tags=["ls20_l4_h5aa"])
        frame, meta = _climb_to_l4(sess)
        p_pu, _ = _plan_to_pickup(frame)
        if p_pu:
            frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")
        log.append({"tag": "start", "snap": _snap(frame), "gate": _gate_walk(frame)})

        # go to (8,6) — recording path used warp via (6,4) then left to (8,6)
        # Try direct geo path first (may use warps)
        p = _geo_path(frame, (8, 6))
        if p is None:
            # manual: to (6,4) DOWN warp, then navigate
            p = _geo_path(frame, (6, 4))
            frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to_64")
            frame, meta = _act(sess, frame, meta, log, 2, "down64")  # DOWN
            p = _geo_path(frame, (8, 6))
        if p is not None:
            frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to_86")
        log.append({"tag": "at_86", "cursor": ls20.init(frame).cursor,
                    "gate": _gate_walk(frame)})
        print("at", ls20.init(frame).cursor)

        # CRITICAL: UP from (8,6) — recording → (8,5)
        frame, meta = _act(sess, frame, meta, log, 1, "up86")
        cur = ls20.init(frame).cursor
        if cur != (8, 5):
            log.append({"tag": "UP86_FAIL", "got": cur})
            # try all dirs from wherever
            for d, name in zip(DIRS, "UDLR"):
                frame, meta = _act(
                    sess, frame, meta, log, DIR_TO_ACTION[d], f"probe_{name}",
                )
                if ls20.init(frame).cursor in ((8, 5), (6, 6), (6, 5)):
                    break

        # from (8,5) try each action — recording went to (6,6) in one step
        if ls20.init(frame).cursor == (8, 5):
            for d, name in zip(DIRS, "UDLR"):
                before_c = ls20.init(frame).cursor
                frame, meta = _act(
                    sess, frame, meta, log, DIR_TO_ACTION[d], f"from85_{name}",
                )
                got = ls20.init(frame).cursor
                if got in ((6, 6), (6, 5), (7, 6), (5, 6)):
                    print(f"ENTERED RING ZONE via {name}: {before_c}->{got}")
                    break
                # rewalk to 85 if needed
                if got != (8, 5):
                    p = _geo_path(frame, (8, 5))
                    if p is None:
                        break
                    frame, meta, _ = _exec_path(sess, frame, meta, p, log, "re85")

        # if on ring, oscillate like recording
        for i in range(6):
            cur = ls20.init(frame).cursor
            if cur not in ((6, 5), (6, 6)):
                break
            # toggle toward the other
            want = (6, 5) if cur == (6, 6) else (6, 6)
            d = (0, -1) if want[1] < cur[1] else (0, 1)
            frame, meta = _act(
                sess, frame, meta, log, DIR_TO_ACTION[d], f"osc_{i}",
            )
            gw = _gate_walk(frame)
            if gw["gate_in_walk_u"]:
                print("GATE OPENED during osc")
                break

        # after ring work, go to (2,1) and LEFT into gate
        p = _geo_path(frame, (2, 1))
        if p is not None:
            frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to_21")
            frame, meta = _act(sess, frame, meta, log, 3, "left_gate")  # LEFT

        lv = int(meta.get("levels_completed") or 0)
        if lv < 4:
            frame, meta, ok = _try_stamp(sess, frame, meta, log, "stamp")
            lv = int(meta.get("levels_completed") or 0)
        else:
            ok = True

        verdict = "PASS" if lv >= 4 else "NO_CLEAR"
        log.append({"tag": "RESULT", "verdict": verdict, "levels": lv,
                    "final": _snap(frame), "gate": _gate_walk(frame)})
        REPORT.write_text(
            f"# L4 H5aa ring via (8,5)\n\n> {verdict}\n\n"
            + "\n".join(f"- `{r}`" for r in log) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {REPORT} {verdict}")
        return 0 if verdict == "PASS" else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
