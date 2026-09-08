"""vc33 L2: pad→delta map + accent14/gap14 align clear hunt.

tags=["vc33_recon"]. Frame-derived; no canned click tables.
Clears L1 via accent/gap align, ACTION1 sync, then probes L2.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import BASE, _api_key  # noqa: E402
from tools.vc33_recon_probe import TAGS, body_changes, body_ndiff, c9_blocks, _headers  # noqa: E402

OUT = ROOT / "tests" / "fixtures" / "vc33_l2_probe_result.json"
FIXTURE_L2_CLEAR = ROOT / "tests" / "fixtures" / "vc33_l2_clear_frame.json"
FIXTURE_L3 = ROOT / "tests" / "fixtures" / "vc33_l3_frame_live.json"


def plane(frame) -> np.ndarray:
    a = np.asarray(frame, dtype=np.int64)
    return a[0] if a.ndim == 3 else a


def components(g: np.ndarray, color: int):
    H, W = g.shape
    seen = np.zeros_like(g, dtype=bool)
    out = []
    for y in range(H):
        for x in range(W):
            if seen[y, x] or int(g[y, x]) != color:
                continue
            stack = [(x, y)]
            seen[y, x] = True
            cells = []
            while stack:
                cx, cy = stack.pop()
                cells.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if (
                        0 <= nx < W
                        and 0 <= ny < H
                        and not seen[ny, nx]
                        and int(g[ny, nx]) == color
                    ):
                        seen[ny, nx] = True
                        stack.append((nx, ny))
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            out.append({
                "n": len(cells),
                "x0": min(xs),
                "y0": min(ys),
                "x1": max(xs),
                "y1": max(ys),
                "cx": sum(xs) / len(xs),
                "cy": sum(ys) / len(ys),
            })
    out.sort(key=lambda b: (b["y0"], b["x0"]))
    return out


def sprite_bundle(g: np.ndarray):
    """Largest CC of colors in {4,11,14} with y>0; split body/accent."""
    accents = {11, 14}
    body = {4}
    interesting = accents | body
    H, W = g.shape
    seen = np.zeros_like(g, dtype=bool)
    best = []
    for y in range(1, H):
        for x in range(W):
            if seen[y, x] or int(g[y, x]) not in interesting:
                continue
            stack = [(x, y)]
            seen[y, x] = True
            cells = []
            while stack:
                cx, cy = stack.pop()
                cells.append((cx, cy, int(g[cy, cx])))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if (
                        0 <= nx < W
                        and 1 <= ny < H
                        and not seen[ny, nx]
                        and int(g[ny, nx]) in interesting
                    ):
                        seen[ny, nx] = True
                        stack.append((nx, ny))
            if len(cells) > len(best):
                best = cells
    if not best:
        return None
    xs = [c[0] for c in best]
    ys = [c[1] for c in best]
    acc_cells = [c for c in best if c[2] in accents]
    body_cells = [c for c in best if c[2] in body]
    def bb(cells):
        if not cells:
            return None
        xs_ = [c[0] for c in cells]
        ys_ = [c[1] for c in cells]
        return {
            "n": len(cells),
            "x0": min(xs_),
            "y0": min(ys_),
            "x1": max(xs_),
            "y1": max(ys_),
            "cx": sum(xs_) / len(xs_),
            "cy": sum(ys_) / len(ys_),
            "colors": sorted({c[2] for c in cells}),
        }
    return {
        "n": len(best),
        "x0": min(xs),
        "y0": min(ys),
        "x1": max(xs),
        "y1": max(ys),
        "cx": sum(xs) / len(xs),
        "cy": sum(ys) / len(ys),
        "accent": bb(acc_cells),
        "body": bb(body_cells),
    }


def beam_gaps(g: np.ndarray):
    """Accent-colored gaps embedded in color5 horizontal beams."""
    # find color5 row bands, then accent colors inside those rows but not near sprite
    ys5, xs5 = np.where(g == 5)
    if len(ys5) == 0:
        return []
    y0, y1 = int(ys5.min()), int(ys5.max())
    gaps = []
    for color in (11, 14):
        for comp in components(g, color):
            # gap sits inside beam y-range and is short in x (≤4)
            if comp["y0"] >= y0 and comp["y1"] <= y1 and (comp["x1"] - comp["x0"]) <= 3:
                # exclude if overlapping sprite y heavily below beams? sprite is usually below
                gaps.append({**comp, "color": color})
    # prefer gaps whose y overlaps color5
    filtered = []
    for gap in gaps:
        band = g[gap["y0"] : gap["y1"] + 1, :]
        if np.any(band == 5):
            filtered.append(gap)
    filtered.sort(key=lambda b: (b["y0"], b["x0"]))
    return filtered


def aligned(g) -> bool:
    sp = sprite_bundle(g)
    gaps = beam_gaps(g)
    if not sp or not sp.get("accent") or not gaps:
        return False
    acc = sp["accent"]
    # match same accent color
    for gap in gaps:
        if gap["color"] in acc.get("colors", []):
            if acc["x0"] == gap["x0"] and acc["x1"] == gap["x1"]:
                return True
    return False


def pick_gap(g):
    sp = sprite_bundle(g)
    gaps = beam_gaps(g)
    if not sp or not sp.get("accent") or not gaps:
        return None
    acc = sp["accent"]
    same = [g for g in gaps if g["color"] in acc.get("colors", [])]
    if not same:
        same = gaps
    # nearest in x
    same.sort(key=lambda g: abs(g["cx"] - acc["cx"]))
    return same[0]


class Sess:
    def __init__(self, key: str):
        self.key = key
        self.s = requests.Session()
        self.card_id = None
        self.game_id = None
        self.guid = None

    def open(self):
        r = self.s.post(
            f"{BASE}/api/scorecard/open",
            headers=_headers(self.key, True),
            json={"tags": TAGS},
            timeout=20,
        )
        r.raise_for_status()
        self.card_id = r.json()["card_id"]
        r = self.s.get(f"{BASE}/api/games/vc33", headers=_headers(self.key), timeout=20)
        r.raise_for_status()
        self.game_id = r.json()["game_id"]

    def reset(self):
        r = self.s.post(
            f"{BASE}/api/cmd/RESET",
            headers=_headers(self.key, True),
            json={"card_id": self.card_id, "game_id": self.game_id},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        self.guid = data["guid"]
        return data

    def action(self, name: str, **kw):
        body = {"game_id": self.game_id, "guid": self.guid, **kw}
        r = self.s.post(
            f"{BASE}/api/cmd/{name}",
            headers=_headers(self.key, True),
            json=body,
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        self.guid = data.get("guid", self.guid)
        return data

    def click(self, x, y):
        return self.action("ACTION6", x=int(x), y=int(y))

    def close(self):
        if not self.card_id:
            return
        try:
            self.s.post(
                f"{BASE}/api/scorecard/close",
                headers=_headers(self.key, True),
                json={"card_id": self.card_id},
                timeout=15,
            )
        except Exception:
            pass


def clear_l1(sess: Sess) -> dict:
    """Frame-derived: click pad that reduces |accent.cx-gap.cx| until aligned."""
    d = sess.reset()
    g = plane(d["frame"])
    steps = []
    for i in range(20):
        lv = int(d.get("levels_completed") or 0)
        if lv >= 1 and aligned(g):
            break
        if lv >= 1:
            break
        sp = sprite_bundle(g)
        gap = pick_gap(g)
        pads = c9_blocks(g)
        if not sp or not sp.get("accent") or not gap or len(pads) < 1:
            raise RuntimeError(f"L1 perceive fail sp={sp} gap={gap} pads={pads}")
        # probe each pad offline? we need online one-step — pick by known L1 map
        # better: try each pad on copies via reset-replay is expensive; instead
        # measure desired dx sign and pick pad empirically from one-step trials
        # stored from previous knowledge only as fallback:
        # Online micro-search: for each pad, reset-replay path then one click — heavy.
        # Lightweight: click each pad from current via undo-less search with resets.
        best = None
        path_clicks = [s["xy"] for s in steps]
        for pi, pad in enumerate(sorted(pads, key=lambda b: b["y0"])):
            # replay
            dd = sess.reset()
            gg = plane(dd["frame"])
            for xy in path_clicks:
                dd = sess.click(*xy)
                gg = plane(dd["frame"])
            xy = (int(round(pad["cx"])), int(round(pad["cy"])))
            sp0 = sprite_bundle(gg)
            dd2 = sess.click(*xy)
            gg2 = plane(dd2["frame"])
            sp1 = sprite_bundle(gg2)
            if not sp0 or not sp1 or not sp0.get("accent") or not sp1.get("accent"):
                continue
            before = abs(sp0["accent"]["cx"] - gap["cx"])
            after = abs(sp1["accent"]["cx"] - pick_gap(gg2)["cx"])
            ddx = sp1["accent"]["cx"] - sp0["accent"]["cx"]
            ddy = sp1["accent"]["cy"] - sp0["accent"]["cy"]
            score = before - after
            cand = {
                "pad_i": pi,
                "xy": xy,
                "score": score,
                "ddx": ddx,
                "ddy": ddy,
                "body_ndiff": body_ndiff(gg, gg2),
                "levels": int(dd2.get("levels_completed") or 0),
            }
            if best is None or cand["score"] > best["score"] or (
                cand["score"] == best["score"] and cand["body_ndiff"] > best["body_ndiff"]
            ):
                best = cand
        if best is None or best["body_ndiff"] == 0 and best["score"] <= 0:
            raise RuntimeError(f"L1 stuck steps={steps}")
        # apply best on real path
        d = sess.reset()
        g = plane(d["frame"])
        for xy in path_clicks:
            d = sess.click(*xy)
            g = plane(d["frame"])
        d = sess.click(*best["xy"])
        g = plane(d["frame"])
        steps.append({**best, "aligned": aligned(g), "levels": int(d.get("levels_completed") or 0),
                      "sprite": sprite_bundle(g), "gap": pick_gap(g)})
        print("L1 step", steps[-1]["xy"], "lv", steps[-1]["levels"], "aligned", steps[-1]["aligned"])
        if steps[-1]["levels"] >= 1:
            break
    return {"steps": steps, "levels": int(d.get("levels_completed") or 0), "frame": g, "data": d}


def enter_l2(sess: Sess) -> dict:
    cleared = clear_l1(sess)
    assert cleared["levels"] >= 1, cleared
    stale = cleared["frame"]
    d = sess.action("ACTION1")
    g = plane(d["frame"])
    diff = int(np.sum(stale != g))
    print("L2 sync ACTION1 diff", diff, "lv", d.get("levels_completed"), summarize(g))
    return {"data": d, "frame": g, "sync_diff": diff, "l1_steps": cleared["steps"]}


def summarize(g):
    return {
        "sprite": sprite_bundle(g),
        "pads": c9_blocks(g),
        "gaps": beam_gaps(g),
        "aligned": aligned(g),
        "hist": {int(k): int(v) for k, v in zip(*np.unique(g, return_counts=True))},
    }


def map_pads(sess: Sess, enter: dict) -> list:
    """From fresh L2 each time, click one pad, measure accent delta."""
    rows = []
    # need deterministic enter: clear L1 + sync each trial
    for trial in range(8):
        ent = enter_l2(sess)
        g0 = ent["frame"]
        pads = sorted(c9_blocks(g0), key=lambda b: b["y0"])
        if trial >= len(pads):
            break
        pad = pads[trial]
        xy = (int(round(pad["cx"])), int(round(pad["cy"])))
        sp0 = sprite_bundle(g0)
        d = sess.click(*xy)
        g1 = plane(d["frame"])
        sp1 = sprite_bundle(g1)
        row = {
            "pad_index_by_y": trial,
            "pad": pad,
            "xy": list(xy),
            "body_ndiff": body_ndiff(g0, g1),
            "changes": body_changes(g0, g1),
            "ddx": None if not (sp0 and sp1) else round(sp1["cx"] - sp0["cx"], 3),
            "ddy": None if not (sp0 and sp1) else round(sp1["cy"] - sp0["cy"], 3),
            "accent_ddx": None
            if not (sp0 and sp1 and sp0.get("accent") and sp1.get("accent"))
            else round(sp1["accent"]["cx"] - sp0["accent"]["cx"], 3),
            "accent_ddy": None
            if not (sp0 and sp1 and sp0.get("accent") and sp1.get("accent"))
            else round(sp1["accent"]["cy"] - sp0["accent"]["cy"], 3),
            "sprite_after": sp1,
            "levels": int(d.get("levels_completed") or 0),
            "aligned": aligned(g1),
        }
        rows.append(row)
        print(
            f"PAD[{trial}] y={pad['y0']} xy={xy} ddx={row['ddx']} ddy={row['ddy']} "
            f"accΔ=({row['accent_ddx']},{row['accent_ddy']}) body={row['body_ndiff']} lv={row['levels']}"
        )
    return rows


def clear_l2(sess: Sess) -> dict:
    ent = enter_l2(sess)
    d = ent["data"]
    g = ent["frame"]
    steps = []
    for i in range(24):
        lv = int(d.get("levels_completed") or 0)
        if lv >= 2:
            break
        sp = sprite_bundle(g)
        gap = pick_gap(g)
        pads = sorted(c9_blocks(g), key=lambda b: b["y0"])
        path = [s["xy"] for s in steps]
        best = None
        for pi, pad in enumerate(pads):
            # replay to L2 start then path
            ent2 = enter_l2(sess)
            gg = ent2["frame"]
            dd = ent2["data"]
            for xy in path:
                dd = sess.click(*xy)
                gg = plane(dd["frame"])
            xy = (int(round(pad["cx"])), int(round(pad["cy"])))
            sp0 = sprite_bundle(gg)
            gap0 = pick_gap(gg)
            dd2 = sess.click(*xy)
            gg2 = plane(dd2["frame"])
            sp1 = sprite_bundle(gg2)
            gap1 = pick_gap(gg2)
            if not (sp0 and sp1 and sp0.get("accent") and sp1.get("accent") and gap0 and gap1):
                continue
            before = abs(sp0["accent"]["cx"] - gap0["cx"]) + abs(sp0["accent"]["cy"] - gap0["cy"])
            after = abs(sp1["accent"]["cx"] - gap1["cx"]) + abs(sp1["accent"]["cy"] - gap1["cy"])
            cand = {
                "pad_i": pi,
                "xy": list(xy),
                "score": before - after,
                "ddx": sp1["cx"] - sp0["cx"],
                "ddy": sp1["cy"] - sp0["cy"],
                "body_ndiff": body_ndiff(gg, gg2),
                "levels": int(dd2.get("levels_completed") or 0),
                "aligned": aligned(gg2),
            }
            if best is None or cand["score"] > best["score"] or (
                abs(cand["score"] - best["score"]) < 1e-6 and cand["body_ndiff"] > best["body_ndiff"]
            ):
                best = cand
        if best is None:
            raise RuntimeError("no pad candidate")
        # apply
        ent3 = enter_l2(sess)
        g = ent3["frame"]
        d = ent3["data"]
        for xy in path:
            d = sess.click(*xy)
            g = plane(d["frame"])
        d = sess.click(*best["xy"])
        g = plane(d["frame"])
        entry = {
            **best,
            "levels": int(d.get("levels_completed") or 0),
            "aligned": aligned(g),
            "sprite": sprite_bundle(g),
            "gap": pick_gap(g),
        }
        steps.append(entry)
        print(
            f"L2 s{i} pad={entry['pad_i']} xy={entry['xy']} score={entry['score']} "
            f"Δ=({entry['ddx']},{entry['ddy']}) lv={entry['levels']} aligned={entry['aligned']}"
        )
        if entry["levels"] >= 2:
            break
        if entry["body_ndiff"] == 0 and entry["score"] <= 0:
            print("stuck")
            break
    return {"steps": steps, "levels": int(d.get("levels_completed") or 0), "frame": g, "data": d,
            "summary": summarize(g)}


def main():
    key = _api_key()
    sess = Sess(key)
    out = {}
    try:
        sess.open()
        out["game_id"] = sess.game_id
        out["card_id"] = sess.card_id

        ent = enter_l2(sess)
        out["l2_enter"] = {
            "sync_diff": ent["sync_diff"],
            "summary": summarize(ent["frame"]),
            "l1_steps": [
                {k: v for k, v in s.items() if k != "sprite"}
                for s in ent["l1_steps"]
            ],
        }

        out["pad_map"] = map_pads(sess, ent)
        cleared = clear_l2(sess)
        out["l2_clear"] = {
            "levels": cleared["levels"],
            "steps": [
                {k: v for k, v in s.items() if k not in ("sprite",)}
                for s in cleared["steps"]
            ],
            "summary": cleared["summary"],
            "cleared": cleared["levels"] >= 2,
        }
        print("L2 cleared?", out["l2_clear"]["cleared"], "levels", cleared["levels"])

        if cleared["levels"] >= 2:
            FIXTURE_L2_CLEAR.write_text(
                json.dumps(
                    {
                        "game_id": sess.game_id,
                        "meta": {
                            "levels_completed": cleared["data"].get("levels_completed"),
                            "state": cleared["data"].get("state"),
                            "available_actions": cleared["data"].get("available_actions"),
                            "win_levels": cleared["data"].get("win_levels"),
                        },
                        "summary": cleared["summary"],
                        "steps": out["l2_clear"]["steps"],
                        "frame": cleared["frame"].tolist(),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            print("saved", FIXTURE_L2_CLEAR)
            stale = cleared["frame"]
            d3 = sess.action("ACTION1")
            g3 = plane(d3["frame"])
            diff = int(np.sum(stale != g3))
            print("L3 sync diff", diff, summarize(g3))
            if diff > 100:
                FIXTURE_L3.write_text(
                    json.dumps(
                        {
                            "game_id": sess.game_id,
                            "meta": {
                                "levels_completed": d3.get("levels_completed"),
                                "state": d3.get("state"),
                                "available_actions": d3.get("available_actions"),
                                "win_levels": d3.get("win_levels"),
                            },
                            "sync": {"action": "ACTION1", "pixel_diff_from_stale": diff},
                            "summary": summarize(g3),
                            "frame": g3.tolist(),
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                print("saved", FIXTURE_L3)
                out["l3_enter"] = {"sync_diff": diff, "summary": summarize(g3)}
    finally:
        sess.close()

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("saved", OUT)
    return 0 if out.get("l2_clear", {}).get("cleared") else 1


if __name__ == "__main__":
    raise SystemExit(main())
