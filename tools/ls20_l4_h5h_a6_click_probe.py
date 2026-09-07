"""L4 H5h: ACTION6 clicks on legend glyph / stamp glyph; LEFT at other cells.

Uses one climb; sequence:
  1. optional LEFT at (3,1)/(4,1) — is legend toggle position-specific?
  2. ACTION6 on legend color14 centroid and stamp color9 centroid
  3. if any effect, try stamp enter
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_l4_arming_probe import _climb_to_l4, _plan_to_pickup
from tools.ls20_l4_h5_arming_probe import _exec_path, _try_stamp, _walk_to
from tools.ls20_l4_h5e_diff_probe import _plane_diff, _snap

REPORT = ROOT / "docs" / "ls20_l4_h5h_a6_click_probe.md"


def _centroid(frame, color, y_min=0, y_max=64):
    g = ls20._plane(frame)
    ys, xs = np.where((g == color) & (np.arange(g.shape[0])[:, None] >= y_min)
                      & (np.arange(g.shape[0])[:, None] < y_max))
    if len(xs) == 0:
        return None
    return int(xs.mean()), int(ys.mean())


def _click6(sess, frame, meta, log, x, y, tag):
    before = frame
    bs = _snap(before)
    try:
        resp = sess.action(6, x=x, y=y)
    except Exception as e:
        log.append({"tag": tag, "error": str(e), "xy": (x, y)})
        print(f"  A6 ({x},{y}) ERROR {e}")
        return frame, meta
    frame, meta = resp["frame"], resp
    as_ = _snap(frame)
    diff = _plane_diff(before, frame, limit=60)
    log.append({
        "tag": tag, "xy": (x, y),
        "diff_n": diff["n"], "transitions": diff["transitions"],
        "after": {k: as_[k] for k in ("c0", "c9", "c14", "stamp_c9", "gate_in_walk_u",
                                      "cursor", "ui")},
        "levels": int(meta.get("levels_completed") or 0),
    })
    print(f"  A6 ({x},{y}): n={diff['n']} trans={diff['transitions']} "
          f"gate_u={as_['gate_in_walk_u']} lv={log[-1]['levels']}")
    return frame, meta


def main() -> int:
    sess = OnlineSession(_api_key())
    log = []
    try:
        sess.open(tags=["ls20_l4_h5h"])
        frame, meta = _climb_to_l4(sess)
        log.append({"tag": "l4", "snap": _snap(frame)})
        p_pu, _ = _plan_to_pickup(frame)
        if p_pu:
            frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")

        # LEFT toggles at (3,1)?
        for cell in ((3, 1), (4, 1)):
            p, _ = _walk_to(frame, cell)
            if not p:
                continue
            frame, meta, _ = _exec_path(sess, frame, meta, p, log, f"to_{cell}")
            before = frame
            bs = _snap(before)
            resp = sess.action(DIR_TO_ACTION[(-1, 0)])
            frame, meta = resp["frame"], resp
            diff = _plane_diff(before, frame, limit=40)
            as_ = _snap(frame)
            log.append({"tag": "left_at", "cell": cell, "diff_n": diff["n"],
                        "transitions": diff["transitions"],
                        "c0": as_["c0"], "cursor": as_["cursor"]})
            print(f"LEFT at {cell}: n={diff['n']} trans={diff['transitions']} "
                  f"c0={as_['c0']} cursor={as_['cursor']}")
            # undo if toggled (A5 restores) so next test is clean
            if diff["n"] >= 40 and "5->0" in str(diff["transitions"]):
                frame, meta = _click6.__wrapped__ if False else (frame, meta)
                # restore via A5
                b2 = frame
                resp = sess.action(5)
                frame, meta = resp["frame"], resp
                d2 = _plane_diff(b2, frame, limit=20)
                log.append({"tag": "a5_restore", "diff_n": d2["n"],
                            "transitions": d2["transitions"]})
                print(f"  A5 restore n={d2['n']}")

        # go to (2,1), LEFT to flip legend, then A6 on legend/stamp
        p, _ = _walk_to(frame, (2, 1))
        frame, meta, _ = _exec_path(sess, frame, meta, p, log, "to21")
        before = frame
        resp = sess.action(DIR_TO_ACTION[(-1, 0)])
        frame, meta = resp["frame"], resp
        diff = _plane_diff(before, frame, limit=20)
        log.append({"tag": "left_21", "diff_n": diff["n"],
                    "transitions": diff["transitions"]})
        print(f"LEFT 21: n={diff['n']}")

        # click targets
        targets = []
        leg = _centroid(frame, 14, y_min=50, y_max=64)
        if leg:
            targets.append(("legend14", leg))
        st = _centroid(frame, 9, y_min=4, y_max=12)
        if st:
            targets.append(("stamp9", st))
        # also click legend panel center and stamp block center
        targets.append(("legend_panel", (5, 57)))
        targets.append(("stamp_center", (11, 7)))
        print("targets", targets)

        for tag, (x, y) in targets:
            frame, meta = _click6(sess, frame, meta, log, x, y, f"a6_{tag}")
            if int(meta.get("levels_completed") or 0) >= 4:
                log.append({"tag": "RESULT", "verdict": "PASS_A6"})
                break
        else:
            # try enter gate
            if ls20.init(frame).cursor == (2, 1):
                resp = sess.action(DIR_TO_ACTION[(-1, 0)])
                frame, meta = resp["frame"], resp
                log.append({"tag": "enter", "snap": _snap(frame),
                            "levels": int(meta.get("levels_completed") or 0)})
            frame, meta, ok = _try_stamp(sess, frame, meta, log, "stamp")
            log.append({"tag": "RESULT", "verdict": "PASS" if ok else "FAIL"})

        REPORT.write_text(
            "# L4 H5h A6 / LEFT locus\n\n"
            + "\n".join(f"- `{r}`" for r in log) + "\n",
            encoding="utf-8",
        )
        print("wrote", REPORT, "verdict", log[-1])
        return 0 if "PASS" in str(log[-1]) else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
