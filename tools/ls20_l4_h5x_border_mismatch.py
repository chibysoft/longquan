"""L4 H5x2: border mismatch with geometric nav + aggressive refuel.

_walk_to energy-BFS fails at low ui; use warp-aware geometric BFS instead.
Soft-reset when ui<40 before each station. Stations ordered by ring/bottom first.
"""
from __future__ import annotations

import sys
import time
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
from tools.ls20_l4_h5e_diff_probe import _snap
from tools.ls20_seated_clear_full import _step_cell

REPORT = ROOT / "docs" / "ls20_l4_h5x_border_mismatch.md"

# ring/bottom first, gate last
STATION_ORDER = [
    (6, 3), (6, 4), (7, 4), (7, 5), (8, 4), (8, 5), (8, 6), (8, 7),
    (9, 4), (9, 6), (10, 5), (4, 10), (5, 10), (6, 10), (9, 10), (10, 10),
    (2, 1),
]


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


def _geo_path(frame, target, limit=50):
    st = ls20.init(frame)
    _, wu, warps = _geom(frame)
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


def _pred_a5(cell, warps):
    lands = {warps.get((cell, d)) for d in DIRS}
    lands.discard(None)
    if len(lands) >= 1:
        # prefer full any-action portal
        if len(lands) == 1:
            return next(iter(lands))
    if (cell, (0, 1)) in warps:
        return warps[(cell, (0, 1))]
    return cell


def _safe_action(sess, aid):
    for i in range(3):
        try:
            return sess.action(aid)
        except Exception:
            time.sleep(0.5 * (i + 1))
            try:
                sess.action(1)
            except Exception:
                pass
    return sess.action(aid)


def _ensure_fuel(sess, frame, meta, log, tag):
    ui = ls20.ui_energy(frame)
    if ui >= 40:
        return frame, meta
    # soft reset at top corridor
    p = _geo_path(frame, (9, 1))
    if p is not None:
        frame, meta, _ = _exec_path(sess, frame, meta, p, log, f"{tag}_softnav")
    for i in range(55):
        try:
            resp = _safe_action(sess, 3 if i % 2 == 0 else 4)
        except Exception as e:
            log.append({"tag": "soft_err", "e": str(e)})
            break
        frame, meta = resp["frame"], resp
        if ls20.ui_energy(frame) >= 80:
            log.append({"tag": "soft_ok", "ui": ls20.ui_energy(frame), "i": i})
            break
    p_pu, _ = _plan_to_pickup(frame)
    if p_pu:
        frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, f"{tag}_pu")
    print(f"  fuel -> ui={ls20.ui_energy(frame)}")
    return frame, meta


def main() -> int:
    sess = OnlineSession(_api_key())
    log = []
    finds = []
    try:
        sess.open(tags=["ls20_l4_h5x2"])
        frame, meta = _climb_to_l4(sess)
        for tag in ("fuel1", "fuel2"):
            p_pu, _ = _plan_to_pickup(frame)
            if not p_pu:
                break
            frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, tag)

        reach, unreach = _reachable(frame)
        stations = [c for c in STATION_ORDER if c in reach]
        # also any other border not listed
        for c in sorted(reach):
            x, y = c
            if c in stations:
                continue
            if any((x + dx, y + dy) in unreach for dx, dy in DIRS):
                stations.append(c)

        log.append({
            "tag": "start", "stations": stations, "unreach": sorted(unreach),
            "snap": _snap(frame),
        })
        print(f"stations={stations}")
        print(f"unreach={sorted(unreach)}")

        for si, loc in enumerate(stations):
            if int(meta.get("levels_completed") or 0) >= 4:
                break
            frame, meta = _ensure_fuel(sess, frame, meta, log, f"s{si}")
            p = _geo_path(frame, loc)
            if p is None:
                log.append({"tag": "skip", "loc": loc, "why": "geo_none"})
                print(f"skip {loc} geo_none")
                continue
            frame, meta, cleared = _exec_path(sess, frame, meta, p, log, f"to_{loc}")
            if cleared:
                log.append({"tag": "RESULT", "verdict": "PASS_WALK"})
                break
            got0 = ls20.init(frame).cursor
            if got0 != loc:
                log.append({"tag": "near", "want": loc, "got": got0})
                print(f"near {loc} got {got0}")
                # still probe from got0 if it's the intended portal cell-ish
                loc = got0

            _, wu, warps = _geom(frame)
            probes = [("A5", None)] + [(f"D{d}", d) for d in DIRS]
            for name, d in probes:
                if d is None:
                    pred = _pred_a5(loc, warps)
                    aid = 5
                else:
                    pred = _step_cell(loc, d, wu, warps)
                    if pred is None:
                        pred = loc
                    aid = DIR_TO_ACTION[d]
                try:
                    resp = _safe_action(sess, aid)
                except Exception as e:
                    log.append({"tag": "err", "loc": loc, "act": name, "e": str(e)})
                    break
                frame, meta = resp["frame"], resp
                got = ls20.init(frame).cursor
                ag = _gate_walk(frame)
                lv = int(meta.get("levels_completed") or 0)
                mis = got != pred
                special = got in unreach or ag["gate_in_walk_u"] or lv >= 4
                if mis or special:
                    row = {
                        "tag": "FIND", "loc": loc, "act": name,
                        "pred": pred, "got": got, "mismatch": mis,
                        "unreach": got in unreach,
                        "gate_u": ag["gate_in_walk_u"], "levels": lv,
                    }
                    finds.append(row)
                    log.append(row)
                    print(
                        f"FIND {loc} {name}: pred={pred} got={got} "
                        f"mis={mis} unreach={got in unreach}"
                    )
                    if got in unreach or ag["gate_in_walk_u"] or lv >= 4:
                        if got in unreach:
                            for d2 in DIRS:
                                resp2 = _safe_action(sess, DIR_TO_ACTION[d2])
                                frame, meta = resp2["frame"], resp2
                                g2 = _gate_walk(frame)
                                log.append({
                                    "tag": "unreach_pulse", "d": d2,
                                    "cur": ls20.init(frame).cursor,
                                    "gate_u": g2["gate_in_walk_u"],
                                })
                                print(
                                    f"  pulse {d2}->{ls20.init(frame).cursor} "
                                    f"gate_u={g2['gate_in_walk_u']}"
                                )
                        frame, meta, ok = _try_stamp(
                            sess, frame, meta, log, "after_find",
                        )
                        if ok or int(meta.get("levels_completed") or 0) >= 4:
                            log.append({"tag": "RESULT", "verdict": "PASS"})
                            break
                if got != loc:
                    p2 = _geo_path(frame, loc)
                    if p2 is None or len(p2) > 35:
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
            print(
                f"  [{si+1}/{len(stations)}] done {loc} "
                f"ui={ls20.ui_energy(frame)} finds={len(finds)}"
            )

        if not any(str(r.get("verdict", "")).startswith("PASS") for r in log):
            log.append({
                "tag": "RESULT", "verdict": "NO_BORDER_FIND",
                "finds": len(finds),
            })
        REPORT.write_text(
            f"# L4 H5x border mismatch\n\n> finds={len(finds)}\n\n"
            + "\n".join(
                f"- `{r}`" for r in log
                if r.get("tag") in (
                    "start", "FIND", "RESULT", "soft_ok", "soft_err",
                    "unreach_pulse", "near", "skip",
                )
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
