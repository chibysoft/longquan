"""L4 H5w: find unmodeled transitions (got != warp-aware step prediction).

Cheap: at each reachable cell, try U/D/L/R (+ A5 once). Log mismatches,
landings in offline-unreachable set, or gate_u flips. Soft-reset for fuel
when ui collapses (corridor burn already known to refill).
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

REPORT = ROOT / "docs" / "ls20_l4_h5w_model_mismatch.md"


def _geom(frame):
    off = ls20.grid_offset(frame)
    wu = ls20.build_walkable(frame, off, armed=False)
    warps = ls20.detect_warps(frame, off, wu)
    return off, wu, warps


def _reachable(frame):
    st = ls20.init(frame)
    _, wu, warps = _geom(frame)
    q = deque([st.cursor])
    seen = {st.cursor}
    while q:
        c = q.popleft()
        for d in DIRS:
            n = _step_cell(c, d, wu, warps)
            if n is not None and n not in seen:
                seen.add(n)
                q.append(n)
    return seen, wu - seen


def _pred_a5(cell, wu, warps):
    """A5 on portal cells: horizontal any-dir land, vertical DOWN-only, eject any."""
    # horizontal / eject: any dir key exists
    for d in DIRS:
        if (cell, d) in warps:
            # if all four dirs share same land => any-action portal
            lands = {warps.get((cell, dd)) for dd in DIRS}
            if len(lands) == 1 and None not in lands:
                return next(iter(lands))
            break
    # vertical DOWN-only
    if (cell, (0, 1)) in warps:
        # only count as A5-trigger if also horizontal? Live: A5 at (8,4) DID warp.
        # Treat A5 like DOWN for vertical portals.
        return warps[(cell, (0, 1))]
    return cell


def main() -> int:
    sess = OnlineSession(_api_key())
    log = []
    finds = []
    try:
        sess.open(tags=["ls20_l4_h5w"])
        frame, meta = _climb_to_l4(sess)
        p_pu, _ = _plan_to_pickup(frame)
        if p_pu:
            frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")

        reach, unreach = _reachable(frame)
        # prioritize cells bordering unreachable or with warps
        _, wu, warps = _geom(frame)
        border = []
        for c in reach:
            x, y = c
            if any((x + dx, y + dy) in unreach or (x + dx, y + dy) not in wu
                   for dx, dy in DIRS):
                border.append(c)
            elif any((c, d) in warps for d in DIRS):
                border.append(c)
        cells = sorted(set(border)) or sorted(reach)
        log.append({
            "tag": "start", "n": len(cells), "n_reach": len(reach),
            "unreach": sorted(unreach), "snap": _snap(frame),
        })
        print(f"stations={len(cells)} reach={len(reach)} unreach={len(unreach)}")

        for ci, loc in enumerate(cells):
            if int(meta.get("levels_completed") or 0) >= 4:
                break
            ui = ls20.ui_energy(frame)
            if ui < 18:
                # soft-reset: burn at spawn corridor
                p, _ = _walk_to(frame, (10, 1))
                if p and len(p) < 25:
                    frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to_spawn")
                for _ in range(40):
                    resp = sess.action(3 if _ % 2 == 0 else 4)
                    frame, meta = resp["frame"], resp
                    if ls20.ui_energy(frame) >= 80:
                        log.append({"tag": "soft_reset", "ui": ls20.ui_energy(frame)})
                        print(f"soft-reset ui={ls20.ui_energy(frame)}")
                        break
                # refuel pickup if available
                p_pu, _ = _plan_to_pickup(frame)
                if p_pu:
                    frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "refuel")

            p, _ = _walk_to(frame, loc)
            if p is None or len(p) > 35:
                continue
            frame, meta, cleared = _exec_path(sess, frame, meta, p, log, f"to_{loc}")
            if cleared:
                log.append({"tag": "RESULT", "verdict": "PASS"})
                break
            if ls20.init(frame).cursor != loc:
                continue

            _, wu, warps = _geom(frame)
            probes = [("A5", None, lambda: sess.action(5))]
            for d in DIRS:
                probes.append((f"D{d}", d, lambda d=d: sess.action(DIR_TO_ACTION[d])))

            for name, d, fn in probes:
                if d is None:
                    pred = _pred_a5(loc, wu, warps)
                else:
                    pred = _step_cell(loc, d, wu, warps)
                    if pred is None:
                        pred = loc  # blocked => stay
                bg = _gate_walk(frame)
                resp = fn()
                frame, meta = resp["frame"], resp
                got = ls20.init(frame).cursor
                ag = _gate_walk(frame)
                lv = int(meta.get("levels_completed") or 0)
                mismatch = got != pred
                special = got in unreach or ag["gate_in_walk_u"] or lv >= 4
                if mismatch or special:
                    row = {
                        "tag": "FIND", "loc": loc, "act": name,
                        "pred": pred, "got": got, "mismatch": mismatch,
                        "unreach": got in unreach,
                        "gate_u": ag["gate_in_walk_u"], "levels": lv,
                    }
                    finds.append(row)
                    log.append(row)
                    print(
                        f"FIND {loc} {name}: pred={pred} got={got} "
                        f"mis={mismatch} unreach={got in unreach}"
                    )
                    if ag["gate_in_walk_u"] or lv >= 4:
                        frame, meta, ok = _try_stamp(
                            sess, frame, meta, log, "after",
                        )
                        if ok:
                            log.append({"tag": "RESULT", "verdict": "PASS"})
                            break
                if got != loc:
                    p2, _ = _walk_to(frame, loc)
                    if p2 is None or len(p2) > 25:
                        break
                    frame, meta, cleared = _exec_path(
                        sess, frame, meta, p2, log, f"re_{loc}",
                    )
                    if cleared:
                        log.append({"tag": "RESULT", "verdict": "PASS"})
                        break
                    if ls20.init(frame).cursor != loc:
                        break
                    _, wu, warps = _geom(frame)
            if any(str(r.get("verdict", "")).startswith("PASS") for r in log):
                break
            if ci % 10 == 0:
                print(
                    f"  [{ci}/{len(cells)}] {loc} ui={ls20.ui_energy(frame)} "
                    f"finds={len(finds)}"
                )

        if not any(str(r.get("verdict", "")).startswith("PASS") for r in log):
            log.append({
                "tag": "RESULT", "verdict": "NO_MISMATCH_ARMING",
                "finds": len(finds),
            })
        REPORT.write_text(
            f"# L4 H5w model mismatch\n\n> finds={len(finds)}\n\n"
            + "\n".join(
                f"- `{r}`" for r in log
                if r.get("tag") in ("start", "FIND", "RESULT", "soft_reset")
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"wrote {REPORT} finds={len(finds)}")
        return 0 if any(str(r.get("verdict", "")).startswith("PASS") for r in log) else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
