"""Non-frog geometries from mid-east: find d14<<34 with bud left.

Families (fresh boot each):
  A  y36 dual-nudge only (no deep15)
  B  light15 east@(58,42) then y36 dual
  C  deep15 (4250+5850) then y36 dual (NO frog)
  D  deep15 → leadS+4 → catch-y40 → dual-east (NO frog/Ny)
  E  haul15 first (~3 hops) then y36 dual / leap

Beat gate vs frog-best: d14<34 with n=2 and bud>=8, or d14<=34 with bud>=10.
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
    haul15_toward,
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
        json={"tags": [f"r11l_geom_{tag}"]},
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


def deep15(sess, data, west=(42, 50), east=(58, 50)):
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    e = max(fr15, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, e, (58, 42), freeze14)
    print(f"  e5842 {st}", flush=True)
    if st == "dead" or data.get("state") == "GAME_OVER":
        return data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    w = min(flock, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, w, west, freeze14)
    print(f"  w{west} {st}", flush=True)
    if st == "dead" or data.get("state") == "GAME_OVER":
        return data, False
    if east:
        freeze14 = lock_other_ship(data["frame"], 15)
        flock = list(lock_other_ship(data["frame"], 14))
        e = max(flock, key=lambda w: w[0])
        data, _, st = move_wp(sess, data, e, east, freeze14)
        print(f"  e{east} {st}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER":
            return data, False
    dump(data, "DEEP15")
    return data, True


def light15_east(sess, data):
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    e = max(fr15, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, e, (58, 42), freeze14)
    print(f"  light e5842 {st}", flush=True)
    dump(data, "LIGHT15")
    return data, st == "moved"


def dual_y36(sess, data, lv0, rounds=6, dxes=(3, 2, 2, 2, 1, 1)):
    best = dump(data, "dual0")
    for i, dx in enumerate(dxes[:rounds]):
        if step_budget(data["frame"]) < 8:
            print("  bud low dual stop", flush=True)
            break
        if data.get("state") == "GAME_OVER" or "frame" not in data:
            break
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        if len(free) != 2 or me["c"][1] < 34:
            print(f"  dual stop flock/y free={free} ship={me['c']}", flush=True)
            break
        data, ok = translate2_nudge(sess, data, fr15, lead_dx=dx)
        if data.get("state") == "GAME_OVER" or "frame" not in data:
            print("  GO dual", flush=True)
            break
        info = dump(data, f"dual{i+1}_dx{dx}")
        if info["n"] != 2:
            print("  flock broke", flush=True)
            break
        if info["d14"] < best["d14"] or (
            info["d14"] == best["d14"] and info["bud"] > best["bud"]
        ):
            best = info
        if not ok:
            print("  dual nudge fail", flush=True)
            break
        if me["c"][0] >= 50:
            break
    return data, best


def leadS_catch_y40(sess, data):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) != 2:
        return data, False
    lead = max(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    print(f"  leadS {st}", flush=True)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) != 2:
        return data, False
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    for gd in ((lag[0] + 2, lead[1]), (lag[0] + 4, lead[1]), (lead[0] - 6, lead[1])):
        if cheb(gd, lead) < 5:
            continue
        if near_any(gd, list(fr15), cheb=5):
            continue
        data, _, st = move_wp(sess, data, lag, gd, fr15)
        print(f"  catch {lag}->{gd} {st}", flush=True)
        if st == "moved":
            dump(data, "Y40")
            return data, True
        if st == "dead" or data.get("state") == "GAME_OVER":
            return data, False
    return data, False


def dual_row(sess, data, rounds=5, dxes=(2, 2, 2, 2, 1)):
    """Same-row dual east after catch (any y)."""
    best = dump(data, "row0")
    for i, dx in enumerate(dxes[:rounds]):
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
        ld = (lead[0] + dx, lead[1])
        if near_any(ld, list(fr15), cheb=5):
            print(f"  lead near15 {ld}", flush=True)
            break
        data, _, st = move_wp(sess, data, lead, ld, fr15)
        print(f"  row-lead {lead}->{ld} {st}", flush=True)
        if st != "moved" or data.get("state") == "GAME_OVER":
            break
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) != 2:
            break
        lag = min(free, key=lambda w: w[0])
        lead_now = max(free, key=lambda w: w[0])
        gd = (lead_now[0] - 6, lag[1])  # stay behind lead
        if cheb(gd, lead_now) < 5:
            gd = (lag[0] + dx, lag[1])
        if near_any(gd, list(fr15), cheb=5):
            print(f"  lag near15 {gd}", flush=True)
            break
        data, _, st = move_wp(sess, data, lag, gd, fr15)
        print(f"  row-lag {lag}->{gd} {st}", flush=True)
        if st != "moved" or data.get("state") == "GAME_OVER":
            break
        info = dump(data, f"row{i+1}")
        if info["n"] != 2:
            break
        if info["d14"] < best["d14"]:
            best = info
    return data, best


def score(info, label):
    beat = (
        info["n"] == 2
        and (
            (info["d14"] < 34 and info["bud"] >= 8)
            or (info["d14"] <= 34 and info["bud"] >= 10)
            or info["d14"] <= 30
        )
    )
    tag = "BEAT" if beat else "best"
    print(
        f"=== {tag} {label}: d14={info['d14']} bud={info['bud']} "
        f"n={info['n']} ship={info['ship']} free={info['free']} ===",
        flush=True,
    )
    return beat


def run_A():
    print("\n===== A y36 dual no-deep15 =====", flush=True)
    sess, data, lv0, ok = boot_mid("A")
    if not ok:
        print("boot fail", flush=True)
        return False
    data, best = dual_y36(sess, data, lv0)
    return score(best, "A")


def run_B():
    print("\n===== B light15 + y36 dual =====", flush=True)
    sess, data, lv0, ok = boot_mid("B")
    if not ok:
        print("boot fail", flush=True)
        return False
    data, ok = light15_east(sess, data)
    if not ok or data.get("state") == "GAME_OVER":
        print("light15 fail", flush=True)
        return False
    data, best = dual_y36(sess, data, lv0)
    return score(best, "B")


def run_C():
    print("\n===== C deep15 + y36 dual NO frog =====", flush=True)
    sess, data, lv0, ok = boot_mid("C")
    if not ok:
        print("boot fail", flush=True)
        return False
    data, ok = deep15(sess, data)
    if not ok or data.get("state") == "GAME_OVER":
        print("deep15 fail", flush=True)
        return False
    data, best = dual_y36(sess, data, lv0, rounds=5, dxes=(2, 2, 2, 2, 1))
    return score(best, "C")


def run_D():
    print("\n===== D deep15 + S + y40 dual NO frog =====", flush=True)
    sess, data, lv0, ok = boot_mid("D")
    if not ok:
        print("boot fail", flush=True)
        return False
    data, ok = deep15(sess, data)
    if not ok or data.get("state") == "GAME_OVER":
        print("deep15 fail", flush=True)
        return False
    data, ok = leadS_catch_y40(sess, data)
    if not ok or data.get("state") == "GAME_OVER":
        print("y40 fail", flush=True)
        dump(data, "D-fail")
        return False
    data, best = dual_row(sess, data)
    return score(best, "D")


def run_E():
    print("\n===== E haul15 first then y36/leap =====", flush=True)
    sess, data, lv0, ok = boot_mid("E")
    if not ok:
        print("boot fail", flush=True)
        return False
    for i in range(3):
        if step_budget(data["frame"]) < 12:
            break
        data, _ = haul15_toward(sess, data, (34, 57), max_step=6, label=f"haul{i}")
        if data.get("state") == "GAME_OVER" or "frame" not in data:
            print("GO haul", flush=True)
            return False
        dump(data, f"HAUL{i}")
    # try dual then one leap
    data, best = dual_y36(sess, data, lv0, rounds=4, dxes=(3, 2, 2, 2))
    if step_budget(data["frame"]) >= 10 and best["n"] == 2:
        fr15 = lock_other_ship(data["frame"], 14)
        data, _ = leap14_once(sess, data, fr15, lv0, stride=6)
        if "frame" in data and data.get("state") != "GAME_OVER":
            best2 = dump(data, "LEAP")
            if best2["n"] == 2 and best2["d14"] < best["d14"]:
                best = best2
    return score(best, "E")


def main():
    results = []
    for name, fn in (
        ("A", run_A),
        ("B", run_B),
        ("C", run_C),
        ("D", run_D),
        ("E", run_E),
    ):
        try:
            beat = fn()
            results.append((name, beat))
        except Exception as e:
            print(f"=== FAIL {name}: {e} ===", flush=True)
            results.append((name, False))
    print("\n===== SUMMARY =====", flush=True)
    for name, beat in results:
        print(f"  {name}: {'BEAT' if beat else 'no'}", flush=True)


if __name__ == "__main__":
    main()
