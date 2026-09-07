"""L4 H5q: short transition search — who changes stamp_c9 or gate_u?

One climb. Visit a few loci; at each, pulse U/D/L/R + A5 (+ A6 on stamp/legend
once). Log any delta in stamp_c9 / gate_in_walk_u / levels.
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

REPORT = ROOT / "docs" / "ls20_l4_h5q_transition_search.md"

LOCI = [(10, 1), (8, 4), (4, 6), (2, 1), (6, 10)]
DIRS = ((0, -1), (0, 1), (-1, 0), (1, 0))


def _sig(s):
    return (s["stamp_c9"], s["gate_in_walk_u"], s["c9"], s["c14"], s["c0"])


def main() -> int:
    sess = OnlineSession(_api_key())
    log = []
    hits = []
    try:
        sess.open(tags=["ls20_l4_h5q"])
        frame, meta = _climb_to_l4(sess)
        p_pu, _ = _plan_to_pickup(frame)
        if p_pu:
            frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")
        log.append({"tag": "start", "snap": _snap(frame)})

        for locus in LOCI:
            p, _ = _walk_to(frame, locus)
            if p is None:
                log.append({"tag": "skip", "locus": locus})
                print(f"skip {locus}")
                continue
            frame, meta, cleared = _exec_path(sess, frame, meta, p, log, f"to_{locus}")
            if cleared:
                log.append({"tag": "RESULT", "verdict": "PASS_WALK"})
                break
            if ls20.init(frame).cursor != locus:
                # accept near-miss for warp landings
                log.append({"tag": "near", "want": locus,
                            "got": ls20.init(frame).cursor})
            base = _snap(frame)
            print(f"@ {base['cursor']} sig={_sig(base)}")

            actions = [(f"D{d}", lambda d=d: sess.action(DIR_TO_ACTION[d])) for d in DIRS]
            actions.append(("A5", lambda: sess.action(5)))
            if locus == (2, 1):
                actions.append(("A6s", lambda: sess.action(6, x=11, y=7)))
                actions.append(("A6l", lambda: sess.action(6, x=5, y=57)))

            for name, fn in actions:
                # repath if we drifted from locus (except after intentional move)
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
                    or (dlt["n"] >= 10 and "5->0" not in str(dlt["transitions"])
                        and "0->5" not in str(dlt["transitions"])
                        and "11->3" not in str(dlt["transitions"]))
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
                    print(f"  HIT {name}: {_sig(bs)} -> {_sig(as_)} n={dlt['n']} "
                          f"trans={dlt['transitions']}")
                else:
                    # keep compact
                    if dlt["n"] > 0 and name.startswith("D"):
                        log.append({**row, "tag": "pulse_quiet"})
                if lv >= 4:
                    log.append({"tag": "RESULT", "verdict": "PASS"})
                    break
                # if we moved away, stop pulsing this locus
                if as_["cursor"] != bs["cursor"] and name.startswith("D"):
                    # continue with new position as soft locus? stop for control
                    break
            else:
                continue
            break

        if not any(r.get("verdict") == "PASS" for r in log):
            log.append({"tag": "RESULT", "verdict": "NO_ARMING_HIT",
                        "hits": len(hits)})
        REPORT.write_text(
            f"# L4 H5q transition search\n\n> hits={len(hits)}\n\n"
            + "\n".join(f"- `{r}`" for r in log) + "\n",
            encoding="utf-8",
        )
        print("wrote", REPORT, "hits", len(hits), log[-1])
        return 0 if log[-1].get("verdict") == "PASS" else 1
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
