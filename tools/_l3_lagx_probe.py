"""After deep15: lag-first translate (keep n=2), then frog, S-south scan."""
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
        f"ship15={me15['c']} d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14, free


def boot_deep(sess):
    data = reset(sess)
    data, _ = clear_l1(sess, data)
    data, _ = clear_l2(sess, data)
    lv0 = data.get("levels_completed") or 0
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _ = clear15_corridor(sess, data, freeze14)
    data, _ = advance_14_mid_east(sess, data, lv0, do_clear15=False)
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, _ = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, _ = move_wp(
        sess, data, min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (48, 42), freeze14
    )
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    data, _, _ = move_wp(sess, data, min(flock, key=lambda w: w[0]), (42, 50), freeze14)
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    data, _, _ = move_wp(sess, data, max(flock, key=lambda w: w[0]), (58, 50), freeze14)
    return data


def frog_to_s40(sess, data):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) < 2:
        return data, False
    lead = max(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) < 2:
        return data, False
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, lag, (lag[0] + 2, lead[1] + 4), fr15)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) < 2:
        return data, False
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, n, (40, 36), fr15)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) < 2:
        return data, False
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    if not near_any((40, 44), list(fr15), cheb=5) and cheb((40, 44), n) >= 5:
        data, _, st = move_wp(sess, data, s, (40, 44), fr15)
        if st == "dead":
            return data, False
    return data, True


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_lagx"]},
        timeout=90,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"
    data = boot_deep(sess)
    dump(data, "deep")

    # Lag-first soft east, then lead — keep sep≥5
    for step_name, pick, tgt_fn in (
        ("lag+3", lambda f: min(f, key=lambda w: w[0]), lambda lag, lead: (lag[0] + 3, 36)),
        ("lag+4", lambda f: min(f, key=lambda w: w[0]), lambda lag, lead: (min(lead[0] - 5, lag[0] + 4), 36)),
        ("lead+2", lambda f: max(f, key=lambda w: w[0]), lambda lag, lead: (lead[0] + 2, 36)),
        ("lead+3", lambda f: max(f, key=lambda w: w[0]), lambda lag, lead: (lead[0] + 3, 36)),
        ("lead+4", lambda f: max(f, key=lambda w: w[0]), lambda lag, lead: (lead[0] + 4, 36)),
    ):
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) != 2:
            print("n!=2 abort xlate", free, flush=True)
            break
        lead = max(free, key=lambda w: w[0])
        lag = min(free, key=lambda w: w[0])
        cur = pick(free)
        ld = tgt_fn(lag, lead)
        if ld == cur or not (0 <= ld[0] < 64):
            continue
        other = lead if cur == lag else lag
        if cheb(ld, other) < 5:
            print(f"skip merge {step_name} {ld}", flush=True)
            continue
        if near_any(ld, list(fr15), cheb=5):
            print(f"skip near15 {step_name} {ld}", flush=True)
            continue
        data, newc, st = move_wp(sess, data, cur, ld, fr15)
        d14, free2 = dump(data, f"after-{step_name}-{st}")
        print(f"  {cur}->{ld} {st}->{newc} n={len(free2)}", flush=True)
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", flush=True)
            return
        if len(free2) < 2:
            print("n1 — stop xlate", flush=True)
            break

    dump(data, "pre-frog")
    data, ok = frog_to_s40(sess, data)
    if not ok:
        print("frogfail", flush=True)
        dump(data, "frog-end")
        return
    d0, free = dump(data, "at4044")
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    fr15 = lock_other_ship(data["frame"], 14)
    for cur, ld in (
        (s, (40, 48)),
        (s, (40, 46)),
        (s, (42, 48)),
        (s, (38, 48)),
        (s, (44, 48)),
        (s, (42, 46)),
        (s, (40, 50)),
        (s, (36, 48)),
        (n, (43, 38)),
        (n, (42, 36)),
        (n, (44, 36)),
        (n, (38, 36)),
    ):
        if step_budget(data["frame"]) < 4:
            break
        if near_any(ld, list(fr15), cheb=5):
            print(f"skip near15 {ld}", flush=True)
            continue
        other = s if cur == n else n
        if cheb(ld, other) < 5:
            continue
        data, newc, st = move_wp(sess, data, cur, ld, fr15)
        me = next(z for z in ships(data["frame"]) if z["chrome"] == 14)
        d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
        print(
            f"  {cur}->{ld} {st}->{newc} ship={me['c']} d14={d14}({d14-d0:+d}) "
            f"bud={step_budget(data['frame'])}",
            flush=True,
        )
        if st == "dead":
            print("DEAD", flush=True)
            return
        if st == "moved":
            dump(data, "HIT")
            print("SUCCESS", flush=True)
            return
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) != 2:
            break
        s = max(free, key=lambda w: (w[1], w[0]))
        n = min(free, key=lambda w: (w[1], w[0]))
    dump(data, "end")
    print("done", flush=True)


if __name__ == "__main__":
    main()
