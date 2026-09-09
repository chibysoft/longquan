"""r11l L3: interleave chrome14 4wp leaps with chrome15 sync waves."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import r11l
from tools.ls20_online_validate import BASE, OnlineSession, _api_key
from tools.r11l_l2_clear_probe import (
    clear_l2,
    free_wps_for,
    formation_pads,
    assign_pads,
    floor_bfs,
    floor_dist,
    move_wp,
    park_compact,
    step_budget,
    owned_map,
    goals_by_chrome,
    near_any,
)
from tools.r11l_l2_core import (
    clearance_path,
    centroid,
    centroid_path_ok,
    ship_footprint_ok,
    _plane,
)
from tools.r11l_l2_probe import ships
from tools.r11l_seated_clear import clear_l1, reset

# East of ship; Chebyshev sep ≥6; survives full L3 chrome15 path.
OFFS15 = ((5, 0), (5, 6))
OFFS14_2 = ((5, 0), (5, 6))  # after accidental 4→2 merge
FLOOR = 5


def manh(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _is_14_seal_lead(c):
    """Chrome14's post-seal-jump locomotive sits at x≥40, y∈[30,38]."""
    return 30 <= c[1] <= 38 and c[0] >= 40


def lock_other_ship(frame, chrome_self):
    """Freeze wps that clearly belong to the other ship (much closer to it)."""
    ss = ships(frame)
    me = next(s for s in ss if s["chrome"] == chrome_self)
    other = next(s for s in ss if s["chrome"] != chrome_self)
    out = []
    for w in r11l.waypoints(frame):
        c = w["c"]
        d_other = manh(c, other["c"])
        d_me = manh(c, me["c"])
        # When moving 14: seal-jump lead stays free for 14 (not frozen as 15's).
        if chrome_self == 14 and _is_14_seal_lead(c):
            continue
        # When moving 15: always freeze 14's seal lead so wave15 can't steal it.
        if chrome_self == 15 and _is_14_seal_lead(c):
            out.append(c)
            continue
        # Strict: closer by ≥8 AND within 16 of the other ship.
        # (Loose owned_map / +2 threshold steals chrome14's eastern wps.)
        if d_other + 8 < d_me and d_other <= 16:
            out.append(c)
    # Dedupe preserve order
    seen = set()
    out = [c for c in out if not (c in seen or seen.add(c))]
    if len(out) >= 2:
        return out[:4]

    # Fallback: among wps closer to other than me, take nearest 2.
    closer = [
        w["c"]
        for w in r11l.waypoints(frame)
        if manh(w["c"], other["c"]) < manh(w["c"], me["c"])
        and not (chrome_self == 14 and _is_14_seal_lead(w["c"]))
    ]
    if chrome_self == 15:
        closer = list(dict.fromkeys(out + closer))
    if closer:
        return sorted(closer, key=lambda c: manh(c, other["c"]))[:4]
    # Last resort: two nearest to other that are also nearer than me+4.
    ranked = sorted(
        (w["c"] for w in r11l.waypoints(frame)),
        key=lambda c: manh(c, other["c"]),
    )
    rest = [
        c
        for c in ranked
        if manh(c, other["c"]) <= manh(c, me["c"]) + 2
        and not (chrome_self == 14 and _is_14_seal_lead(c))
    ]
    if chrome_self == 15:
        rest = list(dict.fromkeys(out + rest))
    return rest[:4]


def count_free14(frame, freeze15):
    me14 = next(s for s in ships(frame) if s["chrome"] == 14)
    seen = []
    for w in r11l.waypoints(frame):
        c = w["c"]
        if near_any(c, freeze15, cheb=2):
            continue
        if manh(c, me14["c"]) <= 30 and c not in seen:
            seen.append(c)
    return seen


