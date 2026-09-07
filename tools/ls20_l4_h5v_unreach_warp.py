"""L4 H5v: hunt unmodeled warps into currently-unreachable walk_u cells.

Offline unreachable set includes bottom strip y=12, island (1,2), ring
approaches (6,5)/(8,5). From every reachable cell, pulse U/D/L/R + A5 and
record any landing in that set (or gate_u flip).
"""
from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.state import DIRS
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_l4_arming_probe import _climb_to_l4, _gate_walk, _plan_to_pickup
from tools.ls20_l4_h5_arming_probe import _exec_path, _walk_to, _try_stamp
from tools.ls20_l4_h5e_diff_probe import _snap
from tools.ls20_seated_clear_full import _step_cell

REPORT = ROOT / "docs" / "ls20_l4_h5v_unreach_warp.md"


def _reach_sets(frame):
    off = ls20.grid_offset(frame)
    wu = ls20.build_walkable(frame, off, armed=False)
    warps = ls20.detect_warps(frame, off, wu)
    st = ls20.init(frame)
    q = deque([st.cursor])
    seen = {st.cursor}
    while q:
        c = q.popleft()
        for d in DIRS:
            n = _step_cell(c, d, wu, warps)
            if n is not None and n not in seen:
                seen.add(n)
                q.append(n)
    return seen, wu - seen, wu, warps


def main() -> int:
    sess = OnlineSession(_api_key())
    log = []
    finds = []
    try:
        sess.open(tags=["ls20_l4_h5v"])
        frame, meta = _climb_to_l4(sess)
        # eat BOTH pickups for fuel budget
        for tag in ("fuel1", "fuel2"):
            p_pu, _ = _plan_to_pickup(frame)
            if not p_pu:
                break
            frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, tag)

        reach, unreach, wu, warps = _reach_sets(frame)
        log.append({
            "tag": "sets", "n_reach": len(reach), "n_unreach": len(unreach),
            "unreach": sorted(unreach), "snap": _snap(frame),
        })
        print(f"reach={len(reach)} unreach={sorted(unreach)}")

        # probe stations: cells with a blocked neighbor or near unreach
        stations = []
        for c in sorted(reach):
            x, y = c
            for dx, dy in DIRS:
                n = (x + dx, y + dy)
                if n in unreach or n not in wu:
                    stations.append(c)
                    break
        # also all vertical-portal / eject origins
        for (cell, d), land in warps.items():
            if cell in reach:
                stations.append(cell)
        stations = sorted(set(stations))
        print(f"stations={len(stations)}")

        actions = (
            [("A5", lambda: sess.action(5))]
            + [(f"D{d}", lambda d=d: sess.action(DIR_TO_ACTION[d])) for d in DIRS]
        )

        for si, loc in enumerate(stations):
            if int(meta.get("levels_completed") or 0) >= 4:
                break
            ui = ls20.ui_energy(frame)
            if ui < 20:
                log.append({"tag": "low_fuel", "ui": ui, "done": si})
                print(f"low fuel ui={ui} after {si} stations")
                break
            p, _ = _walk_to(frame, loc)
            if p is None:
                continue
            if len(p) > 30:
                continue
            frame, meta, cleared = _exec_path(sess, frame, meta, p, log, f"to_{loc}")
            if cleared:
                log.append({"tag": "RESULT", "verdict": "PASS_WALK"})
                break
            if ls20.init(frame).cursor != loc:
                continue
            for name, fn in actions:
                before = ls20.init(frame).cursor
                bg = _gate_walk(frame)
                try:
                    resp = fn()
                except Exception as e:
                    log.append({"tag": "err", "loc": loc, "act": name, "e": str(e)})
                    continue
                frame, meta = resp["frame"], resp
                got = ls20.init(frame).cursor
                ag = _gate_walk(frame)
                lv = int(meta.get("levels_completed") or 0)
                hit = got in unreach or ag["gate_in_walk_u"] or lv >= 4
                if hit:
                    row = {
                        "tag": "FIND", "from": loc, "act": name,
                        "before": before, "got": got,
                        "in_unreach": got in unreach,
                        "gate_u": ag["gate_in_walk_u"], "levels": lv,
                    }
                    finds.append(row)
                    log.append(row)
                    print(f"FIND {loc} {name} -> {got} unreach={got in unreach} "
                          f"gate_u={ag['gate_in_walk_u']}")
                    if ag["gate_in_walk_u"] or lv >= 4:
                        frame, meta, ok = _try_stamp(
                            sess, frame, meta, log, "after_find",
                        )
                        if ok or int(meta.get("levels_completed") or 0) >= 4:
                            log.append({"tag": "RESULT", "verdict": "PASS"})
                            break
                # rewalk to loc if moved
                if got != loc:
                    p2, _ = _walk_to(frame, loc)
                    if p2 is None or len(p2) > 20:
                        break
                    frame, meta, cleared = _exec_path(
                        sess, frame, meta, p2, log, f"re_{loc}",
                    )
                    if cleared:
                        log.append({"tag": "RESULT", "verdict": "PASS"})
                        break
                    if ls20.init(frame).cursor != loc:
                        break
            if any(str(r.get("verdict", "")).startswith("PASS") for r in log):
                break
            if si % 8 == 0:
                print(f"  [{si}/{len(stations)}] at {loc} ui={ls20.ui_energy(frame)}")

        if not any(str(r.get("verdict", "")).startswith("PASS") for r in log):
            log.append({
                "tag": "RESULT", "verdict": "NO_FIND", "finds": len(finds),
            })
        REPORT.write_text(
            f"# L4 H5v unreach warp hunt\n\n> finds={len(finds)}\n\n"
            + "\n".join(
                f"- `{r}`" for r in log
                if r.get("tag") in ("sets", "FIND", "RESULT", "low_fuel")
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"wrote {REPORT} finds={len(finds)}")
        return 0 if finds and any(
            str(r.get("verdict", "")).startswith("PASS") for r in log
        ) else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
