import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20

REC = Path(
    r"D:\Projects\ARC-AGI-3-Agents\recordings"
    r"\ls20-9607627b.lingjingsolo.800.5f1bf1fd-a88e-4c5f-8c63-3c85bc6f5f97.recording.jsonl"
)

rows = [json.loads(l).get("data", {}) for l in open(REC, encoding="utf-8")]


def summarize(tag, d):
    f = d["frame"]
    st = ls20.init(f)
    off = ls20.grid_offset(f)
    stamp = next((g.shape for g in st.goals if g.id == "ls20-stamp"), None)
    marker = next((g.shape for g in st.goals if g.id == "ls20-marker"), None)
    wu = ls20.build_walkable(f, off, armed=False)
    wa = ls20.build_walkable(f, off, armed=True)
    print(
        tag,
        "lv=", d.get("levels_completed"),
        "cursor=", st.cursor,
        "mover=", ls20.locate_mover(f),
        "stamp=", stamp,
        "marker=", marker,
        "ui=", ls20.ui_energy(f),
        "armed_only=", sorted(wa - wu)[:10],
        "n_warps=", len(ls20.detect_warps(f)),
        "avail=", d.get("available_actions"),
    )


for i in [0, 12, 57, 96, 97, 110, 130, 138, 139, 140, 182, 183]:
    if i < len(rows):
        summarize(f"i{i}", rows[i])

fix = json.loads((ROOT / "tests/fixtures/ls20_l4_frame_live.json").read_text())["frame"]
summarize("FIXTURE_L4", {"frame": fx, "levels_completed": 3})

# When does stamp become L4-like (8,4,14,10)?
for i, d in enumerate(rows):
    st = ls20.init(d["frame"])
    stamp = next((g.shape for g in st.goals if g.id == "ls20-stamp"), None)
    if stamp == (8, 4, 14, 10):
        summarize(f"first_L4stamp_i{i}", d)
        break
else:
    print("no L4-like stamp found in recording")
    # show stamp progression at level bounds
    for i, lv in [(96, 3), (139, 4), (183, 5)]:
        st = ls20.init(rows[i]["frame"])
        print("bound", i, "stamp", next((g.shape for g in st.goals if g.id == "ls20-stamp"), None))
