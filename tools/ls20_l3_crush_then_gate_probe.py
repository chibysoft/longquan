"""Probe E10: crush ring (legend flip) -> does the stamp gate (10,10) open?

WHY
  Two armed-only cells exist in L3: (5,9) [ring] and (10,10) [stamp gate], both
  because their 5x2 footprint contains color9. But E7 PROVED (5,9) is enterable
  (the ring gets crushed), while E6/E9 proved (10,10) is HARD-blocked even after
  the C2 ritual (contact + UP/DOWN/DOWN). So color9 hardness is context-
  dependent: the ring's standalone color9 is soft, the stamp glyph C's color9
  (embedded in a color5 solid) is hard.

  The one state-changing interaction we have NOT tried against the gate is the
  ring crush itself: it flips the 24px color12 legend to color9 (E7 diff) and
  dissolves the ring. This probe tests whether that crush is the "arming" step
  that lets the mover enter (10,10) — WITHOUT re-doing the fuel-hungry marker
  contact. Fuel is feasible (crush 16 + gate 15 steps, under the 2-pickup
  budget).

FLOW
  1. reach_l3
  2. walk to (4,9), RIGHT into (5,9) -> crush ring, legend flips
  3. save dissolved frame; plan fuel-aware path to (10,9) [gate approach]
  4. execute; explicit DOWN into (10,10), record entry + levels

USAGE
  python tools/ls20_l3_crush_then_gate_probe.py --plan-only
  python tools/ls20_l3_crush_then_gate_probe.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import MAX_FUEL, _energy_bfs
from tools.ls20_l3_armed_controller import reach_l3

REPORT = ROOT / "docs" / "ls20_l3_crush_then_gate_probe.md"
FIXTURE_OUT = ROOT / "tests" / "fixtures" / "ls20_l3_frame_dissolved.json"

POINT = (4, 9)       # ring-left adjacent (walkable unarmed)
RING = (5, 9)        # enter (crush) the ring
GATE_ABOVE = (10, 9) # stamp gate approach cell


def _plan_path(frame, target, walk=None):
    state = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    if walk is None:
        walk = ls20.build_walkable(frame, offset, armed=False)
    warps = ls20.detect_warps(frame, offset, walk)
    pickups = ls20.energy_pickups(frame)
    ui = ls20.ui_energy(frame)
    fuel0 = MAX_FUEL if ui >= 64 or ui <= 0 else max(1, min(MAX_FUEL, (ui - 8) // 4))
    p, cell, fuel, pmask = _energy_bfs(
        state.cursor, fuel0, 0, walk, pickups, offset,
        lambda c, _f, _p: c == target, warps,
    )
    return p, cell, fuel, pmask


def _ov(a, b):
    ox0, oy0 = max(a[0], b[0]), max(a[1], b[1])
    ox1, oy1 = min(a[2], b[2]), min(a[3], b[3])
    return (ox1 - ox0 + 1) * (oy1 - oy0 + 1) if ox0 <= ox1 and oy0 <= oy1 else 0


def _snap(frame, tag, levels):
    g = ls20._plane(frame)
    arr = np.asarray(frame)
    return {
        "tag": tag, "levels": levels, "mover": ls20.locate_mover(frame),
        "layers": arr.shape[0] if arr.ndim == 3 else 1,
        "c9": int((g == 9).sum()), "c12": int((g == 12).sum()),
        "c11": int((g == 11).sum()),
    }


def plan_only() -> int:
    data = json.loads((ROOT / "tests" / "fixtures" / "ls20_l3_frame_live.json")
                      .read_text(encoding="utf-8"))
    frame = data["frame"]
    p, _, _, _ = _plan_path(frame, POINT)
    print(f"POINT={POINT} RING={RING} GATE_ABOVE={GATE_ABOVE}")
    print(f"path to (4,9) len={None if p is None else len(p)}")
    if p:
        print(f"  actions={[DIR_TO_ACTION[a] for a in p]}")
    return 0


def run_online() -> int:
    key = _api_key()
    if not key:
        raise RuntimeError("ARC_API_KEY not found")
    sess = OnlineSession(key)
    try:
        frame, meta = reach_l3(sess)
        lv = int(meta.get("levels_completed") or 0)
        print(f"reached L3 levels={lv}")
        log = [_snap(frame, "l3_start", lv)]

        # --- crush ring ---
        p, _, _, _ = _plan_path(frame, POINT)
        if p is None:
            raise RuntimeError(f"no path to {POINT}")
        print(f"walking {len(p)} steps to {POINT}")
        for a in p:
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            nl = int(meta.get("levels_completed") or 0)
            if nl > lv:
                _write_report(log + [_snap(frame, "CLEARED", nl)], "CLEARED")
                return 0
        resp = sess.action(DIR_TO_ACTION[(1, 0)])  # RIGHT into (5,9) -> crush
        frame, meta = resp["frame"], resp
        nl = int(meta.get("levels_completed") or 0)
        log.append(_snap(frame, "post_crush", nl))
        print(f"post-crush: mover={ls20.locate_mover(frame)} lv={nl} "
              f"c9={log[-1]['c9']} c12={log[-1]['c12']}")

        # save dissolved frame
        try:
            g = ls20._plane(frame)
            FIXTURE_OUT.write_text(json.dumps({"frame": g.tolist()}),
                                   encoding="utf-8")
            print(f"saved dissolved frame -> {FIXTURE_OUT}")
        except Exception as e:
            print(f"(frame save failed: {e})")

        # --- plan to gate approach (10,9) on the DISSOLVED frame ---
        p2, cell2, fuel2, pmask2 = _plan_path(frame, GATE_ABOVE)
        if p2 is None:
            log.append({"tag": "no_path_to_gate_after_crush", "levels": nl})
            _write_report(log, "NO_PATH_TO_GATE")
            print(">>> no fuel/path to (10,9) after crush")
            return 1
        print(f"plan to (10,9): len={len(p2)} fuel={fuel2}")

        # --- execute, watch levels, stop at gate approach ---
        for i, a in enumerate(p2, 1):
            resp = sess.action(DIR_TO_ACTION[a])
            frame, meta = resp["frame"], resp
            nl = int(meta.get("levels_completed") or 0)
            mover = ls20.locate_mover(frame)
            log.append({"step": i, "action": DIR_TO_ACTION[a], "mover": mover,
                        "levels": nl})
            if nl > lv:
                _write_report(log, "CLEARED")
                print(f">>> CLEARED at step {i}")
                return 0

        # --- decisive: explicit DOWN into (10,10) ---
        before = ls20.locate_mover(frame)
        resp = sess.action(DIR_TO_ACTION[(0, 1)])  # DOWN
        frame, meta = resp["frame"], resp
        nl = int(meta.get("levels_completed") or 0)
        after = ls20.locate_mover(frame)
        entered = after != before
        log.append(_snap(frame, "after_DOWN_into_gate", nl))
        print(f"DOWN into (10,10): before={before} after={after} "
              f"entered={entered} lv={nl}")

        if nl > lv:
            _write_report(log, "CLEARED")
            return 0
        if entered:
            _write_report(log, "GATE_ENTERED_NO_CLEAR")
            print(">>> crush OPENED the gate, mover entered (10,10), but no clear")
            return 1
        _write_report(log, "GATE_STILL_BLOCKED")
        print(">>> crush did NOT open the gate; (10,10) still blocked")
        return 1
    finally:
        sess.close()


def _write_report(log, verdict) -> None:
    lines = [
        "# ls20 L3 压环后盖印门判定（E10）报告",
        "",
        "> 脚本：`tools/ls20_l3_crush_then_gate_probe.py`",
        "> 性质：设计期探路（最小动作 + 记录 mover bbox / levels）",
        "",
        "---",
        "",
        "## 结论",
        "",
        f"**{verdict}**",
        "",
        "## 逐步",
        "",
    ]
    for d in log:
        lines.append(f"- `{d}`")
    lines += [
        "",
        "## 判读",
        "",
        "- `CLEARED`：压环（legend flip）本身或其后路径使 levels 2→3。",
        "- `GATE_ENTERED_NO_CLEAR`：压环使 (10,10) 可进，但未过关（盖印机制另需）。",
        "- `GATE_STILL_BLOCKED`：压环后 (10,10) 仍被 color9 字形 C 硬挡",
        "  → legend flip 不是武装步骤，武装判据另找。",
        "- `NO_PATH_TO_GATE`：压环后燃料/路径不足以到达 (10,9)。",
        "",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan-only", action="store_true")
    args = ap.parse_args()
    if args.plan_only:
        return plan_only()
    return run_online()


if __name__ == "__main__":
    raise SystemExit(main())
