"""From d15=4 pose: try (33,56)→(34,57) and related 1-step goal docks."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import clear_l2, move_wp, step_budget
from tools.r11l_l2_probe import ships
from tools.r11l_l3_2wp_probe import advance_14_mid_east
from tools.r11l_l3_sync_probe import clear15_corridor, lock_other_ship, near_any
from tools.r11l_seated_clear import clear_l1, reset
from tools._l3_savebud_probe import deep15, se_to_n6038, do_s6048, do_fin15, dump

GOAL14, GOAL15 = (55, 53), (34, 57)


def boot(do_s60=True):
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_dock15"]},
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
    data, ok = deep15(sess, data, do_east15b=False, early_tgt=(40, 56))
    if not ok:
        return sess, data, False
    data, ok = se_to_n6038(sess, data)
    if not ok:
        return sess, data, False
    if do_s60:
        data, ok = do_s6048(sess, data)
        if not ok:
            return sess, data, False
    data, _ = do_fin15(sess, data)
    dump(data, "base")
    return sess, data, True


# Explicit (src, tgt) pairs — allow cheb=1
CANDS = [
    ((33, 56), (34, 57)),
    ((33, 56), (34, 56)),
    ((33, 56), (32, 57)),
    ((33, 56), (33, 57)),
    ((33, 56), (35, 57)),
    ((41, 56), (41, 57)),
    ((41, 56), (40, 57)),
    ((41, 56), (37, 57)),
    ((41, 56), (34, 57)),  # may merge
    ((41, 56), (45, 56)),
    ((41, 56), (48, 56)),
    ((33, 56), (28, 56)),
    ((33, 56), (30, 56)),
]


def main():
    hits = []
    for do_s60 in (True, False):
        print(f"\n##### s60={do_s60} #####", flush=True)
        for src, tgt in CANDS:
            sess, data, ok = boot(do_s60=do_s60)
            if not ok:
                print("boot fail", flush=True)
                continue
            fr15 = list(lock_other_ship(data["frame"], 14))
            # map src to nearest live pad
            if not fr15:
                continue
            cur = min(fr15, key=lambda w: abs(w[0] - src[0]) + abs(w[1] - src[1]))
            other = next((w for w in fr15 if w != cur), cur)
            freeze14 = lock_other_ship(data["frame"], 15)
            if max(abs(tgt[0] - other[0]), abs(tgt[1] - other[1])) < 5:
                print(f"  skip {cur}->{tgt} merge other={other}", flush=True)
                continue
            if near_any(tgt, list(freeze14), cheb=5):
                print(f"  skip {cur}->{tgt} near14", flush=True)
                continue
            if cur == tgt:
                continue
            data, newc, st = move_wp(sess, data, cur, tgt, freeze14)
            print(
                f"  {cur}->{tgt} {st}->{newc} bud={step_budget(data['frame']) if 'frame' in data else '?'}",
                flush=True,
            )
            if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                print("DEAD", flush=True)
                continue
            if st != "moved":
                continue
            me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
            d14 = abs(me14["c"][0] - GOAL14[0]) + abs(me14["c"][1] - GOAL14[1])
            d15 = abs(me15["c"][0] - GOAL15[0]) + abs(me15["c"][1] - GOAL15[1])
            tags = []
            if d15 < 4:
                tags.append(f"BEAT15:{d15}")
            if d15 == 0:
                tags.append("D15CLEAR")
            if d14 < 25:
                tags.append(f"BEAT14:{d14}")
            if (data.get("levels_completed") or 0) >= 3:
                tags.append("PASS")
            dump(data, f"hit-{tgt}")
            print(f"RESULT {' '.join(tags) or 'LIVE'} {cur}->{tgt} d14={d14} d15={d15}", flush=True)
            hits.append((do_s60, cur, tgt, tags, d14, d15, step_budget(data["frame"])))

    print("\n===== HITS =====", flush=True)
    for h in hits:
        print(h, flush=True)


if __name__ == "__main__":
    main()
