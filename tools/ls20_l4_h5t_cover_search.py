"""L4 H5t: cover every reachable walk_u cell; watch gate_u / levels.

One climb. Refuel at pickups when ui low. After first visit to each cell,
log if gate_in_walk_u flips or levels>=4. If gate opens, try enter+stamp.
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

REPORT = ROOT / "docs" / "ls20_l4_h5t_cover_search.md"


def _reachable(frame):
    st = ls20.init(frame)
    off = ls20.grid_offset(frame)
    wu = ls20.build_walkable(frame, off, armed=False)
    warps = ls20.detect_warps(frame, off, wu)
    q = deque([st.cursor])
    seen = {st.cursor}
    while q:
        c = q.popleft()
        for d in DIRS:
            n = _step_cell(c, d, wu, warps)
            if n is not None and n not in seen:
                seen.add(n)
                q.append(n)
    return sorted(seen), wu, warps, off


def main() -> int:
    sess = OnlineSession(_api_key())
    log = []
    hits = []
    try:
        sess.open(tags=["ls20_l4_h5t"])
        frame, meta = _climb_to_l4(sess)
        p_pu, _ = _plan_to_pickup(frame)
        if p_pu:
            frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")
        targets, _, _, _ = _reachable(frame)
        log.append({
            "tag": "start", "n_targets": len(targets),
            "snap": _snap(frame), "targets_head": targets[:12],
        })
        print(f"targets={len(targets)}")

        visited = set()
        # prioritize unusual cells: near ring, gate, pickups, warps
        priority = [
            (2, 1), (3, 1), (4, 1), (1, 7), (3, 7), (3, 9),
            (4, 6), (4, 7), (6, 4), (8, 4), (8, 6), (8, 9),
            (6, 8), (6, 9), (6, 10), (10, 4), (10, 6), (10, 12),
            (11, 12), (7, 5), (5, 3), (2, 9), (2, 12),
        ]
        order = [c for c in priority if c in set(targets)]
        order += [c for c in targets if c not in set(order)]

        for ti, locus in enumerate(order):
            if locus in visited:
                continue
            ui = ls20.ui_energy(frame)
            if ui < 28:
                p_pu, _ = _plan_to_pickup(frame)
                if p_pu:
                    frame, meta, cleared = _exec_path(
                        sess, frame, meta, p_pu, log, f"refuel_{ti}",
                    )
                    if cleared:
                        log.append({"tag": "RESULT", "verdict": "PASS_REFUEL"})
                        break
            p, _ = _walk_to(frame, locus)
            if p is None:
                log.append({"tag": "skip", "locus": locus})
                continue
            # cap path length to save API
            if len(p) > 25:
                log.append({"tag": "far", "locus": locus, "len": len(p)})
                continue
            before_g = _gate_walk(frame)
            frame, meta, cleared = _exec_path(
                sess, frame, meta, p, log, f"v{ti}_{locus}",
            )
            if cleared:
                log.append({"tag": "RESULT", "verdict": "PASS_WALK", "at": locus})
                break
            got = ls20.init(frame).cursor
            visited.add(got)
            after_g = _gate_walk(frame)
            opened = (not before_g["gate_in_walk_u"]) and after_g["gate_in_walk_u"]
            lv = int(meta.get("levels_completed") or 0)
            if opened or lv >= 4 or after_g["stamp_c9"] == 0:
                hits.append({
                    "tag": "HIT", "want": locus, "got": got,
                    "before": before_g, "after": after_g, "levels": lv,
                })
                log.append(hits[-1])
                print(f"HIT at {got} gate_u={after_g['gate_in_walk_u']} lv={lv}")
                if opened or lv >= 4:
                    frame, meta, ok = _try_stamp(sess, frame, meta, log, "after_open")
                    if ok or int(meta.get("levels_completed") or 0) >= 4:
                        log.append({"tag": "RESULT", "verdict": "PASS"})
                        break
            if ti % 5 == 0:
                print(
                    f"  [{ti}/{len(order)}] at {got} visited={len(visited)} "
                    f"ui={ls20.ui_energy(frame)} gate_u={after_g['gate_in_walk_u']}"
                )
            if lv >= 4:
                break

        if not any(str(r.get("verdict", "")).startswith("PASS") for r in log):
            log.append({
                "tag": "RESULT", "verdict": "NO_GATE_OPEN",
                "visited": len(visited), "hits": len(hits),
            })
        REPORT.write_text(
            f"# L4 H5t cover search\n\n> visited={len(visited)} hits={len(hits)}\n\n"
            + "\n".join(f"- `{r}`" for r in log if r.get("tag") in (
                "start", "HIT", "RESULT", "skip", "far",
            ) or r.get("tag", "").startswith("RESULT"))
            + "\n\n## full log size\n\n"
            + f"- events={len(log)}\n",
            encoding="utf-8",
        )
        # also dump full
        (ROOT / "docs" / "ls20_l4_h5t_cover_search_full.md").write_text(
            "\n".join(f"- `{r}`" for r in log) + "\n", encoding="utf-8",
        )
        print(f"wrote {REPORT} visited={len(visited)} hits={len(hits)}")
        return 0 if any(str(r.get("verdict", "")).startswith("PASS") for r in log) else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