def sync_to(sess, data, locked, targets, label=""):
    """Move chrome15 free wps onto absolute targets (assign by nearest)."""
    print(f"  sync_to {label} targets={targets} bud={step_budget(data['frame'])}")
    moved_any = False
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)

    def cur15():
        # Never touch wps closer to chrome14.
        me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        out = []
        for w in r11l.waypoints(data["frame"]):
            c = w["c"]
            if near_any(c, locked, cheb=2):
                continue
            if manh(c, me15["c"]) <= 14 and manh(c, me15["c"]) <= manh(c, me14["c"]) + 4:
                out.append(c)
        return out

    for _ in range(len(targets) + 6):
        cur = cur15()
        if len(cur) < min(2, len(targets)):
            print("  lost wps", cur)
            return data, False
        if all(
            min(abs(w[0] - t[0]) + abs(w[1] - t[1]) for t in targets) <= 2 for w in cur
        ):
            return data, True
        best = None
        for w in cur:
            for t in sorted(targets, key=lambda t: abs(t[0] - w[0]) + abs(t[1] - w[1])):
                if any(max(abs(t[0] - o[0]), abs(t[1] - o[1])) < 6 for o in cur if o != w):
                    continue
                if near_any(t, locked, cheb=6):
                    continue
                d = abs(t[0] - w[0]) + abs(t[1] - w[1])
                if d <= 2:
                    continue
                score = (-d, w, t)
                if best is None or score < best:
                    best = score
                break
        if best is None:
            print("  no sync_to move")
            return data, moved_any
        _, wp, dest = best
        g = _plane(data["frame"])
        trial = list(cur)
        wi = cur.index(wp)
        trial[wi] = dest
        if not centroid_path_ok(cur, trial, g, samples=14):
            mid = ((wp[0] + dest[0]) // 2, (wp[1] + dest[1]) // 2)
            if mid == wp or near_any(mid, [c for c in cur if c != wp], 5):
                print(f"  path_ok fail {wp}->{dest}")
                continue
            dest = mid
            trial[wi] = dest
            if not centroid_path_ok(cur, trial, g, samples=14):
                print(f"  path_ok fail mid {wp}->{dest}")
                continue
        data, newc, st = move_wp(sess, data, wp, dest, locked)
        print(
            f"    {wp}->{dest} {st}->{newc} "
            f"ships={[(s['c'], s['chrome']) for s in ships(data['frame'])] if 'frame' in data else '?'} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or "frame" not in data:
            return data, False
        if st in ("noop", "forbidden", "lost", "near_locked", "occupied", "error"):
            continue
        moved_any = True
        if (data.get("levels_completed") or 0) >= 3:
            return data, True
        me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    cur = cur15()
    ok = bool(cur) and all(
        min(abs(w[0] - t[0]) + abs(w[1] - t[1]) for t in targets) <= 3 for w in cur
    )
    return data, ok or moved_any


def pads_at(g, hop, n=4):
    """Prefer cardinal diamond (past choke), else formation_pads; n=2 after merge."""

    def cell_ok(p):
        if not (0 <= p[0] < 64 and 0 <= p[1] < 64):
            return False
        return int(g[p[1], p[0]]) not in (2, 10)

    if n <= 2:
        for offs in (OFFS14_2, ((6, 0), (0, 6)), ((4, -1), (4, 5)), ((0, 5), (6, 5))):
            pads = [(hop[0] + ox, hop[1] + oy) for ox, oy in offs]
            if all(cell_ok(p) for p in pads) and ship_footprint_ok(g, hop[0], hop[1]):
                if max(abs(pads[0][0] - pads[1][0]), abs(pads[0][1] - pads[1][1])) >= 5:
                    return pads
        pads = formation_pads(g, hop, 2, ring_min=5, ring_max=8)
        return pads if len(pads) >= 2 else []

    # West corridor + east: cardinal diamond preferred.
    # (Choke-safe compact pads live in leap14_east_once — don't break west hops.)
    for rad in (5, 6, 7):
        dia = [
            (hop[0], hop[1] - rad),
            (hop[0] + rad, hop[1]),
            (hop[0], hop[1] + rad),
            (hop[0] - rad, hop[1]),
        ]
        if all(cell_ok(p) for p in dia) and ship_footprint_ok(g, hop[0], hop[1]):
            return dia
    pads = formation_pads(g, hop, n, ring_min=5, ring_max=8)
    pads = [
        p
        for p in pads
        if p[1] <= hop[1] + 6 and abs(p[0] - hop[0]) + abs(p[1] - hop[1]) <= 14
    ]
    return pads if len(pads) >= n else []


def pads_east(g, hop, n=4):
    """Compact pads for near-choke / east hops — no tall south spike."""
    if n <= 2:
        return pads_at(g, hop, 2)

    def cell_ok(p):
        if not (0 <= p[0] < 64 and 0 <= p[1] < 64):
            return False
        return int(g[p[1], p[0]]) not in (2, 10)

    pads = formation_pads(g, hop, n, ring_min=5, ring_max=7)
    pads = [
        p
        for p in pads
        if p[1] <= hop[1] + 3 and abs(p[0] - hop[0]) + abs(p[1] - hop[1]) <= 12
    ]
    if len(pads) >= n:
        return pads[:n]
    stagger = []
    for dx, dy in ((5, 0), (-5, 0), (0, -5), (4, 2), (-4, 2), (2, 3), (-2, 3), (5, 3), (-5, 3)):
        p = (hop[0] + dx, hop[1] + dy)
        if not cell_ok(p) or p[1] > hop[1] + 3:
            continue
        if near_any(p, stagger, cheb=5):
            continue
        stagger.append(p)
        if len(stagger) >= n:
            return stagger[:n]
    # Soft diamond only — never tall south spike (hazard / merge).
    for rad in (5, 6):
        dia = [
            (hop[0], hop[1] - rad),
            (hop[0] + rad, hop[1]),
            (hop[0], hop[1] + min(rad, 4)),
            (hop[0] - rad, hop[1]),
        ]
        if all(cell_ok(p) for p in dia) and ship_footprint_ok(g, hop[0], hop[1]):
            if all(
                max(abs(dia[i][0] - dia[j][0]), abs(dia[i][1] - dia[j][1])) >= 5
                for i in range(4)
                for j in range(i + 1, 4)
            ):
                return dia
    return stagger if len(stagger) >= n else []


def reshape_to_pads(sess, data, chrome, locked, pads, lv0, label="", max_moves=5, early_ship_dist=0):
    """Pull free wps onto pads; allow midpoints when centroid path is blocked.

    If early_ship_dist > 0, stop once the ship is within that Manhattan distance
    of the pads centroid (saves budget on west hops).
    """
    print(f"  reshape {label} pads={pads} bud={step_budget(data['frame'])}")
    moves = 0
    blacklist = set()  # (wp, dest) pairs that noop'd — never retry
    noops = 0
    pad_c = centroid(pads)
    pad_ci = (int(round(pad_c[0])), int(round(pad_c[1])))
    ship0 = None
    if chrome == 14:
        ship0 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)["c"]
    for _ in range(len(pads) * 4 + 4):
        if moves >= max_moves:
            print("  reshape move cap")
            break
        if noops >= 2:
            print("  reshape noop cap")
            break
        if step_budget(data["frame"]) < 8:
            print("  reshape budget floor")
            break
        if (data.get("levels_completed") or 0) > lv0:
            return data, True
        # Early-exit disabled for L3 west (left unfinished pads / burned neck diamond).
        if False and early_ship_dist > 0 and chrome == 14 and ship0 is not None:
            me_chk = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            cur_chk = free_wps_for(data["frame"], chrome, locked)
            if chrome == 14:
                near14 = [
                    w["c"]
                    for w in r11l.waypoints(data["frame"])
                    if abs(w["c"][0] - me_chk["c"][0]) + abs(w["c"][1] - me_chk["c"][1])
                    <= 28
                    and not near_any(w["c"], locked, cheb=2)
                ]
                for p in near14:
                    if p not in cur_chk:
                        cur_chk.append(p)
            straggler = any(
                abs(w[1] - pad_ci[1]) > 10 or abs(w[0] - pad_ci[0]) > 12
                for w in cur_chk
            )
            if (
                manh(me_chk["c"], pad_ci) <= early_ship_dist
                and manh(me_chk["c"], ship0) >= 6
                and not straggler
                and len(cur_chk) >= len(pads)
            ):
                print(f"  reshape early-ok ship={me_chk['c']} hop≈{pad_ci}")
                return data, True
        # All non-locked wps — owned_map drifts mid-migrate and drops chrome14 wps.
        cur = free_wps_for(data["frame"], chrome, locked)
        if chrome == 14:
            me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            near14 = [
                w["c"]
                for w in r11l.waypoints(data["frame"])
                if abs(w["c"][0] - me14["c"][0]) + abs(w["c"][1] - me14["c"][1]) <= 28
                and not near_any(w["c"], locked, cheb=2)
            ]
            # Union: free_wps can miss stragglers; near14 can miss far west pads mid-hop.
            merged = []
            for p in near14 + cur:
                if p not in merged:
                    merged.append(p)
            cur = merged
        if len(cur) < len(pads):
            all_wps = [w["c"] for w in r11l.waypoints(data["frame"])]
            print(
                f"  reshape lost wps cur={cur} need={len(pads)} "
                f"locked={locked} all={all_wps}"
            )
            return data, False
        if all(min(abs(w[0] - t[0]) + abs(w[1] - t[1]) for t in pads) <= 3 for w in cur):
            return data, True
        g = _plane(data["frame"])
        pairs = assign_pads(cur, pads, g)
        best = None
        bud = step_budget(data["frame"])
        # East corridor / low budget / near choke: cap travel hard.
        me_now = next((s for s in ships(data["frame"]) if s["chrome"] == chrome), None)
        on_east = me_now is not None and me_now["c"][1] >= 34
        near_choke = me_now is not None and 28 <= me_now["c"][1] < 34
        if near_choke or on_east or bud < 18:
            # Corridor with budget: longer leaps (ship must cover ~35 cells east).
            max_travel = 10 if (on_east and bud >= 16) else 6
        elif bud < 24:
            max_travel = 8
        else:
            max_travel = 12
        sep_need = 6 if (near_choke or on_east) else 5
        # West: prefer longer hops (each ACTION6 ~costs 3 regardless of length).
        west_mode = (not near_choke) and (not on_east) and bud >= 24
        for i, pad in pairs:
            wp = cur[i]
            d = abs(wp[0] - pad[0]) + abs(wp[1] - pad[1])
            if d <= 3:
                continue
            opts = []
            if on_east and bud >= 16:
                step_sizes = (8, 10, 6, 4, 12)
            elif near_choke or on_east:
                step_sizes = (4, 6, 5, 3, 8)
            elif west_mode:
                step_sizes = (10, 12, 8, 6, 4)
            else:
                step_sizes = (6, 8, 4, 10, 12)
            for ms in step_sizes:
                stepped = floor_bfs(g, wp, pad, max_step=ms)
                if stepped and stepped != wp and stepped not in opts:
                    opts.append(stepped)
            if pad not in opts and abs(pad[0] - wp[0]) + abs(pad[1] - wp[1]) <= max_travel + 2:
                opts.append(pad)
            for dest in opts:
                if dest is None or dest == wp:
                    continue
                if (wp, dest) in blacklist:
                    continue
                travel = abs(dest[0] - wp[0]) + abs(dest[1] - wp[1])
                if travel > max_travel:
                    continue
                if not (0 <= dest[0] < 64 and 0 <= dest[1] < 64):
                    continue
                if int(g[dest[1], dest[0]]) in (2, 10):
                    continue
                # Engine merges wps at Chebyshev < 5 — keep ≥6 near choke.
                if near_any(dest, [cur[j] for j in range(len(cur)) if j != i], cheb=sep_need):
                    continue
                if near_any(dest, locked, cheb=6):
                    continue
                trial = list(cur)
                trial[i] = dest
                if not centroid_path_ok(cur, trial, g, samples=10):
                    continue
                tc = centroid(trial)
                tci = (int(round(tc[0])), int(round(tc[1])))
                if not ship_footprint_ok(g, tci[0], tci[1]):
                    continue
                if any(max(abs(p[0] - tci[0]), abs(p[1] - tci[1])) < 3 for p in trial):
                    continue
                score = (-d, -travel, i, dest)
                if best is None or score < best:
                    best = score
        if best is None:
            # Last-ditch: any body-safe cardinal step toward nearest pad.
            for i, wp in enumerate(cur):
                pad = min(pads, key=lambda t: abs(t[0] - wp[0]) + abs(t[1] - wp[1]))
                for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, 1)):
                    dest = (wp[0] + dx, wp[1] + dy)
                    if (wp, dest) in blacklist:
                        continue
                    if not (0 <= dest[0] < 64 and 0 <= dest[1] < 64):
                        continue
                    if int(g[dest[1], dest[0]]) in (2, 10):
                        continue
                    if near_any(dest, [c for c in cur if c != wp], cheb=sep_need):
                        continue
                    trial = list(cur)
                    trial[i] = dest
                    if not centroid_path_ok(cur, trial, g, samples=8):
                        continue
                    tc = centroid(trial)
                    tci = (int(round(tc[0])), int(round(tc[1])))
                    if not ship_footprint_ok(g, *tci):
                        continue
                    if any(max(abs(p[0] - tci[0]), abs(p[1] - tci[1])) < 3 for p in trial):
                        continue
                    # Must not increase lag to pad.
                    if abs(dest[0] - pad[0]) + abs(dest[1] - pad[1]) >= abs(wp[0] - pad[0]) + abs(wp[1] - pad[1]):
                        continue
                    best = (0, 0, i, dest)
                    break
                if best is not None:
                    break
        if best is None:
            print("  reshape stuck", cur, pads)
            return data, False
        _, _, i, dest = best
        wp = cur[i]
        # Abort reshape if a move drops below expected flock size.
        n_before = len(cur)
        data, newc, st = move_wp(sess, data, wp, dest, locked)
        print(
            f"    {wp}->{dest} {st}->{newc} "
            f"ships={[(s['c'], s['chrome']) for s in ships(data['frame'])] if 'frame' in data else '?'} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or "frame" not in data:
            return data, False
        if st in ("noop", "forbidden", "lost", "near_locked", "occupied", "error", "already"):
            blacklist.add((wp, dest))
            noops += 1
            continue
        n_after = len(r11l.waypoints(data["frame"]))
        # L3 expects 6; after a merge we may have 4 (2+2) — stop reshape, caller adapts.
        if n_after < 4:
            print(f"  reshape wp-merge catastrophic total={n_after}; stop")
            return data, False
        if n_after < n_before + len(locked):  # flock shrank
            # Rough: if total dropped, treat as merge.
            pass
        if n_after < 6 and n_before >= 4 and chrome == 14:
            print(f"  reshape wp-merge detected total={n_after}; stop (adapt 2wp)")
            return data, False
        moves += 1
        noops = 0
    if "frame" not in data:
        return data, False
    cur = free_wps_for(data["frame"], chrome, locked)
    ok = all(min(abs(w[0] - t[0]) + abs(w[1] - t[1]) for t in pads) <= 4 for w in cur)
    return data, ok


def collapse14_to_2wp(sess, data, freeze15, lv0):
    """Merge chrome14 4→2 by walking stragglers into eastern keepers (cheb<5)."""
    cur = count_free14(data["frame"], freeze15)
    if len(cur) <= 2:
        return data, True
    if step_budget(data["frame"]) < 16:
        return data, False
    g = _plane(data["frame"])
    keepers = sorted(cur, key=lambda w: (-w[0], -w[1]))[:2]
    stragglers = [w for w in cur if w not in keepers]
    print(
        f"  collapse14→2wp keepers={keepers} stragglers={stragglers} "
        f"bud={step_budget(data['frame'])}"
    )
    moves = 0
    for wp in stragglers:
        if moves >= 2 or step_budget(data["frame"]) < 10:
            break
        if len(count_free14(data["frame"], freeze15)) <= 2:
            break
        # Refresh keepers from current flock (may have moved).
        cur_now = count_free14(data["frame"], freeze15)
        if wp not in cur_now:
            continue
        ks = sorted(cur_now, key=lambda w: (-w[0], -w[1]))[:2]
        if wp in ks:
            continue
        k = min(ks, key=lambda p: max(abs(p[0] - wp[0]), abs(p[1] - wp[1])))
        # Step toward keeper until Chebyshev ≤3 (engine merges at <5).
        cheb = max(abs(k[0] - wp[0]), abs(k[1] - wp[1]))
        if cheb < 5:
            continue  # already merging range — wait
        # Land at cheb=3 from keeper along the line.
        dx = 0 if k[0] == wp[0] else (1 if k[0] > wp[0] else -1)
        dy = 0 if k[1] == wp[1] else (1 if k[1] > wp[1] else -1)
        # Move up to 6 cells toward keeper.
        dest = wp
        for _ in range(6):
            nxt = (dest[0] + dx, dest[1] + dy)
            if max(abs(k[0] - nxt[0]), abs(k[1] - nxt[1])) < 3:
                break
            if not (0 <= nxt[0] < 64 and 0 <= nxt[1] < 64):
                break
            if int(g[nxt[1], nxt[0]]) in (2, 10):
                break
            dest = nxt
            if max(abs(k[0] - dest[0]), abs(k[1] - dest[1])) <= 3:
                break
        if dest == wp:
            continue
        # Soft safety: don't enter ship hull of keepers centroid.
        trial = [dest if c == wp else c for c in cur_now]
        tc = centroid(trial)
        tci = (int(round(tc[0])), int(round(tc[1])))
        if not ship_footprint_ok(g, *tci):
            continue
        data, newc, st = move_wp(sess, data, wp, dest, freeze15)
        moves += 1
        print(
            f"    collapse {wp}->{dest} (→{k}) {st}->{newc} "
            f"n={len(r11l.waypoints(data['frame'])) if 'frame' in data else '?'} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or "frame" not in data:
            return data, False
        if st != "moved":
            print("  collapse14 abort noop")
            break
        g = _plane(data["frame"])
    cur = count_free14(data["frame"], freeze15)
    print(f"  collapse14 end cur={cur} bud={step_budget(data['frame'])}")
    return data, len(cur) <= 2


def sync_east14(sess, data, freeze15, stride=12):
    """East leap: pull lagging (western) corridor wps east — both if possible."""
    if step_budget(data["frame"]) < 5:
        return data, False
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    goal = goals_by_chrome(data["frame"])[14]
    cur = count_free14(data["frame"], freeze15)
    all_wps = [w["c"] for w in r11l.waypoints(data["frame"])]
    if len(cur) < 2:
        print(f"  sync_east14 few-free cur={cur} all={all_wps} freeze={freeze15}")
        return data, False
    print(
        f"  sync_east14 begin cur={cur} all={all_wps} "
        f"ship={me['c']} bud={step_budget(data['frame'])}"
    )
    band = [w for w in cur if 24 <= w[1] <= 38] or list(cur)
    before = me["c"]
    g = _plane(data["frame"])
    # Pull deep-north stragglers south before east — they poison footprint checks
    # and long diagonals from y=25 → GAME_OVER. Absolute y<28 only (not
    # relative-to-ship, which mis-tags corridor wps at y=28 when ship is at 32).
    cur0 = count_free14(data["frame"], freeze15)
    # Simple north polish: deep-north y<28 → y=31/34 (proven after shallow
    # cleared to (14,36)). Skip complex lift — it noops and burns budget.
    # Always lift deep-north (y<28) — skipping left (14,25) and stuck ship at y=32.
    north_strag = [w for w in cur0 if w[1] < 28]
    if step_budget(data["frame"]) < 10:
        north_strag = []
    for wp in sorted(north_strag, key=lambda w: w[1])[:1]:
        if step_budget(data["frame"]) < 12:
            break
        dest = None
        for t in (
            (wp[0], 31),
            (wp[0], 34),
            (wp[0] + 2, 34),
            (wp[0] + 4, 34),
            (wp[0] + 6, 34),
            (wp[0], min(34, wp[1] + 6)),
        ):
            if not (0 <= t[0] < 64 and 0 <= t[1] < 64):
                continue
            if t == wp or int(g[t[1], t[0]]) in (2, 10):
                continue
            if near_any(t, [c for c in cur0 if c != wp] + freeze15, cheb=5):
                continue
            dest = t
            break
        if dest is None:
            break
        data, newc, st = move_wp(sess, data, wp, dest, freeze15)
        print(
            f"    sync14-north {wp}->{dest} {st}->{newc} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or "frame" not in data:
            return data, False
        if st == "noop":
            break
        if st == "moved":
            g = _plane(data["frame"])
            me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        break

    moved_any = me["c"] != before
    pulls = 0
    cur0 = count_free14(data["frame"], freeze15)
    band0 = [w for w in cur0 if 24 <= w[1] <= 38]
    lead0 = max((w[0] for w in band0), default=0) if band0 else 0
    # Compact remaining shallow only if no lead yet and bud allows.
    shallow = sorted(
        [w for w in cur0 if 28 <= w[1] <= 32],
        key=lambda w: (w[1], abs(w[0] - 20)),
    )
    # Compact shallow even with a lead — leaving (14,31) then lead-hop drops flock.
    if step_budget(data["frame"]) < 10:
        shallow = []
    for wp in shallow[:1]:
        if step_budget(data["frame"]) < 6:
            break
        dest = None
        # Prefer short cardinal south hops (long SE noops on live).
        # Same-x south often blocked by a sibling on (x,36) — offset east.
        cands = []
        for step in (4, 5, 6):
            cands.append((wp[0], min(34, wp[1] + step)))
        for ox in (6, 8, 4, 2, 10, 0):
            cands.append((wp[0] + ox, 34))
            cands.append((wp[0] + ox, 33))
        for tgt in ((wp[0] + 6, 34), (wp[0] + 4, 34), (wp[0], 34)):
            nxt = floor_bfs(g, wp, tgt, max_step=6)
            if nxt and nxt != wp:
                cands.append(nxt)
        for t in cands:
            if not (0 <= t[0] < 64 and 0 <= t[1] < 64):
                continue
            if t == wp or t[1] < 33:
                continue
            if int(g[t[1], t[0]]) not in (5, 3, 0, 6):
                continue
            if near_any(t, [c for c in cur0 if c != wp] + freeze15, cheb=6):
                continue
            trial = [t if c == wp else c for c in cur0]
            tc = centroid(trial)
            tci = (int(round(tc[0])), int(round(tc[1])))
            if not ship_footprint_ok(g, *tci):
                continue
            # Pure/near-south compact: path_ok often false-negatives on live;
            # end footprint is enough for ≤6 south hops.
            almost_south = abs(t[0] - wp[0]) <= 4 and t[1] >= wp[1] + 3
            if not almost_south and not centroid_path_ok(cur0, trial, g):
                continue
            if floor_dist(g, wp, t, limit=24) is None:
                continue
            if abs(t[0] - wp[0]) + abs(t[1] - wp[1]) > 10:
                continue
            dest = t
            break
        if dest is None:
            continue
        data, newc, st = move_wp(sess, data, wp, dest, freeze15)
        print(
            f"    sync14-compact {wp}->{dest} {st}->{newc} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or "frame" not in data:
            return data, False
        if st == "noop":
            break
        if st == "moved":
            moved_any = True
            g = _plane(data["frame"])
            me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            cur0 = count_free14(data["frame"], freeze15)

    cur = count_free14(data["frame"], freeze15)
    # Only corridor-band for east pulls (y≥28).
    band = [w for w in cur if 28 <= w[1] <= 38] or [
        w for w in cur if 24 <= w[1] <= 38
    ]
    if not band:
        return data, moved_any
    # Seed an eastern lead if flock is stuck west of x=26 (after clear15,
    # south-once alone leaves no locomotive past the old seal line).
    lead_x = max(w[0] for w in band)
    if lead_x < 28 and step_budget(data["frame"]) >= 8 and pulls < 1:
        g = _plane(data["frame"])
        seed_from = sorted(
            band + [w for w in cur if w[1] < 28],
            key=lambda w: (-(w[1] < 28), -w[0], abs(w[1] - 34)),
        )
        for wp in seed_from[:3]:
            if step_budget(data["frame"]) < 8:
                break
            others = [c for c in cur if c != wp]
            placed = False
            for dest in (
                (wp[0] + 4, 34),
                (wp[0] + 5, 34),
                (wp[0] + 6, 34),
                (30, 34),
                (32, 34),
                (28, 36),
                (30, 36),
            ):
                if not (0 <= dest[0] < 64 and 0 <= dest[1] < 64):
                    continue
                if dest == wp:
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
                print(
                    f"    sync14-seed {wp}->{dest} {st}->{newc} "
                    f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                )
                if st == "dead" or "frame" not in data:
                    return data, False
                if st == "noop":
                    break
                if st == "moved":
                    pulls += 1
                    moved_any = True
                    placed = True
                    g = _plane(data["frame"])
                    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
                    cur = count_free14(data["frame"], freeze15)
                    band = [w for w in cur if 28 <= w[1] <= 38] or [
                        w for w in cur if 24 <= w[1] <= 38
                    ]
                    break
            if placed:
                break
    # Recompute lagging after north fix / band shrink.
    stacked = False
    for i, a in enumerate(band):
        for b in band[i + 1 :]:
            if abs(a[1] - b[1]) <= 2 and 5 <= abs(a[0] - b[0]) <= 22:
                stacked = True
                break
        if stacked:
            break

    def _try_pull(order, label):
        nonlocal data, g, me, pulls, moved_any
        for w in list(order[:3]):
            if pulls >= 2 or step_budget(data["frame"]) < 5:
                break
            # Refresh plane each attempt — live hazards differ from fixture.
            g = _plane(data["frame"])
            me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            # Shallow poison: any east pull at ship y≤32 often GAME_OVER.
            if me["c"][1] < 33 and label in ("-lead", "-lag", "-sib", ""):
                continue
            cur_now = count_free14(data["frame"], freeze15)
            if w not in cur_now:
                band_now = [c for c in cur_now if 28 <= c[1] <= 38] or cur_now
                if not band_now:
                    break
                w = min(band_now, key=lambda c: (c[0], abs(c[1] - 34)))
            others = [c for c in cur_now if c != w]
            placed = False
            noop_hit = False
            east_block = [
                o for o in others if o[0] > w[0] and abs(o[1] - w[1]) <= 4
            ]
            # Approach lead from the west — never jump past it (GAME_OVER).
            if east_block:
                lead_x = max(o[0] for o in east_block)
                gap = lead_x - w[0]
                # Never close with dx>=8 — merges western flock on live.
                dx_list = [
                    d
                    for d in (gap - 6, gap - 5, 6, 5, 4)
                    if 4 <= d <= 6
                ]
                if not dx_list:
                    dx_list = [6, 5, 4]
            else:
                # Lead long-jumps (dx≥8) drop western wps on live (4→1).
                # Never advance lead while ship still in shallow poison y≤32.
                sealed = any(
                    30 <= p[1] <= 38 and 28 <= p[0] <= 40 for p in freeze15
                )
                if label == "-lead":
                    # y=33 still GAME_OVER'd on live 2wp lead hop — need y>=34.
                    if me["c"][1] < 34:
                        continue
                    nfree = len(count_free14(data["frame"], freeze15))
                    if nfree <= 2:
                        # Only short lead until lag catches (gap<=8).
                        lags = [c for c in others if c[0] < w[0]]
                        gap = (w[0] - max(c[0] for c in lags)) if lags else 0
                        if gap > 8:
                            continue
                        dx_list = [4, 5]
                    else:
                        dx_list = [4, 5, 6]
                elif sealed:
                    dx_list = [4, 5, 6]
                else:
                    # Never dx>=8 until seated collapse proves safe; short only.
                    dx_list = [4, 5, 6]
            # DO NOT seal-jump (28→42): live engine drops western wps (4→1).
            # clear15_corridor must vacate ~(37,34) first; then short hops.
            # After seal-jump: never retouch the x≥40 lead — haul lag only.
            if label == "-lead" and w[0] >= 40:
                continue
            for dx in dx_list:
                if placed or noop_hit:
                    break
                for dy in (0, -2, 2, -4, 4):
                    # Keep corridor band. Once ship is on y>=34, never land y<34
                    # (v1 sync after mid-east: lag→(27,32) poisoned flock).
                    y_lo = 34 if me["c"][1] >= 34 else 32
                    ty = min(36, max(y_lo, w[1] + dy))
                    t = (w[0] + dx, ty)
                    if t[0] >= 64:
                        continue
                    # Never land within cheb≤5 of chrome15 corridor seal — merges.
                    if any(
                        30 <= p[1] <= 38
                        and 28 <= p[0] <= 40
                        and max(abs(t[0] - p[0]), abs(t[1] - p[1])) <= 5
                        for p in freeze15
                    ):
                        continue
                    if int(g[t[1], t[0]]) not in (5, 3, 0, 6):
                        continue
                    if near_any(t, others + freeze15, cheb=5):
                        continue
                    trial = [t if c == w else c for c in cur_now]
                    tc = centroid(trial)
                    tci = (int(round(tc[0])), int(round(tc[1])))
                    if not ship_footprint_ok(g, *tci):
                        continue
                    # Lead and 2wp always need path_ok — short hops still GAME_OVER.
                    nfree = len(cur_now)
                    need_path = (
                        label == "-lead"
                        or nfree <= 2
                        or dx >= 8
                        or t[0] >= 42
                    )
                    if need_path and not centroid_path_ok(cur_now, trial, g):
                        continue
                    data, newc, st = move_wp(sess, data, w, t, freeze15)
                    print(
                        f"    sync14{label} {w}->{t} {st}->{newc} "
                        f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                    )
                    if st == "dead" or "frame" not in data:
                        return False
                    if st == "noop":
                        noop_hit = True
                        break
                    if st == "moved":
                        pulls += 1
                        placed = True
                        moved_any = True
                        g = _plane(data["frame"])
                        me = next(
                            s for s in ships(data["frame"]) if s["chrome"] == 14
                        )
                        break
                if placed:
                    break
            if noop_hit and pulls == 0 and label == "-lead":
                break
            # Lag noops burn budget with zero progress — stop the haul.
            if noop_hit and label == "-lag":
                break
        return True

    if stacked:
        lead = sorted(band, key=lambda w: (-w[0], abs(w[1] - 34)))
        lag = sorted(band, key=lambda w: (w[0], abs(w[1] - 34)))
        lead_x0 = lead[0][0] if lead else 0
        post_seal = lead_x0 >= 40 and me["c"][0] < lead_x0 - 8
        print(
            f"  sync_east14 STACKED lead={lead[:1]} lag={lag[:3]} "
            f"ship={me['c']} post_seal={post_seal} "
            f"bud={step_budget(data['frame'])}"
        )
        if post_seal:
            # Lead already past seal — only haul western lag; never retouch lead.
            if me["c"][1] >= 33:
                lag2 = [w for w in lag if w[0] < lead_x0 - 2][:2]
                if lag2:
                    # One BFS step toward a pad west of lead — avoids noop spam.
                    g = _plane(data["frame"])
                    hauled = False
                    for wp in lag2:
                        if step_budget(data["frame"]) < 6 or pulls >= 2:
                            break
                        cur_now = count_free14(data["frame"], freeze15)
                        if wp not in cur_now:
                            continue
                        others = [c for c in cur_now if c != wp]
                        for pad in (
                            (lead_x0 - 6, 34),
                            (lead_x0 - 8, 34),
                            (lead_x0 - 6, 36),
                            (wp[0] + 6, 34),
                            (wp[0] + 5, 34),
                        ):
                            if pad[0] <= wp[0]:
                                continue
                            if near_any(pad, others + freeze15, cheb=5):
                                continue
                            nxt = floor_bfs(g, wp, pad, max_step=6)
                            if not nxt or nxt == wp:
                                continue
                            if near_any(nxt, others + freeze15, cheb=5):
                                continue
                            trial = [nxt if c == wp else c for c in cur_now]
                            tc = centroid(trial)
                            tci = (int(round(tc[0])), int(round(tc[1])))
                            if not ship_footprint_ok(g, *tci):
                                continue
                            data, newc, st = move_wp(sess, data, wp, nxt, freeze15)
                            print(
                                f"    sync14-lagbfs {wp}->{nxt} (pad{pad}) {st}->{newc} "
                                f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                            )
                            if st == "dead" or "frame" not in data:
                                return data, False
                            if st == "moved":
                                pulls += 1
                                moved_any = True
                                hauled = True
                                g = _plane(data["frame"])
                                break
                            # noop: stop — further tries burn bud
                            break
                        if hauled:
                            break
                    if not hauled and lag2:
                        if not _try_pull(lag2[:1], "-lag"):
                            return data, False
        elif me["c"][1] < 33:
            # Do not east-pull while ship sits in shallow poison — south first.
            print(
                f"  sync_east14 defer-east ship={me['c']} "
                f"bud={step_budget(data['frame'])}"
            )
        else:
            # Twin-lag merge DISABLED — live noops burned budget with 0 progress.
            west_lags = [w for w in lag if w[0] < lead_x0 - 4]
            if False and len(west_lags) >= 2 and pulls < 1 and step_budget(data["frame"]) >= 10:
                a, b = sorted(west_lags, key=lambda w: w[0])[:2]
                cheb_ab = max(abs(a[0] - b[0]), abs(a[1] - b[1]))
                if 3 <= cheb_ab <= 8:
                    g = _plane(data["frame"])
                    # Step a toward b until cheb<=3 (engine merges at <5).
                    dest = a
                    for _ in range(6):
                        dx = 0 if b[0] == dest[0] else (1 if b[0] > dest[0] else -1)
                        dy = 0 if b[1] == dest[1] else (1 if b[1] > dest[1] else -1)
                        nxt = (dest[0] + dx, dest[1] + dy)
                        if max(abs(b[0] - nxt[0]), abs(b[1] - nxt[1])) < 3:
                            break
                        if not (0 <= nxt[0] < 64 and 0 <= nxt[1] < 64):
                            break
                        if int(g[nxt[1], nxt[0]]) in (2, 10):
                            break
                        dest = nxt
                        if max(abs(b[0] - dest[0]), abs(b[1] - dest[1])) <= 3:
                            break
                    if dest != a:
                        data, newc, st = move_wp(sess, data, a, dest, freeze15)
                        print(
                            f"    sync14-merge-lag {a}->{dest} (→{b}) {st}->{newc} "
                            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                        )
                        if st == "dead" or "frame" not in data:
                            return data, False
                        if st == "moved":
                            pulls += 1
                            moved_any = True
                            g = _plane(data["frame"])
                            me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
                            cur = count_free14(data["frame"], freeze15)
                            band = [w for w in cur if 28 <= w[1] <= 38] or cur
                            lead = sorted(band, key=lambda w: (-w[0], abs(w[1] - 34)))
                            lag = sorted(band, key=lambda w: (w[0], abs(w[1] - 34)))
                            lead_x0 = lead[0][0] if lead else 0
            # Free shallow traps BEFORE any lead — else lead hop drops western flock.
            shallow_band = [w for w in band if 28 <= w[1] <= 32]
            if shallow_band and step_budget(data["frame"]) >= 6:
                g = _plane(data["frame"])
                wp = sorted(shallow_band, key=lambda w: w[1])[0]
                cur_now = count_free14(data["frame"], freeze15)
                # Prefer MERGE shallow into same-x southern sib (near_any blocks
                # separation; engine merges at cheb<5 — intentional).
                sibs_col = [
                    c
                    for c in cur_now
                    if c != wp and c[0] == wp[0] and c[1] >= 34
                ]
                if sibs_col and pulls < 1:
                    sib = sibs_col[0]
                    # Land at cheb=3 north of sib (merge range).
                    dest = (sib[0], sib[1] - 3)
                    if dest[1] < wp[1]:
                        dest = (sib[0], wp[1] + 2)  # step south toward sib
                    # Walk up to 4 cells toward sib.
                    dest = wp
                    for _ in range(5):
                        if max(abs(sib[0] - dest[0]), abs(sib[1] - dest[1])) <= 3:
                            break
                        dy = 1 if sib[1] > dest[1] else (-1 if sib[1] < dest[1] else 0)
                        dx = 0 if sib[0] == dest[0] else (1 if sib[0] > dest[0] else -1)
                        nxt = (dest[0] + dx, dest[1] + dy)
                        if not (0 <= nxt[0] < 64 and 0 <= nxt[1] < 64):
                            break
                        if int(g[nxt[1], nxt[0]]) in (2, 10):
                            break
                        dest = nxt
                    if dest != wp and max(abs(sib[0] - dest[0]), abs(sib[1] - dest[1])) <= 4:
                        # Do NOT near_any against sib — we want merge.
                        others = [c for c in cur_now if c != wp and c != sib]
                        if not near_any(dest, others + freeze15, cheb=5):
                            trial = [dest if c == wp else c for c in cur_now]
                            # Allow trial with dest near sib.
                            tc = centroid([c for c in trial if c != sib] + [sib])
                            tci = (int(round(tc[0])), int(round(tc[1])))
                            if True:  # merge-shallow: allow near sib
                                data, newc, st = move_wp(
                                    sess, data, wp, dest, freeze15
                                )
                                print(
                                    f"    sync14-merge-shallow {wp}->{dest} (→{sib}) "
                                    f"{st}->{newc} "
                                    f"n={len(r11l.waypoints(data['frame'])) if 'frame' in data else '?'} "
                                    f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                                )
                                if st == "dead" or "frame" not in data:
                                    return data, False
                                if st == "moved":
                                    pulls += 1
                                    moved_any = True
                                    g = _plane(data["frame"])
                                    me = next(
                                        s
                                        for s in ships(data["frame"])
                                        if s["chrome"] == 14
                                    )
                                    cur_now = count_free14(data["frame"], freeze15)
                                    band = [
                                        w
                                        for w in cur_now
                                        if 28 <= w[1] <= 38
                                    ] or cur_now
                                    lead = sorted(
                                        band,
                                        key=lambda w: (-w[0], abs(w[1] - 34)),
                                    )
                                    lag = sorted(
                                        band,
                                        key=lambda w: (w[0], abs(w[1] - 34)),
                                    )
                                    lead_x0 = lead[0][0] if lead else 0
                                    shallow_band = [
                                        w for w in band if 28 <= w[1] <= 32
                                    ]
                                else:
                                    # noop: do not retry merge-shallow this turn.
                                    pulls = max(pulls, 1)
                # Same-x southern blocker (e.g. 14,36 vs 14,31) — nudge it east first.
                blockers = [
                    c
                    for c in cur_now
                    if c != wp and c[0] == wp[0] and c[1] >= 34
                ]
                if blockers and pulls < 1:
                    blk = blockers[0]
                    others_b = [c for c in cur_now if c != blk]
                    for dest in (
                        (blk[0] + 6, blk[1]),
                        (blk[0] + 5, 34),
                        (blk[0] + 4, 36),
                        (blk[0] + 8, 34),
                    ):
                        if not (0 <= dest[0] < 64 and 0 <= dest[1] < 64):
                            continue
                        if int(g[dest[1], dest[0]]) not in (5, 3, 0, 6):
                            continue
                        if near_any(dest, others_b + freeze15, cheb=5):
                            continue
                        trial = [dest if c == blk else c for c in cur_now]
                        tc = centroid(trial)
                        tci = (int(round(tc[0])), int(round(tc[1])))
                        if not ship_footprint_ok(g, *tci):
                            continue
                        data, newc, st = move_wp(sess, data, blk, dest, freeze15)
                        print(
                            f"    sync14-clear-blocker {blk}->{dest} {st}->{newc} "
                            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                        )
                        if st == "dead" or "frame" not in data:
                            return data, False
                        if st == "moved":
                            pulls += 1
                            moved_any = True
                            g = _plane(data["frame"])
                            me = next(
                                s for s in ships(data["frame"]) if s["chrome"] == 14
                            )
                            cur_now = count_free14(data["frame"], freeze15)
                            band = [w for w in cur_now if 28 <= w[1] <= 38] or cur_now
                        break
                # Refresh shallow after blocker move.
                shallow_band = [w for w in band if 28 <= w[1] <= 32]
                if not shallow_band:
                    shallow_band = [w for w in cur_now if 28 <= w[1] <= 32]
                if shallow_band and pulls < 2:
                    wp = sorted(shallow_band, key=lambda w: w[1])[0]
                    others = [c for c in cur_now if c != wp]
                    for dest in (
                        (wp[0] + 6, 34),
                        (wp[0] + 8, 34),
                        (wp[0] + 6, 36),
                        (wp[0] + 4, 36),
                        (wp[0], 36),
                        (wp[0] + 2, 34),
                    ):
                        if not (0 <= dest[0] < 64 and 0 <= dest[1] < 64):
                            continue
                        if dest[1] < 33 or dest == wp:
                            continue
                        if int(g[dest[1], dest[0]]) not in (5, 3, 0, 6):
                            continue
                        if near_any(dest, others + freeze15, cheb=5):
                            continue
                        trial = [dest if c == wp else c for c in cur_now]
                        tc = centroid(trial)
                        tci = (int(round(tc[0])), int(round(tc[1])))
                        if not ship_footprint_ok(g, *tci):
                            continue
                        data, newc, st = move_wp(sess, data, wp, dest, freeze15)
                        print(
                            f"    sync14-lift-shallow {wp}->{dest} {st}->{newc} "
                            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                        )
                        if st == "dead" or "frame" not in data:
                            return data, False
                        if st == "moved":
                            pulls += 1
                            moved_any = True
                            # Stop this sync — lead same turn dropped mid wp on live.
                            after = next(
                                s for s in ships(data["frame"]) if s["chrome"] == 14
                            )["c"]
                            print(
                                f"  sync_east14 post-lift stop ship={after} "
                                f"bud={step_budget(data['frame'])}"
                            )
                            return data, True
                        break
                # Still shallow? Hold lead this turn (no force_east either).
                band_now = [
                    w
                    for w in count_free14(data["frame"], freeze15)
                    if 28 <= w[1] <= 38
                ]
                if any(28 <= w[1] <= 32 for w in band_now):
                    print(
                        f"  sync_east14 hold-lead shallow ship={me['c']} "
                        f"bud={step_budget(data['frame'])}"
                    )
                    after = next(
                        s for s in ships(data["frame"]) if s["chrome"] == 14
                    )["c"]
                    return data, after != before or pulls > 0 or moved_any
            # 2wp with lead far ahead: haul lag first — lone lead hop GAME_OVER'd.
            nfree_s = len(count_free14(data["frame"], freeze15))
            lag_gap = 0
            if lead and lag:
                lag_gap = lead[0][0] - lag[0][0]
            if nfree_s <= 2 and lag_gap > 8:
                print(
                    f"  sync_east14 2wp-lag-first gap={lag_gap} "
                    f"ship={me['c']} bud={step_budget(data['frame'])}"
                )
                if not _try_pull(lag[:1], "-lag"):
                    return data, False
            elif not _try_pull(lead[:1], "-lead"):
                return data, False
            # Always try one lag pull after lead (or instead) to unstick centroid.
            # Prefer y≥33 lag — shallow lag burns bud with weak ship movement.
            if pulls < 2 and step_budget(data["frame"]) >= 6:
                cur_l = count_free14(data["frame"], freeze15)
                band_l = [w for w in cur_l if 28 <= w[1] <= 38] or cur_l
                lead_x = max((w[0] for w in band_l), default=0)
                lag2 = sorted(
                    [w for w in band_l if w[0] < lead_x - 2 and w[1] >= 33],
                    key=lambda w: (w[0], abs(w[1] - 34)),
                )
                if not lag2:
                    lag2 = sorted(
                        [w for w in band_l if w[0] < lead_x - 2],
                        key=lambda w: (w[0], abs(w[1] - 34)),
                    )
                if lag2:
                    if not _try_pull(lag2[:2], "-lag"):
                        return data, False
    else:
        if me["c"][1] < 33:
            print(
                f"  sync_east14 defer-east ship={me['c']} "
                f"bud={step_budget(data['frame'])}"
            )
        else:
            lagging = sorted(band, key=lambda w: (w[0], abs(w[1] - 34)))
            print(
                f"  sync_east14 lag={lagging[:3]} ship={me['c']} "
                f"bud={step_budget(data['frame'])}"
            )
            if not _try_pull(lagging, ""):
                return data, False

    after = next(s for s in ships(data["frame"]) if s["chrome"] == 14)["c"]
    print(
        f"  sync_east14 ship {before}->{after} pulls={pulls} "
        f"bud={step_budget(data['frame'])}"
    )
    return data, after != before or pulls > 0


def force_east_step(sess, data, freeze15):
    """One body-safe east step of the easternmost corridor wp."""
    if step_budget(data["frame"]) < 5:
        return data, False
    cur = count_free14(data["frame"], freeze15)
    if len(cur) < 2:
        cur = free_wps_for(data["frame"], 14, freeze15)
    band = [w for w in cur if 24 <= w[1] <= 38] or list(cur)
    if not band:
        return data, False
    g = _plane(data["frame"])
    # Prefer easternmost corridor wp only — western nudges burn bud without
    # opening the seal and often GAME_OVER.
    ordered = sorted(band, key=lambda w: (-w[0], abs(w[1] - 34)))[:1]
    # Keep strides short while multi-wp — dx≥8 drops lagging wps on live.
    step_try = (
        ((4, 0), (5, 0), (6, 0), (4, 2), (4, -2), (5, 2), (3, 0))
        if len(cur) >= 3
        else ((8, 0), (6, 0), (4, 0), (5, 0), (4, 2), (4, -2), (3, 0), (5, 2))
    )
    for wp in ordered:
        for dx, dy in step_try:
            dest = (wp[0] + dx, wp[1] + dy)
            if not (0 <= dest[0] < 64 and 0 <= dest[1] < 64):
                continue
            if dest[1] > 38 or dest[1] < 30:
                continue
            if int(g[dest[1], dest[0]]) not in (5, 3, 0, 6):
                continue
            if near_any(dest, [c for c in cur if c != wp], cheb=5):
                continue
            if near_any(dest, freeze15, cheb=5):
                continue
            trial = [dest if c == wp else c for c in cur]
            tc = centroid(trial)
            tci = (int(round(tc[0])), int(round(tc[1])))
            if not ship_footprint_ok(g, *tci):
                continue
            if not centroid_path_ok(cur, trial, g):
                continue
            if any(max(abs(p[0] - tci[0]), abs(p[1] - tci[1])) < 3 for p in trial):
                continue
            before = next(s for s in ships(data["frame"]) if s["chrome"] == 14)["c"]
            data, newc, st = move_wp(sess, data, wp, dest, freeze15)
            print(
                f"  force_east {wp}->{dest} {st}->{newc} "
                f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
                f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
            )
            if st == "dead" or "frame" not in data:
                return data, False
            if st == "moved":
                me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
                return data, me["c"] != before
            return data, False
    print(f"  force_east none band={band} cur={cur} freeze15={freeze15}")
    return data, False


def emergency_nudge14(sess, data, freeze15, lv0, blacklist=None):
    """When reshape is frozen near the neck, nudge the lagging wp south/east."""
    if step_budget(data["frame"]) < 8:
        return data, False
    if blacklist is None:
        blacklist = set()
    cur = count_free14(data["frame"], freeze15)
    if len(cur) < 2:
        cur = free_wps_for(data["frame"], 14, freeze15)
    if len(cur) < 2:
        return data, False
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    g = _plane(data["frame"])
    # Approach choke: pull NORTH-most wps south (south-most often already at y=36).
    if me["c"][1] < 33:
        # Prefer clearing shallow corridor first, THEN seed east lead.
        # (Lead-first left (14,32) blocking north (14,25)→(14,31).)
        ordered = sorted(
            cur,
            key=lambda w: (
                0 if 28 <= w[1] <= 32 else 1,  # shallow first
                0 if (w[1] < 30 and w[0] >= 20) else 1,  # then deep-north lead seed
                w[1],
                -w[0],
            ),
        )
        cand_deltas = [
            (0, 4),   # (14,32)→(14,36)
            (0, 5),
            (4, 8),   # (24,25)→(28,33) lead seed
            (4, 6),
            (6, 8),
            (2, 8),
            (2, 4),
            (-2, 4),
            (1, 3),
            (-1, 3),
            (3, 3),
            (4, 4),
            (-4, 4),
            (0, 3),
            (2, 2),
            (4, 0),
        ]
    else:
        ordered = sorted(cur, key=lambda w: (-w[0], -w[1]))
        cand_deltas = [(4, 0), (6, 0), (3, 3), (4, 2), (2, 0), (0, 2), (3, 0)]
    max_attempts = 2 if step_budget(data["frame"]) < 16 else 5
    attempts = 0
    for wp in ordered[:4]:
        for dx, dy in cand_deltas:
            if attempts >= max_attempts:
                print(f"  nudge14 none cur={cur} ship={me['c']} attempts={attempts}")
                return data, False
            dest = (wp[0] + dx, wp[1] + dy)
            if (wp, dest) in blacklist:
                continue
            if not (0 <= dest[0] < 64 and 0 <= dest[1] < 64):
                continue
            max_south = 36 if me["c"][1] < 34 else min(38, me["c"][1] + 3)
            if dest[1] > max_south:
                continue
            # Avoid parking deep-north wp as lead — (28,33) from (24,25) leaves
            # flock split; prefer corridor y≥34 when ship is already near choke.
            if me["c"][1] >= 28 and dest[1] < 34 and wp[1] < 30:
                # Allow only if dest reaches at least y=33
                if dest[1] < 33:
                    continue
            if int(g[dest[1], dest[0]]) in (2, 10):
                continue
            sep = 5
            if near_any(dest, [c for c in cur if c != wp], cheb=sep):
                continue
            if near_any(dest, freeze15, cheb=6):
                continue
            trial = [dest if c == wp else c for c in cur]
            tc = centroid(trial)
            tci = (int(round(tc[0])), int(round(tc[1])))
            if not ship_footprint_ok(g, tci[0], tci[1]):
                continue
            if any(max(abs(p[0] - tci[0]), abs(p[1] - tci[1])) < 3 for p in trial):
                continue
            if me["c"][1] >= 33 and not centroid_path_ok(cur, trial, g, samples=8):
                continue
            data, newc, st = move_wp(sess, data, wp, dest, freeze15)
            attempts += 1
            if st in ("dead", "error") or "frame" not in data:
                return data, False
            print(
                f"  nudge14 {wp}->{dest} {st}->{newc} "
                f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c']} "
                f"bud={step_budget(data['frame'])}"
            )
            if st == "moved":
                return data, True
            blacklist.add((wp, dest))
            if step_budget(data["frame"]) < 12:
                return data, False
    print(f"  nudge14 none cur={cur} ship={me['c']} attempts={attempts}")
    return data, False


def leap14_east_once(sess, data, freeze15, lv0, stride=6):
    """Body-safe east hop after the y≈34 neck using reshape_to_pads."""
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    goal = goals_by_chrome(data["frame"])[14]
    fine = clearance_path(data["frame"], me["c"], goal, step=1)
    if not fine:
        return data, False
    idx = min(
        range(len(fine)),
        key=lambda i: abs(fine[i][0] - me["c"][0]) + abs(fine[i][1] - me["c"][1]),
    )
    g = _plane(data["frame"])
    flock = count_free14(data["frame"], freeze15)
    n = 2 if len(flock) < 4 else 4
    if len(flock) < 2:
        print(f"  east14 flock too small {flock}")
        return data, False
    before = me["c"]
    bud0 = step_budget(data["frame"])
    if bud0 < 6:
        return data, False

    # Skip collapse for now — short-walk rarely merges and burns nothing useful.
    # (Re-enable once keepers stay east of stragglers mid-corridor.)

    # Near choke: up to 3 south nudges. Order matters:
    # 1) clear shallow (14,32)→(14,36)  2) seed lead (24,25)→(28,33)
    # Stop only when lead exists AND no y∈[28,32] shallow remains.
    # Skip when west_south already planted ≥2 corridor leads — nudge merges them.
    flock0 = count_free14(data["frame"], freeze15)
    corridor0 = [w for w in flock0 if w[1] >= 33]
    shallow0 = [w for w in flock0 if 28 <= w[1] <= 32]
    if me["c"][1] < 32 and not (len(corridor0) >= 2 and not shallow0):
        moved_any = False
        bl: set = set()
        bud_south0 = step_budget(data["frame"])
        for _burst in range(4):
            if step_budget(data["frame"]) < 8:
                break
            if bud_south0 - step_budget(data["frame"]) >= 12:
                break
            me_b = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            flock_b = count_free14(data["frame"], freeze15)
            lead_x = max((w[0] for w in flock_b), default=0)
            shallow_b = [w for w in flock_b if 28 <= w[1] <= 32]
            if me_b["c"][1] >= 32 and lead_x >= 28 and not shallow_b:
                break
            before_b = me_b["c"]
            data, _ = emergency_nudge14(sess, data, freeze15, lv0, blacklist=bl)
            if "frame" not in data or data.get("state") == "GAME_OVER":
                return data, False
            me_a = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            if me_a["c"] != before_b:
                moved_any = True
                me = me_a
                continue
            break
        if me["c"][1] < 28:
            if moved_any:
                print(
                    f"  east14 south-burst ship={me['c']} "
                    f"bud={step_budget(data['frame'])}"
                )
                return data, True
            elif step_budget(data["frame"]) < 8:
                return data, False
            else:
                print("  east14 south stuck → east anyway")
        else:
            print(
                f"  east14 south-burst ship={me['c']} "
                f"bud={step_budget(data['frame'])}"
            )

    # At neck with 4wp and enough bud: collapse to 2wp for longer east strides.
    # Skip when stragglers are too far — partial collapse burns 3 and leaves 3wp.
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    flock = count_free14(data["frame"], freeze15)
    if (
        me["c"][1] >= 31
        and len(flock) >= 4
        and step_budget(data["frame"]) >= 18
    ):
        keepers = sorted(flock, key=lambda w: (-w[0], -w[1]))[:2]
        stragglers = [w for w in flock if w not in keepers]
        cheap = all(
            min(max(abs(s[0] - k[0]), abs(s[1] - k[1])) for k in keepers) <= 8
            for s in stragglers
        )
        # Baseline needed collapse of deep-north (14,25) even when "far".
        must = any(s[1] <= 32 for s in stragglers)
        if cheap or must:
            data, ok_c = collapse14_to_2wp(sess, data, freeze15, lv0)
            if data.get("state") == "GAME_OVER" or "frame" not in data:
                return data, False
            if ok_c:
                print(
                    f"  east14 collapsed flock={count_free14(data['frame'], freeze15)} "
                    f"bud={step_budget(data['frame'])}"
                )
        else:
            print(
                f"  east14 skip-collapse far-stragglers={stragglers} "
                f"keepers={keepers} bud={step_budget(data['frame'])}"
            )

    # East corridor: bigger strides when budget allows.
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    fine = clearance_path(data["frame"], me["c"], goal, step=1)
    if not fine:
        return data, False
    idx = min(
        range(len(fine)),
        key=lambda i: abs(fine[i][0] - me["c"][0]) + abs(fine[i][1] - me["c"][1]),
    )
    bud_now = step_budget(data["frame"])
    st = 10 if bud_now >= 18 else max(stride, 6)
    hop = fine[min(idx + st, len(fine) - 1)]
    for j in range(idx + 1, min(idx + st + 10, len(fine))):
        if fine[j][1] >= 33 and fine[j][0] >= me["c"][0] + 3:
            hop = fine[j]
            if fine[j][0] >= me["c"][0] + st:
                break
    g = _plane(data["frame"])
    flock = count_free14(data["frame"], freeze15)
    n = 2 if len(flock) < 4 else 4
    pads = pads_east(g, hop, n)
    if len(pads) < n:
        hx, hy = hop
        pads = [(hx, hy - 5), (hx + 5, hy), (hx, hy + 4), (hx - 5, hy)]
        pads = [p for p in pads if 0 <= p[0] < 64 and 0 <= p[1] < 64]

    before = me["c"]
    ok = False
    # Corridor band: lagging-wp sync leaps — do this BEFORE pad reshape.
    # Allow from y≥28 (south-once often lands at 29).
    if me["c"][1] >= 28 and bud_now >= 6:
        data, ok = sync_east14(sess, data, freeze15, stride=10 if bud_now >= 14 else 6)
        if "frame" not in data or data.get("state") == "GAME_OVER":
            return data, False
        me2 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        if me2["c"][0] > before[0]:
            return data, True
        if ok and me2["c"] != before:
            return data, True
    # Fallback: if still shallow (y<33), nudge south — do NOT force_east (poisons).
    if me["c"][1] >= 28:
        me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        if me["c"][1] < 33:
            data, nudged = emergency_nudge14(sess, data, freeze15, lv0)
            if nudged:
                me2 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
                print(
                    f"  east14 shallow-nudge ship={me2['c']} "
                    f"bud={step_budget(data['frame'])}"
                )
                return data, True
            return data, False
        flock_f = count_free14(data["frame"], freeze15)
        if any(28 <= w[1] <= 32 for w in flock_f):
            print(
                f"  east14 skip-force shallow={ [w for w in flock_f if 28<=w[1]<=32] } "
                f"bud={step_budget(data['frame'])}"
            )
            return data, False
        data, forced = force_east_step(sess, data, freeze15)
        if forced:
            me2 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            print(
                f"  east14 force-first ship={me2['c']} "
                f"bud={step_budget(data['frame'])}"
            )
            return data, True
        # Pull lagging west wps east even if lead is sealed — dual pull.
        data, ok = sync_east14(sess, data, freeze15, stride=6)
        if "frame" in data and ok:
            me2 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            if me2["c"] != before:
                return data, True
        return data, False

    if len(pads) < n:
        print(f"  east14 no pads at {hop} n={n} got={pads}")
        return force_east_step(sess, data, freeze15)

    if "frame" not in data or data.get("state") == "GAME_OVER":
        return data, False
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    dist = abs(me["c"][0] - goal[0]) + abs(me["c"][1] - goal[1])
    moved = me["c"][0] > before[0] or manh(me["c"], before) >= 2
    print(
        f"  east14 ship={me['c']} dist={dist} ok={ok} moved={moved} "
        f"bud={step_budget(data['frame'])} (Δ{bud0 - step_budget(data['frame'])})"
    )
    if not moved:
        data, forced = force_east_step(sess, data, freeze15)
        if forced:
            return data, True
        if bud0 >= 12:
            data, nudged = emergency_nudge14(sess, data, freeze15, lv0)
            return data, nudged
    return data, dist <= 8 or moved



def leap14_west_south(sess, data, freeze15, lv0):
    """Lean west-wall descent: 2-3 long south pulls instead of a full diamond.

    After hop1 lands on x~19/y~18, a second 5-move diamond burns ~15 and still
    needs a south-burst. Prefer planting corridor leads at y>=33 with fewer moves.
    """
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    if not (me["c"][0] <= 22 and me["c"][1] < 28):
        return data, False
    if step_budget(data["frame"]) < 14:
        return data, False
    before = me["c"]
    bud0 = step_budget(data["frame"])
    g = _plane(data["frame"])
    cur = count_free14(data["frame"], freeze15)
    print(f"  west_south begin ship={me['c']} cur={cur} bud={bud0}")
    ordered = sorted(cur, key=lambda w: (-w[1], abs(w[0] - 19), -w[0]))
    moves = 0
    for wp in ordered:
        if moves >= 3 or step_budget(data["frame"]) < 10:
            break
        me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        if me["c"][1] >= 28:
            break
        cur = count_free14(data["frame"], freeze15)
        if wp not in cur:
            continue
        others = [c for c in cur if c != wp]
        dest = None
        cands = []
        if wp[1] < 28:
            # Stagger landings so 3 south pulls don't stack on y=36 and merge.
            cands.extend([
                (24, 33), (28, 34), (14, 36), (20, 36),
                (wp[0], 34), (wp[0] + 4, 34), (wp[0] + 6, 33),
                (wp[0], 36), (wp[0] + 4, 36), (wp[0] - 2, 35),
            ])
            for ty in (34, 33, 36, 35):
                for ox in (0, 4, 6, -2, 2, 8):
                    cands.append((wp[0] + ox, ty))
        else:
            for ox in (4, 6, 8, 0):
                cands.append((wp[0] + ox, min(36, wp[1] + 4)))
        for t in cands:
            if not (0 <= t[0] < 64 and 0 <= t[1] < 64):
                continue
            if t == wp or t[1] < 33:
                continue
            if int(g[t[1], t[0]]) not in (5, 3, 0, 6):
                continue
            if near_any(t, others + freeze15, cheb=5):
                continue
            travel = abs(t[0] - wp[0]) + abs(t[1] - wp[1])
            if travel < 4 or travel > 22:
                continue
            trial = [t if c == wp else c for c in cur]
            tc = centroid(trial)
            tci = (int(round(tc[0])), int(round(tc[1])))
            if not ship_footprint_ok(g, *tci):
                continue
            dest = t
            break
        if dest is None:
            continue
        data, newc, st = move_wp(sess, data, wp, dest, freeze15)
        moves += 1
        print(
            f"    west_south {wp}->{dest} {st}->{newc} "
            f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or "frame" not in data:
            return data, False
        if st == "noop":
            continue
        if st == "moved":
            g = _plane(data["frame"])
    if "frame" not in data:
        return data, False
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    moved = me["c"] != before or me["c"][1] > before[1]
    print(
        f"  west_south end ship={me['c']} moves={moves} "
        f"bud={step_budget(data['frame'])} (d{bud0 - step_budget(data['frame'])})"
    )
    return data, moved


def leap14_once(sess, data, freeze15, lv0, stride=12):
    """One coarse hop for chrome14 along clearance path."""
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    goal = goals_by_chrome(data["frame"])[14]
    # Already on/past neck → dedicated east hopper.
    if me["c"][1] >= 34 and me["c"][0] >= 20:
        return leap14_east_once(sess, data, freeze15, lv0, stride=6)
    # West wall lean-south DISABLED (2026-09-09): accidental 2wp then
    # lead (34,34)->(38,34) GAME_OVER. Keep classic diamond hops.
    if False and me["c"][0] <= 22 and 16 <= me["c"][1] < 28:
        data, ok = leap14_west_south(sess, data, freeze15, lv0)
        if data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        if me["c"][1] >= 27:
            return leap14_east_once(sess, data, freeze15, lv0, stride=6)
        # Leads already in corridor: skip second diamond even if ship still y<27.
        flock = count_free14(data["frame"], freeze15)
        corridor_leads = [w for w in flock if w[1] >= 33]
        # Need ship y>=28 — handing off at y=25 burns a dead east turn + nudge.
        if len(corridor_leads) >= 2 and me["c"][1] >= 28:
            print(f"  west_south handoff leads={corridor_leads} ship={me['c']}")
            return leap14_east_once(sess, data, freeze15, lv0, stride=6)
        if ok:
            return data, True
    fine = clearance_path(data["frame"], me["c"], goal, step=1)
    if not fine:
        return data, False
    ni = next((i for i, c in enumerate(fine) if c[1] >= 34 and 18 <= c[0] <= 24), None)
    if ni is None:
        ni = next((i for i, c in enumerate(fine) if c[1] >= 34 and c[0] >= 20), None)
    g = _plane(data["frame"])
    neck = (20, 34)
    if me["c"][1] < 34 and me["c"][0] <= 30:
        if ship_footprint_ok(g, *neck):
            hop = neck
        elif ni is not None:
            hop = fine[ni]
        else:
            hop = fine[min(stride, len(fine) - 1)]
        # Already on west wall mid-corridor: prefer neck over a mid hop that
        # plants y=25 pads. Mid is still used while descending from y≈18.
        if me["c"][1] < 28 and abs(me["c"][0] - neck[0]) + abs(me["c"][1] - neck[1]) >= 14:
            mid_i = min(stride, ni if ni is not None else stride, len(fine) - 1)
            mid = fine[mid_i]
            if mid[1] < 34 and mid[0] <= neck[0] + 2:
                hop = mid
        # Already on/past choke — hand off to east hopper.
        if hop == neck and me["c"][1] >= 33 and me["c"][0] >= 19:
            return leap14_east_once(sess, data, freeze15, lv0, stride=4)
    elif ni is not None and me["c"][1] < 34:
        hop = fine[ni]
    else:
        hop = fine[min(max(stride, 14), len(fine) - 1)]
    pads = pads_at(g, hop, 4)
    if len(pads) < 4:
        print(f"  leap14 no pads at {hop}")
        data, nudged = emergency_nudge14(sess, data, freeze15, lv0)
        return data, nudged
    before = me["c"]
    # Near choke (y≥27): hand off — don't burn neck diamond.
    if hop == neck and me["c"][1] >= 27 and me["c"][0] <= 24:
        print(
            f"  leap14 near-neck handoff ship={me['c']} "
            f"bud={step_budget(data['frame'])}"
        )
        if me["c"][1] < 33:
            data, _ = emergency_nudge14(sess, data, freeze15, lv0)
            if data.get("state") == "GAME_OVER" or "frame" not in data:
                return data, False
        return leap14_east_once(sess, data, freeze15, lv0, stride=8)
    # Classic west: always max_moves=5 — cap 4 merges / incomplete diamonds.
    cap = 5
    data, ok = reshape_to_pads(
        sess,
        data,
        14,
        freeze15,
        pads,
        lv0,
        label=f"14@{hop}",
        max_moves=cap,
        early_ship_dist=0,
    )
    if "frame" not in data or data.get("state") == "GAME_OVER":
        return data, False
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    dist = abs(me["c"][0] - goal[0]) + abs(me["c"][1] - goal[1])
    moved = abs(me["c"][0] - before[0]) + abs(me["c"][1] - before[1]) >= 2
    print(
        f"  leap14 ship={me['c']} dist={dist} ok={ok} moved={moved} "
        f"bud={step_budget(data['frame'])}"
    )
    if not moved:
        data, nudged = emergency_nudge14(sess, data, freeze15, lv0)
        if nudged and "frame" in data:
            return data, True
    return data, dist <= 8 or moved


def clear15_corridor(sess, data, freeze14):
    """Move chrome15 wps off y≈34 east-corridor so chrome14 can advance past x≈30.

    L3 enter parks 15 at ~(37,34)/(52,40); near_locked(cheb=5) then blocks
    any 14 dest near (37,34) — e.g. (31,36)→(39,36).

    CRITICAL: only touch lock_other_ship(..., 14) wps — free_wps_for(15)
    can steal chrome14's eastern lead once it drifts toward ship15.
    """
    if step_budget(data["frame"]) < 6:
        return data, False
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    # Authoritative chrome15 flock = what we freeze while moving 14.
    flock15 = lock_other_ship(data["frame"], 14)
    # Only the seal park ~(37,34) — never touch x≥42 (chrome14 lead after seal-jump
    # sits there and lock_other_ship falsely attributes it to 15).
    blockers = [
        w
        for w in flock15
        if 30 <= w[1] <= 38
        and 28 <= w[0] <= 40
        and (
            manh(w, me15["c"]) + 6 < manh(w, me14["c"])
            # Corridor seal must clear even after 14 advances (manh gap shrinks).
            or manh(w, me15["c"]) <= 16
        )
    ]
    if not blockers:
        return data, False
    g = _plane(data["frame"])
    goal = goals_by_chrome(data["frame"])[15]
    # Prefer the westernmost corridor blocker (the one sealing 14's path).
    wp = min(blockers, key=lambda w: (w[0], abs(w[1] - 34)))
    others = [c for c in flock15 if c != wp]
    free14 = [
        w["c"]
        for w in r11l.waypoints(data["frame"])
        if w["c"] not in flock15
    ]
    # Vacate the seal cell: prefer EAST first (away from chrome14's approach),
    # then south. Going SW toward (34,40) collides with 14 once lead is at (31,36).
    anchors = [
        (48, 50),
        (45, 52),
        (50, 46),
        (42, 50),
        (43, 45),
        (48, 40),
        (45, 42),
        (34, 52),
        goal,
    ]
    cands = []
    for tgt in anchors:
        nxt = floor_bfs(g, wp, tgt, max_step=12)
        if nxt is not None and nxt != wp:
            cands.append(nxt)
    for dy, dx in (
        (0, 6),
        (0, 8),
        (2, 6),
        (4, 6),
        (6, 4),
        (6, 0),
        (8, -2),
        (4, 4),
        (2, 4),
    ):
        cands.append((wp[0] + dx, min(60, wp[1] + dy)))
    seen = set()
    ordered = []
    for dest in sorted(
        cands,
        key=lambda t: (
            0 if t[0] >= 40 else 1,  # east vacate first
            0 if t[1] >= 40 else 1,
            abs(t[0] - goal[0]) + abs(t[1] - goal[1]),
        ),
    ):
        if dest in seen or dest == wp:
            continue
        seen.add(dest)
        ordered.append(dest)
    for dest in ordered[:14]:
        if not (0 <= dest[0] < 64 and 0 <= dest[1] < 64):
            continue
        # Must leave cheb-5 bubble around seal so 14 can use (39,36).
        if max(abs(dest[0] - wp[0]), abs(dest[1] - wp[1])) < 5:
            continue
        if int(g[dest[1], dest[0]]) not in (5, 3, 0, 6, 1):
            continue
        if near_any(dest, others + freeze14, cheb=5):
            continue
        if near_any(dest, free14, cheb=5):
            continue
        data, newc, st = move_wp(sess, data, wp, dest, freeze14)
        print(
            f"  clear15_corridor {wp}->{dest} {st}->{newc} "
            f"ship15={next(s for s in ships(data['frame']) if s['chrome']==15)['c'] if 'frame' in data else '?'} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or "frame" not in data:
            return data, False
        if st == "moved":
            return data, True
        if step_budget(data["frame"]) < 6:
            return data, False
    print(f"  clear15_corridor none blockers={blockers}")
    return data, False


def wave15_once(sess, data, freeze14, lv0, stride=22):
    """Reshape onto OFFS15 then one sync leap along clearance path."""
    if step_budget(data["frame"]) < 14:
        print("  wave15 skip low bud")
        return data, False
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    goal = goals_by_chrome(data["frame"])[15]
    dist0 = abs(me["c"][0] - goal[0]) + abs(me["c"][1] - goal[1])
    # Near goal: aim offsets at the goal itself.
    if dist0 <= 18:
        targets = [(goal[0] + o[0], goal[1] + o[1]) for o in OFFS15]
        before = me["c"]
        data, ok = sync_to(sess, data, freeze14, targets, "15goal")
        me = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
        dist = abs(me["c"][0] - goal[0]) + abs(me["c"][1] - goal[1])
        moved = me["c"] != before
        print(
            f"  wave15goal ship={me['c']} dist={dist} ok={ok} moved={moved} "
            f"bud={step_budget(data['frame'])}"
        )
        return data, dist <= 5 or moved
    # Ensure flock is on the verified offset pair before leaping.
    here = [(me["c"][0] + o[0], me["c"][1] + o[1]) for o in OFFS15]
    data, _ = sync_to(sess, data, freeze14, here, "15reshape")
    if (data.get("levels_completed") or 0) >= 3:
        return data, True
    if data.get("state") == "GAME_OVER" or "frame" not in data:
        return data, False
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    fine = clearance_path(data["frame"], me["c"], goal, step=1)
    if not fine:
        return data, False
    hop = fine[min(max(stride, 10), len(fine) - 1)]
    targets = [(hop[0] + o[0], hop[1] + o[1]) for o in OFFS15]
    before = me["c"]
    data, ok = sync_to(sess, data, freeze14, targets, f"15@{hop}")
    if "frame" not in data:
        return data, False
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    dist = abs(me["c"][0] - goal[0]) + abs(me["c"][1] - goal[1])
    moved = me["c"] != before
    print(
        f"  wave15 ship={me['c']} dist={dist} ok={ok} moved={moved} "
        f"bud={step_budget(data['frame'])}"
    )
    return data, dist <= 5 or moved


def haul15_toward(sess, data, goal15, *, max_step=8, label="haul15", _unused=None):
    """Move one chrome15 wp. Live: clearance is EAST then SOUTH — never SW early."""
    if step_budget(data["frame"]) < 8:
        return data, False
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    freeze14 = lock_other_ship(data["frame"], 15)
    flock15 = list(lock_other_ship(data["frame"], 14))
    if not flock15:
        flock15 = [
            w["c"]
            for w in r11l.waypoints(data["frame"])
            if manh(w["c"], me15["c"]) + 2 < manh(w["c"], me14["c"])
        ]
    flock15 = [
        c for c in flock15 if manh(c, me15["c"]) <= manh(c, me14["c"]) + 4
    ]
    if not flock15:
        print(f"  {label} no chrome15 flock ship15={me15['c']}")
        return data, False
    g = _plane(data["frame"])
    # Prefer western wp that still seals 14's SE (x~40), else nearest to ship.
    ordered = sorted(
        flock15,
        key=lambda w: (w[0], abs(w[1] - me15["c"][1])),
    )
    print(f"  {label} flock15={ordered[:3]} goal={goal15} ship15={me15['c']}")

    # Prefer clearance hop (east-then-south) when available.
    fine = clearance_path(data["frame"], me15["c"], goal15, step=1)
    hop = None
    if fine and len(fine) > 4:
        hop = fine[min(max(max_step, 6), len(fine) - 1)]

    for wp in ordered[:2]:
        cands = []
        if hop is not None:
            # Aim this wp toward hop+OFFS-ish, but keep single-wp move.
            cands.append(
                (
                    wp[0] + max(-2, min(6, hop[0] - me15["c"][0])),
                    wp[1] + max(0, min(4, hop[1] - me15["c"][1])),
                )
            )
        # East / SE / soft south only while y < 50. West only when already deep south.
        if wp[1] < 50:
            deltas = (
                (4, 0),
                (6, 0),
                (4, 2),
                (6, 2),
                (2, 2),
                (0, 2),
                (4, 3),
                (0, 3),
                (8, 0),
            )
        else:
            deltas = (
                (-4, 2),
                (-6, 0),
                (-4, 0),
                (0, 2),
                (-2, 2),
                (0, 3),
            )
        for dx, dy in deltas:
            cands.append((wp[0] + dx, min(60, wp[1] + dy)))
        seen = set()
        for nxt in cands:
            if nxt in seen or nxt == wp:
                continue
            seen.add(nxt)
            if not (0 <= nxt[0] < 64 and 0 <= nxt[1] < 64):
                continue
            if nxt[1] - wp[1] > 3:
                continue
            if near_any(nxt, freeze14, cheb=5):
                continue
            if near_any(nxt, [c for c in flock15 if c != wp], cheb=5):
                continue
            if max(abs(nxt[0] - wp[0]), abs(nxt[1] - wp[1])) < 2:
                continue
            trial = [nxt if c == wp else c for c in flock15]
            # If flock incomplete, still require destination cell soft-ok.
            tc = centroid(trial)
            tci = (int(round(tc[0])), int(round(tc[1])))
            if not ship_footprint_ok(g, *tci):
                continue
            if not centroid_path_ok(flock15, trial, g, samples=8):
                continue
            data, newc, st = move_wp(sess, data, wp, nxt, freeze14)
            print(
                f"  {label} {wp}->{nxt} {st}->{newc} "
                f"ship15={next(s for s in ships(data['frame']) if s['chrome']==15)['c'] if 'frame' in data else '?'} "
                f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
            )
            if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                return data, False
            if st == "moved":
                return data, True
            break  # one noop per wp — save bud
    return data, False


def advance_14_frog_ny_stack(sess, data, goal15):
    """Post mid-east: deep15 → leadS+4 → frog → Ny36 → S40 → N(43,38).

    Live-probed:
      east15 (52,40)→(58,42), west15 (41,40)→(48,42);
      then frog-ny to free=(43,38)+(40,44), ship~(34,38) d14≈36 bud≈10.
    N(43,38) works under deep15; same-col south (43,40/42) noop; (42,40/42/45/46) dead.
    """
    if step_budget(data["frame"]) < 16:
        return data, False
    freeze15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], freeze15)
    if len(free) != 2:
        return data, False

    # Deep vacate chrome15: push east wp first so west can reach (48,42).
    freeze14 = lock_other_ship(data["frame"], 15)
    flock15 = list(lock_other_ship(data["frame"], 14))
    if flock15 and step_budget(data["frame"]) >= 8:
        west15 = min(flock15, key=lambda w: w[0])
        east15 = max(flock15, key=lambda w: w[0])
        if west15[0] >= 47 and west15[1] >= 41:
            print(f"  frog-ny 15deep skip (already {west15})")
        else:
            # east first
            if east15[0] < 56:
                for tgt in ((58, 42), (56, 44), (58, 40)):
                    if max(abs(tgt[0] - west15[0]), abs(tgt[1] - west15[1])) < 5:
                        continue
                    if near_any(tgt, list(freeze14), cheb=5):
                        continue
                    data, newc, st = move_wp(sess, data, east15, tgt, freeze14)
                    print(f"  frog-ny east15 {east15}->{tgt} {st}->{newc}")
                    if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                        return data, False
                    if st == "moved":
                        freeze14 = lock_other_ship(data["frame"], 15)
                        flock15 = list(lock_other_ship(data["frame"], 14))
                        west15 = min(flock15, key=lambda w: w[0])
                        east15 = max(flock15, key=lambda w: w[0])
                        break
            # Prefer direct west→(42,50) after east@(58,42): skips (48,42) hop,
            # saves ~2 bud; Ne then lands d14=34 with bud≈6 (live).
            moved15 = False
            for tgt in ((42, 50), (48, 42), (46, 42), (50, 42), (45, 42)):
                if max(abs(tgt[0] - east15[0]), abs(tgt[1] - east15[1])) < 5:
                    continue
                if near_any(tgt, list(freeze14), cheb=5):
                    continue
                data, newc, st = move_wp(sess, data, west15, tgt, freeze14)
                print(f"  frog-ny west15 {west15}->{tgt} {st}->{newc}")
                if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                    return data, False
                if st == "moved":
                    moved15 = True
                    freeze14 = lock_other_ship(data["frame"], 15)
                    flock15 = list(lock_other_ship(data["frame"], 14))
                    west15 = min(flock15, key=lambda w: w[0])
                    east15 = max(flock15, key=lambda w: w[0])
                    break
            if not moved15:
                data, _ = haul15_toward(
                    sess, data, goal15, max_step=4, label="15soft"
                )
                if data.get("state") == "GAME_OVER" or "frame" not in data:
                    return data, False
            # Deeper south vacate (live zigzag toward goal):
            # Prefer already@(42,50); else (48,42)→(42,50)→east(58,50).
            # Keep east at x≥56 — east@(48,54) makes mid-corridor leadS DEAD.
            # Leave ≥12 bud for frog when possible.
            if step_budget(data["frame"]) >= 10:
                freeze14 = lock_other_ship(data["frame"], 15)
                flock15 = list(lock_other_ship(data["frame"], 14))
                west15 = min(flock15, key=lambda w: w[0])
                east15 = max(flock15, key=lambda w: w[0])
                if west15[1] < 48 and west15[0] > 42:
                    tgt = (42, 50)
                    if max(abs(tgt[0] - east15[0]), abs(tgt[1] - east15[1])) >= 5 and not near_any(
                        tgt, list(freeze14), cheb=5
                    ):
                        data, newc, st = move_wp(sess, data, west15, tgt, freeze14)
                        print(f"  frog-ny west15b {west15}->{tgt} {st}->{newc}")
                        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                            return data, False
                        if st == "moved":
                            freeze14 = lock_other_ship(data["frame"], 15)
                            flock15 = list(lock_other_ship(data["frame"], 14))
                            west15 = min(flock15, key=lambda w: w[0])
                            east15 = max(flock15, key=lambda w: w[0])
                if east15[1] < 48 and step_budget(data["frame"]) >= 6:
                    for tgt in ((58, 50), (56, 48), (58, 48)):
                        if max(abs(tgt[0] - west15[0]), abs(tgt[1] - west15[1])) < 5:
                            continue
                        if near_any(tgt, list(freeze14), cheb=5):
                            continue
                        data, newc, st = move_wp(sess, data, east15, tgt, freeze14)
                        print(f"  frog-ny east15b {east15}->{tgt} {st}->{newc}")
                        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                            return data, False
                        if st == "moved":
                            freeze14 = lock_other_ship(data["frame"], 15)
                            flock15 = list(lock_other_ship(data["frame"], 14))
                            west15 = min(flock15, key=lambda w: w[0])
                            east15 = max(flock15, key=lambda w: w[0])
                            break
                # Skip deeper zig (38,52)/(42,54): burns ~5 bud; S→(48,42)+Ne
                # under west@(42,50)+east@(58,50) reaches d14=34 bud≈6.
                # (38,50)/(34,54) make S40 DEAD — still banned if ever re-enabled.
                print(
                    f"  frog-ny zig skip (save bud) west={west15} "
                    f"bud={step_budget(data['frame'])}"
                )
    if data.get("state") == "GAME_OVER" or "frame" not in data:
        return data, False

    freeze15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], freeze15)
    if len(free) != 2:
        return data, False
    lead = max(free, key=lambda w: w[0])
    lag = min(free, key=lambda w: w[0])
    print(
        f"--- L3 frog-ny stack ship="
        f"{next(s for s in ships(data['frame']) if s['chrome']==14)['c']} "
        f"lead={lead} lag={lag} bud={step_budget(data['frame'])} ---"
    )
    data, newc, st = move_wp(
        sess, data, lead, (lead[0], lead[1] + 4), freeze15
    )
    print(f"  frog-ny leadS {lead}->{(lead[0], lead[1]+4)} {st}->{newc}")
    if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
        return data, False
    if st != "moved":
        return data, False

    freeze15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], freeze15)
    if len(free) != 2:
        return data, False
    lead = max(free, key=lambda w: (w[1], w[0]))
    lag = min(free, key=lambda w: (w[1], w[0]))
    frog = (lag[0] + 2, lead[1] + 4)
    data, newc, st = move_wp(sess, data, lag, frog, freeze15)
    print(f"  frog-ny frog {lag}->{frog} {st}->{newc}")
    if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
        return data, False
    if st != "moved":
        return data, False

    freeze15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], freeze15)
    if len(free) < 2:
        return data, False
    south = max(free, key=lambda w: (w[1], w[0]))
    north = min(free, key=lambda w: (w[1], w[0]))
    # Prefer Ny(46/45/44,36): with S(48,42) lands d14=34 bud≈10 (skips Ne).
    # Fallback (42,36)/(40,36) then Ne to reach d14=34 bud≈6.
    ny_ok = False
    for nyt in ((46, 36), (45, 36), (44, 36), (42, 36), (40, 36)):
        if near_any(nyt, list(freeze15), cheb=5):
            continue
        # Ny(48,36) makes S(48,42) noop — keep x≤46
        if max(abs(nyt[0] - south[0]), abs(nyt[1] - south[1])) < 5:
            continue
        data, newc, st = move_wp(sess, data, north, nyt, freeze15)
        print(f"  frog-ny Ny {north}->{nyt} {st}->{newc}")
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if st == "moved":
            ny_ok = True
            break
        # soft-fail — try next Ny
        freeze15 = lock_other_ship(data["frame"], 14)
        free = count_free14(data["frame"], freeze15)
        if len(free) < 2:
            return data, False
        south = max(free, key=lambda w: (w[1], w[0]))
        north = min(free, key=lambda w: (w[1], w[0]))
    if not ny_ok:
        return data, False

    freeze15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], freeze15)
    south = max(free, key=lambda w: (w[1], w[0]))
    others = [w for w in free if w != south]
    # Under west15@(42,50)+east@(58,50): n3 south→(48,42) HIT d14 40→35 bud≈7
    # (skip S4044 intermediate — saves 2). Under west@(42,54): S(40,46) also OK.
    # Under west@(38,50)/(34,54): S40 DEAD.
    west15_now = min(list(freeze15), key=lambda w: w[0]) if freeze15 else (0, 0)
    if west15_now[1] >= 54:
        s_tgts = ((40, 46), (48, 42), (40, 44))
    else:
        s_tgts = ((48, 42), (40, 44), (40, 46))
    for stgt in s_tgts:
        if near_any(stgt, list(freeze15), cheb=5):
            print(f"  frog-ny S{stgt} near15 — skip")
            continue
        if any(max(abs(stgt[0] - o[0]), abs(stgt[1] - o[1])) < 5 for o in others):
            print(f"  frog-ny S{stgt} merge — skip")
            continue
        data, newc, st = move_wp(sess, data, south, stgt, freeze15)
        print(f"  frog-ny S {south}->{stgt} {st}->{newc}")
        if st == "dead":
            print(f"  frog-ny S{stgt} dead — try next")
            if data.get("state") == "GAME_OVER" or "frame" not in data:
                return data, False
            freeze15 = lock_other_ship(data["frame"], 14)
            free = count_free14(data["frame"], freeze15)
            if len(free) < 2:
                break
            south = max(free, key=lambda w: (w[1], w[0]))
            others = [w for w in free if w != south]
            continue
        if data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if st == "moved":
            break

    # If already on (48,42): Ne only when north still west of x44.
    # Ny(44,36)+S already d14=34 bud≈10 — skip Ne to keep budget.
    freeze15 = lock_other_ship(data["frame"], 14)
    free = count_free14(data["frame"], freeze15)
    if len(free) >= 2 and step_budget(data["frame"]) >= 4:
        south = max(free, key=lambda w: (w[0], w[1]))
        north = min(free, key=lambda w: (w[1], w[0]))
        others_n = [w for w in free if w != north]
        if south == (48, 42) or (south[0] >= 46 and south[1] >= 40):
            if north[0] >= 44:
                print(f"  frog-ny Ne skip (north already {north})")
            else:
                for tgt in ((45, 36), (44, 36)):
                    if near_any(tgt, list(freeze15), cheb=5):
                        continue
                    if any(max(abs(tgt[0] - o[0]), abs(tgt[1] - o[1])) < 5 for o in others_n):
                        continue
                    data, newc, st = move_wp(sess, data, north, tgt, freeze15)
                    print(f"  frog-ny Ne {north}->{tgt} {st}->{newc}")
                    if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                        return data, False
                    if st == "moved":
                        break
        else:
            others = [w for w in free if w != south]
            for tgt in ((48, 42), (45, 40)):
                if near_any(tgt, list(freeze15), cheb=5):
                    print(f"  frog-ny SE{tgt} near15 — skip")
                    continue
                if any(max(abs(tgt[0] - o[0]), abs(tgt[1] - o[1])) < 5 for o in others):
                    print(f"  frog-ny SE{tgt} merge — skip")
                    continue
                data, newc, st = move_wp(sess, data, south, tgt, freeze15)
                print(f"  frog-ny SE {south}->{tgt} {st}->{newc}")
                if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                    return data, False
                if st == "moved":
                    break
    elif step_budget(data["frame"]) < 4:
        print(f"  frog-ny SE skip (bud={step_budget(data['frame'])})")

    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    print(
        f"  L3 frog-ny done ship={me14['c']} "
        f"bud={step_budget(data['frame'])} "
        f"free={count_free14(data['frame'], lock_other_ship(data['frame'], 14))}"
    )
    return data, True


