"""Save bud: skip lagSE(26,44) and/or Ny46; keep S6044→N6038→S6248.

Target: N6038 with bud≥10, then continue south.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import advance_14_mid_east
from tools.r11l_l3_sync_probe import clear15_corridor, count_free14, lock_other_ship, near_any
from tools.r11l_seated_clear import clear_l1, reset


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def dump(data, label):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
    d15 = abs(me15["c"][0] - 34) + abs(me15["c"][1] - 57)
    print(
        f"{label} ship14={me['c']} d14={d14} free={sorted(free)} n={len(free)} "
        f"d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14, d15, step_budget(data["frame"]), me["c"], sorted(free)


def open_gate():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_save2"]},
        timeout=90,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"
    data = reset(sess)
    data, _ = clear_l1(sess, data)
    data, _ = clear_l2(sess, data)
    lv0 = data.get("levels_completed") or 0
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _ = clear15_corridor(sess, data, freeze14)
    data, _ = advance_14_mid_east(sess, data, lv0, do_clear15=False)
    # deep15 fixed
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, st = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    if st != "moved":
        return sess, data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, st = move_wp(
        sess, data, min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (42, 50), freeze14
    )
    if st != "moved":
        return sess, data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, st = move_wp(
        sess, data, max(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (58, 54), freeze14
    )
    if st != "moved":
        return sess, data, False
    print(f"  deep done bud={step_budget(data['frame'])}", flush=True)
    return sess, data, True


def se_start(sess, data, mode):
    """mode: base | skip_lag | skip_ny | skip_both | lead_se"""
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) != 2:
        return data, False
    lead = max(free, key=lambda w: w[0])
    lag = min(free, key=lambda w: w[0])

    if mode == "lead_se":
        # try lead → (36,44) directly
        data, _, st = move_wp(sess, data, lead, (36, 44), fr15)
        print(f"  leadSE {lead}->(36,44) {st} bud={step_budget(data['frame'])}", flush=True)
        if st != "moved":
            return data, False
    elif mode in ("skip_lag", "skip_both"):
        data, _, st = move_wp(sess, data, lag, (36, 44), fr15)
        print(f"  lagDirect {lag}->(36,44) {st} bud={step_budget(data['frame'])}", flush=True)
        if st != "moved":
            # fallback try (34,44)/(38,44)
            for t in ((34, 44), (38, 44), (32, 44)):
                fr15 = lock_other_ship(data["frame"], 14)
                free = count_free14(data["frame"], fr15)
                lag = min(free, key=lambda w: w[0])
                lead = max(free, key=lambda w: w[0])
                if cheb(t, lead) < 5 or near_any(t, list(fr15), cheb=5):
                    continue
                data, _, st = move_wp(sess, data, lag, t, fr15)
                print(f"  lagDirect {lag}->{t} {st} bud={step_budget(data['frame'])}", flush=True)
                if st == "moved":
                    break
                if st == "dead":
                    return data, False
            else:
                return data, False
    else:
        data, _, st = move_wp(sess, data, lag, (26, 44), fr15)
        print(f"  lagSE {st} bud={step_budget(data['frame'])}", flush=True)
        if st != "moved":
            return data, False
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        src = (26, 44) if (26, 44) in free else max(free, key=lambda w: (w[1], w[0]))
        data, _, st = move_wp(sess, data, src, (36, 44), fr15)
        print(f"  extE {st} bud={step_budget(data['frame'])}", flush=True)
        if st != "moved":
            return data, False

    do_ny = mode in ("base", "skip_lag", "lead_se")
    if do_ny:
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        north = min(free, key=lambda w: (w[1], w[0]))
        data, _, st = move_wp(sess, data, north, (46, 36), fr15)
        print(f"  Ny46 {st} bud={step_budget(data['frame'])}", flush=True)
        if st != "moved":
            return data, False

    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    north = min(free, key=lambda w: (w[1], w[0]))
    south = max(free, key=lambda w: (w[1], w[0]))
    for nt in ((48, 32), (50, 32), (46, 32)):
        if cheb(nt, south) < 5 or near_any(nt, list(fr15), cheb=5):
            continue
        data, _, st = move_wp(sess, data, north, nt, fr15)
        print(f"  N4832 {st} bud={step_budget(data['frame'])}", flush=True)
        if st == "moved":
            dump(data, "N4832")
            return data, True
        if st == "dead":
            return data, False
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) < 2:
            return data, False
        north = min(free, key=lambda w: (w[1], w[0]))
        south = max(free, key=lambda w: (w[1], w[0]))
    return data, False


def chain_to_s6248(sess, data):
    marks = {}
    for who, tgt, key in (
        ("S", (60, 44), "S6044"),
        ("N", (60, 38), "N6038"),
        ("S", (62, 48), "S6248"),
    ):
        if step_budget(data["frame"]) < 3:
            print("budout before", key, flush=True)
            break
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) < 2:
            return data, marks, False
        north = min(free, key=lambda w: (w[1], w[0]))
        south = max(free, key=lambda w: (w[1], w[0]))
        if who == "S":
            cands = [w for w in free if w[1] >= 40]
            if cands:
                south = max(cands, key=lambda w: (w[0], w[1]))
        cur = north if who == "N" else south
        other = south if who == "N" else north
        if cheb(tgt, other) < 5 or near_any(tgt, list(fr15), cheb=5):
            print(f"  {key} skip", flush=True)
            return data, marks, False
        data, newc, st = move_wp(sess, data, cur, tgt, fr15)
        print(f"  {key} {cur}->{tgt} {st}->{newc} bud={step_budget(data['frame'])}", flush=True)
        if st != "moved":
            return data, marks, False
        d14, d15, bud, ship, free = dump(data, key)
        marks[key] = (d14, d15, bud, ship, free)
    return data, marks, "N6038" in marks


PLANS = ["base", "skip_ny", "skip_lag", "skip_both", "lead_se"]


def main():
    summary = []
    for mode in PLANS:
        print(f"\n===== {mode} =====", flush=True)
        sess, data, ok = open_gate()
        if not ok:
            summary.append((mode, "deep-fail", None))
            continue
        data, ok = se_start(sess, data, mode)
        if not ok:
            summary.append((mode, "se-fail", None))
            continue
        data, marks, ok = chain_to_s6248(sess, data)
        n6038 = marks.get("N6038")
        s6248 = marks.get("S6248")
        summary.append(
            (
                mode,
                "ok" if ok else "partial",
                n6038[2] if n6038 else None,  # bud at N6038
                s6248[:3] if s6248 else None,  # d14,d15,bud after S6248
            )
        )
        print(f"RESULT {mode} N6038_bud={n6038[2] if n6038 else None} S6248={s6248[:3] if s6248 else None}", flush=True)

    print("\n===== SUMMARY =====", flush=True)
    for row in summary:
        print(row, flush=True)


if __name__ == "__main__":
    main()
