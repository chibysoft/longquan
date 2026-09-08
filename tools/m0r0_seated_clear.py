"""m0r0 seated clearer: hazard-aware mate (flush + compress).

L3+: color-9 markers block piece configuration space — relocate blockers
out of the way (select A6 → steer → deposit via A6 on ghost), then mate.

Usage:
  python tools/m0r0_seated_clear.py
  python tools/m0r0_seated_clear.py --max-levels 6
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import m0r0
from tools.ls20_online_validate import BASE, OnlineSession, _api_key


def reset(sess: OnlineSession):
    body = {"card_id": sess.card_id, "game_id": sess.game_id}
    if sess.guid:
        body["guid"] = sess.guid
    data = sess.s.post(
        f"{BASE}/api/cmd/RESET", headers=sess._headers(True), json=body, timeout=60
    ).json()
    sess.guid = data["guid"]
    return data


def act(sess: OnlineSession, aid: int, x: int | None = None, y: int | None = None):
    body: dict = {"game_id": sess.game_id, "guid": sess.guid}
    if x is not None:
        body["x"] = x
        body["y"] = y
    data = sess.s.post(
        f"{BASE}/api/cmd/ACTION{aid}",
        headers=sess._headers(True),
        json=body,
        timeout=60,
    ).json()
    if "frame" not in data:
        raise RuntimeError(f"ACTION{aid} failed: {data}")
    sess.guid = data.get("guid", sess.guid)
    return data


def ensure_twins(sess: OnlineSession, data):
    """After a clear, leftover single block — try nudges until twins + mate path."""
    if len(m0r0.locate_pieces(data["frame"])) == 2:
        if m0r0.find_mate_path(data["frame"]) is not None:
            return data
    leftover = data
    for nudge in (4, 1, 2, 3):
        data = act(sess, nudge)
        pcs = m0r0.locate_pieces(data["frame"])
        print(f"  interstitial A{nudge} -> pcs={pcs}")
        if len(pcs) == 2 and m0r0.find_mate_path(data["frame"]) is not None:
            return data
        if len(pcs) == 2:
            leftover = data
    if len(m0r0.locate_pieces(leftover["frame"])) == 2:
        return leftover
    raise RuntimeError("could not enter twin layout")


def _spread_for_gap(sess: OnlineSession, data, n: int = 6):
    """Pull twins apart so the x≈26–29 gap is free for marker descent."""
    for _ in range(n):
        pcs = m0r0.locate_pieces(data["frame"])
        if len(pcs) == 2 and not any(p[0] <= 29 and p[2] >= 26 for p in pcs):
            return data
        data = act(sess, 3)
    return data


def _deposit_restore(sess: OnlineSession, data):
    """A6 on a ghost (color 1) deposits selected marker and restores pieces."""
    g = np.asarray(data["frame"][0])
    ys, xs = np.where(g == 1)
    if len(xs) == 0:
        raise RuntimeError("deposit: no ghost cells")
    return act(sess, 6, int(xs[0]), int(ys[0]))


def _c11_tl(frame, w: int | None = None):
    b = m0r0.selected_marker_bbox(frame, w)
    if b is None:
        return None
    return (b[0], b[1])


def _live_steer_marker(
    sess: OnlineSession,
    data,
    goal: tuple[int, int],
    w: int,
    step: int,
    limit: int = 45,
):
    """Greedy steer with offline BFS hint; survive live noops."""
    for _ in range(limit):
        cur = _c11_tl(data["frame"], w)
        if cur is None:
            return data, False
        if cur == goal:
            return data, True
        path = m0r0.marker_steer_path(data["frame"], cur, goal, step=step, w=w)
        order: list[int] = list(path[:1]) if path else []
        if cur[1] < goal[1]:
            order.append(2)
        if cur[1] > goal[1]:
            order.append(1)
        if cur[0] < goal[0]:
            order.append(4)
        if cur[0] > goal[0]:
            order.append(3)
        order += [4, 2, 3, 1]
        seen: set[int] = set()
        moved = False
        for a in order:
            if a in seen:
                continue
            seen.add(a)
            data2 = act(sess, a)
            nxt = _c11_tl(data2["frame"], w)
            if nxt and nxt != cur:
                data = data2
                moved = True
                break
            data = data2
        if not moved:
            return data, False
    return data, _c11_tl(data["frame"], w) == goal


def relocate_blocking_markers(sess: OnlineSession, data, limit: int = 12):
    """Move color-9 markers until find_mate_path succeeds (L3 2x2 / L4 3x3)."""
    for round_i in range(limit):
        if m0r0.find_mate_path(data["frame"]) is not None:
            return data
        ms = m0r0.color_blobs(data["frame"], m0r0.MARKER)
        if not ms:
            return data
        w = m0r0.infer_marker_size(data["frame"])
        step = m0r0.infer_params(data["frame"]).step
        goals = m0r0.safe_marker_goals(data["frame"], step=step, w=w)
        if not goals:
            raise RuntimeError("no safe/unlocking marker goals")
        # Prefer elevated markers; L4 often has a single center marker.
        upper = [m for m in ms if m[1] < 47]
        sole = m0r0.markers_blocking_mate(data["frame"])
        if sole:
            blockers = sole
        elif upper:
            blockers = sorted(upper, key=lambda m: (m[0], m[1]), reverse=True)
        else:
            blockers = ms
        home = blockers[0]
        occupied = {(m[0], m[1]) for m in ms}

        # Prefer unlocking goals (already preferred by safe_marker_goals).
        ranked = [g for g in goals if g not in occupied]
        if not ranked:
            ranked = list(goals)
        # Multi-marker (L3): prefer bottom / far goals by score
        if len(ms) > 1:
            pcs = m0r0.locate_pieces(data["frame"])

            def score(tl):
                pen = 0 if tl[1] >= 47 else -50
                dist = min(abs(tl[0] - p[0]) + abs(tl[1] - p[1]) for p in pcs) if pcs else 0
                side = 10 if (home[0] >= 30 and tl[0] >= 40) or (home[0] < 30 and tl[0] < 30) else 0
                return pen + dist + side

            ranked = sorted(ranked, key=score, reverse=True)

        if w <= 2:
            data = _spread_for_gap(sess, data, n=6)
        print(f"  marker relocate round {round_i}: {home} w={w} step={step} goals={len(ranked)}")
        data = act(sess, 6, home[0], home[1])
        start = _c11_tl(data["frame"], w)
        if start is None:
            # L4: walls are also color 11 — click may have failed
            print("  select failed (no compact c11); abort round")
            continue

        success = False
        for g2 in ranked[:20]:
            if m0r0.marker_steer_path(data["frame"], start, g2, step=step, w=w) is None:
                continue
            print(f"  try goal {g2} from {start}")
            data, ok = _live_steer_marker(sess, data, g2, w=w, step=step)
            start = _c11_tl(data["frame"], w) or start
            if not ok:
                if len(ms) > 1 and start[1] >= 47:
                    ok = True
                else:
                    continue
            data = _deposit_restore(sess, data)
            success = m0r0.find_mate_path(data["frame"]) is not None
            print(
                f"  parked goal={g2} ms={m0r0.color_blobs(data['frame'], m0r0.MARKER)} mate={success}"
            )
            break  # one marker per outer round
        if _c11_tl(data["frame"], w):
            data = _deposit_restore(sess, data)
        print(
            f"  after relocate ok={success} ms={m0r0.color_blobs(data['frame'], m0r0.MARKER)} "
            f"mate={m0r0.find_mate_path(data['frame']) is not None}"
        )
        if success:
            return data
    if m0r0.find_mate_path(data["frame"]) is None:
        raise RuntimeError(
            f"markers still block mate; ms={m0r0.color_blobs(data['frame'], m0r0.MARKER)}"
        )
    return data


def _is_l5_layout(frame) -> bool:
    """L5: no color-9 markers; walls 6|7; door/pad colors 12/14/15."""
    g = np.asarray(frame[0])
    if m0r0.color_blobs(frame, m0r0.MARKER):
        return False
    return bool(
        np.any(g == 6) and np.any(g == 7) and np.any(g == 12) and np.any(g == 15)
    )


def _enter_twins_simple(sess: OnlineSession, data):
    """Nudge until two pieces exist (do not require find_mate_path — L5 false-positives)."""
    for nudge in (4, 1, 2, 3, 4):
        if len(m0r0.locate_pieces(data["frame"])) == 2:
            return data
        data = act(sess, nudge)
        print(f"  enter-twins A{nudge} -> pcs={m0r0.locate_pieces(data['frame'])}")
    if len(m0r0.locate_pieces(data["frame"])) != 2:
        raise RuntimeError("could not enter twin layout (simple)")
    return data


def _l5_normalize_spawn(sess: OnlineSession, data):
    """Open-loop golden path assumes bottom spawn (2,50)/(58,50). Live A4=outward."""
    spawn = [(2, 50, 5, 53), (58, 50, 61, 53)]
    for _ in range(12):
        pcs = m0r0.locate_pieces(data["frame"])
        if pcs == spawn:
            return data
        if len(pcs) != 2:
            data = act(sess, 4)
            continue
        # Bottom band: spread to walls with outward A4, or drop with A2
        if pcs[0][1] >= 46 and pcs[1][1] >= 46:
            if pcs[0][0] > 2:
                data = act(sess, 4)
            elif pcs[0][1] < 50:
                data = act(sess, 2)
            else:
                # already wall-spread at y50 but not exact — stop
                if pcs[0][0] <= 2 and pcs[1][0] >= 58:
                    return data
                data = act(sess, 4)
            continue
        data = act(sess, 2)
    print(f"  L5 spawn normalize leftover pcs={m0r0.locate_pieces(data['frame'])}")
    return data


def _is_l6_layout(frame) -> bool:
    """L6: color-8 hazard belt; one color-9 marker; pads 12/14; no color-15."""
    g = np.asarray(frame[0])
    ms = m0r0.color_blobs(frame, m0r0.MARKER)
    return bool(
        np.any(g == 8)
        and np.any(g == 12)
        and np.any(g == 14)
        and not np.any(g == 15)
        and len(ms) == 1
    )


def _l6_normalize_spawn(sess: OnlineSession, data):
    """Birth twins (22,22)/(38,22). Parallel-Y: A1 up, A2 down; A3 out, A4 in."""
    spawn = [(22, 22, 25, 25), (38, 22, 41, 25)]
    for _ in range(10):
        pcs = m0r0.locate_pieces(data["frame"])
        if pcs == spawn:
            return data
        if len(pcs) != 2:
            data = act(sess, 4)
            continue
        lx, ly = pcs[0][0], pcs[0][1]
        if lx < 22:
            data = act(sess, 4)
        elif lx > 22:
            data = act(sess, 3)
        elif ly < 22:
            data = act(sess, 2)
        elif ly > 22:
            data = act(sess, 1)
        else:
            break
    print(f"  L6 spawn normalize leftover pcs={m0r0.locate_pieces(data['frame'])}")
    return data


def _l6_park_marker(sess: OnlineSession, data, waypoints: list[tuple[int, int]]):
    """Select color-9 marker, steer through waypoints, deposit on ghost."""
    ms = m0r0.color_blobs(data["frame"], m0r0.MARKER)
    if not ms:
        raise RuntimeError("L6: no color-9 marker")
    data = act(sess, 6, ms[0][0], ms[0][1])
    w = ms[0][2] - ms[0][0] + 1
    step = 4
    for goal in waypoints:
        data, ok = _live_steer_marker(sess, data, goal, w=w, step=step, limit=60)
        if not ok:
            cur = _c11_tl(data["frame"], w)
            raise RuntimeError(f"L6 marker steer fail goal={goal} cur={cur}")
    data = _deposit_restore(sess, data)
    return data


def clear_l6(sess: OnlineSession, data) -> tuple:
    """L6 seated path: pad HOLD + bridges → h-merge on bottom pad → A1 off-pad → A3.

    Live L6: Y co-directed (A1 both up / A2 both down); X mirror like L1–4
    (A3 expand / A4 contract). Compress after leaving c14 pad is A3 (not A4).
    """
    lv0 = data.get("levels_completed") or 0
    data = _enter_twins_simple(sess, data)
    data = _l6_normalize_spawn(sess, data)
    executed: list[int] = []
    pcs = m0r0.locate_pieces(data["frame"])
    print(f"  L6 clear enter pcs={pcs}")

    def _step(a: int, label: str = ""):
        nonlocal data
        data = act(sess, a)
        executed.append(a)
        if (data.get("levels_completed") or 0) > lv0:
            print(f"  cleared L6 mid-{label or 'step'} via A{a}")
            return True
        return False

    # Dual top-pad hold: left c12@y14 + right c14@y14 → open BR12
    for a in (1, 1, 3):
        if _step(a, "pad"):
            return data, executed
    print(f"  L6 on pads pcs={m0r0.locate_pieces(data['frame'])}")

    # Park marker left; ride BR12: right block to bottom pad y42
    data = _l6_park_marker(sess, data, [(19, 19)])
    for _ in range(10):
        pcs = m0r0.locate_pieces(data["frame"])
        if len(pcs) == 2 and pcs[1][1] >= 42:
            break
        if _step(2, "bridge"):
            return data, executed
    # Nudge if right overshot while left still holding
    for _ in range(4):
        pcs = m0r0.locate_pieces(data["frame"])
        if len(pcs) != 2:
            break
        if pcs[1][1] <= 42 or pcs[0][1] != 14:
            break
        if _step(1, "bridge-nudge"):
            return data, executed
    print(f"  L6 post-bridge pcs={m0r0.locate_pieces(data['frame'])}")

    # Marker blocks left inward; right contracts to (22,42)
    data = _l6_park_marker(sess, data, [(23, 15)])
    for _ in range(8):
        pcs = m0r0.locate_pieces(data["frame"])
        if len(pcs) == 2 and pcs[1] == (22, 42, 25, 45):
            break
        if _step(4, "contract"):
            return data, executed
    print(f"  L6 right@22,42 pcs={m0r0.locate_pieces(data['frame'])}")

    # Clear block; true A4 swap → (22,14)/(18,42) with right on bottom c14
    data = _l6_park_marker(sess, data, [(19, 19)])
    if _step(4, "swap"):
        return data, executed
    print(f"  L6 post-swap pcs={m0r0.locate_pieces(data['frame'])}")

    # Marker under bottom band so A2 merges horizontally on pad
    data = _l6_park_marker(
        sess, data, [(19, 39), (15, 39), (15, 47), (19, 47)]
    )
    for _ in range(14):
        pcs = m0r0.locate_pieces(data["frame"])
        if len(pcs) == 1:
            break
        if _step(2, "h-merge"):
            return data, executed
    live = m0r0.locate_pieces(data["frame"])
    print(f"  L6 merged pcs={live}")
    if len(live) != 1:
        raise RuntimeError(f"L6 h-merge failed; pcs={live}")

    # Must leave bottom pad before compress — on-pad A3/A4 only re-split/remerge.
    if _step(1, "off-pad"):
        return data, executed
    print(f"  L6 off-pad pcs={m0r0.locate_pieces(data['frame'])}")
    for ca in (3, 4, 1, 2):
        if _step(ca, "compress"):
            print(
                f"  L6 compress A{ca} -> lv={data.get('levels_completed')} "
                f"pcs={m0r0.locate_pieces(data['frame'])}"
            )
            return data, executed
        print(
            f"  L6 compress A{ca} -> lv={data.get('levels_completed')} "
            f"pcs={m0r0.locate_pieces(data['frame'])}"
        )
        if len(m0r0.locate_pieces(data["frame"])) != 1:
            break
    raise RuntimeError(
        f"L6 clear failed; pcs={m0r0.locate_pieces(data['frame'])} "
        f"lv={data.get('levels_completed')}"
    )


def clear_l5(sess: OnlineSession, data) -> tuple:
    """L5 seated path: break Lx+Rx=60 → golden pad hold → climb → top mate → A3.

    Live L5 swaps A3/A4 vs L1–4 model (A3=inward). Compress after merge is A3.
    """
    lv0 = data.get("levels_completed") or 0
    data = _enter_twins_simple(sess, data)
    data = _l5_normalize_spawn(sess, data)
    golden = [3, 3, 3, 1, 1, 1, 1, 3, 1, 4, 4, 1, 4, 4]
    # After golden+climb A1: offline plate BFS (live A3=inward) to top flush.
    after_door = [
        1, 3, 2, 4, 4, 4, 1, 1, 3, 3, 3, 3, 3, 1, 1, 1, 1, 1, 4, 4, 1, 1, 1, 1, 1, 3, 3, 3
    ]
    executed: list[int] = []
    pcs = m0r0.locate_pieces(data["frame"])
    print(f"  L5 clear enter pcs={pcs}")

    def _run(seq: list[int], label: str):
        nonlocal data
        for a in seq:
            data = act(sess, a)
            executed.append(a)
            if (data.get("levels_completed") or 0) > lv0:
                print(f"  cleared L5 mid-{label} via A{a}")
                return True
        return False

    if _run(golden, "golden"):
        return data, executed
    pcs = m0r0.locate_pieces(data["frame"])
    print(f"  L5 golden pcs={pcs}")
    # Expect (10|14|18,42) + (58,26); climb through c12 door
    if _run([1], "climb"):
        return data, executed
    print(f"  L5 through door pcs={m0r0.locate_pieces(data['frame'])}")
    if _run(after_door, "mate"):
        return data, executed
    live = m0r0.locate_pieces(data["frame"])
    print(f"  L5 post-mate pcs={live}")
    if len(live) == 1:
        # L5 horizontal compress = A3 (inward); A4 splits
        for ca in (3, 4, 1, 2):
            data = act(sess, ca)
            executed.append(ca)
            lv = data.get("levels_completed") or 0
            print(f"  L5 compress A{ca} -> lv={lv} pcs={m0r0.locate_pieces(data['frame'])}")
            if lv > lv0:
                return data, executed
    raise RuntimeError(
        f"L5 clear failed; pcs={m0r0.locate_pieces(data['frame'])} "
        f"lv={data.get('levels_completed')}"
    )


def clear_one_level(sess: OnlineSession, data) -> tuple:
    lv0 = data.get("levels_completed") or 0
    # L5/L6: do not use ensure_twins (find_mate_path false-positives / hazard).
    if lv0 == 4:
        return clear_l5(sess, data)
    if lv0 == 5:
        return clear_l6(sess, data)
    data = ensure_twins(sess, data)
    if _is_l5_layout(data["frame"]):
        return clear_l5(sess, data)
    if _is_l6_layout(data["frame"]):
        return clear_l6(sess, data)
    if m0r0.find_mate_path(data["frame"]) is None and m0r0.color_blobs(
        data["frame"], m0r0.MARKER
    ):
        print("  no mate path — clearing blocking markers (L3+)")
        data = relocate_blocking_markers(sess, data)
    params = m0r0.infer_params(data["frame"])
    path = m0r0.find_mate_path(data["frame"], params)
    if not path:
        raise RuntimeError(
            f"no mate path; pcs={m0r0.locate_pieces(data['frame'])} params={params}"
        )
    print(f"  plan len={len(path)} params={params} path={path}")

    # Closed-loop: replan after each step (independent blocks diverge from open-loop).
    executed: list[int] = []
    seen_pcs: set[tuple] = set()
    stall = 0
    for _ in range(100):
        pcs_key = tuple(m0r0.locate_pieces(data["frame"]))
        if pcs_key in seen_pcs:
            stall += 1
        else:
            stall = 0
            seen_pcs.add(pcs_key)
        path = m0r0.find_mate_path(data["frame"], params)
        if not path:
            for ca in m0r0.mate_compress_actions(data["frame"], params) or [4, 1, 2]:
                data = act(sess, ca)
                executed.append(ca)
                if (data.get("levels_completed") or 0) > lv0:
                    print(f"  cleared -> levels={data.get('levels_completed')} via compress A{ca}")
                    return data, executed
            raise RuntimeError(
                f"lost mate path mid-clear; pcs={m0r0.locate_pieces(data['frame'])}"
            )
        # On stall/cycle, try later actions in the plan
        idx = min(stall, len(path) - 1)
        a = path[idx]
        data = act(sess, a)
        executed.append(a)
        lv = data.get("levels_completed") or 0
        live = m0r0.locate_pieces(data["frame"])
        if lv > lv0:
            print(f"  cleared -> levels={lv} after A{a} (exec {len(executed)})")
            return data, executed
        if len(live) == 1:
            print(f"  merged: {live}")
            for ca in m0r0.mate_compress_actions(data["frame"], params) or [4, 1, 2]:
                data = act(sess, ca)
                executed.append(ca)
                lv = data.get("levels_completed") or 0
                print(f"  compress A{ca} -> lv={lv} pcs={m0r0.locate_pieces(data['frame'])}")
                if lv > lv0:
                    return data, executed
            raise RuntimeError("merged but compress did not clear")
        params = m0r0.infer_params(data["frame"])
        if stall > 12:
            raise RuntimeError(
                f"closed-loop stalled; pcs={live} path0={path[:4]}"
            )

    raise RuntimeError(
        f"closed-loop budget exhausted; pcs={m0r0.locate_pieces(data['frame'])} "
        f"n10={int((np.asarray(data['frame'][0])==10).sum())}"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-levels", type=int, default=6)
    args = ap.parse_args()

    key = _api_key()
    sess = OnlineSession(key)
    r = sess.s.post(
        f"{BASE}/api/scorecard/open",
        headers=sess._headers(True),
        json={"tags": ["m0r0_clear"]},
        timeout=60,
    )
    sess.card_id = r.json()["card_id"]
    meta = sess.s.get(f"{BASE}/api/games/m0r0", headers=sess._headers(), timeout=60).json()
    sess.game_id = meta["game_id"]
    print("game", sess.game_id, "win_levels", meta.get("win_levels"))

    data = reset(sess)
    paths = []
    while (data.get("levels_completed") or 0) < args.max_levels:
        if data.get("state") == "WIN":
            break
        lv = data.get("levels_completed") or 0
        print(f"=== level {lv} -> {lv + 1} ===")
        try:
            data, path = clear_one_level(sess, data)
            paths.append(path)
        except Exception as e:
            print("FAIL", e)
            out = ROOT / "tests" / "fixtures" / f"m0r0_fail_lv{lv}.json"
            out.write_text(
                json.dumps(
                    {
                        "frame": data["frame"],
                        "levels_completed": lv,
                        "pcs": m0r0.locate_pieces(data["frame"]),
                        "error": str(e),
                    }
                ),
                encoding="utf-8",
            )
            print("saved", out)
            sess.close()
            return 1
        print(f"  now levels={data.get('levels_completed')} state={data.get('state')}")

    print("DONE levels", data.get("levels_completed"), "state", data.get("state"))
    print("paths", paths)
    sess.close()
    ok = (data.get("levels_completed") or 0) >= args.max_levels or data.get("state") == "WIN"
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
