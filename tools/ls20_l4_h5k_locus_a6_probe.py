"""L4 H5k: legend-flip locus sampling + A6 on gate while flipped.

One climb. For each LEFT-blocked playfield cell (reachable sample):
  go there, LEFT, see if c0 jumps (~+80). Restore with A5 if flipped.
Then at (2,1) flip and A6-click gate/stamp pixels.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import _step_cell
from tools.ls20_l4_arming_probe import _climb_to_l4, _plan_to_pickup
from tools.ls20_l4_h5_arming_probe import _exec_path, _try_stamp, _walk_to
from tools.ls20_l4_h5e_diff_probe import _plane_diff, _snap

REPORT = ROOT / "docs" / "ls20_l4_h5k_locus_a6_probe.md"

# Reachable LEFT-blocked samples (exclude known-unreachable pockets)
SAMPLE = [(7, 1), (6, 2), (4, 2), (3, 3), (6, 8), (8, 9), (9, 3), (2, 1)]
GATE_CLICKS = [
    ("gate_tl", 9, 5),
    ("gate_c", 11, 6),
    ("glyph", 11, 7),
    ("glyph9", 12, 6),
    ("stamp_c", 11, 7),
]


def _left_blocked(frame):
    off = ls20.grid_offset(frame)
    wu = ls20.build_walkable(frame, off, armed=False)
    warps = ls20.detect_warps(frame, off, wu)
    out = []
    for c in sorted(wu):
        nxt = _step_cell(c, (-1, 0), wu, warps)
        if nxt is None:
            px, py = ls20.cursor_to_pixel(c, off)
            if py < 54:
                out.append(c)
    return out


def main() -> int:
    sess = OnlineSession(_api_key())
    log = []
    flip_sites = []
    try:
        sess.open(tags=["ls20_l4_h5k"])
        frame, meta = _climb_to_l4(sess)
        log.append({"tag": "l4", "snap": _snap(frame),
                    "left_blocked": _left_blocked(frame)})
        p_pu, _ = _plan_to_pickup(frame)
        if p_pu:
            frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")

        for cell in SAMPLE:
            p, _ = _walk_to(frame, cell)
            if p is None:
                log.append({"tag": "skip", "cell": cell, "reason": "unreachable"})
                print(f"skip {cell} unreachable")
                continue
            frame, meta, _ = _exec_path(sess, frame, meta, p, log, f"to_{cell}")
            cur = ls20.init(frame).cursor
            if cur != cell:
                log.append({"tag": "miss", "want": cell, "got": cur})
                print(f"miss {cell} got {cur}")
                continue
            # ensure unflipped
            s0 = _snap(frame)
            if s0["c0"] > 40:
                resp = sess.action(5)
                frame, meta = resp["frame"], resp
                s0 = _snap(frame)
            before = frame
            c0b = s0["c0"]
            resp = sess.action(DIR_TO_ACTION[(-1, 0)])
            frame, meta = resp["frame"], resp
            s1 = _snap(frame)
            d = _plane_diff(before, frame, limit=15)
            flipped = s1["c0"] - c0b >= 60
            row = {
                "tag": "left_locus", "cell": cell,
                "c0_before": c0b, "c0_after": s1["c0"],
                "flipped": flipped, "cursor": s1["cursor"],
                "diff_n": d["n"], "transitions": d["transitions"],
                "gate_u": s1["gate_in_walk_u"],
                "levels": int(meta.get("levels_completed") or 0),
            }
            log.append(row)
            print(f"LEFT@{cell}: c0 {c0b}->{s1['c0']} flipped={flipped} "
                  f"cursor={s1['cursor']} n={d['n']}")
            if flipped:
                flip_sites.append(cell)
            if int(meta.get("levels_completed") or 0) >= 4:
                log.append({"tag": "RESULT", "verdict": "PASS_LOCUS"})
                break
            # restore if flipped
            if flipped:
                resp = sess.action(5)
                frame, meta = resp["frame"], resp

        # --- A6 while flipped at (2,1) ---
        print(f"flip_sites={flip_sites}")
        log.append({"tag": "flip_sites", "sites": flip_sites})
        p, _ = _walk_to(frame, (2, 1))
        if p:
            frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to21")
        if ls20.init(frame).cursor == (2, 1):
            if _snap(frame)["c0"] < 40:
                resp = sess.action(DIR_TO_ACTION[(-1, 0)])
                frame, meta = resp["frame"], resp
            print(f"flipped at 21 c0={_snap(frame)['c0']}")
            for tag, x, y in GATE_CLICKS:
                if _snap(frame)["c0"] < 40:
                    # reflip
                    if ls20.init(frame).cursor != (2, 1):
                        p, _ = _walk_to(frame, (2, 1))
                        if p:
                            frame, meta, _ = _exec_path(sess, frame, meta, p, log, "re21")
                    if ls20.init(frame).cursor == (2, 1) and _snap(frame)["c0"] < 40:
                        resp = sess.action(DIR_TO_ACTION[(-1, 0)])
                        frame, meta = resp["frame"], resp
                before = frame
                c0b = _snap(frame)["c0"]
                try:
                    resp = sess.action(6, x=x, y=y)
                except Exception as e:
                    log.append({"tag": "a6_err", "xy": (x, y), "error": str(e)})
                    print(f"A6 {tag} ERR {e}")
                    continue
                frame, meta = resp["frame"], resp
                s = _snap(frame)
                d = _plane_diff(before, frame, limit=20)
                row = {
                    "tag": "a6_flipped", "name": tag, "xy": (x, y),
                    "c0_before": c0b, "c0_after": s["c0"],
                    "cursor": s["cursor"], "gate_u": s["gate_in_walk_u"],
                    "diff_n": d["n"], "transitions": d["transitions"],
                    "levels": int(meta.get("levels_completed") or 0),
                }
                log.append(row)
                print(f"A6 {tag}({x},{y}): c0 {c0b}->{s['c0']} n={d['n']} "
                      f"gate_u={s['gate_in_walk_u']} lv={row['levels']}")
                if int(meta.get("levels_completed") or 0) >= 4:
                    log.append({"tag": "RESULT", "verdict": "PASS_A6"})
                    break
            else:
                frame, meta, ok = _try_stamp(sess, frame, meta, log, "stamp")
                log.append({"tag": "RESULT",
                            "verdict": "PASS" if ok else "FAIL",
                            "flip_sites": flip_sites})
        else:
            log.append({"tag": "RESULT", "verdict": "NO_21_FOR_A6",
                        "flip_sites": flip_sites})

        REPORT.write_text(
            f"# L4 H5k locus + A6\n\n> flip_sites: `{flip_sites}`\n\n"
            + "\n".join(f"- `{r}`" for r in log) + "\n",
            encoding="utf-8",
        )
        print("wrote", REPORT)
        return 0 if any("PASS" in str(r.get("verdict", "")) for r in log) else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
