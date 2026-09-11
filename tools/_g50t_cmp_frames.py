import json
from pathlib import Path
import numpy as np

def load(name):
    raw = json.loads(Path("tests/fixtures", name).read_text(encoding="utf-8"))
    fr = raw.get("frame", raw)
    arr = np.array(fr)
    if arr.ndim == 3:
        arr = arr[0]
    return arr

for name in ["g50t_l3_tip2_frame.json", "g50t_l3_latched_frame.json"]:
    g = load(name)
    print("===", name, "e8", int((g == 8).sum()))
    for y in [28, 34, 40, 46]:
        row = []
        for x in [10, 16, 22, 28, 34, 40, 46, 52]:
            sub = g[y - 2 : y + 3, x - 2 : x + 3]
            c = int(g[y, x])
            n8 = int((sub == 8).sum())
            n0 = int((sub == 0).sum())
            ok = n8 == 0 and n0 == 0
            row.append(f"{x}:{'Y' if ok else 'n'}{c}")
        print("y", y, row)
