"""From deep15 + Y40 pose: dense SE/east exits better than frog.

Boot: mid-east → deep15(4250+5850) → leadS+4 → catch → free≈(24,40)+(33,40) bud≈16.
Scan lead/lag hops; report IMPROVED if d14 decreases with n=2.
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
    return d14, free, fr15, me["c"]


def boot_y40():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_y40x"]},
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
    # deep15
    freeze14 = lock_other_ship(data["frame"], 15)
    fr15 = list(lock_other_ship(data["frame"], 14))
    data, _, st = move_wp(sess, data, max(fr15, key=lambda w: w[0]), (58, 42), freeze14)
    if st == "dead":
        return sess, data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, st = move_wp(
        sess, data, min(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (42, 50), freeze14
    )
    if st == "dead":
        return sess, data, False
    freeze14 = lock_other_ship(data["frame"], 15)
    data, _, st = move_wp(
        sess, data, max(lock_other_ship(data["frame"], 14), key=lambda w: w[0]), (58, 50), freeze14
    )
    if st == "dead":
        return sess, data, False
    # leadS + catch
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: w[0])
    data, _, st = move_wp(sess, data, lead, (lead[0], lead[1] + 4), fr15)
    if st != "moved":
        print(f"leadS {st}", flush=True)
        return sess, data, False
    fr15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], fr15)
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    caught = False
    for gd in ((lag[0] + 2, lead[1]), (lag[0] + 4, lead[1]), (lead[0] - 6, lead[1])):
        if cheb(gd, lead) < 5:
            continue
        if near_any(gd, list(fr15), cheb=5):
            continue
        data, _, st = move_wp(sess, data, lag, gd, fr15)
        print(f"catch {lag}->{gd} {st}", flush=True)
        if st == "moved":
            caught = True
            break
        if st == "dead":
            return sess, data, False
    if not caught:
        return sess, data, False
    dump(data, "Y40")
    return sess, data, True


# Candidate offsets from lead / lag
LEAD_TGTS = []
for dx in range(2, 16):
    for dy in range(-2, 10):
        if dx + abs(dy) < 2:
            continue
        if dy < 0 and dx < 4:
            continue
        LEAD_TGTS.append((dx, dy))
# Prefer SE
LEAD_TGTS.sort(key=lambda t: (t[0] + t[1], -t[1], t[0]))

LAG_TGTS = []
for dx in range(0, 14):
    for dy in range(0, 10):
        if dx + dy < 2:
            continue
        LAG_TGTS.append((dx, dy))


def try_one(from_wp, tgt, other, fr15):
    if cheb(tgt, other) < 5:
        return "merge"
    if near_any(tgt, list(fr15), cheb=5):
        return "near15"
    if cheb(from_wp, tgt) < 2:
        return "tiny"
    return "ok"


def main():
    hits = []
    # Scan lead exits first (fresh boot per batch of ~8 to save time — actually
    # each live move mutates; must reboot each trial).
    cands = []
    # Hand-picked priority + denser SE grid
    for x in range(35, 52, 1):
        for y in (40, 42, 44, 46, 48):
            cands.append(("L", (x, y)))
    for x in range(28, 48, 2):
        for y in (42, 44, 46, 48):
            cands.append(("G", (x, y)))  # lag

    # Dedup preserve order
    seen = set()
    uniq = []
    for who, tgt in cands:
        k = (who, tgt)
        if k in seen:
            continue
        seen.add(k)
        uniq.append((who, tgt))

    print(f"scan {len(uniq)} cands", flush=True)
    for i, (who, tgt) in enumerate(uniq):
        sess, data, ok = boot_y40()
        if not ok or data.get("state") == "GAME_OVER":
            print(f"boot fail @{i}", flush=True)
            continue
        d0, free, fr15, ship = dump(data, "base")
        if len(free) != 2:
            continue
        lead = max(free, key=lambda w: w[0])
        lag = min(free, key=lambda w: w[0])
        cur = lead if who == "L" else lag
        other = lag if who == "L" else lead
        reason = try_one(cur, tgt, other, fr15)
        if reason != "ok":
            print(f"--- {who} {cur}->{tgt} skip {reason} ---", flush=True)
            continue
        print(f"--- {who} {cur}->{tgt} ---", flush=True)
        data, newc, st = move_wp(sess, data, cur, tgt, fr15)
        if st == "dead" or data.get("state") == "GAME_OVER":
            print(f"DEAD {st}", flush=True)
            continue
        if st != "moved":
            print(f"{st}", flush=True)
            continue
        d1, free1, fr151, ship1 = dump(data, "HIT")
        if len(free1) != 2:
            print(f"FLOCK n={len(free1)}", flush=True)
            continue
        if d1 < d0:
            print(
                f"IMPROVED {who} {cur}->{newc} d14 {d0}->{d1} "
                f"bud={step_budget(data['frame'])} ship={ship1}",
                flush=True,
            )
            hits.append((who, cur, newc, d0, d1, step_budget(data["frame"]), ship1, free1))
            # one follow-up hop from improved pose
            lead2 = max(free1, key=lambda w: w[0])
            lag2 = min(free1, key=lambda w: w[0])
            for who2, src, tgts in (
                ("L2", lead2, [(lead2[0] + d, lead2[1] + e) for d in (2, 4, 6, 8) for e in (0, 2, 4)]),
                ("G2", lag2, [(lag2[0] + d, lag2[1] + e) for d in (2, 4, 6) for e in (0, 2, 4)]),
            ):
                for t2 in tgts:
                    o2 = lag2 if who2.startswith("L") else lead2
                    if try_one(src, t2, o2, fr151) != "ok":
                        continue
                    data2, nc2, st2 = move_wp(sess, data, src, t2, fr151)
                    if st2 == "moved" and "frame" in data2:
                        d2, free2, _, ship2 = dump(data2, f"hop2")
                        if len(free2) == 2 and d2 < d1:
                            print(
                                f"HOP2 {who2} {src}->{nc2} d14 {d1}->{d2} "
                                f"bud={step_budget(data2['frame'])}",
                                flush=True,
                            )
                            hits.append(
                                (who2, src, nc2, d1, d2, step_budget(data2["frame"]), ship2, free2)
                            )
                            data = data2
                            d1 = d2
                            free1 = free2
                            fr151 = lock_other_ship(data["frame"], 14)
                            lead2 = max(free1, key=lambda w: w[0])
                            lag2 = min(free1, key=lambda w: w[0])
                        break
                    if st2 == "dead" or data2.get("state") == "GAME_OVER":
                        break
                else:
                    continue
                break

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)
    if not hits:
        print("no improve from Y40", flush=True)


if __name__ == "__main__":
    main()
