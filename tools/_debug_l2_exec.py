"""One-shot debug: L2 open-loop exec with layer-aware color-12 logging."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import plan_two_phase


def bb(g, cols):
    ys, xs = np.where(np.isin(g, cols))
    if len(xs) == 0:
        return None
    return (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))


def main() -> int:
    sess = OnlineSession(_api_key())
    sess.open(tags=["ls20_l2_debug"])
    try:
        r = sess.reset()
        frame, meta = r["frame"], r
        path, _ = plan_two_phase(frame)
        for d in path:
            out = sess.action(DIR_TO_ACTION[d])
            frame, meta = out["frame"], out
            if int(meta.get("levels_completed") or 0) >= 1:
                break
        sync = sess.action(2)
        frame, meta = sync["frame"], sync
        print("L2 start", ls20.locate_mover(frame))
        path, info = plan_two_phase(frame)
        print("plan", info, "n", len(path))
        for i, a in enumerate(path, 1):
            out = sess.action(DIR_TO_ACTION[a])
            frame, meta = out["frame"], out
            arr = np.asarray(frame)
            g0 = arr[0] if arr.ndim == 3 else arr
            g1 = arr[1] if arr.ndim == 3 and arr.shape[0] > 1 else None
            c12_0 = bb(g0, (12,))
            c12_1 = bb(g1, (12,)) if g1 is not None else None
            print(
                f"{i:02d} A{DIR_TO_ACTION[a]} c12_0={c12_0} c12_1={c12_1} "
                f"c01={bb(g0, (0, 1))} carry={ls20.carrying_near_mover(frame)} "
                f"lv={meta.get('levels_completed')} shape={arr.shape}"
            )
            if c12_0 is None:
                out_path = ROOT / "tests/fixtures/ls20_l2_fail_step.json"
                out_path.write_text(
                    json.dumps({"i": i, "frame": arr.tolist()}, separators=(",", ":")),
                    encoding="utf-8",
                )
                print("saved", out_path)
                # also print where 12 went on any layer
                for li in range(arr.shape[0] if arr.ndim == 3 else 1):
                    layer = arr[li] if arr.ndim == 3 else arr
                    print(f"  layer{li} c12={bb(layer, (12,))} top={dict(zip(*np.unique(layer, return_counts=True)))}")
                break
            if i > info["path1_len"] + 5 and int(meta.get("levels_completed") or 0) < 2:
                # keep going a bit into phase2
                pass
        return 0
    finally:
        sess.close()


if __name__ == "__main__":
    raise SystemExit(main())
