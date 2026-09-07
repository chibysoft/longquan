"""L4 H5r: denser transition search — stamp_c9 / gate_u deltas.

Fixes H5q early-exit: after a move pulse, rewalk to locus and continue;
never abort the outer locus loop on a single DIR pulse.
One climb. Fuel via nearest pickup first.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_l4_arming_probe import _climb_to_l4, _plan_to_pickup
from tools.ls20_l4_h5_arming_probe import _exec_path, _walk_to
from tools.ls20_l4_h5e_diff_probe import _plane_diff, _snap

REPORT = ROOT / "docs" / "ls20_l4_h5r_transition_search.md"

# Gate approach, mid warps, stamp-adjacent, legend row, ring-adjacent if reachable
LOCI = [
    (2, 1), (3, 1), (1, 2), (10, 1), (8, 4), (10, 4),
    (4, 6), (6, 5), (5, 6), (6, 10), (3, 9), (8, 9),
]
DIRS = ((0, -1), (0, 1), (-1, 0), (1, 0))


def _sig(s):
    return (s["stamp_c9"], s["gate_in_walk_u"], s["c9"], s["c14"], s["c0"])


def _ensure_at(sess, frame, meta, locus, log, tag):
    cur = ls20.init(frame).cursor
    if cur == locus:
        return frame, meta, True
    p, _ = _walk_to(frame, locus)
    if p is None:
        log.append({"tag": "unreachable", "want": locus, "at": cur})
        return frame, meta, False
    frame, meta, cleared = _exec_path(sess, frame, meta, p, log, tag)
    if cleared:
        return frame, meta, False
    got = ls20.init(frame).cursor
    if got != locus:
        log.append({"tag": "near", "want": locus, "got": got})
        return frame, meta, got == locus  # False
    return frame, meta, True


def main() -> int:
    sess = OnlineSession(_api_key())
    log = []
    hits = []
    try:
        sess.open(tags=["ls20_l4_h5r"])
        frame, meta = _climb_to_l4(sess)
        p_pu, _ = _plan_to_pickup(frame)
        if p_pu:
            frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")
        log.append({"tag": "start", "snap": _snap(frame)})

        for locus in LOCI:
            frame, meta, ok = _ensure_at(sess, frame, meta, locus, log, f"to_{locus}")
            if int(meta.get("levels_completed") or 0) >= 4:
                log.append({"tag": "RESULT", "verdict": "PASS_WALK"})
                break
            if not ok:
                print(f"skip {locus}")
                continue
            base = _snap(frame)
            print(f"@ {locus} sig={_sig(base)}")

            # A5 first (no move), then A6 at stamp/legend once near gate
            named = [("A5", lambda: sess.action(5))]
            if locus in ((2, 1), (3, 1), (1, 2)):
                named.append(("A6s", lambda: sess.action(6, x=11, y=7)))
                named.append(("A6l", lambda: sess.action(6, x=5, y=57)))
            for d in DIRS:
                named.append((f"D{d}", lambda d=d: sess.action(DIR_TO_ACTION[d])))

            for name, fn in named:
                frame, meta, ok = _ensure_at(
                    sess, frame, meta, locus, log, f"re_{locus}_{name}",
                )
                if not ok or int(meta.get("levels_completed") or 0) >= 4:
                    break
                before = frame
                bs = _snap(before)
                try:
                    resp = fn()
                except Exception as e:
                    log.append({"tag": "err", "locus": locus, "act": name, "e": str(e)})
                    continue
                frame, meta = resp["frame"], resp
                as_ = _snap(frame)
                dlt = _plane_diff(before, frame, limit=20)
                lv = int(meta.get("levels_completed") or 0)
                interesting = (
                    _sig(as_) != _sig(bs)
                    or as_["gate_in_walk_u"]
                    or lv >= 4
                    or (
                        dlt["n"] >= 8
                        and "5->0" not in str(dlt["transitions"])
                        and "0->5" not in str(dlt["transitions"])
                        and "11->3" not in str(dlt["transitions"])
                        and "3->11" not in str(dlt["transitions"])
                    )
                )
                row = {
                    "tag": "pulse", "locus": locus, "act": name,
                    "before_sig": _sig(bs), "after_sig": _sig(as_),
                    "cursor": as_["cursor"], "n": dlt["n"],
                    "trans": dlt["transitions"], "levels": lv,
                    "interesting": interesting,
                }
                if interesting:
                    hits.append(row)
                    log.append(row)
                    print(
                        f"  HIT {name}: {_sig(bs)} -> {_sig(as_)} n={dlt['n']} "
                        f"trans={dlt['transitions']}"
                    )
                elif dlt["n"] > 0:
                    log.append({**row, "tag": "pulse_quiet"})
                if lv >= 4:
                    log.append({"tag": "RESULT", "verdict": "PASS"})
                    break
            if int(meta.get("levels_completed") or 0) >= 4:
                break

        if not any(r.get("verdict", "").startswith("PASS") for r in log):
            log.append({
                "tag": "RESULT", "verdict": "NO_ARMING_HIT", "hits": len(hits),
            })
        REPORT.write_text(
            f"# L4 H5r transition search\n\n> hits={len(hits)}\n\n"
            + "\n".join(f"- `{r}`" for r in log) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {REPORT} hits {hits and hits[0] or {'tag': 'RESULT', 'hits': 0}}")
        return 0 if any(r.get("verdict", "").startswith("PASS") for r in log) else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
