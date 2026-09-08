"""vc33 L2: after +x stuck, try upper pads to unblock corridor."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l2_probe import (  # noqa: E402
    Sess,
    aligned,
    body_changes,
    body_ndiff,
    c9_blocks,
    enter_l2,
    pick_gap,
    plane,
    sprite_bundle,
    summarize,
)

OUT = ROOT / "tests" / "fixtures" / "vc33_l2_unblock_hunt.json"


def pads_by_y(g):
    return sorted(c9_blocks(g), key=lambda b: b["y0"])


def click_pad(sess, g, y0):
    pad = next(p for p in pads_by_y(g) if p["y0"] == y0)
    xy = (int(round(pad["cx"])), int(round(pad["cy"])))
    d = sess.click(*xy)
    g2 = plane(d["frame"])
    return d, g2, xy


def col_hist(g, x0, x1):
    """nonzero colors in x band."""
    band = g[:, x0 : x1 + 1]
    return {int(k): int(v) for k, v in zip(*np.unique(band, return_counts=True))}


def main():
    key = _api_key()
    sess = Sess(key)
    out = {"trials": []}
    try:
        sess.open()
        out["game_id"] = sess.game_id

        # Trial A: +x until stuck, then each upper pad, then +x again
        for opener_y in (16, 24, None):
            for opener_first in (True, False):
                # opener_first: click opener before any +x
                label = f"opener{opener_y}_first{opener_first}"
                ent = enter_l2(sess)
                d = ent["data"]
                g = ent["frame"]
                log = []
                print("===", label)

                def step(kind, y0=None):
                    nonlocal d, g
                    g0 = g
                    sp0 = sprite_bundle(g)
                    if kind == "plus":
                        d, g, xy = click_pad(sess, g, 44)
                    elif kind == "minus":
                        d, g, xy = click_pad(sess, g, 36)
                    else:
                        d, g, xy = click_pad(sess, g, y0)
                    sp1 = sprite_bundle(g)
                    entry = {
                        "kind": kind,
                        "y0": y0 if kind == "open" else (44 if kind == "plus" else 36),
                        "xy": list(xy),
                        "body_ndiff": body_ndiff(g0, g),
                        "changes": body_changes(g0, g),
                        "acc": (sp1 or {}).get("accent"),
                        "ddx": None if not (sp0 and sp1) else round(sp1["cx"] - sp0["cx"], 3),
                        "levels": int(d.get("levels_completed") or 0),
                        "aligned": aligned(g),
                    }
                    log.append(entry)
                    print(
                        f"  {kind} y={entry['y0']} body={entry['body_ndiff']} "
                        f"ddx={entry['ddx']} lv={entry['levels']} aligned={entry['aligned']} "
                        f"acc={entry['acc']}"
                    )
                    return entry

                if opener_first and opener_y is not None:
                    step("open", opener_y)

                # +x until stuck (max 8)
                for _ in range(8):
                    e = step("plus")
                    if e["levels"] >= 2:
                        break
                    if e["body_ndiff"] == 0 or (e["ddx"] or 0) == 0:
                        break
                if log[-1]["levels"] >= 2:
                    out["trials"].append({"label": label, "log": log, "cleared": True})
                    print("CLEARED early")
                    continue

                if not opener_first and opener_y is not None:
                    step("open", opener_y)
                    # try +x more
                    for _ in range(8):
                        e = step("plus")
                        if e["levels"] >= 2:
                            break
                        if e["body_ndiff"] == 0 or (e["ddx"] or 0) == 0:
                            break

                out["trials"].append({
                    "label": label,
                    "log": log,
                    "cleared": any(e["levels"] >= 2 for e in log),
                    "final": summarize(g),
                })

        # Trial B: alternate openers with +x
        for pattern in ("O16,+", "O24,+", "+,O16,+", "+,O24,+", "O16,O24,+", "O24,O16,+",
                        "+,+,O16,+", "+,+,O24,+", "+,+,+,O16,+", "+,+,+,O24,+"):
            ent = enter_l2(sess)
            d = ent["data"]
            g = ent["frame"]
            log = []
            print("=== pattern", pattern)
            stuck = False
            for token in (pattern.split(",") * 6)[:18]:
                if token == "+":
                    e = None
                    g0 = g
                    sp0 = sprite_bundle(g)
                    d, g, xy = click_pad(sess, g, 44)
                    sp1 = sprite_bundle(g)
                    e = {
                        "token": token,
                        "xy": list(xy),
                        "body_ndiff": body_ndiff(g0, g),
                        "ddx": None if not (sp0 and sp1) else round(sp1["cx"] - sp0["cx"], 3),
                        "levels": int(d.get("levels_completed") or 0),
                        "aligned": aligned(g),
                        "acc": (sp1 or {}).get("accent"),
                    }
                elif token.startswith("O"):
                    y0 = int(token[1:])
                    g0 = g
                    sp0 = sprite_bundle(g)
                    d, g, xy = click_pad(sess, g, y0)
                    sp1 = sprite_bundle(g)
                    e = {
                        "token": token,
                        "xy": list(xy),
                        "body_ndiff": body_ndiff(g0, g),
                        "ddx": None if not (sp0 and sp1) else round(sp1["cx"] - sp0["cx"], 3),
                        "levels": int(d.get("levels_completed") or 0),
                        "aligned": aligned(g),
                        "acc": (sp1 or {}).get("accent"),
                        "changes": body_changes(g0, g),
                    }
                log.append(e)
                print(f"  {e['token']} body={e['body_ndiff']} ddx={e['ddx']} lv={e['levels']} acc={e['acc']}")
                if e["levels"] >= 2:
                    break
                if e["token"] == "+" and (e["body_ndiff"] == 0 or (e["ddx"] or 0) == 0):
                    # if pattern has more openers ahead in remaining, continue; else stop cycle
                    stuck = True
            out["trials"].append({
                "label": f"pat:{pattern}",
                "log": log,
                "cleared": any(e["levels"] >= 2 for e in log),
                "final": summarize(g),
            })
            if out["trials"][-1]["cleared"]:
                print("CLEARED", pattern)
                # save clear frame
                break

        cleared = [t["label"] for t in out["trials"] if t.get("cleared")]
        out["cleared_hits"] = cleared
        print("HITS", cleared)
    finally:
        sess.close()

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("saved", OUT)
    return 0 if cleared else 1


if __name__ == "__main__":
    raise SystemExit(main())
