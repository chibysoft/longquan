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
            for dest in ((28, 34), (24, 36), (22, 36), (32, 34), (30, 34), (36, 34)):
                if dest[0] <= 16 or dest[1] < 34:
                    continue
                if near_any(dest, others + freeze15, cheb=5):
                    continue
                if int(g[dest[1], dest[0]]) not in (5, 3, 0, 6):
                    continue
                nxt = floor_bfs(g, wp, dest, max_step=12)
                if not nxt or nxt == wp or nxt[1] < 32:
                    continue
                if near_any(nxt, others + freeze15, cheb=5):
                    continue
                data, newc, st = move_wp(sess, data, wp, nxt, freeze15)
                print(
                    f"    promote {wp}->{nxt} {st}->{newc} "
                    f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                )
                if st == "dead" or data.get("state") == "GAME_OVER":
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
    # Prefer easternmost + a second with cheb>=5 (avoid same-column keepers).
    east = max(corridor, key=lambda w: (w[0], w[1]))
    rest = sorted(
        [w for w in corridor if w != east],
        key=lambda w: (
            0 if max(abs(w[0] - east[0]), abs(w[1] - east[1])) >= 5 else 1,
            -w[0],
            -w[1],
        ),
    )
    keepers = [east] + rest[:1]
    stragglers = [w for w in cur if w not in keepers]
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
        k = min(ks, key=lambda p: max(abs(p[0] - wp[0]), abs(p[1] - wp[1])))
        # On wrap column, prefer EASTERN keeper — same-column merge noops.
        if wp[0] <= 16:
            east = [c for c in ks if c[0] >= 20]
            if east:
                k = min(east, key=lambda p: abs(p[0] - 24) + abs(p[1] - 34))
        # Shallow @y~24 is north of hazard band; go west/east then south.
        # Phase A: north of hazard and still east of wrap column → slide west.
        # Phase B: already at wrap column (x<=14) or past hazard → go south/SE.
        if wp[1] <= 26 and wp[0] > 14:
            pads = [(14, 24), (13, 24), (12, 24), (14, 25), (13, 25)]
        elif wp[1] <= 26 and wp[0] <= 14:
            # South along wrap, then SE toward eastern keeper.
            pads = [
                (14, 28),
                (14, 32),
                (k[0] - 3, 34),
                (k[0] - 2, 34),
                (20, 34),
                (22, 34),
                (24, 34),
                k,
            ]
        else:
            # Diagonal cheb-2/3 approach — never land on same cell / manh<=1.
            pads = [
                (k[0] - 3, 34),
                (k[0] - 2, 34),
                (k[0] + 3, 34),
                (k[0] + 2, 34),
                (k[0] - 3, k[1]),
                (k[0] + 3, k[1]),
                (k[0], max(34, k[1] - 3)),
                (20, 34),
                (24, 34),
                (28, 34),
            ]
        dest = None
        wrapping = wp[1] <= 26 and wp[0] > 14
        on_wrap_col = wp[0] <= 14
        for pad in pads:
            if not (0 <= pad[0] < 64 and 0 <= pad[1] < 64):
                continue
            if wrapping:
                pass  # y=24 west-slide pads ok
            elif pad[1] < 34:
                # interim south on wrap column only
                if not (on_wrap_col and 28 <= pad[1] < 34):
                    continue
            nxt = floor_bfs(g, wp, pad, max_step=8)
            if not nxt or nxt == wp:
                print(f"    collapse skip pad{pad} bfs={nxt}")
                continue
            if wrapping:
                if nxt[0] >= wp[0]:
                    print(f"    collapse skip pad{pad} nxt{nxt} not west wrap")
                    continue
            elif on_wrap_col and wp[1] < 34:
                # must progress south or SE toward keeper
                if nxt[1] < wp[1] + 2 and nxt[0] <= wp[0]:
                    print(f"    collapse skip pad{pad} nxt{nxt} no south/SE")
                    continue
            elif nxt[1] < 34:
                print(f"    collapse skip pad{pad} nxt{nxt} shallow land")
                continue
            # Collapse INTENTIONALLY merges into a keeper — only avoid freeze15.
            if near_any(nxt, freeze15, cheb=5):
                print(f"    collapse skip pad{pad} nxt{nxt} near freeze")
                continue
            # Don't land ON keeper cell (occupied); land cheb 2–3 to merge.
            if nxt == k or (abs(nxt[0] - k[0]) + abs(nxt[1] - k[1]) <= 1):
                # rewrite to cheb-3 approach
                ax = 0 if k[0] == wp[0] else (1 if k[0] > wp[0] else -1)
                ay = 0 if k[1] == wp[1] else (1 if k[1] > wp[1] else -1)
                alt = (k[0] - 3 * (1 if k[0] != wp[0] else 0), k[1] - 3 * (1 if k[1] != wp[1] else 0))
                # simpler: offset south/west of k
                for alt in ((k[0], k[1] - 3), (k[0], k[1] - 2), (k[0] - 3, k[1]), (k[0] + 3, k[1])):
                    if alt[1] < 32 or not (0 <= alt[0] < 64):
                        continue
                    if abs(alt[0] - k[0]) + abs(alt[1] - k[1]) <= 1:
                        continue
                    if max(abs(alt[0] - k[0]), abs(alt[1] - k[1])) > 3:
                        continue
                    if near_any(alt, freeze15, cheb=5):
                        continue
                    nxt = alt
                    break
                else:
                    print(f"    collapse skip pad{pad} cannot approach {k}")
                    continue
            dest = nxt
            print(f"    collapse pick pad{pad} nxt{nxt}")
            break
        if dest is None:
            print(f"    collapse no-path {wp} toward {k}")
            continue
        trial = [dest if c == wp else c for c in cur_now]
        tc = centroid(trial)
        tci = (int(round(tc[0])), int(round(tc[1])))
        if not ship_footprint_ok(g, *tci):
            continue
        data, newc, st = move_wp(sess, data, wp, dest, freeze15)
        print(
            f"    collapse {wp}->{dest} (→{k}) {st}->{newc} "
            f"n={len(count_free14(data['frame'], freeze15)) if 'frame' in data else '?'} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if st != "moved":
            print(f"  collapse noop/skip {st} — try next")
            continue
        g = _plane(data["frame"])
    cur = count_free14(data["frame"], freeze15)
    print(f"  collapse end n={len(cur)} cur={cur}")
    return data, len(cur) == 2


def translate2(sess, data, freeze15, dx: int, dy: int = 0):
    """Pair move. If lag trails by >8, haul lag only (no lead-only race)."""
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    cur = count_free14(data["frame"], freeze15)
    if len(cur) != 2:
        print(f"  translate2 need exactly 2, got {cur}")
        return data, False
    if me["c"][1] < 34 or any(w[1] < 34 for w in cur):
        print(f"  translate2 refuse shallow ship={me['c']} cur={cur}")
        return data, False
    if not (4 <= dx <= 10):
        print(f"  translate2 dx out of range {dx}")
        return data, False

    g = _plane(data["frame"])
    lead = max(cur, key=lambda w: (w[0], w[1]))
    lag = min(cur, key=lambda w: (w[0], w[1]))
    gap = lead[0] - lag[0]
    if gap > 8:
        print(f"  translate2 lag-haul gap={gap} lead={lead} lag={lag}")
        # Try several approach pads toward lead; first success wins.
        pads = []
        for px in (lead[0] - 6, lead[0] - 8, lead[0] - 5, lag[0] + 6, lag[0] + 4, lag[0] + 8):
            for py in (34, 36, 35):
                pads.append((px, py))
        cur_now = count_free14(data["frame"], freeze15)
        others = [c for c in cur_now if c != lag]
        for pad in pads:
            if pad[0] <= lag[0] or pad[1] < 34:
                continue
            if near_any(pad, others + freeze15, cheb=5):
                continue
            nxt = floor_bfs(g, lag, pad, max_step=6)
            if not nxt or nxt == lag:
                continue
            if near_any(nxt, others + freeze15, cheb=5):
                continue
            trial = [nxt if c == lag else c for c in cur_now]
            tc = centroid(trial)
            tci = (int(round(tc[0])), int(round(tc[1])))
            if not ship_footprint_ok(g, *tci):
                continue
            if not centroid_path_ok(cur_now, trial, g, samples=12):
                continue
            data, newc, st = move_wp(sess, data, lag, nxt, freeze15)
            print(
                f"  translate2-lag {lag}->{nxt} (pad{pad}) {st}->{newc} "
                f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
                f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
            )
            if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                return data, False
            if st == "moved":
                return data, True
            # noop: try next pad (already paid); do not retry same
            continue
        print("  translate2 lag-haul all pads failed")
        return data, False

    ordered = [lag, lead]
    for wp in ordered:
        cur_now = count_free14(data["frame"], freeze15)
        if wp not in cur_now:
            continue
        others = [c for c in cur_now if c != wp]
        dest = (wp[0] + dx, wp[1] + dy)
        if dest[1] < 34 or not (0 <= dest[0] < 64 and 0 <= dest[1] < 64):
            print(f"  translate2 bad dest {dest}")
            return data, False
        if int(g[dest[1], dest[0]]) not in (5, 3, 0, 6):
            nxt = floor_bfs(g, wp, dest, max_step=max(dx, 6))
            if not nxt or nxt == wp:
                print(f"  translate2 blocked cell {dest}")
                return data, False
            dest = nxt
        if near_any(dest, others + freeze15, cheb=5):
            alt = None
            for ady in (0, 2, -2, 1, -1):
                t = (wp[0] + dx, min(38, max(34, wp[1] + ady)))
                if t == wp or not (0 <= t[0] < 64):
                    continue
                if int(g[t[1], t[0]]) not in (5, 3, 0, 6):
                    continue
                if near_any(t, others + freeze15, cheb=5):
                    continue
                alt = t
                break
            if alt is None:
                print(f"  translate2 near sibling/lock {dest}")
                return data, False
            dest = alt
        if any(
            30 <= p[1] <= 38
            and 28 <= p[0] <= 40
            and max(abs(dest[0] - p[0]), abs(dest[1] - p[1])) <= 5
            for p in freeze15
        ):
            print(f"  translate2 seal bubble {dest}")
            return data, False
        trial = [dest if c == wp else c for c in cur_now]
        tc = centroid(trial)
        tci = (int(round(tc[0])), int(round(tc[1])))
        if not ship_footprint_ok(g, *tci):
            print(f"  translate2 footprint fail {trial} cent={tci}")
            return data, False
        if not centroid_path_ok(cur_now, trial, g, samples=12):
            print(f"  translate2 path_ok fail {wp}->{dest}")
            return data, False
        data, newc, st = move_wp(sess, data, wp, dest, freeze15)
        print(
            f"  translate2 {wp}->{dest} {st}->{newc} "
            f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if st != "moved":
            print("  translate2 abort", st)
            return data, False
        g = _plane(data["frame"])
    return data, True



def west_to_neck(sess, data, freeze15, lv0):
    """Classic west hop1 only; then short south pulls into y>=34 corridor.

    No second diamond. No west_south experiment beyond 3 explicit south pulls.
    """
    # Hop1: reshape toward (19,19) diamond via existing leap14_once once.
    data, ok = leap14_once(sess, data, freeze15, lv0, stride=12)
    if data.get("state") == "GAME_OVER" or "frame" not in data:
        return data, False
    snap(data, freeze15, "after-hop1")

    # Corridor plant + south tugs until ship y>=28 (or 2 staggered plants).
    # Never BFS into y~30–33 hazard — that dead→GAME_OVER.
    g = _plane(data["frame"])
    moves = 0
    while moves < 8 and step_budget(data["frame"]) >= 10:
        me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        if me["c"][1] >= 28:
            break
        cur = count_free14(data["frame"], freeze15)
        cor = [c for c in cur if c[1] >= 34]
        if len(cor) >= 2:
            xs = sorted(c[0] for c in cor)
            if xs[-1] - xs[0] >= 5 and me["c"][1] >= 26:
                print(f"  plant enough corridor={cor} ship={me['c']} moves={moves}")
                break
        # Prefer southernmost shallow — pulls ship south faster.
        cands_wp = sorted(
            [w for w in cur if w[1] < 34],
            key=lambda w: (-w[1], abs(w[0] - 22)),
        )
        placed = False
        # While ship is north of neck, prefer south corridor pads near wrap (x~18–26),
        # not far-east (32,34) which barely moves ship south.
        if me["c"][1] < 26:
            base_dests = [
                (24, 36),
                (22, 36),
                (20, 36),
                (26, 36),
                (18, 36),
                (24, 34),
                (22, 34),
                (20, 34),
                (28, 36),
                (26, 34),
            ]
        else:
            base_dests = [
                (28, 34),
                (30, 34),
                (26, 34),
                (32, 34),
                (24, 36),
                (22, 36),
                (20, 36),
                (28, 36),
            ]
        for wp in cands_wp:
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
                if not ship_footprint_ok(g, *tci):
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
        # Interim south tug — stay at/below y=28 until past hazard, or jump to y>=34.
        tugged = False
        for wp in cands_wp:
            others = [c for c in cur if c != wp]
            for dy, dx in (
                (10, 2),
                (10, 4),
                (8, 4),
                (8, 6),
                (6, 6),
                (12, 0),
                (8, 0),
                (6, 2),
                (6, -2),
                (4, 4),
            ):
                raw_y = wp[1] + dy
                # Skip landing in hazard band 29–33 unless full corridor jump.
                if 29 <= raw_y <= 33:
                    dest = (wp[0] + dx, 34)
                else:
                    dest = (wp[0] + dx, min(36, raw_y))
                if dest[1] <= wp[1] or dest == wp:
                    continue
                if not (0 <= dest[0] < 64 and 0 <= dest[1] < 64):
                    continue
                if dest[0] <= 14:
                    continue
                if int(g[dest[1], dest[0]]) not in (5, 3, 0, 6):
                    continue
                if near_any(dest, others + freeze15, cheb=5):
                    continue
                trial = [dest if c == wp else c for c in cur]
                tc = centroid(trial)
                tci = (int(round(tc[0])), int(round(tc[1])))
                if not ship_footprint_ok(g, *tci):
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


def run_probe(dx_list=(6, 6, 6, 8)):
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
    print("=== L3 2wp probe ===")
    lv0 = d.get("levels_completed") or 0

    freeze14 = lock_other_ship(d["frame"], 15)
    d, cleared = clear15_corridor(sess, d, freeze14)
    print(f"early-clear15={cleared} bud={step_budget(d['frame'])}")
    freeze15 = lock_other_ship(d["frame"], 14)

    d, ok = west_to_neck(sess, d, freeze15, lv0)
    if d.get("state") == "GAME_OVER" or "frame" not in d:
        print("FAIL GO during west")
        return 1
    info = snap(d, freeze15, "west-done")
    corridor = [w for w in info["free14"] if w[1] >= 34]
    if not ok and len(corridor) >= 1 and info["bud"] >= 30:
        print(f"  west soft-ok corridor={corridor} ship={info['ship']}")
        ok = True
    if not ok:
        print("FAIL west did not reach y>=28")
        return 1

    info = snap(d, freeze15, "pre-lift")
    corridor = [w for w in info["free14"] if w[1] >= 34]
    # If >=2 corridor wps already, do NOT burn lift noops (costs ~6 bud).
    if len(corridor) >= 2 and info["ship"][1] >= 32:
        print(f"  skip-lift corridor={corridor} ship={info['ship']} bud={info['bud']}")
        ok = True
    else:
        d, ok = ensure_y34(sess, d, freeze15)
        if d.get("state") == "GAME_OVER" or "frame" not in d:
            print("FAIL GO during lift")
            return 1
        info = snap(d, freeze15, "lifted")
        if not ok:
            print("WARN lift incomplete — try collapse anyway")

    ok = False
    for ci in range(4):
        d, ok = collapse_to_2(sess, d, freeze15)
        if d.get("state") == "GAME_OVER" or "frame" not in d:
            print("FAIL GO during collapse")
            return 1
        freeze15 = lock_other_ship(d["frame"], 14)
        info = snap(d, freeze15, f"collapsed-{ci}")
        if ok:
            break
        print(f"  collapse round{ci} still n={info['n']}")
    if not ok:
        print("FAIL collapse to 2wp")
        return 1

    # After 2wp: NEVER call ensure_y34 (noop-lift → GO). One diagonal haul only.
    info = snap(d, freeze15, "pre-relift")
    shallow = [w for w in info["free14"] if w[1] < 34]
    if info["n"] == 2 and shallow:
        wp = shallow[0]
        lead = max(info["free14"], key=lambda w: (w[1], w[0]))
        g = _plane(d["frame"])
        hauled = False
        for dest in (
            (lead[0] - 3, 34),
            (lead[0] + 3, 34),
            (lead[0], 34),
            (24, 34),
            (22, 34),
            (20, 34),
        ):
            if dest[1] < 34 or dest == wp:
                continue
            if near_any(dest, [lead] + freeze15, cheb=5) and max(
                abs(dest[0] - lead[0]), abs(dest[1] - lead[1])
            ) > 3:
                continue
            # Allow cheb 2–3 from lead (merge) or sep>=5.
            cheb_l = max(abs(dest[0] - lead[0]), abs(dest[1] - lead[1]))
            if cheb_l < 2 or (cheb_l > 3 and cheb_l < 5):
                continue
            if abs(dest[0] - lead[0]) + abs(dest[1] - lead[1]) <= 1:
                continue
            if int(g[dest[1], dest[0]]) not in (5, 3, 0, 6):
                continue
            trial = [dest if c == wp else c for c in info["free14"]]
            tc = centroid(trial)
            tci = (int(round(tc[0])), int(round(tc[1])))
            if not ship_footprint_ok(g, *tci):
                continue
            d, newc, st = move_wp(sess, d, wp, dest, freeze15)
            print(
                f"  post2-haul {wp}->{dest} {st}->{newc} "
                f"bud={step_budget(d['frame']) if 'frame' in d else '?'}"
            )
            if st == "dead" or d.get("state") == "GAME_OVER" or "frame" not in d:
                print("FAIL GO during post2-haul")
                return 1
            if st == "moved":
                hauled = True
                break
            # noop: stop, do not retry
            break
        if not hauled:
            print("  post2-haul skipped/failed — continue with current 2wp")
    elif info["n"] == 2:
        print("  skip-relift already 2wp")
    freeze15 = lock_other_ship(d["frame"], 14)
    info = snap(d, freeze15, "pre-translate")

    for round_i, dx in enumerate(dx_list):
        if step_budget(d["frame"]) < 8:
            break
        if success_gate(info):
            break
        if info["ship"][1] < 34 or any(w[1] < 34 for w in info["free14"]):
            print(f"  translate refuse shallow ship={info['ship']} free={info['free14']}")
            break
        # Prefer short strides when bud is tight relative to gate.
        if info["bud"] < 34 and dx > 5:
            dx = 5
        print(f"--- translate round{round_i} dx={dx} ---")
        d, ok = translate2(sess, d, freeze15, dx=dx, dy=0)
        if d.get("state") == "GAME_OVER" or "frame" not in d:
            print(f"FAIL GO on translate dx={dx}")
            return 1
        freeze15 = lock_other_ship(d["frame"], 14)
        info = snap(d, freeze15, f"after-dx{dx}")
        if not ok:
            print(f"translate dx={dx} soft-fail — continue next round")
            continue
        if success_gate(info):
            break

    print("=== RESULT ===")
    print(info)
    if success_gate(info):
        print("PASS gate: mid-east 2wp bud>=28")
        return 0
    print(
        "FAIL gate: "
        f"need ship x>=28 y>=34 n=2 bud>=28; "
        f"got ship={info['ship']} n={info['n']} bud={info['bud']}"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(run_probe())
