"""r11l L3 minimal probe: 2wp long-stride without GAME_OVER.

Scope (deliberately narrow):
  - Reuse seated L1/L2 + early clear15 + classic west hop1 only.
  - At west wall, lean-south into corridor, collapse/merge to exactly 2wp.
  - East only via SAME-DELTA formation translate (no lead-only race).
  - Hard gates: ship y>=34, both wps y>=34, sep cheb>=5, footprint+path_ok.
  - Stop on first noop / GAME_OVER.

Success (single gate):
  ship x>=28 and y>=34, free14==2, bud>=28, state!=GAME_OVER.

Usage:
  python tools/r11l_l3_2wp_probe.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import r11l
from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import (
    clear_l2,
    floor_bfs,
    goals_by_chrome,
    move_wp,
    near_any,
    step_budget,
)
from tools.r11l_l2_core import (
    centroid,
    centroid_path_ok,
    ship_footprint_ok,
    _plane,
)
from tools.r11l_l2_probe import ships
from tools.r11l_l3_sync_probe import (
    clear15_corridor,
    count_free14,
    leap14_once,
    lock_other_ship,
    reshape_to_pads,
    pads_at,
)
from tools.r11l_seated_clear import clear_l1, reset


def snap(data, freeze15, tag=""):
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    cur = count_free14(data["frame"], freeze15)
    bud = step_budget(data["frame"])
    gmap = goals_by_chrome(data["frame"])
    d14 = abs(me["c"][0] - gmap[14][0]) + abs(me["c"][1] - gmap[14][1])
    print(
        f"  [{tag}] ship={me['c']} free14={cur} n={len(cur)} "
        f"d14={d14} bud={bud} state={data.get('state')}"
    )
    return {
        "ship": me["c"],
        "free14": list(cur),
        "n": len(cur),
        "d14": d14,
        "bud": bud,
        "state": data.get("state"),
    }


def success_gate(info) -> bool:
    sx, sy = info["ship"]
    return (
        info["state"] != "GAME_OVER"
        and info["n"] == 2
        and sx >= 28
        and sy >= 34
        and info["bud"] >= 28
    )


def ensure_y34(sess, data, freeze15):
    """Lift shallow free14 into y>=34; on noop try merge-into-keeper instead."""
    g = _plane(data["frame"])
    blacklist = set()
    for _ in range(6):
        me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        cur = count_free14(data["frame"], freeze15)
        low = sorted([w for w in cur if w[1] < 34], key=lambda w: w[1])
        if me["c"][1] >= 34 and not low:
            return data, True
        if step_budget(data["frame"]) < 8:
            return data, False
        # NEVER "lift" an already-corridor wp — that noop-spammed to GAME_OVER.
        if not low:
            print(f"  lift: no shallow left ship={me['c']} cur={cur}")
            return data, me["c"][1] >= 33
        targets = low[:1]  # one shallow at a time
        moved = False
        for wp in targets:
            others = [c for c in cur if c != wp]
            keepers = [c for c in others if c[1] >= 34]
            cands = []
            # Lift destinations.
            for t in (
                (wp[0], 34),
                (wp[0], 35),
                (wp[0] + 2, 34),
                (wp[0] + 4, 34),
                (wp[0] - 2, 34),
                (wp[0] + 6, 34),
                (24, 34),
                (28, 34),
                (20, 36),
            ):
                cands.append(("lift", t))
            # Merge into nearest corridor keeper (cheb=3) if lift blocked.
            for k in keepers:
                dx = 0 if k[0] == wp[0] else (1 if k[0] > wp[0] else -1)
                dy = 0 if k[1] == wp[1] else (1 if k[1] > wp[1] else -1)
                dest = wp
                for __ in range(8):
                    if max(abs(k[0] - dest[0]), abs(k[1] - dest[1])) <= 3:
                        break
                    nxt = (dest[0] + dx, dest[1] + dy)
                    if not (0 <= nxt[0] < 64 and 0 <= nxt[1] < 64):
                        break
                    if int(g[nxt[1], nxt[0]]) in (2, 10):
                        break
                    dest = nxt
                if dest != wp and dest[1] >= 32:
                    cands.append(("merge", dest))
            for kind, t in cands:
                if (wp, t) in blacklist:
                    continue
                if not (0 <= t[0] < 64 and 0 <= t[1] < 64) or t == wp:
                    continue
                if kind == "lift" and t[1] < 34:
                    continue
                if int(g[t[1], t[0]]) not in (5, 3, 0, 6):
                    continue
                if near_any(t, others + freeze15, cheb=5) and kind == "lift":
                    continue
                # merge intentionally enters cheb<=3 of keeper
                if kind == "merge" and near_any(t, [c for c in others if c not in keepers] + freeze15, cheb=5):
                    continue
                trial = [t if c == wp else c for c in cur]
                tc = centroid(trial)
                tci = (int(round(tc[0])), int(round(tc[1])))
                if not ship_footprint_ok(g, *tci):
                    continue
                data, newc, st = move_wp(sess, data, wp, t, freeze15)
                print(
                    f"  {kind} {wp}->{t} {st}->{newc} "
                    f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                )
                if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                    return data, False
                if st != "moved":
                    blacklist.add((wp, t))
                    continue
                g = _plane(data["frame"])
                # One successful lift/merge per call — looping burned bud to GO.
                me2 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
                cur2 = count_free14(data["frame"], freeze15)
                return data, me2["c"][1] >= 33 and (
                    all(w[1] >= 34 for w in cur2) or len([w for w in cur2 if w[1] < 34]) <= 1
                )
            if moved:
                break
        if not moved:
            print("  lift/merge: stuck", cur, "ship", me["c"])
            # Accept if ship already on corridor and only 1 shallow left to merge next phase.
            return data, me["c"][1] >= 33 and len(low) <= 1
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    cur = count_free14(data["frame"], freeze15)
    return data, me["c"][1] >= 34 and all(w[1] >= 34 for w in cur)

def neck_slide14(sess, data, freeze15):
    """Pull ship onto west neck (x<=19) by sliding an eastern corridor wp west.

    Needed when 2 corridor plants left ship at ~(20,26): any south merge then
    puts the centroid through the y~29–33 hazard band.
    """
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    if me["c"][0] <= 19 and me["c"][1] >= 28:
        return data, True
    if step_budget(data["frame"]) < 10:
        return data, False
    cur = count_free14(data["frame"], freeze15)
    cor = [w for w in cur if w[1] >= 34]
    if len(cor) < 1:
        return data, False
    g = _plane(data["frame"])
    # Prefer western corridor wp to slide further west (eastern one stays as east keeper).
    lead = min(cor, key=lambda w: w[0])
    others = [c for c in cur if c != lead]
    for dest in (
        (14, lead[1]),
        (15, lead[1]),
        (16, lead[1]),
        (14, 36),
        (16, 36),
        (14, 34),
        (16, 34),
        (lead[0] - 4, lead[1]),
        (lead[0] - 6, 34),
    ):
        if dest[0] < 14 or dest[1] < 34 or dest == lead:
            continue
        if not (0 <= dest[0] < 64 and 0 <= dest[1] < 64):
            continue
        if int(g[dest[1], dest[0]]) not in (5, 3, 0, 6):
            continue
        if near_any(dest, others + freeze15, cheb=5):
            continue
        trial = [dest if c == lead else c for c in cur]
        tc = centroid(trial)
        tci = (int(round(tc[0])), int(round(tc[1])))
        if not ship_footprint_ok(g, *tci):
            continue
        data, newc, st = move_wp(sess, data, lead, dest, freeze15)
        print(
            f"  neck-slide {lead}->{dest} {st}->{newc} "
            f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if st == "moved":
            me2 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            return data, me2["c"][0] <= 20
    print("  neck-slide no-move", cur, "ship", me["c"])
    return data, False


def collapse_to_2(sess, data, freeze15):
    """Merge free14 down to 2 by walking western into eastern (cheb<=3)."""
    cur = count_free14(data["frame"], freeze15)
    if len(cur) <= 2:
        return data, True
    if step_budget(data["frame"]) < 12:
        return data, False
    g = _plane(data["frame"])
    # Keepers must already be on corridor y>=34 — never keep a shallow wp.
    corridor = [w for w in cur if w[1] >= 34]
    if len(corridor) < 2:
        print(f"  collapse promote corridor={corridor}")
        shallow = sorted([w for w in cur if w[1] < 34], key=lambda w: -w[1])
        for wp in shallow[:3]:
            others = [c for c in count_free14(data["frame"], freeze15) if c != wp]
            promoted = False
            for dest in ((24, 36), (21, 36), (27, 36), (30, 36), (18, 36)):
                if dest[0] <= 16 or dest[1] < 34:
                    continue
                if near_any(dest, others + freeze15, cheb=5):
                    continue
                # Direct ACTION6 — floor_bfs dies in hazard mid-band.
                nxt = dest
                data, newc, st = move_wp(sess, data, wp, nxt, freeze15)
                print(
                    f"    promote {wp}->{nxt} {st}->{newc} "
                    f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                )
                if st == "dead" or data.get("state") == "GAME_OVER":
                    print("    promote dead — abort")
                    return data, False
                if st == "moved":
                    g = _plane(data["frame"])
                    promoted = True
                    break
            cur = count_free14(data["frame"], freeze15)
            corridor = [w for w in cur if w[1] >= 34]
            if len(corridor) >= 2:
                break
            if not promoted:
                continue
        if len(corridor) < 2:
            print(f"  collapse need >=2 corridor, got {corridor}")
            return data, False
    # Two eastern corridor keepers with cheb>=5; never keep wrap-column (x<=16).
    corridor_e = [w for w in corridor if w[0] > 16] or list(corridor)
    corridor_sorted = sorted(corridor_e, key=lambda w: (-w[0], -w[1]))
    keepers = []
    for w in corridor_sorted:
        if not keepers:
            keepers.append(w)
            continue
        if max(abs(w[0] - keepers[0][0]), abs(w[1] - keepers[0][1])) >= 5:
            keepers.append(w)
            break
    if len(keepers) < 2 and len(corridor_sorted) >= 2:
        keepers = corridor_sorted[:2]
    # Mid-band shallow first (v16: (19,14) then (16,22)); wrap-col last.
    stragglers = sorted(
        [w for w in cur if w not in keepers],
        key=lambda w: (0 if (w[1] < 34 and w[0] > 16) else 1, 0 if w[1] < 34 else 1, -w[1], w[0]),
    )
    print(f"  collapse keepers={keepers} stragglers={stragglers}")
    for wp in stragglers:
        if len(count_free14(data["frame"], freeze15)) <= 2:
            break
        if step_budget(data["frame"]) < 8:
            break
        cur_now = count_free14(data["frame"], freeze15)
        if wp not in cur_now:
            continue
        # Only corridor keepers — shallow straggler must walk around hazard.
        ks = [c for c in cur_now if c[1] >= 34]
        if not ks:
            continue
        # Always absorb toward EASTERNMOST corridor keeper (v16).
        k = max(ks, key=lambda p: (p[0], p[1]))
        if wp[0] <= 16:
            east = [c for c in ks if c[0] >= 20]
            if east:
                k = max(east, key=lambda p: p[0])

        # Phase order for shallow north of hazard:
        #   A) sync-style walk ≤6 toward keeper (safer footprint than one long jump)
        #   B) direct ACTION6 onto corridor cheb==3 of keeper
        #   C) west-wrap ONLY if <2 corridor keepers (wrap previously ate keepers)
        dx = 0 if k[0] == wp[0] else (1 if k[0] > wp[0] else -1)
        dy = 0 if k[1] == wp[1] else (1 if k[1] > wp[1] else -1)
        step_dest = wp
        for _ in range(6):
            nxts = (step_dest[0] + dx, step_dest[1] + dy)
            if not (0 <= nxts[0] < 64 and 0 <= nxts[1] < 64):
                break
            if int(g[nxts[1], nxts[0]]) in (2, 10):
                break
            if max(abs(k[0] - nxts[0]), abs(k[1] - nxts[1])) < 3:
                break
            step_dest = nxts
            if max(abs(k[0] - step_dest[0]), abs(k[1] - step_dest[1])) <= 3:
                break
        walk_pads = [step_dest] if step_dest != wp else []
        # Proven v16 order: (21,36) then (27,36).
        direct_pads = [
            (21, 36),
            (27, 36),
            (k[0] + 3, 36),
            (k[0] - 3, 36) if k[0] - 3 > 16 else (k[0] + 3, 36),
            (24, 36),
            (30, 36),
        ]
        wrap_pads = [(14, 24), (13, 24), (12, 24), (14, 25), (13, 25)]
        south_pads = [
            (14, 28),
            (14, 32),
            (k[0] + 3, 34),
            (20, 34),
            (22, 34),
            (24, 34),
        ]
        have_corridor_keepers = len(ks) >= 2
        me_y0 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)["c"][1]
        if wp[1] < 34 and wp[0] > 14:
            # East-shifted pads (v65): aim post-collapse ship x≥24.
            phases = [("direct", [(23, 36), (29, 36), (21, 36), (27, 36), (24, 36)])]
        elif wp[1] < 34 and wp[0] <= 14:
            # Never west-wrap when keepers exist (v45 ate corridor). One-shot direct only.
            if have_corridor_keepers:
                phases = [("direct", [(23, 36), (29, 36), (21, 36), (27, 36), (24, 36)])]
            elif me_y0 < 34:
                phases = [("wrap", [(14, 24), (13, 24), (14, 25)])]
            else:
                phases = [("direct", direct_pads)]
        else:
            # Corridor extra (incl. wrap-col y>=34): step east then merge.
            if wp[0] <= 16:
                phases = [("direct", [
                    (18, 36),
                    (20, 36),
                    (21, 36),
                    (22, 36),
                    (24, 36),
                    (k[0] - 3, 36) if k[0] - 3 > 16 else (21, 36),
                    (k[0] + 3, 36),
                ])]
            else:
                phases = [("direct", [
                    (k[0] + 3, 36),
                    (k[0] - 3, 36) if k[0] - 3 > 16 else (k[0] + 3, 38),
                    (k[0] + 3, 38),
                    (k[0] - 3, 38) if k[0] - 3 > 16 else (k[0] + 3, 36),
                ])]

        moved_one = False
        tried = set()
        for phase, pads in phases:
            for pad in pads:
                if not (0 <= pad[0] < 64 and 0 <= pad[1] < 64) or pad == wp:
                    continue
                if phase == "wrap":
                    nxt = pad
                elif phase == "south" and pad[1] < 34:
                    if not (28 <= pad[1] < 34 and pad[0] <= 14):
                        continue
                    nxt = pad
                elif phase == "walk":
                    nxt = pad
                else:
                    if pad[1] < 34 or pad[0] <= 16:
                        continue
                    nxt = pad
                cheb_k = max(abs(nxt[0] - k[0]), abs(nxt[1] - k[1]))
                if phase == "direct" and (nxt == k or cheb_k < 3 or cheb_k > 4):
                    rewritten = False
                    for alt in (
                        (k[0] + 3, 36),
                        (k[0] - 3, 36) if k[0] - 3 > 16 else (k[0] + 3, 38),
                        (k[0] + 3, 38),
                        (k[0] - 3, 38) if k[0] - 3 > 16 else (k[0] + 3, 36),
                    ):
                        if alt[1] < 34 or not (0 <= alt[0] < 64) or alt == wp:
                            continue
                        if alt[0] <= 16:
                            continue
                        if max(abs(alt[0] - k[0]), abs(alt[1] - k[1])) != 3:
                            continue
                        if near_any(alt, freeze15, cheb=5):
                            continue
                        others_x = [c for c in cur_now if c != wp and c != k]
                        if near_any(alt, others_x, cheb=3):
                            continue
                        nxt = alt
                        rewritten = True
                        break
                    if not rewritten:
                        print(f"    collapse skip pad{pad} cannot approach {k}")
                        continue
                if phase == "wrap" and wp[0] > 14 and nxt[0] >= wp[0]:
                    continue
                if phase == "wrap" and wp[0] <= 14 and nxt[1] <= wp[1]:
                    continue  # on wrap col: must go south
                if phase == "walk" and nxt[1] < wp[1] and nxt[0] <= wp[0]:
                    continue
                if phase != "wrap" and near_any(nxt, freeze15, cheb=5):
                    print(f"    collapse skip pad{pad} nxt{nxt} near freeze")
                    continue
                if phase == "direct" and nxt[0] <= 16:
                    continue
                if nxt in tried:
                    continue
                tried.add(nxt)
                trial = [nxt if c == wp else c for c in cur_now]
                tc = centroid(trial)
                tci = (int(round(tc[0])), int(round(tc[1])))
                me_y = next(s for s in ships(data["frame"]) if s["chrome"] == 14)["c"][1]
                # Prefer y>=36 when ship still north (y=34 edge is dead-prone).
                if phase == "direct" and me_y < 34 and nxt[1] < 36:
                    continue
                if phase != "wrap" and me_y >= 34 and not ship_footprint_ok(g, *tci):
                    print(f"    collapse skip pad{pad} nxt{nxt} footprint {tci}")
                    continue
                data, newc, st = move_wp(sess, data, wp, nxt, freeze15)
                print(
                    f"    collapse-{phase} {wp}->{nxt} (→{k}) {st}->{newc} "
                    f"n={len(count_free14(data['frame'], freeze15)) if 'frame' in data else '?'} "
                    f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                )
                if data.get("state") == "GAME_OVER" or "frame" not in data:
                    return data, False
                if st == "dead":
                    print(f"    collapse dead pad — stop this wp")
                    break
                if st == "occupied" or st == "noop":
                    continue
                if st != "moved":
                    continue
                g = _plane(data["frame"])
                moved_one = True
                break
            if moved_one:
                break
        if not moved_one:
            print(f"    collapse no-path {wp} toward {k}")
            continue
    cur = count_free14(data["frame"], freeze15)
    print(f"  collapse end n={len(cur)} cur={cur}")
    return data, len(cur) == 2



def _translate_dest_ok(g, cur, wp, dest, others, freeze15, me, *, close_gap=False):
    if dest[1] < 34 or not (0 <= dest[0] < 64):
        return False
    if dest == wp or dest[0] <= wp[0]:
        return False
    if max(abs(dest[0] - me[0]), abs(dest[1] - me[1])) < 3:
        return False
    # Lag must finish east of ship when ship sits between flock.
    if others and wp[0] < me[0] < max(others, key=lambda p: p[0])[0]:
        if dest[0] < me[0] + 2:
            return False
    if close_gap:
        # Allow cheb 3–4 to lead (still off-sprite); full cheb5 blocks all pairs.
        if any(max(abs(dest[0] - o[0]), abs(dest[1] - o[1])) < 3 for o in others):
            return False
        if near_any(dest, list(freeze15), cheb=5):
            return False
    else:
        if near_any(dest, list(others) + list(freeze15), cheb=5):
            return False
    return True


def lag_haul_east(sess, data, freeze15):
    """Y-lift lag then east on offset row — same-row east hits ship (noop); diagonal merges lead."""
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    cur = count_free14(data["frame"], freeze15)
    if len(cur) != 2 or me["c"][1] < 34:
        return data, False
    if me["c"][0] < 24 or me["c"][0] >= 28 or step_budget(data["frame"]) < 28:
        return data, False
    lead = max(cur, key=lambda w: (w[0], w[1]))
    lag = min(cur, key=lambda w: (w[0], w[1]))
    me_c = me["c"]

    def _ship():
        return next(s for s in ships(data["frame"]) if s["chrome"] == 14)["c"]

    def _n():
        return len(count_free14(data["frame"], freeze15))

    def _bud():
        return step_budget(data["frame"])

    # 1) pure y-lift (same x) — open a lane around the ship
    if lag[1] == me_c[1]:
        lifted = False
        for ly in (38, 34):
            gd = (lag[0], ly)
            if max(abs(gd[0] - me_c[0]), abs(gd[1] - me_c[1])) < 2:
                continue
            if near_any(gd, [lead] + list(freeze15), cheb=5):
                continue
            data, newc, st = move_wp(sess, data, lag, gd, freeze15)
            print(
                f"  lag-haul ylift {lag}->{gd} {st}->{newc} "
                f"ship={_ship() if 'frame' in data else '?'} "
                f"n={_n() if 'frame' in data else '?'} "
                f"bud={_bud() if 'frame' in data else '?'}"
            )
            if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                return data, False
            if st != "moved":
                continue
            if _n() != 2:
                print("  lag-haul ylift flock broke")
                return data, False
            lag = newc
            me_c = _ship()
            cur = count_free14(data["frame"], freeze15)
            lead = max(cur, key=lambda w: (w[0], w[1]))
            lifted = True
            break
        if not lifted:
            print("  lag-haul ylift failed")
            return data, False

    # 2) east on offset row; cheb_lead>=6 to avoid merge into lead
    cur = count_free14(data["frame"], freeze15)
    lead = max(cur, key=lambda w: (w[0], w[1]))
    lag = min(cur, key=lambda w: (w[0], w[1]))
    me_c = _ship()
    cands = []
    for x in range(lag[0] + 3, lead[0] - 5):
        dest = (x, lag[1])
        cheb = max(abs(dest[0] - lead[0]), abs(dest[1] - lead[1]))
        if cheb < 6 or cheb > 10:
            continue
        fx = (dest[0] + lead[0]) / 2.0
        if fx < 27.5:
            continue
        if max(abs(dest[0] - me_c[0]), abs(dest[1] - me_c[1])) < 2:
            continue
        if near_any(dest, list(freeze15), cheb=5):
            continue
        cands.append((fx, dest))
    cands.sort(reverse=True)
    print(f"  lag-haul east-cands={cands[:5]}")
    for fx, dest in cands[:4]:
        data, newc, st = move_wp(sess, data, lag, dest, freeze15)
        print(
            f"  lag-haul east {lag}->{dest} {st}->{newc} "
            f"ship={_ship() if 'frame' in data else '?'} "
            f"n={_n() if 'frame' in data else '?'} "
            f"bud={_bud() if 'frame' in data else '?'}"
        )
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if st != "moved":
            print("  lag-haul east noop — stop (save bud)")
            return data, False
        if _n() != 2:
            print("  lag-haul east flock broke")
            return data, False
        if newc == lead or near_any(newc, [lead], cheb=3):
            print(f"  lag-haul merged into lead {newc}")
            return data, False
        return data, True
    print("  lag-haul no east dest")
    return data, False


def finish_nudge2(sess, data, freeze15):
    """Last dual hop when ship already mid-east: lead+5..7 then lag past ship → x>=28."""
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    cur = count_free14(data["frame"], freeze15)
    if len(cur) != 2 or me["c"][1] < 34:
        return data, False
    if me["c"][0] < 24 or me["c"][0] >= 28 or step_budget(data["frame"]) < 28:
        return data, False
    lead = max(cur, key=lambda w: (w[0], w[1]))
    lag = min(cur, key=lambda w: (w[0], w[1]))
    gap = lead[0] - lag[0]
    g = _plane(data["frame"])
    me_c = me["c"]

    pairs = []
    for adx in (5, 6, 7, 4):
        if gap + adx > 18:
            continue
        ld = (lead[0] + adx, lead[1])
        if not _translate_dest_ok(g, cur, lead, ld, [lag], freeze15, me_c):
            continue
        trial_lead = [ld if c == lead else c for c in cur]
        tc = centroid(trial_lead)
        me_pred = (int(round(tc[0])), int(round(tc[1])))
        for lax in (10, 11, 9, 12, 8, 13):
            gd = (lag[0] + lax, lag[1])
            # Must clear ship when sandwiched (else engine noop / no east pull).
            if me_c[0] > lag[0] and gd[0] < me_c[0] + 2:
                continue
            cheb_l = abs(gd[0] - ld[0])
            if not (5 <= cheb_l <= 10):
                continue
            if not _translate_dest_ok(
                g, trial_lead, lag, gd, [ld], freeze15, me_pred, close_gap=True
            ):
                continue
            fx = (ld[0] + gd[0]) / 2.0
            if fx < 27.5:
                continue
            pairs.append((ld, gd, fx))
            break
    pairs.sort(key=lambda p: -p[2])
    print(f"  finish-nudge pairs={[ (a,b) for a,b,_ in pairs[:4] ]}")

    tried = set()
    for ld, gd, _ in pairs:
        if ld in tried:
            continue
        tried.add(ld)
        if len(tried) > 3:
            break
        data2, newc, st = move_wp(sess, data, lead, ld, freeze15)
        print(
            f"  finish-nudge lead {lead}->{ld} {st}->{newc} "
            f"ship={next(s for s in ships(data2['frame']) if s['chrome']==14)['c'] if 'frame' in data2 else '?'} "
            f"bud={step_budget(data2['frame']) if 'frame' in data2 else '?'}"
        )
        if st == "dead" or data2.get("state") == "GAME_OVER" or "frame" not in data2:
            return data2, False
        if st != "moved":
            continue
        cur2 = count_free14(data2["frame"], freeze15)
        if len(cur2) != 2:
            print(f"  finish-nudge post-lead flock broke {cur2}")
            return data2, False
        lag_now = min(cur2, key=lambda w: (w[0], w[1]))
        me2 = next(s for s in ships(data2["frame"]) if s["chrome"] == 14)["c"]
        lag_targets = [gd]
        for lax in (10, 11, 9, 12, 8, 13, 7):
            alt = (lag_now[0] + lax, lag_now[1])
            if alt == gd:
                continue
            if me2[0] > lag_now[0] and alt[0] < me2[0] + 2:
                continue
            cheb_l = abs(alt[0] - ld[0])
            if not (5 <= cheb_l <= 10):
                continue
            if max(abs(alt[0] - me2[0]), abs(alt[1] - me2[1])) < 3:
                continue
            if near_any(alt, [ld] + list(freeze15), cheb=3):
                continue
            lag_targets.append(alt)
        for tgt in lag_targets:
            data3, newc, st = move_wp(sess, data2, lag_now, tgt, freeze15)
            print(
                f"  finish-nudge lag {lag_now}->{tgt} {st}->{newc} "
                f"ship={next(s for s in ships(data3['frame']) if s['chrome']==14)['c'] if 'frame' in data3 else '?'} "
                f"n={len(count_free14(data3['frame'], freeze15)) if 'frame' in data3 else '?'} "
                f"bud={step_budget(data3['frame']) if 'frame' in data3 else '?'}"
            )
            if st == "dead" or data3.get("state") == "GAME_OVER" or "frame" not in data3:
                return data3, False
            if st != "moved":
                continue
            if len(count_free14(data3["frame"], freeze15)) != 2:
                print("  finish-nudge flock broke")
                return data3, False
            return data3, True
        print("  finish-nudge lag all noop — keep lead, stop pairs")
        return data2, False
    return data, False


def translate2(sess, data, freeze15, dx: int = 5, dy: int = 0):
    """v67: lead+5 then same-row lag. With east plant (26/20) lands ship x≥28."""
    return translate2_nudge(sess, data, freeze15, lead_dx=5)


def translate2_nudge(sess, data, freeze15, lead_dx: int = 5):
    """Lead +lead_dx then lag toward old lead. lead_dx=5 for mid-east; ≤3 post-gate."""
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    cur = count_free14(data["frame"], freeze15)
    if len(cur) != 2:
        print(f"  translate2 need exactly 2, got {cur}")
        return data, False
    if me["c"][1] < 34 or any(w[1] < 34 for w in cur):
        print(f"  translate2 refuse shallow ship={me['c']} cur={cur}")
        return data, False

    lead = max(cur, key=lambda w: (w[0], w[1]))
    lag = min(cur, key=lambda w: (w[0], w[1]))
    print(f"  translate2 v67 lead={lead} lag={lag} ship={me['c']} dx={lead_dx}")

    ld = (lead[0] + lead_dx, lead[1])
    gap_after = ld[0] - lag[0]
    if gap_after > 16:
        print(f"  translate2 refuse gap_after={gap_after}")
        return data, False
    data, newc, st = move_wp(sess, data, lead, ld, freeze15)
    print(
        f"  translate2-lead {lead}->{ld} {st}->{newc} "
        f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
        f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
    )
    if st != "moved" or data.get("state") == "GAME_OVER" or "frame" not in data:
        return data, False
    cur2 = count_free14(data["frame"], freeze15)
    if len(cur2) != 2:
        print(f"  translate2 post-lead flock broke {cur2}")
        return data, False
    lag_now = min(cur2, key=lambda w: (w[0], w[1]))
    # Aim old lead x; engine clamps west of ship (~+3) — enough with east formation.
    gd = (lag_now[0] + 10, lag_now[1])
    data, newc, st = move_wp(sess, data, lag_now, gd, freeze15)
    print(
        f"  translate2-lag {lag_now}->{gd} {st}->{newc} "
        f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
        f"n={len(count_free14(data['frame'], freeze15)) if 'frame' in data else '?'} "
        f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
    )
    if st != "moved" or data.get("state") == "GAME_OVER" or "frame" not in data:
        return data, False
    if len(count_free14(data["frame"], freeze15)) != 2:
        print("  translate2 post-lag flock broke")
        return data, False
    return data, True


def advance_14_post_mideast(sess, data, lv0, rounds: int = 4):
    """After mid-east gate: short dual nudges (lead+3). Never sync_east14 lag scramble."""
    for i in range(rounds):
        if data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if (data.get("levels_completed") or 0) > lv0:
            return data, True
        freeze15 = lock_other_ship(data["frame"], 14)
        me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        cur = count_free14(data["frame"], freeze15)
        bud = step_budget(data["frame"])
        print(
            f"  post-mideast r{i} ship={me['c']} free={cur} n={len(cur)} bud={bud}"
        )
        if bud < 12:
            break
        if me["c"][0] >= 42 and me["c"][1] >= 34:
            print("  post-mideast reached x>=42")
            break
        if len(cur) != 2 or me["c"][1] < 34 or any(w[1] < 34 for w in cur):
            print("  post-mideast stop (need clean 2wp y>=34)")
            break
        lead = max(cur, key=lambda w: (w[0], w[1]))
        lag = min(cur, key=lambda w: (w[0], w[1]))
        gap = lead[0] - lag[0]
        # Keep gap≤16 after lead: use +3 when gap≥11, else +4/+5.
        adx = 3 if gap >= 11 else (4 if gap >= 8 else 5)
        data, ok = translate2_nudge(sess, data, freeze15, lead_dx=adx)
        if data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if not ok:
            print("  post-mideast nudge soft-fail — stop")
            break
    return data, True


def west_to_neck(sess, data, freeze15, lv0):
    """Classic west hop1 only; then plant TWO corridor pads + south tugs.

    Proven (v23/v24): two corridor plants at y=36, ship ~26–27, bud~34–37.
    Do NOT stop after the first corridor plant.
    """
    data, ok = leap14_once(sess, data, freeze15, lv0, stride=12)
    if data.get("state") == "GAME_OVER" or "frame" not in data:
        return data, False
    snap(data, freeze15, "after-hop1")

    g = _plane(data["frame"])
    moves = 0
    while moves < 8 and step_budget(data["frame"]) >= 10:
        me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        if me["c"][1] >= 28:
            break
        cur = count_free14(data["frame"], freeze15)
        cor = [c for c in cur if c[1] >= 34]
        if len(cor) >= 2:
            xs = sorted(c[0] for c in cor if c[0] > 16) or sorted(c[0] for c in cor)
            if len(xs) >= 2 and xs[-1] - xs[0] >= 5:
                # STOP — wrap south-tugs create (9,34) / dead→GO (v49/v52).
                print(f"  plant enough corridor={cor} ship={me['c']} moves={moves}")
                break
        cands_wp = sorted(
            [w for w in cur if w[1] < 34 and w[0] > 14],
            key=lambda w: (-w[1], abs(w[0] - 22)),
        )
        if not cands_wp:
            cands_wp = sorted(
                [w for w in cur if w[1] < 34],
                key=lambda w: (-w[1], abs(w[0] - 22)),
            )
        placed = False
        # Proven pair shifted +2 east so dual can clear x=28 (v16 was 24/18 → ship 26).
        base_dests = [
            (26, 36),
            (20, 36),
        ]
        if len(cor) < 2:
            for wp in cands_wp:
                if wp[0] <= 14:
                    continue
                others = [c for c in cur if c != wp]
                dests = list(base_dests) + [
                    (wp[0] + 6, 36),
                    (wp[0] + 4, 36),
                    (wp[0] + 2, 36),
                    (wp[0], 36),
                    (wp[0] + 8, 34),
                    (wp[0] + 4, 34),
                ]
                for dest in dests:
                    if not (0 <= dest[0] < 64 and 0 <= dest[1] < 64) or dest == wp:
                        continue
                    if dest[1] < 34 or dest[0] <= 16:
                        continue
                    if int(g[dest[1], dest[0]]) not in (5, 3, 0, 6):
                        continue
                    if near_any(dest, others + freeze15, cheb=5):
                        continue
                    travel = abs(dest[0] - wp[0]) + abs(dest[1] - wp[1])
                    if travel < 4 or travel > 32:
                        continue
                    trial = [dest if c == wp else c for c in cur]
                    tc = centroid(trial)
                    tci = (int(round(tc[0])), int(round(tc[1])))
                    if me["c"][1] >= 34 and not ship_footprint_ok(g, *tci):
                        continue
                    data, newc, st = move_wp(sess, data, wp, dest, freeze15)
                    moves += 1
                    print(
                        f"  plant {wp}->{dest} {st}->{newc} "
                        f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c']} "
                        f"bud={step_budget(data['frame'])}"
                    )
                    if st == "dead" or data.get("state") == "GAME_OVER":
                        return data, False
                    if st == "noop":
                        continue
                    if st == "moved":
                        g = _plane(data["frame"])
                        placed = True
                        break
                if placed:
                    break
        if placed:
            continue
        tugged = False
        tug_wps = (
            [w for w in cur if w[0] <= 14 and w[1] < 28]
            if len(cor) >= 2
            else cands_wp
        )
        for wp in tug_wps or cands_wp:
            others = [c for c in cur if c != wp]
            # v16: wrap (14,16)->(16,22). Prefer those pads first for wrap-col.
            pref = []
            if wp[0] <= 14:
                pref = [(16, 22)]  # v16 only; other pads noop/dead→GO
            for dest in pref:
                if not (0 <= dest[0] < 64 and 0 <= dest[1] < 64) or dest == wp:
                    continue
                if dest[1] <= wp[1]:
                    continue
                if near_any(dest, others + freeze15, cheb=5):
                    continue
                if int(g[dest[1], dest[0]]) not in (5, 3, 0, 6):
                    continue
                trial = [dest if c == wp else c for c in cur]
                tc = centroid(trial)
                tci = (int(round(tc[0])), int(round(tc[1])))
                if me["c"][1] >= 34 and not ship_footprint_ok(g, *tci):
                    continue
                data, newc, st = move_wp(sess, data, wp, dest, freeze15)
                moves += 1
                print(
                    f"  south-tug {wp}->{dest} {st}->{newc} "
                    f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c']} "
                    f"bud={step_budget(data['frame'])}"
                )
                if st == "dead" or data.get("state") == "GAME_OVER":
                    return data, False
                if st == "moved":
                    g = _plane(data["frame"])
                    tugged = True
                    break
            if tugged:
                break
            for dy, dx in (
                (8, -4),
                (8, -2),
                (6, -4),
                (10, -2),
                (8, 0),
                (6, 0),
                (6, 2),
                (4, -2),
                (10, 2),
                (8, 4),
            ):
                raw_y = wp[1] + dy
                if 29 <= raw_y <= 33:
                    dest = (wp[0] + dx, 34)
                else:
                    dest = (wp[0] + dx, min(36, raw_y))
                if dest[1] <= wp[1] or dest == wp:
                    continue
                if not (0 <= dest[0] < 64 and 0 <= dest[1] < 64):
                    continue
                if dest[0] <= 14 and wp[0] > 14:
                    continue
                if int(g[dest[1], dest[0]]) not in (5, 3, 0, 6):
                    continue
                if near_any(dest, others + freeze15, cheb=5):
                    continue
                trial = [dest if c == wp else c for c in cur]
                tc = centroid(trial)
                tci = (int(round(tc[0])), int(round(tc[1])))
                if me["c"][1] >= 34 and not ship_footprint_ok(g, *tci):
                    continue
                data, newc, st = move_wp(sess, data, wp, dest, freeze15)
                moves += 1
                print(
                    f"  south-tug {wp}->{dest} {st}->{newc} "
                    f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c']} "
                    f"bud={step_budget(data['frame'])}"
                )
                if st == "dead" or data.get("state") == "GAME_OVER":
                    return data, False
                if st == "moved":
                    g = _plane(data["frame"])
                    tugged = True
                    break
            if tugged:
                break
        if not tugged:
            print("  plant/tug stuck", cur, "ship", me["c"])
            break
    snap(data, freeze15, "after-plant")
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    return data, me["c"][1] >= 27



def _install_reshape_cap3():
    """Cap chrome14 west reshape so 2wp forms with bud left for translate."""
    import tools.r11l_l3_sync_probe as _sync

    if getattr(_sync.reshape_to_pads, "_r11l_2wp_cap", False):
        return
    _rr = _sync.reshape_to_pads

    def _reshape_cap(sess, data, chrome, locked, pads, lv0, label="", max_moves=5, early_ship_dist=0):
        if chrome == 14 and max_moves > 3:
            max_moves = 3
        return _rr(
            sess, data, chrome, locked, pads, lv0,
            label=label, max_moves=max_moves, early_ship_dist=early_ship_dist,
        )

    _reshape_cap._r11l_2wp_cap = True
    _sync.reshape_to_pads = _reshape_cap


def advance_14_mid_east(sess, data, lv0, *, do_clear15: bool = True):
    """L3 chrome14: plant/collapse 2wp then one dual translate to mid-east gate.

    Gate: ship x>=28 y>=34, free14==2, bud>=28. Returns (data, ok).
    Assumes already in L3 (after L1/L2). Lazy-safe to call from clear_l3.
    """
    _install_reshape_cap3()
    if do_clear15:
        freeze14 = lock_other_ship(data["frame"], 15)
        data, cleared = clear15_corridor(sess, data, freeze14)
        print(f"  mid-east early-clear15={cleared} bud={step_budget(data['frame'])}")
    freeze15 = lock_other_ship(data["frame"], 14)

    # Already past gate — nothing to do.
    info0 = {
        "ship": next(s for s in ships(data["frame"]) if s["chrome"] == 14)["c"],
        "free14": count_free14(data["frame"], freeze15),
        "n": len(count_free14(data["frame"], freeze15)),
        "bud": step_budget(data["frame"]),
        "state": data.get("state"),
    }
    info0["n"] = len(info0["free14"])
    if success_gate(info0):
        print(f"  mid-east already gated ship={info0['ship']} bud={info0['bud']}")
        return data, True

    data, ok = west_to_neck(sess, data, freeze15, lv0)
    if data.get("state") == "GAME_OVER" or "frame" not in data:
        print("  mid-east FAIL GO during west")
        return data, False
    freeze15 = lock_other_ship(data["frame"], 14)
    info = snap(data, freeze15, "west-done")
    corridor = [w for w in info["free14"] if w[1] >= 34]
    if (
        not ok
        and info["bud"] >= 30
        and (
            (len(corridor) >= 2 and info["ship"][1] >= 23)
            or (len(corridor) >= 1 and info["ship"][1] >= 26)
        )
    ):
        print(f"  mid-east west soft-ok corridor={corridor} ship={info['ship']}")
        ok = True
    if not ok:
        print("  mid-east FAIL west did not reach y>=28")
        return data, False

    corridor = [w for w in info["free14"] if w[1] >= 34]
    if len(corridor) >= 2:
        print(f"  mid-east skip-lift corridor={corridor} ship={info['ship']}")
    else:
        data, ok = ensure_y34(sess, data, freeze15)
        if data.get("state") == "GAME_OVER" or "frame" not in data:
            print("  mid-east FAIL GO during lift")
            return data, False
        freeze15 = lock_other_ship(data["frame"], 14)
        info = snap(data, freeze15, "lifted")
        if not ok:
            print("  mid-east WARN lift incomplete — collapse anyway")

    ok = False
    for ci in range(4):
        data, ok = collapse_to_2(sess, data, freeze15)
        if data.get("state") == "GAME_OVER" or "frame" not in data:
            print("  mid-east FAIL GO during collapse")
            return data, False
        freeze15 = lock_other_ship(data["frame"], 14)
        info = snap(data, freeze15, f"collapsed-{ci}")
        if ok:
            break
        print(f"  mid-east collapse round{ci} still n={info['n']}")
    if not ok:
        print("  mid-east FAIL collapse to 2wp")
        return data, False

    # Skip post2-haul / unwrap when already corridor 2wp (PASS path).
    freeze15 = lock_other_ship(data["frame"], 14)
    info = snap(data, freeze15, "pre-translate")
    if info["n"] == 2 and info["ship"][1] >= 34:
        lag = min(info["free14"], key=lambda w: (w[0], w[1]))
        lead = max(info["free14"], key=lambda w: (w[0], w[1]))
        if lag[0] <= 16:
            for dest in ((lead[0] - 6, lead[1]), (20, 36), (22, 36)):
                if dest[0] <= 16 or near_any(dest, [lead] + freeze15, cheb=5):
                    continue
                cheb_l = max(abs(dest[0] - lead[0]), abs(dest[1] - lead[1]))
                if not (5 <= cheb_l <= 8):
                    continue
                data, newc, st = move_wp(sess, data, lag, dest, freeze15)
                print(f"  mid-east unwrap-lag {lag}->{dest} {st}->{newc}")
                if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                    return data, False
                break
            freeze15 = lock_other_ship(data["frame"], 14)
            info = snap(data, freeze15, "pre-translate")

    # One dual translate is enough with east plant (ship 24→28).
    if (
        info["n"] == 2
        and info["ship"][1] >= 34
        and info["bud"] >= 8
        and not success_gate(info)
        and info["ship"][0] < 28
    ):
        print(f"--- mid-east translate ship={info['ship']} bud={info['bud']} ---")
        data, ok = translate2(sess, data, freeze15, dx=5, dy=0)
        if data.get("state") == "GAME_OVER" or "frame" not in data:
            print("  mid-east FAIL GO on translate")
            return data, False
        freeze15 = lock_other_ship(data["frame"], 14)
        info = snap(data, freeze15, "after-translate")

    ok = success_gate(info)
    print(
        f"  mid-east gate={'PASS' if ok else 'FAIL'} "
        f"ship={info['ship']} n={info['n']} bud={info['bud']}"
    )
    return data, ok


def run_probe(dx_list=(5, 5, 5)):
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3_2wp"]},
        timeout=60,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"
    d = reset(sess)
    d, _ = clear_l1(sess, d)
    print("=== L2 ===")
    d, _ = clear_l2(sess, d)
    print("=== L3 2wp mid-east ===")
    lv0 = d.get("levels_completed") or 0
    d, ok = advance_14_mid_east(sess, d, lv0, do_clear15=True)
    freeze15 = lock_other_ship(d["frame"], 14) if "frame" in d else []
    info = (
        snap(d, freeze15, "gate")
        if "frame" in d
        else {"ship": (0, 0), "n": 0, "bud": 0, "state": d.get("state"), "free14": []}
    )
    print("=== RESULT ===")
    print(info)
    if not ok or not success_gate(info):
        print(
            "FAIL gate: "
            f"need ship x>=28 y>=34 n=2 bud>=28; "
            f"got ship={info['ship']} n={info['n']} bud={info['bud']}"
        )
        return 1
    print("PASS gate: mid-east 2wp bud>=28")

    # Post-gate: short dual nudges (not lead+5, not sync_east14 lag scramble).
    if info["bud"] >= 20 and info["n"] == 2 and info["ship"][0] < 45:
        print("--- post-gate nudge ---")
        d, _ = advance_14_post_mideast(sess, d, lv0, rounds=3)
        if "frame" in d and d.get("state") != "GAME_OVER":
            freeze15 = lock_other_ship(d["frame"], 14)
            info = snap(d, freeze15, "post-nudge")
            print(f"  post-nudge ship={info['ship']} n={info['n']} bud={info['bud']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_probe())
