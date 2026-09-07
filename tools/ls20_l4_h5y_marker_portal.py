"""L4 H5y: marker-contact at (4,6) then retest portal (6,4) and gate.

Hypothesis: overlapping fake marker (c0) disables horizontal portal at (6,4),
allowing entry to (6,5) → ring crush → arming; or directly opens gate.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.match import carrying_bbox_from_cursor
from longquan.interactive.state import DIRS
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_l4_arming_probe import _climb_to_l4, _gate_walk, _plan_to_pickup
from tools.ls20_l4_h5_arming_probe import _exec_path, _try_stamp
from tools.ls20_l4_h5e_diff_probe import _plane_diff, _snap
from tools.ls20_seated_clear_full import _step_cell

REPORT = ROOT / "docs" / "ls20_l4_h5y_marker_portal.md"


def _geo_path(frame, target, limit=50):
    from collections import deque
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


def _ov(a, b):
    x0 = max(a[0], b[0]); y0 = max(a[1], b[1])
    x1 = min(a[2], b[2]); y1 = min(a[3], b[3])
    return max(0, x1 - x0 + 1) * max(0, y1 - y0 + 1)


def _safe(sess, aid):
    for i in range(3):
        try:
            return sess.action(aid)
        except Exception:
            time.sleep(0.4 * (i + 1))
    return sess.action(aid)


def main() -> int:
    sess = OnlineSession(_api_key())
    log = []
    try:
        sess.open(tags=["ls20_l4_h5y"])
        frame, meta = _climb_to_l4(sess)
        p_pu, _ = _plan_to_pickup(frame)
        if p_pu:
            frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")

        # --- baseline: (6,4) should warp ---
        p = _geo_path(frame, (6, 4))
        assert p is not None
        frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to_64_base")
        log.append({"tag": "base_64", "snap": _snap(frame), "gate": _gate_walk(frame)})
        before = frame
        resp = _safe(sess, DIR_TO_ACTION[(0, 1)])  # DOWN
        frame, meta = resp["frame"], resp
        got = ls20.init(frame).cursor
        log.append({"tag": "base_down", "got": got, "expect_warp": (10, 4)})
        print(f"baseline (6,4) DOWN -> {got} (expect (10,4))")

        # --- go to marker contact (4,6) ---
        p = _geo_path(frame, (4, 6))
        if p is None:
            log.append({"tag": "FAIL", "why": "no path to (4,6)"})
        else:
            frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to_46")
        st = ls20.init(frame)
        marker = next((g.shape for g in st.goals if g.id == "ls20-marker"), None)
        cov = 0
        if marker is not None:
            cov = _ov(
                carrying_bbox_from_cursor(st.cursor, ls20.grid_offset(frame)),
                marker,
            )
        gw = _gate_walk(frame)
        log.append({
            "tag": "at_46", "cursor": st.cursor, "marker_ov": cov,
            "gate": gw, "snap": _snap(frame),
        })
        print(f"at {st.cursor} marker_ov={cov} gate_u={gw['gate_in_walk_u']}")

        # pulse A5 + UDD at marker
        for name, aids in [
            ("A5", [5]),
            ("UDD", [1, 2, 2]),
            ("A5b", [5]),
        ]:
            before = frame
            bg = _gate_walk(before)
            for aid in aids:
                resp = _safe(sess, aid)
                frame, meta = resp["frame"], resp
            ag = _gate_walk(frame)
            dlt = _plane_diff(before, frame, limit=20)
            log.append({
                "tag": f"pulse_{name}", "cursor": ls20.init(frame).cursor,
                "gate_u": ag["gate_in_walk_u"], "stamp9": ag["stamp_c9"],
                "n": dlt["n"], "trans": dlt["transitions"],
                "levels": int(meta.get("levels_completed") or 0),
            })
            print(
                f"  {name}: gate_u={ag['gate_in_walk_u']} n={dlt['n']} "
                f"trans={dlt['transitions']}"
            )
            if ag["gate_in_walk_u"] or int(meta.get("levels_completed") or 0) >= 4:
                break

        # repath to (4,6) if drifted
        if ls20.init(frame).cursor != (4, 6):
            p = _geo_path(frame, (4, 6))
            if p:
                frame, meta, _ = _exec_path(sess, frame, meta, p, log, "re_46")

        # --- after contact: try enter (6,5) via (6,4) DOWN ---
        p = _geo_path(frame, (6, 4))
        if p is None:
            log.append({"tag": "no_path_64_after"})
            print("no path to (6,4) after marker")
        else:
            frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to_64_after")
            before = frame
            resp = _safe(sess, DIR_TO_ACTION[(0, 1)])
            frame, meta = resp["frame"], resp
            got = ls20.init(frame).cursor
            ag = _gate_walk(frame)
            dlt = _plane_diff(before, frame, limit=15)
            log.append({
                "tag": "after_down64", "got": got,
                "gate": ag, "n": dlt["n"], "trans": dlt["transitions"],
                "levels": int(meta.get("levels_completed") or 0),
            })
            print(f"after-marker (6,4) DOWN -> {got} gate_u={ag['gate_in_walk_u']}")
            if got == (6, 5):
                print("PORTAL DISABLED — entered (6,5)!")
                # try enter ring (6,6)
                for d in DIRS:
                    resp = _safe(sess, DIR_TO_ACTION[d])
                    frame, meta = resp["frame"], resp
                    cur = ls20.init(frame).cursor
                    ag = _gate_walk(frame)
                    log.append({
                        "tag": "from_65", "d": d, "cur": cur, "gate": ag,
                        "levels": int(meta.get("levels_completed") or 0),
                    })
                    print(f"  from65 {d} -> {cur} gate_u={ag['gate_in_walk_u']}")

        # try gate entry from (2,1)
        p = _geo_path(frame, (2, 1))
        if p is not None:
            frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to_21")
            for d in ((-1, 0), (0, -1), (0, 1)):
                before = frame
                resp = _safe(sess, DIR_TO_ACTION[d])
                frame, meta = resp["frame"], resp
                ag = _gate_walk(frame)
                log.append({
                    "tag": "gate_try", "d": d,
                    "cur": ls20.init(frame).cursor, "gate": ag,
                    "levels": int(meta.get("levels_completed") or 0),
                    "diff": _plane_diff(before, frame, limit=8),
                })
                print(
                    f"  gate {d}: cur={ls20.init(frame).cursor} "
                    f"gate_u={ag['gate_in_walk_u']} lv={meta.get('levels_completed')}"
                )
                if int(meta.get("levels_completed") or 0) >= 4:
                    break

        if int(meta.get("levels_completed") or 0) < 4:
            frame, meta, ok = _try_stamp(sess, frame, meta, log, "final")
        else:
            ok = True

        lv = int(meta.get("levels_completed") or 0)
        verdict = "PASS" if lv >= 4 else "NO_ARMING"
        log.append({"tag": "RESULT", "verdict": verdict, "levels": lv})
        REPORT.write_text(
            f"# L4 H5y marker→portal\n\n> {verdict}\n\n"
            + "\n".join(f"- `{r}`" for r in log) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {REPORT} {verdict}")
        return 0 if verdict == "PASS" else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
