"""Post mid-east NON-FROG 14 east families.

Pose after mid-east: ship~(28,36) free~(23,36)+(34,36) bud≈32 fr15~(41,40)+(52,40).

Families (fresh boot each):
  V  vacate15 only (various dests) then y36 dual dx=2
  S0 leadS+4 only (no catch/frog) then micro dual
  Y40 lag-first then lead east (dual, keep gap≤12)
  SE  staggered: lag SE then lead SE (no frog pattern)
  R   leap14_east / reshape strides

Beat: d14<34 n=2 bud>=8, or d14<=30, or clear progress d14<=38 with bud>=16
  (frog-best is 34/10 — non-frog must beat or match with room to continue)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import advance_14_mid_east, translate2_nudge
from tools.r11l_l3_sync_probe import (
    clear15_corridor,
    count_free14,
    leap14_once,
    lock_other_ship,
    near_any,
)
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
    return {
        "d14": d14,
        "d15": d15,
        "bud": step_budget(data["frame"]),
        "n": len(free),
        "ship": me["c"],
        "free": sorted(free),
        "fr15": sorted(fr15),
    }


def boot_mid(tag):
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": [f"r11l_nf_{tag}"]},
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
    data, ok = advance_14_mid_east(sess, data, lv0, do_clear15=False)
    info = dump(data, f"MID-{tag}")
    return sess, data, lv0, ok and info["n"] == 2


def score(info, label, base_d14=44):
    """Progress vs mid-east d14=44; beat frog if d14<=34 bud>=10 or d14<34."""
    if info["n"] != 2:
        print(f"=== FAIL {label}: n={info['n']} ===", flush=True)
        return False
    progressed = info["d14"] < base_d14 - 2
    beat_frog = info["d14"] < 34 or (info["d14"] <= 34 and info["bud"] >= 10)
    strong = info["d14"] <= 38 and info["bud"] >= 16
    tag = "BEAT" if beat_frog else ("STRONG" if strong else ("PROG" if progressed else "best"))
    print(
        f"=== {tag} {label}: d14={info['d14']} bud={info['bud']} "
        f"ship={info['ship']} free={info['free']} ===",
        flush=True,
    )
    return beat_frog or strong


def vac15(sess, data, tgt):
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    # Prefer western sealer
    west = min(fr15, key=lambda w: w[0])
    east = max(fr15, key=lambda w: w[0])
    src = west
    if cheb(tgt, east) < 5 and cheb(tgt, west) >= 5:
        src = west
    elif near_any(tgt, list(lock_other_ship(data["frame"], 15) and []), cheb=0):
        pass
    freeze14 = lock_other_ship(data["frame"], 15)
    # Don't merge with 14
    free14 = count_free14(data["frame"], lock_other_ship(data["frame"], 14))
    if near_any(tgt, free14, cheb=5):
        print(f"  vac near14 {tgt}", flush=True)
        return data, False
    if cheb(tgt, east if src == west else west) < 5:
        print(f"  vac merge15 {tgt}", flush=True)
        return data, False
    data, newc, st = move_wp(sess, data, src, tgt, freeze14)
    print(f"  vac {src}->{tgt} {st}->{newc}", flush=True)
    return data, st == "moved"


def dual_y36(sess, data, rounds=5, dxes=(2, 2, 2, 2, 1)):
    best = dump(data, "dual0")
    for i, dx in enumerate(dxes[:rounds]):
        if step_budget(data["frame"]) < 8:
            break
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        if len(free) != 2 or me["c"][1] < 34:
            break
        data, ok = translate2_nudge(sess, data, fr15, lead_dx=dx)
        if data.get("state") == "GAME_OVER" or "frame" not in data:
            break
        info = dump(data, f"dual{i+1}")
        if info["n"] != 2:
            break
        if info["d14"] < best["d14"]:
            best = info
        if not ok:
            break
    return data, best


def micro_dual_row(sess, data, rounds=6):
    """Lead +2 then lag catch same-row; stop on noop/n!=2."""
    best = dump(data, "row0")
    for i in range(rounds):
        if step_budget(data["frame"]) < 8:
            break
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) != 2:
            break
        lead = max(free, key=lambda w: w[0])
        lag = min(free, key=lambda w: w[0])
        if lead[1] != lag[1]:
            print(f"  not same-row {free}", flush=True)
            break
        # try dx 2 then 3 then 1
        moved = False
        for dx in (2, 3, 1, 4):
            ld = (lead[0] + dx, lead[1])
            if near_any(ld, list(fr15), cheb=5):
                continue
            if ld[0] - lag[0] > 14:
                continue
            data, _, st = move_wp(sess, data, lead, ld, fr15)
            print(f"  lead {lead}->{ld} {st}", flush=True)
            if st == "dead" or data.get("state") == "GAME_OVER":
                return data, best
            if st != "moved":
                continue
            fr15 = lock_other_ship(data["frame"], 14)
            free = count_free14(data["frame"], fr15)
            if len(free) != 2:
                print(f"  flock after lead n={len(free)}", flush=True)
                return data, best
            lag = min(free, key=lambda w: w[0])
            lead2 = max(free, key=lambda w: w[0])
            gd = (lead2[0] - 6, lag[1])
            if cheb(gd, lead2) < 5:
                gd = (lag[0] + dx, lag[1])
            if near_any(gd, list(fr15), cheb=5):
                print(f"  lag near15 {gd}", flush=True)
                break
            data, _, st = move_wp(sess, data, lag, gd, fr15)
            print(f"  lag {lag}->{gd} {st}", flush=True)
            if st == "dead" or data.get("state") == "GAME_OVER":
                return data, best
            if st != "moved":
                break
            info = dump(data, f"row{i+1}")
            if info["n"] != 2:
                return data, best
            if info["d14"] < best["d14"]:
                best = info
            moved = True
            break
        if not moved:
            print("  micro dual stuck", flush=True)
            break
    return data, best


# ---- families ----

def run_V():
    """Vacate sealer then y36 dual."""
    dests = [
        (48, 36),
        (50, 38),
        (45, 44),
        (50, 42),
        (58, 42),
        (42, 46),
    ]
    results = []
    for tgt in dests:
        print(f"\n===== V vac->{tgt} =====", flush=True)
        sess, data, lv0, ok = boot_mid(f"V{tgt[0]}")
        if not ok:
            continue
        data, ok = vac15(sess, data, tgt)
        if not ok or data.get("state") == "GAME_OVER":
            continue
        dump(data, "VAC")
        data, best = dual_y36(sess, data)
        score(best, f"V{tgt}")
        results.append(best)
    return results


def run_Y40_lagfirst():
    """deep15 optional light: only east5842; leadS+catch; lag-first SE then lead."""
    print("\n===== Y40 lag-first (light15 east5842) =====", flush=True)
    sess, data, lv0, ok = boot_mid("Y40L")
    if not ok:
        return
    # light vac east only
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, st = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    print(f"  e5842 {st}", flush=True)
    # also push west sealer south-east away from y40 band
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    west = min(flock, key=lambda w: w[0])
    for wt in ((48, 42), (45, 44), (50, 42), (42, 46)):
        if near_any(wt, count_free14(data["frame"], lock_other_ship(data["frame"], 14)), cheb=5):
            continue
        if cheb(wt, max(flock, key=lambda w: w[0])) < 5:
            continue
        data, _, st = move_wp(sess, data, west, wt, freeze14)
        print(f"  w {west}->{wt} {st}", flush=True)
        if st == "moved":
            break
        if st == "dead":
            return
    dump(data, "VAC15")
    # leadS + catch y40
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    print(f"  leadS {st}", flush=True)
    if st != "moved":
        return
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    for gd in ((lag[0] + 2, lead[1]), (lag[0] + 4, lead[1]), (lead[0] - 6, lead[1])):
        if cheb(gd, lead) < 5 or near_any(gd, list(fr15), cheb=5):
            continue
        data, _, st = move_wp(sess, data, lag, gd, fr15)
        print(f"  catch {lag}->{gd} {st}", flush=True)
        if st == "moved":
            break
        if st == "dead":
            return
    best = dump(data, "Y40")
    # lag-first moves
    lag_tgts = [
        (28, 42),
        (30, 42),
        (28, 44),
        (30, 44),
        (26, 44),
        (32, 42),
        (32, 44),
        (28, 40),
        (30, 40),
    ]
    for lt in lag_tgts:
        if step_budget(data["frame"]) < 8:
            break
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) != 2:
            break
        lead = max(free, key=lambda w: w[0])
        lag = min(free, key=lambda w: w[0])
        if cheb(lt, lead) < 5 or near_any(lt, list(fr15), cheb=5):
            print(f"  skip lag {lt}", flush=True)
            continue
        data, _, st = move_wp(sess, data, lag, lt, fr15)
        print(f"  lag1 {lag}->{lt} {st}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER":
            return
        if st != "moved":
            continue
        info = dump(data, "lag1")
        if info["n"] != 2:
            print("flock", flush=True)
            return
        # now lead east same row or SE
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        lead = max(free, key=lambda w: w[0])
        lag = min(free, key=lambda w: w[0])
        for ld in (
            (lead[0] + 2, lead[1]),
            (lead[0] + 4, lead[1]),
            (lead[0] + 2, lead[1] + 2),
            (lead[0] + 4, lead[1] + 2),
            (lead[0] + 6, lead[1]),
        ):
            if cheb(ld, lag) < 5 or near_any(ld, list(fr15), cheb=5):
                continue
            if ld[0] - lag[0] > 14:
                continue
            data, _, st = move_wp(sess, data, lead, ld, fr15)
            print(f"  lead1 {lead}->{ld} {st}", flush=True)
            if st == "dead" or data.get("state") == "GAME_OVER":
                return
            if st == "moved":
                info = dump(data, "lead1")
                if info["n"] == 2 and info["d14"] < best["d14"]:
                    best = info
                break
        # continue micro dual from here
        data, best2 = micro_dual_row(sess, data, rounds=4)
        if best2["d14"] < best["d14"]:
            best = best2
        score(best, "Y40L")
        return
    score(best, "Y40L")


def run_SE_stagger():
    """No frog: lag SE then lead SE from mid after deep15 full."""
    print("\n===== SE stagger after deep15 =====", flush=True)
    sess, data, lv0, ok = boot_mid("SE")
    if not ok:
        return
    # deep15 C-style
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, st = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    if st == "dead":
        return
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, st = move_wp(
        sess, data, min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (42, 50), freeze14
    )
    if st == "dead":
        return
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, st = move_wp(
        sess, data, max(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (58, 50), freeze14
    )
    dump(data, "DEEP")
    best = dump(data, "se0")
    # stagger pairs (lag_tgt, lead_tgt)
    pairs = [
        ((26, 40), (36, 40)),
        ((28, 40), (38, 40)),
        ((28, 42), (38, 42)),
        ((30, 42), (40, 42)),
        ((28, 44), (38, 44)),
        ((30, 44), (40, 44)),
        ((26, 44), (36, 44)),
        ((27, 42), (37, 42)),
    ]
    for lag_t, lead_t in pairs:
        print(f"\n--- pair lag{lag_t} lead{lead_t} ---", flush=True)
        sess, data, lv0, ok = boot_mid("SEp")
        if not ok:
            continue
        freeze14 = lock_other_ship(data["frame"], 15)
        fr15 = list(lock_other_ship(data["frame"], 14))
        data, _, st = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
        if st == "dead":
            continue
        freeze14 = lock_other_ship(data["frame"], 15)
        data, _, st = move_wp(
            sess, data, min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (42, 50), freeze14
        )
        if st == "dead":
            continue
        freeze14 = lock_other_ship(data["frame"], 15)
        data, _, st = move_wp(
            sess, data, max(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (58, 50), freeze14
        )
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) != 2:
            continue
        lead = max(free, key=lambda w: w[0])
        lag = min(free, key=lambda w: w[0])
        if cheb(lag_t, lead) < 5 or near_any(lag_t, list(fr15), cheb=5):
            print("skip lag", flush=True)
            continue
        data, _, st = move_wp(sess, data, lag, lag_t, fr15)
        print(f"  lag {lag}->{lag_t} {st}", flush=True)
        if st != "moved":
            continue
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) != 2:
            print(f"flock n={len(free)}", flush=True)
            continue
        lead = max(free, key=lambda w: w[0])
        lag = min(free, key=lambda w: w[0])
        if cheb(lead_t, lag) < 5 or near_any(lead_t, list(fr15), cheb=5):
            print("skip lead", flush=True)
            continue
        data, _, st = move_wp(sess, data, lead, lead_t, fr15)
        print(f"  lead {lead}->{lead_t} {st}", flush=True)
        if st != "moved":
            continue
        info = dump(data, "pair")
        if info["n"] != 2:
            print("flock2", flush=True)
            continue
        if info["d14"] < best["d14"]:
            best = info
        # extend micro dual
        data, best2 = micro_dual_row(sess, data, rounds=5)
        if best2["d14"] < best["d14"]:
            best = best2
        if best["d14"] <= 38:
            score(best, f"SE{lag_t}-{lead_t}")
            if best["d14"] <= 34:
                return best
    score(best, "SE-best")
    return best


def run_R():
    """leap14_east strides after deep15."""
    print("\n===== R leap14 after deep15 =====", flush=True)
    sess, data, lv0, ok = boot_mid("R")
    if not ok:
        return
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, _ = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, _ = move_wp(
        sess, data, min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (42, 50), freeze14
    )
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, _ = move_wp(
        sess, data, max(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (58, 50), freeze14
    )
    best = dump(data, "R0")
    for i in range(4):
        if step_budget(data["frame"]) < 10:
            break
        fr15 = lock_other_ship(data["frame"], 14)
        data, ok = leap14_once(sess, data, fr15, lv0, stride=6)
        if data.get("state") == "GAME_OVER" or "frame" not in data:
            break
        info = dump(data, f"R{i+1}")
        if info["n"] != 2:
            print("flock break", flush=True)
            break
        if info["d14"] < best["d14"]:
            best = info
        if not ok:
            break
    score(best, "R")


def main():
    run_V()
    run_Y40_lagfirst()
    run_SE_stagger()
    run_R()


if __name__ == "__main__":
    main()
