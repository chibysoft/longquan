"""Dense exit scan after prevac15 (42,50)+east15 south; also no-N438 pose."""
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
        f"{label} ship14={me['c']} d14={d14} free={sorted(free)} "
        f"ship15={me15['c']} d15={d15} fr15={sorted(fr15)} bud={step_budget(data['frame'])}",
        flush=True,
    )
    return d14


def setup(sess, east_tgt=(58, 50), west_tgt=(42, 50)):
    data = reset(sess)
    data, _ = clear_l1(sess, data)
    data, _ = clear_l2(sess, data)
    lv0 = data.get("levels_completed") or 0
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _ = clear15_corridor(sess, data, freeze14)
    data, _ = advance_14_mid_east(sess, data, lv0, do_clear15=False)
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    east = max(fr15, key=lambda w: w[0])
    west = min(fr15, key=lambda w: w[0])
    # east first deeper
    data, newc, st = move_wp(sess, data, east, east_tgt, freeze14)
    print(f"east15 {east}->{east_tgt} {st}->{newc}", flush=True)
    if st == "dead":
        return data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    flock = list(lock_other_ship(data["frame"], 14))
    west = min(flock, key=lambda w: w[0])
    east = max(flock, key=lambda w: w[0])
    if cheb(west_tgt, east) >= 5 and not near_any(west_tgt, list(freeze14), cheb=5):
        data, newc, st = move_wp(sess, data, west, west_tgt, freeze14)
        print(f"west15 {west}->{west_tgt} {st}->{newc}", flush=True)
        if st == "dead":
            return data, False
    return data, True


def frog(sess, data, do_n438=True):
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, lag, (lag[0] + 2, lead[1] + 4), fr15)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    n = min(free, key=lambda w: (w[1], w[0]))
    data, _, st = move_wp(sess, data, n, (40, 36), fr15)
    if st != "moved":
        return data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    s = max(free, key=lambda w: (w[1], w[0]))
    if not near_any((40, 44), list(fr15), cheb=5) and cheb((40, 44), min(free, key=lambda w: (w[1], w[0]))) >= 5:
        data, _, st = move_wp(sess, data, s, (40, 44), fr15)
        if st == "dead":
            return data, False
    if do_n438:
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        n = min(free, key=lambda w: (w[1], w[0]))
        s = max(free, key=lambda w: (w[1], w[0]))
        for tgt in ((43, 38), (43, 36)):
            if near_any(tgt, list(fr15), cheb=5) or cheb(tgt, s) < 5:
                continue
            data, _, st = move_wp(sess, data, n, tgt, fr15)
            if st == "dead":
                return data, False
            if st == "moved":
                break
    return data, True


def grid_cands(n, s):
    out = []
    # N ring / SE / south
    for dx in range(-2, 8):
        for dy in range(-2, 8):
            if dx == 0 and dy == 0:
                continue
            ld = (n[0] + dx, n[1] + dy)
            if 0 <= ld[0] < 64 and 0 <= ld[1] < 64:
                out.append(("N", n, ld))
    for dx in range(-6, 6):
        for dy in range(-2, 8):
            if dx == 0 and dy == 0:
                continue
            ld = (s[0] + dx, s[1] + dy)
            if 0 <= ld[0] < 64 and 0 <= ld[1] < 64:
                out.append(("S", s, ld))
    # prefer SE-ish for N, south/east for S
    def score(item):
        tag, cur, ld = item
        return -(ld[0] + ld[1] * 0.5) if tag == "N" else -(ld[1] + ld[0] * 0.3)

    out.sort(key=score)
    # unique ld
    seen = set()
    uniq = []
    for item in out:
        if item[2] in seen:
            continue
        seen.add(item[2])
        uniq.append(item)
    return uniq


def scan_batch(sess, data, max_tries=12):
    """Try up to max_tries live moves; return on any moved that improves or equals d14."""
    d0 = dump(data, "scan-start")
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    if len(free) != 2:
        return data, False
    s = max(free, key=lambda w: (w[1], w[0]))
    n = min(free, key=lambda w: (w[1], w[0]))
    ban = {
        (42, 40),
        (42, 42),
        (42, 45),
        (42, 46),
        (41, 44),
        (42, 44),
        (43, 44),
        (43, 40),
        (43, 42),
    }
    tries = 0
    for tag, cur, ld in grid_cands(n, s):
        if tries >= max_tries or step_budget(data["frame"]) < 4:
            break
        if ld in ban or ld == cur:
            continue
        other = s if cur == n else n
        if cheb(ld, other) < 5:
            continue
        if near_any(ld, list(fr15), cheb=5):
            continue
        if ld[1] <= 36 and ld[0] >= 45:
            continue
        # skip known-worsening west S unless we want map
        if tag == "S" and ld[0] < 38 and ld[1] == 44:
            continue
        data, newc, st = move_wp(sess, data, cur, ld, fr15)
        tries += 1
        me = next(z for z in ships(data["frame"]) if z["chrome"] == 14)
        d14 = abs(me["c"][0] - 55) + abs(me["c"][1] - 53)
        print(
            f"  {tag} {cur}->{ld} {st}->{newc} ship={me['c']} d14={d14}({d14-d0:+d}) "
            f"bud={step_budget(data['frame'])}",
            flush=True,
        )
        if st == "dead" or data.get("state") == "GAME_OVER":
            print("DEAD", flush=True)
            return data, False
        if st == "moved":
            dump(data, "HIT")
            if d14 < d0:
                print("IMPROVED", flush=True)
                return data, True
            print("moved-no-improve", flush=True)
            return data, True  # still useful geometry
        # refresh
        fr15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], fr15)
        if len(free) != 2:
            break
        s = max(free, key=lambda w: (w[1], w[0]))
        n = min(free, key=lambda w: (w[1], w[0]))
    return data, False


def run_variant(name, east_tgt, west_tgt, do_n438, max_tries=14):
    print(f"\n===== {name} e={east_tgt} w={west_tgt} n438={do_n438} =====", flush=True)
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": [f"r11l_{name}"]},
        timeout=90,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"
    data, ok = setup(sess, east_tgt, west_tgt)
    if not ok:
        print("setupfail", flush=True)
        return False
    data, ok = frog(sess, data, do_n438=do_n438)
    if not ok:
        print("frogfail", flush=True)
        return False
    data, hit = scan_batch(sess, data, max_tries=max_tries)
    return hit


def main():
    variants = [
        ("e5850_w4250_n", (58, 50), (42, 50), True),
        ("e5850_w4250_noN", (58, 50), (42, 50), False),
        ("e5852_w4650_n", (58, 52), (46, 50), True),
        ("e5648_w4250_n", (56, 48), (42, 50), True),
        ("e5850_w4848_n", (58, 50), (48, 48), True),
        ("e5252_w4052_n", (52, 52), (40, 52), True),
    ]
    for name, e, w, n438 in variants:
        hit = run_variant(name, e, w, n438)
        if hit:
            print("SUCCESS", name, flush=True)
            # keep going to map more? stop on first improve path
            # return
    print("all done", flush=True)


if __name__ == "__main__":
    main()
