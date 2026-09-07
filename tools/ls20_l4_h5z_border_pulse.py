"""L4 H5z: resilient border pulse (land+apply warps) — one action set per station.

No rewalk-after-pulse (avoids API thrash). Soft-reset between stations if ui<36.
Logs pred!=got and unreach landings.
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

REPORT = ROOT / "docs" / "ls20_l4_h5z_border_pulse.md"

STATIONS = [
    (7, 5), (7, 4), (8, 4), (8, 6), (8, 7), (6, 4), (6, 3),
    (9, 4), (9, 6), (10, 5), (10, 10), (6, 10), (5, 10), (4, 10),
    (9, 10), (2, 1), (4, 6), (3, 7), (1, 7),
]


def _geom(frame):
    off = ls20.grid_offset(frame)
    wu = ls20.build_walkable(frame, off, armed=False)
    warps = ls20.detect_warps(frame, off, wu)
    return wu, warps


def _unreach(frame):
    st = ls20.init(frame)
    wu, warps = _geom(frame)
    q = deque([st.cursor])
    seen = {st.cursor}
    while q:
        c = q.popleft()
        for d in DIRS:
            n = _step_cell(c, d, wu, warps)
            if n is not None and n not in seen:
                seen.add(n)
                q.append(n)
    return wu - seen


def _geo_path(frame, target, limit=55):
    st = ls20.init(frame)
    wu, warps = _geom(frame)
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
    last = None
    for i in range(4):
        try:
            return sess.action(aid)
        except Exception as e:
            last = e
            time.sleep(0.6 * (i + 1))
            try:
                sess.action(1)
            except Exception:
                pass
    raise last


def _refuel(sess, frame, meta, log):
    if ls20.ui_energy(frame) >= 36:
        return frame, meta
    p = _geo_path(frame, (9, 1))
    if p is not None:
        try:
            frame, meta, _ = _exec_path(sess, frame, meta, p, log, "softnav")
        except Exception as e:
            log.append({"tag": "softnav_err", "e": str(e)})
            return frame, meta
    for i in range(45):
        try:
            resp = _safe(sess, 3 if i % 2 == 0 else 4)
        except Exception as e:
            log.append({"tag": "soft_err", "e": str(e)})
            break
        frame, meta = resp["frame"], resp
        if ls20.ui_energy(frame) >= 80:
            log.append({"tag": "soft_ok", "ui": 80, "i": i})
            break
    p_pu, _ = _plan_to_pickup(frame)
    if p_pu:
        try:
            frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "pu")
        except Exception as e:
            log.append({"tag": "pu_err", "e": str(e)})
    print(f"  refuel ui={ls20.ui_energy(frame)}")
    return frame, meta


def main() -> int:
    sess = OnlineSession(_api_key())
    log = []
    finds = []
    try:
        sess.open(tags=["ls20_l4_h5z"])
        frame, meta = _climb_to_l4(sess)
        for t in ("f1", "f2"):
            p_pu, _ = _plan_to_pickup(frame)
            if not p_pu:
                break
            frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, t)

        unreach = _unreach(frame)
        log.append({
            "tag": "start", "unreach": sorted(unreach), "snap": _snap(frame),
        })
        print("unreach", sorted(unreach))

        for si, loc in enumerate(STATIONS):
            if int(meta.get("levels_completed") or 0) >= 4:
                break
            try:
                frame, meta = _refuel(sess, frame, meta, log)
                p = _geo_path(frame, loc)
                if p is None:
                    log.append({"tag": "skip", "loc": loc})
                    print(f"skip {loc}")
                    continue
                frame, meta, cleared = _exec_path(
                    sess, frame, meta, p, log, f"to_{loc}",
                )
                if cleared:
                    log.append({"tag": "RESULT", "verdict": "PASS"})
                    break
                cur = ls20.init(frame).cursor
                if cur != loc:
                    log.append({"tag": "near", "want": loc, "got": cur})
                    loc = cur
                wu, warps = _geom(frame)
                # one-shot probes; do NOT rewalk — accept drift to next station
                for name, d in [("A5", None)] + [(f"D{d}", d) for d in DIRS]:
                    if d is None:
                        lands = {warps.get((loc, dd)) for dd in DIRS}
                        lands.discard(None)
                        pred = next(iter(lands)) if len(lands) == 1 else (
                            warps.get((loc, (0, 1)), loc)
                        )
                        aid = 5
                    else:
                        pred = _step_cell(loc, d, wu, warps)
                        if pred is None:
                            pred = loc
                        aid = DIR_TO_ACTION[d]
                    before_u = _gate_walk(frame)["gate_in_walk_u"]
                    resp = _safe(sess, aid)
                    frame, meta = resp["frame"], resp
                    got = ls20.init(frame).cursor
                    ag = _gate_walk(frame)
                    lv = int(meta.get("levels_completed") or 0)
                    mis = got != pred
                    if mis or got in unreach or ag["gate_in_walk_u"] or lv >= 4:
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
                        if ag["gate_in_walk_u"] or lv >= 4 or got in unreach:
                            frame, meta, ok = _try_stamp(
                                sess, frame, meta, log, "hit",
                            )
                            if ok or int(meta.get("levels_completed") or 0) >= 4:
                                log.append({"tag": "RESULT", "verdict": "PASS"})
                                break
                    # update loc for subsequent dirs from new position
                    if got != loc:
                        loc = got
                        wu, warps = _geom(frame)
                        break  # next station after one move
                print(
                    f"  [{si+1}/{len(STATIONS)}] ui={ls20.ui_energy(frame)} "
                    f"at={ls20.init(frame).cursor} finds={len(finds)}"
                )
            except Exception as e:
                log.append({"tag": "station_err", "loc": loc, "e": str(e)})
                print(f"station_err {loc}: {e}")
                break

        if not any(str(r.get("verdict", "")).startswith("PASS") for r in log):
            log.append({
                "tag": "RESULT", "verdict": "NO_FIND", "finds": len(finds),
            })
        REPORT.write_text(
            f"# L4 H5z border pulse\n\n> finds={len(finds)}\n\n"
            + "\n".join(
                f"- `{r}`" for r in log
                if r.get("tag") in (
                    "start", "FIND", "RESULT", "skip", "near",
                    "soft_ok", "station_err",
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
