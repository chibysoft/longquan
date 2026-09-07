"""L4 H5u: clean neighbor-expansion cover for gate_u / levels.

From each newly reached cell, try U/D/L/R once. Refuel when ui<24.
Navigate back to frontier cells via short BFS on current warps.
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
from tools.ls20_l4_h5_arming_probe import _exec_path, _try_stamp
from tools.ls20_l4_h5e_diff_probe import _plane_diff, _snap
from tools.ls20_seated_clear_full import _step_cell

REPORT = ROOT / "docs" / "ls20_l4_h5u_bfs_cover.md"


def _geom(frame):
    off = ls20.grid_offset(frame)
    wu = ls20.build_walkable(frame, off, armed=False)
    warps = ls20.detect_warps(frame, off, wu)
    return off, wu, warps


def _bfs_dirs(start, goal, wu, warps, limit=40):
    if start == goal:
        return []
    q = deque([(start, [])])
    seen = {start}
    while q:
        c, path = q.popleft()
        if len(path) >= limit:
            continue
        for d in DIRS:
            n = _step_cell(c, d, wu, warps)
            if n is None or n in seen:
                continue
            np = path + [d]
            if n == goal:
                return np
            seen.add(n)
            q.append((n, np))
    return None


def main() -> int:
    sess = OnlineSession(_api_key())
    log = []
    hits = []
    try:
        sess.open(tags=["ls20_l4_h5u"])
        frame, meta = _climb_to_l4(sess)
        p_pu, _ = _plan_to_pickup(frame)
        if p_pu:
            frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")

        start = ls20.init(frame).cursor
        visited = {start}
        # cells whose 4 dirs have not all been tried
        pending = deque([start])
        tried = {}  # cell -> set of dirs already attempted
        log.append({"tag": "start", "snap": _snap(frame)})
        print(f"start {start}")
        steps = 0
        max_steps = 150

        while pending and steps < max_steps:
            if int(meta.get("levels_completed") or 0) >= 4:
                log.append({"tag": "RESULT", "verdict": "PASS"})
                break

            ui = ls20.ui_energy(frame)
            if ui < 24:
                p_pu, _ = _plan_to_pickup(frame)
                if p_pu:
                    frame, meta, cleared = _exec_path(
                        sess, frame, meta, p_pu, log, f"fuel_{steps}",
                    )
                    if cleared:
                        log.append({"tag": "RESULT", "verdict": "PASS_FUEL"})
                        break
                else:
                    log.append({"tag": "no_fuel", "ui": ui, "at": ls20.init(frame).cursor})
                    break

            target = pending[0]
            off, wu, warps = _geom(frame)
            cur = ls20.init(frame).cursor
            if cur != target:
                path = _bfs_dirs(cur, target, wu, warps)
                if path is None:
                    pending.popleft()
                    log.append({"tag": "unreachable_pending", "want": target, "at": cur})
                    continue
                # take only first step toward target
                d0 = path[0]
                resp = sess.action(DIR_TO_ACTION[d0])
                frame, meta = resp["frame"], resp
                steps += 1
                continue

            # at target — try an untried dir
            pending.popleft()
            done = tried.setdefault(target, set())
            off, wu, warps = _geom(frame)
            for d in DIRS:
                if d in done:
                    continue
                done.add(d)
                pred = _step_cell(target, d, wu, warps)
                if pred is None:
                    continue
                before = frame
                bg = _gate_walk(before)
                resp = sess.action(DIR_TO_ACTION[d])
                frame, meta = resp["frame"], resp
                steps += 1
                got = ls20.init(frame).cursor
                ag = _gate_walk(frame)
                dlt = _plane_diff(before, frame, limit=15)
                lv = int(meta.get("levels_completed") or 0)
                row = {
                    "from": target, "dir": d, "pred": pred, "got": got,
                    "gate_u": ag["gate_in_walk_u"], "stamp9": ag["stamp_c9"],
                    "n": dlt["n"], "trans": dlt["transitions"],
                    "levels": lv, "ui": ls20.ui_energy(frame),
                }
                opened = (not bg["gate_in_walk_u"]) and ag["gate_in_walk_u"]
                big = dlt["n"] >= 40 and "5->0" not in str(dlt["transitions"]) \
                    and "0->5" not in str(dlt["transitions"])
                if opened or lv >= 4 or big:
                    hits.append(row)
                    log.append({"tag": "HIT", **row})
                    print(
                        f"HIT {target}{d}->{got} open={opened} lv={lv} "
                        f"n={dlt['n']} trans={dlt['transitions']}"
                    )
                if got not in visited:
                    visited.add(got)
                    pending.append(got)
                    tried.setdefault(got, set())
                # re-queue target if dirs remain
                if len(done) < 4:
                    pending.append(target)
                if opened:
                    frame, meta, ok = _try_stamp(sess, frame, meta, log, "open")
                    if ok or int(meta.get("levels_completed") or 0) >= 4:
                        log.append({"tag": "RESULT", "verdict": "PASS"})
                        pending.clear()
                break  # one probe then re-loop (position may have changed)

            if steps % 20 == 0:
                print(
                    f"  steps={steps} visited={len(visited)} "
                    f"pending={len(pending)} ui={ls20.ui_energy(frame)} "
                    f"at={ls20.init(frame).cursor}"
                )

        if not any(str(r.get("verdict", "")).startswith("PASS") for r in log):
            log.append({
                "tag": "RESULT", "verdict": "NO_OPEN",
                "visited": len(visited), "hits": len(hits), "steps": steps,
                "visited_list": sorted(visited),
            })
        REPORT.write_text(
            f"# L4 H5u BFS cover\n\n"
            f"> visited={len(visited)} hits={len(hits)} steps={steps}\n\n"
            + "\n".join(
                f"- `{r}`" for r in log
                if r.get("tag") in ("start", "HIT", "RESULT", "no_fuel",
                                    "unreachable_pending")
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"wrote {REPORT} visited={len(visited)} hits={len(hits)}")
        return 0 if any(str(r.get("verdict", "")).startswith("PASS") for r in log) else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