def clear_l3(sess, data):
    """L3: interleave chrome14 leaps and chrome15 sync (shared ~63 ACTION6)."""
    lv0 = data.get("levels_completed") or 0
    gmap = goals_by_chrome(data["frame"])
    owned = owned_map(data["frame"])
    print("L3 enter", ships(data["frame"]), gmap, owned)
    east_stalls = 0
    stack_ban = set()  # live noops — never retry (retry → dead/GO)
    stack_soft = 0  # after soft-fail, stop burning stack-east

    # Unseal corridor ASAP so 14's east legs aren't blocked from the first hop.
    freeze14 = lock_other_ship(data["frame"], 15)
    data, cleared0 = clear15_corridor(sess, data, freeze14)
    if cleared0:
        print(f"  L3 early-clear15 bud={step_budget(data['frame'])}")

    # Proven 2wp mid-east path (plant 26/20 → collapse → dual translate).
    # Replaces west-hop + east-stall scramble when ship still west of x=28.
    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    if me14["c"][0] < 28 or me14["c"][1] < 34:
        from tools.r11l_l3_2wp_probe import advance_14_mid_east

        print("=== L3 mid-east 2wp ===")
        data, mid_ok = advance_14_mid_east(sess, data, lv0, do_clear15=False)
        if data.get("state") == "GAME_OVER" or "frame" not in data:
            raise RuntimeError("GAME_OVER mid-east 2wp")
        if (data.get("levels_completed") or 0) > lv0:
            return data, []
        me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        print(
            f"  L3 mid-east done ok={mid_ok} ship={me14['c']} "
            f"bud={step_budget(data['frame'])}"
        )
        # Post mid-east: frog → Ny36 → S40 stack (east corridor), not west-y44.
        if mid_ok and me14["c"][0] >= 28 and me14["c"][1] >= 34:
            data, stack_ok = advance_14_frog_ny_stack(sess, data, gmap[15])
            if data.get("state") == "GAME_OVER" or "frame" not in data:
                raise RuntimeError("GAME_OVER frog-ny stack")
            me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            print(
                f"  L3 post-mid done ok={stack_ok} ship={me14['c']} "
                f"bud={step_budget(data['frame'])}"
            )

    for turn in range(20):
        if (data.get("levels_completed") or 0) > lv0:
            return data, []
        if data.get("state") == "GAME_OVER":
            raise RuntimeError("GAME_OVER interleaved")
        bud = step_budget(data["frame"])
        me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
        d14 = abs(me14["c"][0] - gmap[14][0]) + abs(me14["c"][1] - gmap[14][1])
        d15 = abs(me15["c"][0] - gmap[15][0]) + abs(me15["c"][1] - gmap[15][1])
        print(f"L3 turn{turn} d14={d14} d15={d15} bud={bud}")
        if d14 <= 6 and d15 <= 6:
            break
        if bud < 4:
            break

        # Lock by proximity to the other ship — owned_map steals chrome14's
        # eastern wps once they drift toward ship15.
        freeze15 = lock_other_ship(data["frame"], 14)
        freeze14 = lock_other_ship(data["frame"], 15)

        # Vacate chrome15 mid-park — disabled: live noops burn bud; SE south-first instead.
        if False and bud >= 8 and any(38 <= p[0] <= 46 and 38 <= p[1] <= 44 for p in freeze15):
            g = _plane(data["frame"])
            blocker = min(
                (p for p in freeze15 if 38 <= p[0] <= 46 and 38 <= p[1] <= 44),
                key=lambda w: w[0],
            )
            for tgt in (
                (42, 50),
                (48, 50),
                (50, 46),
                (45, 52),
                (52, 42),
                (48, 36),
            ):
                nxt = floor_bfs(g, blocker, tgt, max_step=10)
                if not nxt or nxt == blocker:
                    nxt = tgt
                if near_any(nxt, count_free14(data["frame"], freeze15), cheb=5):
                    continue
                if max(abs(nxt[0] - blocker[0]), abs(nxt[1] - blocker[1])) < 2:
                    continue
                data, newc, st = move_wp(sess, data, blocker, nxt, freeze14)
                print(
                    f"  vacate15 {blocker}->{nxt} {st}->{newc} "
                    f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                )
                if "frame" in data:
                    freeze15 = lock_other_ship(data["frame"], 14)
                    freeze14 = lock_other_ship(data["frame"], 15)
                    bud = step_budget(data["frame"])
                if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                    break
                if st == "moved":
                    break
                # noop burns bud — skip remaining vacate this turn
                break
            if data.get("state") == "GAME_OVER" or "frame" not in data:
                break

        # Gate: after mid-east SE band — ship may drift west to x~25 while wps at y44.
        free14n = count_free14(data["frame"], freeze15)
        # Frog-ny stack: both wps east of x38 (e.g. (43,36)+(40,44)). SE-cont
        # catch-lag toward (47/48,36) is live-dead — use micro stack-east instead.
        stack_east = (
            len(free14n) == 2
            and all(w[0] >= 38 for w in free14n)
            and me14["c"][0] >= 30
            and me14["c"][1] >= 34
        )
        if stack_east and d14 > 10 and bud >= 4 and stack_soft < 1:
            south = max(free14n, key=lambda w: (w[1], w[0]))
            north = min(free14n, key=lambda w: (w[1], w[0]))
            print(
                f"  L3 stack-east ship={me14['c']} N={north} S={south} bud={bud}"
            )
            progressed = False
            noops = 0
            tried = set()
            # Known live: S y44 east (41/42/43,44) and +2/+3 same-row = noop burns.
            # N diagonals stay near15 until west15 leaves y42 — vacate15 first.
            hard_ban = {
                (42, 40),
                (42, 42),
                (42, 45),
                (42, 46),
                (43, 40),
                (43, 42),
                (41, 44),
                (42, 44),
                (43, 44),
                (48, 48),  # dead under 4250+5850 after E48
                (50, 42),  # noop
                (50, 44),  # noop
                (50, 46),  # dead with bud≥6 at d14=34
                (52, 46),  # dead after N-noop (also often noop)
                (52, 48),  # dead
                (48, 36),  # noop→dead under Ne pose
                (50, 36),  # noop under Ne
                (52, 44),  # dead under Ne with bud≈4
                (48, 46),  # noop under Ne
            }
            hard_ban |= stack_ban
            # Prefer vacate west15 south when sealing N-east cells.
            seal_n = near_any((45, 40), list(freeze15), cheb=5) or near_any(
                (46, 38), list(freeze15), cheb=5
            )
            if seal_n and step_budget(data["frame"]) >= 6:
                flock = list(freeze15)
                west15 = min(flock, key=lambda w: w[0])
                east15 = max(flock, key=lambda w: w[0])
                for tgt in (
                    (38, 52),
                    (42, 50),
                    (48, 50),
                    (42, 54),
                    (48, 48),
                    (45, 50),
                ):
                    if step_budget(data["frame"]) < 4:
                        break
                    if max(abs(tgt[0] - east15[0]), abs(tgt[1] - east15[1])) < 5:
                        continue
                    if near_any(tgt, list(freeze14), cheb=5):
                        continue
                    data, newc, st = move_wp(sess, data, west15, tgt, freeze14)
                    print(
                        f"  stack-vac15 {west15}->{tgt} {st}->{newc} "
                        f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                    )
                    if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                        break
                    if st == "moved":
                        progressed = True
                        break
                    # one soft fail is enough — don't burn on more noops
                    break
                if progressed:
                    continue
                if data.get("state") == "GAME_OVER" or "frame" not in data:
                    break
                freeze15 = lock_other_ship(data["frame"], 14)
                freeze14 = lock_other_ship(data["frame"], 15)
                free14n = count_free14(data["frame"], freeze15)
                if len(free14n) == 2:
                    south = max(free14n, key=lambda w: (w[1], w[0]))
                    north = min(free14n, key=lambda w: (w[1], w[0]))
            # After frog SE: free often (40,36)+(48,42) ship~(36,37) d14≈35.
            # Live HIT: north→(45,36) d14 35→34. Do NOT vacate west15 after E48.
            # Ny44 pose: north already (44,36) — skip +1 east (burns "already").
            # Ban (43,38) here (noop→dead). East SE mostly noop/dead.
            if north[0] >= 44:
                stack_cands = [
                    (south, (50, 44)),
                    (south, (54, 44)),
                    (south, (52, 46)),
                    (south, (48, 46)),
                    (south, (50, 46)),
                    (north, (48, 38)),
                    (north, (50, 38)),
                    (north, (48, 40)),
                    (north, (50, 40)),
                    (north, (52, 38)),
                    (north, (46, 40)),
                    # (52,42) live-noop under Ny44/46 — omit
                ]
            else:
                stack_cands = [
                    (north, (45, 36)),
                    (north, (48, 36)),
                    (north, (50, 36)),
                    (north, (47, 38)),
                    (north, (48, 38)),
                    (north, (50, 38)),
                    (north, (45, 40)),
                    (north, (48, 40)),
                    (north, (46, 38)),
                    (north, (44, 40)),
                    (south, (52, 44)),
                    (south, (50, 46)),
                    (south, (54, 48)),
                    (south, (48, 46)),
                    (south, (50, 40)),
                    (south, (52, 42)),
                ]
            for cur, ld in stack_cands:
                if step_budget(data["frame"]) < 4:
                    break
                if not (0 <= ld[0] < 64 and 0 <= ld[1] < 64):
                    continue
                if ld in tried or ld == cur:
                    continue
                tried.add(ld)
                # "already"/tiny hops still burn ACTION6 — never try cheb≤1.
                if max(abs(ld[0] - cur[0]), abs(ld[1] - cur[1])) <= 1:
                    continue
                # Allow same-row east on y36 under E48 (45/48/50,36 live path).
                # Only ban far-east shallow that historically collapsed n=1 alone.
                if ld[1] <= 36 and ld[0] >= 52:
                    continue
                if ld in hard_ban:
                    continue
                # (43,38) noop→dead under free=(40,36)+(48,42)
                if ld == (43, 38) and south[0] >= 46:
                    continue
                # Same-row S east on y44 is live-noop
                if cur == south and south[1] == 44 and ld[1] == 44 and ld[0] > south[0]:
                    continue
                other = south if cur == north else north
                if max(abs(ld[0] - other[0]), abs(ld[1] - other[1])) < 5:
                    continue
                if near_any(ld, list(freeze15), cheb=5):
                    continue
                data, newc, st = move_wp(sess, data, cur, ld, freeze15)
                print(
                    f"  stack-east {cur}->{ld} {st}->{newc} "
                    f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
                    f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                )
                if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                    break
                if st == "moved":
                    progressed = True
                    break
                # "already" burns bud like noop — stop after one soft-fail
                if st == "already":
                    stack_ban.add(ld)
                    noops += 1
                    if noops >= 1:
                        print("  stack-east soft-fail — stop burns")
                        stack_soft += 1
                        break
                    continue
                noops += 1
                stack_ban.add(ld)
                if noops >= 1:
                    print("  stack-east soft-fail — stop burns")
                    stack_soft += 1
                    break
            if progressed:
                continue
            # Soft haul15 toward goal with leftover bud (14 SE stalled at d14≈34).
            # haul15_toward itself needs bud≥8; otherwise just mark stalled.
            if step_budget(data["frame"]) >= 8 and d15 > 6:
                data, _ = haul15_toward(
                    sess, data, gmap[15], max_step=4, label="15stack"
                )
                if data.get("state") == "GAME_OVER" or "frame" not in data:
                    break
                continue
            if stack_soft < 1:
                stack_soft += 1
            print("  stack-east stalled — fall through")

        post_gate = (
            (me14["c"][0] >= 24 and me14["c"][1] >= 34)
            or any(w[1] >= 40 and w[0] <= 36 for w in free14n)
        )
        band14 = [w for w in free14n if w[1] >= 34 and w[0] <= 42]
        if len(band14) >= 2:
            free14n = sorted(band14, key=lambda w: (w[0], w[1]))[:2]
        if (
            len(free14n) == 2
            and post_gate
            and d14 > 10
            and bud >= 8
            and not stack_east
        ):
            lead = max(free14n, key=lambda w: (w[1], w[0]))
            lag = min(free14n, key=lambda w: (w[1], w[0]))
            print(
                f"  L3 SE-cont ship={me14['c']} lead={lead} lag={lag} bud={bud}"
            )
            progressed = False

            # 1) Catch lag: SAME-ROW EAST first (probed HIT), then soft SE.
            # Pure south from x≤25 at y42 is live-noop.
            if lead[1] - lag[1] >= 1 or (lead[0] - lag[0]) >= 4:
                catch_noops = 0
                for gd in (
                    (lag[0] + 4, lag[1]),
                    (lag[0] + 5, lag[1]),
                    (lag[0] + 3, lag[1]),
                    (lag[0] + 6, lag[1]),
                    (lag[0] + 4, min(lead[1], lag[1] + 1)),
                    (lag[0] + 3, min(lead[1], lag[1] + 1)),
                    (lag[0] + 5, min(lead[1], lag[1] + 1)),
                    (lag[0] + 4, min(lead[1], lag[1] + 2)),
                    (lag[0] + 2, min(lead[1], lag[1] + 2)),
                    (max(18, lead[0] - 6), lead[1]),
                    (max(18, lead[0] - 5), lead[1]),
                ):
                    if not (0 <= gd[0] < 64 and 0 <= gd[1] < 64):
                        continue
                    if gd == lag:
                        continue
                    if max(abs(gd[0] - lead[0]), abs(gd[1] - lead[1])) < 5:
                        continue
                    if near_any(gd, [lead] + list(freeze15), cheb=5):
                        continue
                    # Ban y36 x≥45 from frog-ny leftovers
                    if gd[1] <= 36 and gd[0] >= 45:
                        continue
                    data, newc, st = move_wp(sess, data, lag, gd, freeze15)
                    print(
                        f"  SE-cont catch-lag {lag}->{gd} {st}->{newc} "
                        f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
                        f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                    )
                    if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                        break
                    if st == "moved":
                        freeze15 = lock_other_ship(data["frame"], 14)
                        free14n = [
                            w
                            for w in count_free14(data["frame"], freeze15)
                            if w[1] >= 34 and w[0] <= 42
                        ]
                        if len(free14n) < 2:
                            free14n = count_free14(data["frame"], freeze15)
                        if len(free14n) >= 2:
                            lead = max(free14n, key=lambda w: (w[1], w[0]))
                            lag = min(free14n, key=lambda w: (w[1], w[0]))
                            progressed = True
                            east_stalls = 0
                        break
                    catch_noops += 1
                    if catch_noops >= 2:
                        break
                    continue
                if data.get("state") == "GAME_OVER" or "frame" not in data:
                    break

            # 2) Lead only if lag roughly aligned (dy<=2); tiny steps only.
            free_now = count_free14(data["frame"], freeze15)
            band_now = [w for w in free_now if w[1] >= 34 and w[0] <= 42]
            if len(band_now) >= 2:
                free_now = sorted(band_now, key=lambda w: (w[0], w[1]))[:2]
                lag = min(free_now, key=lambda w: (w[1], w[0]))
                lead = max(free_now, key=lambda w: (w[1], w[0]))
            if (
                not (data.get("state") == "GAME_OVER")
                and "frame" in data
                and len(free_now) == 2
                and lead[1] - lag[1] <= 2
                and step_budget(data["frame"]) >= 8
            ):
                noops = 0
                # Prefer west-south (away from 15 seal ~x41) then tiny east.
                for ld in (
                    (max(18, lead[0] - 3), min(48, lead[1] + 2)),
                    (max(18, lead[0] - 2), min(48, lead[1] + 2)),
                    (max(18, lead[0] - 4), min(48, lead[1] + 1)),
                    (lead[0], min(48, lead[1] + 2)),
                    (lead[0] + 2, lead[1]),
                    (lead[0] + 2, min(48, lead[1] + 1)),
                ):
                    if not (0 <= ld[0] < 64 and 0 <= ld[1] < 64):
                        continue
                    if max(abs(ld[0] - lag[0]), abs(ld[1] - lag[1])) < 5:
                        continue
                    if near_any(ld, list(freeze15), cheb=5):
                        continue
                    data, newc, st = move_wp(sess, data, lead, ld, freeze15)
                    print(
                        f"  SE-cont lead {lead}->{ld} {st}->{newc} "
                        f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
                    )
                    if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
                        print("  SE-cont lead dead — stop")
                        break
                    if st != "moved":
                        noops += 1
                        if noops >= 2:
                            print("  SE-cont lead 2x noop — stop (save bud)")
                            break
                        continue
                    freeze15 = lock_other_ship(data["frame"], 14)
                    band_chk = [
                        w
                        for w in count_free14(data["frame"], freeze15)
                        if w[1] >= 34 and w[0] <= 42
                    ]
                    if len(band_chk) < 2:
                        print("  SE-cont flock broke")
                        break
                    progressed = True
                    east_stalls = 0
                    break
                if data.get("state") == "GAME_OVER" or "frame" not in data:
                    break

            # 3) haul15 only with spare bud AND 14 progressed this turn.
            if (
                "frame" in data
                and data.get("state") != "GAME_OVER"
                and progressed
                and step_budget(data["frame"]) >= 14
                and d15 > 8
            ):
                data, ok15 = haul15_toward(
                    sess, data, gmap[15], max_step=6, label="haul15"
                )
                if data.get("state") == "GAME_OVER" or "frame" not in data:
                    break
                if ok15:
                    east_stalls = 0

            if progressed:
                continue
            east_stalls += 1
            # Don't fall into sync_east y34 path when already on SE band.
            if east_stalls >= 3:
                print(f"  SE-cont stalled {east_stalls} — break east scramble")
                if east_stalls >= 5:
                    break
                continue

        # Past mid-east SE band: never sync_east / leap14_east (y34 toxic / burns bud).
        free14n = count_free14(data["frame"], freeze15)
        on_se = (me14["c"][0] >= 24 and me14["c"][1] >= 34) or any(
            w[1] >= 40 and w[0] <= 36 for w in free14n
        )
        if on_se:
            bud_now = step_budget(data["frame"]) if "frame" in data else 0
            freeze15b = lock_other_ship(data["frame"], 14) if "frame" in data else []
            seals = any(p[0] <= 44 and 38 <= p[1] <= 44 for p in freeze15b)
            if seals and d15 > 8 and bud_now >= 14:
                data, ok15 = haul15_toward(
                    sess, data, gmap[15], max_step=6, label="15postgate"
                )
                if data.get("state") == "GAME_OVER" or "frame" not in data:
                    break
                if ok15:
                    continue
            east_stalls += 1
            if east_stalls >= 6:
                print(f"  postgate stall {east_stalls} — stop")
                break
            continue

        on_neck = me14["c"][1] >= 33 and me14["c"][0] >= 19
        near_neck = me14["c"][1] >= 28 and me14["c"][0] >= 17
        approach = me14["c"][1] >= 26 and me14["c"][0] >= 17

        # Clear 15's seal as soon as we approach the choke — before east leads.
        if approach and bud >= 8:
            freeze15 = lock_other_ship(data["frame"], 14)
            freeze14 = lock_other_ship(data["frame"], 15)
            sealed = any(
                30 <= p[1] <= 38 and 28 <= p[0] <= 40 for p in freeze15
            )
            if sealed:
                data, cleared = clear15_corridor(sess, data, freeze14)
                if data.get("state") == "GAME_OVER" or "frame" not in data:
                    break
                if cleared:
                    freeze15 = lock_other_ship(data["frame"], 14)
                    freeze14 = lock_other_ship(data["frame"], 15)
                    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
                    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
                    d14 = abs(me14["c"][0] - gmap[14][0]) + abs(me14["c"][1] - gmap[14][1])
                    d15 = abs(me15["c"][0] - gmap[15][0]) + abs(me15["c"][1] - gmap[15][1])
                    bud = step_budget(data["frame"])
                    if near_neck and bud >= 8 and d14 > 8:
                        data, progressed = leap14_east_once(
                            sess, data, freeze15, lv0, stride=4
                        )
                        if data.get("state") == "GAME_OVER" or "frame" not in data:
                            break
                        if progressed:
                            east_stalls = 0
                            continue

        # East corridor (incl. near-choke y≥28): short body-safe hops, no neck diamond.
        if (on_neck or near_neck) and d14 > 8 and bud >= 5 and east_stalls < 8:
            data, progressed = leap14_east_once(sess, data, freeze15, lv0, stride=4)
            if data.get("state") == "GAME_OVER" or "frame" not in data:
                break
            if (data.get("levels_completed") or 0) > lv0:
                return data, []
            if progressed:
                east_stalls = 0
                # Prefer jumping past seal in sync; only clear15 if still blocked
                # and we have budget to spare.
                if "frame" in data and step_budget(data["frame"]) >= 14:
                    fr15 = lock_other_ship(data["frame"], 14)
                    free14b = count_free14(data["frame"], fr15)
                    lead_x = max((w[0] for w in free14b), default=0) if free14b else 0
                    sealed = any(
                        30 <= p[1] <= 38 and 30 <= p[0] <= 45 for p in fr15
                    )
                    if lead_x >= 30 and sealed:
                        fr14 = lock_other_ship(data["frame"], 15)
                        data, cleared = clear15_corridor(sess, data, fr14)
                        if cleared:
                            print("  post-east clear15 ok")
                    # Once 14 lead is past seal line, spend one cheap 15 south hop
                    # while bud still allows — otherwise 15 never moves (d15 stuck).
                    elif False and (
                        lead_x >= 28
                        and not sealed
                        and step_budget(data["frame"]) >= 16
                        and d15 > 8
                    ):
                        fr14 = lock_other_ship(data["frame"], 15)
                        me15b = next(
                            s for s in ships(data["frame"]) if s["chrome"] == 15
                        )
                        # One short sync toward goal — not full wave reshape.
                        g15 = goals_by_chrome(data["frame"])[15]
                        hop15 = (
                            me15b["c"][0] + (g15[0] - me15b["c"][0]) // 3,
                            me15b["c"][1] + max(4, (g15[1] - me15b["c"][1]) // 3),
                        )
                        targets = [(hop15[0] + o[0], hop15[1] + o[1]) for o in OFFS15]
                        before15 = me15b["c"]
                        data, _ = sync_to(sess, data, fr14, targets, "15interleave")
                        if "frame" in data:
                            me15a = next(
                                s for s in ships(data["frame"]) if s["chrome"] == 15
                            )
                            print(
                                f"  interleave15 {before15}->{me15a['c']} "
                                f"bud={step_budget(data['frame'])}"
                            )
                continue
            east_stalls += 1
            print(f"  east stall {east_stalls} → try clear15/wave15")
            # Post-seal: haul lag before burning ACTION6 on wave15.
            if "frame" in data and step_budget(data["frame"]) >= 8:
                fr15 = lock_other_ship(data["frame"], 14)
                free14b = count_free14(data["frame"], fr15)
                lx = max((w[0] for w in free14b), default=0) if free14b else 0
                if lx >= 40:
                    data, ok = sync_east14(
                        sess, data, fr15, stride=8
                    )
                    if "frame" in data and ok:
                        me14b = next(
                            s for s in ships(data["frame"]) if s["chrome"] == 14
                        )
                        if me14b["c"][0] > me14["c"][0] or ok:
                            east_stalls = 0
                            continue
            # Fall through: 15 must unseal the corridor (do NOT continue).

        # West corridor only — stay north of choke approach band.
        if (not near_neck) and d14 > 6 and bud >= 12:
            st = 12
            data, progressed = leap14_once(sess, data, freeze15, lv0, stride=st)
            if data.get("state") == "GAME_OVER":
                raise RuntimeError("GAME_OVER leap14")
            if "frame" not in data:
                break
            if progressed:
                continue
            print("  leap14 no progress → try 15")

        if "frame" not in data or data.get("state") == "GAME_OVER":
            break

        # Allow 15 once 14 is at/near the choke — needed to unseal (37,34).
        # Never full-wave15 on thin budget while 14 still needs the east corridor.
        allow15 = on_neck or near_neck or me14["c"][1] >= 31
        if d15 > 6 and bud >= 8 and allow15:
            # Cheap corridor clear before full wave if still sealed.
            data, cleared = clear15_corridor(sess, data, freeze14)
            if data.get("state") == "GAME_OVER" or "frame" not in data:
                break
            if cleared:
                continue
            # Full wave only with spare budget AND chrome15 still seals corridor.
            flock15_now = lock_other_ship(data["frame"], 14)
            still_sealed = any(
                30 <= p[1] <= 38 and 28 <= p[0] <= 40 for p in flock15_now
            )
            if step_budget(data["frame"]) < 16 or not still_sealed:
                me14c = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
                if (
                    not still_sealed
                    and me14c["c"][0] >= 28
                    and d15 > 10
                    and step_budget(data["frame"]) >= 8
                ):
                    data, ok15 = haul15_toward(
                        sess, data, gmap[15], max_step=8, label="15unsealed"
                    )
                    if data.get("state") == "GAME_OVER" or "frame" not in data:
                        break
                    if ok15:
                        continue
                print(
                    f"  skip wave15 thin/unsealed bud={step_budget(data['frame'])} "
                    f"d14={d14} sealed={still_sealed}"
                )
                if east_stalls >= 4:
                    break
                # Retry 14 east instead of burning 15.
                if d14 > 8 and step_budget(data["frame"]) >= 8:
                    data, progressed = leap14_east_once(
                        sess, data, freeze15, lv0, stride=4
                    )
                    if progressed:
                        east_stalls = 0
                        continue
                continue
            st15 = 8 if me14["c"][1] >= 33 else 14
            data, _ = wave15_once(sess, data, freeze14, lv0, stride=st15)
            if data.get("state") == "GAME_OVER":
                raise RuntimeError("GAME_OVER wave15")
            if "frame" not in data:
                break
            # If 15 didn't move, one more short attempt then stop spinning.
            me15b = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
            before15 = me15["c"]
            if me15b["c"] == before15:
                if on_neck and bud >= 12 and d14 > 8 and east_stalls < 6:
                    data, progressed = leap14_east_once(
                        sess, data, freeze15, lv0, stride=4
                    )
                    if not progressed:
                        break
                    continue
                break
            continue

        if d14 > 6 and bud >= 12:
            if on_neck or near_neck:
                data, progressed = leap14_east_once(sess, data, freeze15, lv0, stride=4)
            else:
                data, progressed = leap14_once(sess, data, freeze15, lv0, stride=10)
            if data.get("state") == "GAME_OVER" or "frame" not in data:
                break
            if not progressed:
                break
            continue
        break

    if (data.get("levels_completed") or 0) > lv0:
        return data, []
    if "frame" not in data or data.get("state") == "GAME_OVER":
        raise RuntimeError(
            f"L3 fail state={data.get('state')} err={data.get('error')} "
            f"lv={data.get('levels_completed')}"
        )

    me14 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    me15 = next(s for s in ships(data["frame"]) if s["chrome"] == 15)
    freeze15 = [
        w["c"]
        for w in r11l.waypoints(data["frame"])
        if abs(w["c"][0] - me15["c"][0]) + abs(w["c"][1] - me15["c"][1]) <= 14
    ]
    freeze14 = [
        w["c"]
        for w in r11l.waypoints(data["frame"])
        if abs(w["c"][0] - me14["c"][0]) + abs(w["c"][1] - me14["c"][1]) <= 14
    ]
    d14 = abs(me14["c"][0] - gmap[14][0]) + abs(me14["c"][1] - gmap[14][1])
    d15 = abs(me15["c"][0] - gmap[15][0]) + abs(me15["c"][1] - gmap[15][1])
    print(f"L3 final d14={d14} d15={d15} bud={step_budget(data['frame'])}")

    if 4 < d14 <= 14 and step_budget(data["frame"]) >= 6:
        owned = owned_map(data["frame"])
        owned[14] = free_wps_for(data["frame"], 14, freeze15)
        data, owned, _ = park_compact(
            sess, data, 14, gmap[14], owned, freeze15, lv0, budget=10, max_spread=16
        )
    if (data.get("levels_completed") or 0) > lv0:
        return data, []
    if 4 < d15 <= 14 and step_budget(data["frame"]) >= 6:
        owned = owned_map(data["frame"])
        owned[15] = free_wps_for(data["frame"], 15, freeze14)
        data, owned, _ = park_compact(
            sess, data, 15, gmap[15], owned, freeze14, lv0, budget=10, max_spread=14
        )

    if (data.get("levels_completed") or 0) <= lv0:
        raise RuntimeError(
            f"L3 fail ships={ships(data['frame'])} lv={data.get('levels_completed')} "
            f"bud={step_budget(data['frame'])}"
        )
    return data, []


def main():
    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["r11l_l3sync"]},
        timeout=60,
    )
    sess.card_id = r.json()["card_id"]
    sess.game_id = "r11l-495a7899"
    d = reset(sess)
    d, _ = clear_l1(sess, d)
    print("=== L2 ===")
    d, _ = clear_l2(sess, d)
    print("=== L3 ===")
    try:
        d, _ = clear_l3(sess, d)
        print("PASS", d.get("levels_completed"), d.get("state"))
    except Exception as e:
        print("FAIL", e)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
