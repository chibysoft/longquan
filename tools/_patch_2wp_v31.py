"""Defer wrap-column long jumps; only slide to y=24 while ship north."""
from pathlib import Path

p = Path(__file__).resolve().parent / "r11l_l3_2wp_probe.py"
t = p.read_text(encoding="utf-8")

old = '''        have_corridor_keepers = len(ks) >= 2
        if wp[1] < 34 and wp[0] > 14:
            # Direct first when keepers already on corridor (walk mid-band → dead/noop).
            phases = [("direct", direct_pads), ("walk", walk_pads)]
            if not have_corridor_keepers:
                phases.append(("wrap", wrap_pads))
        elif wp[1] < 34 and wp[0] <= 14:
            phases = [("direct", direct_pads), ("walk", walk_pads)]  # no south 28-32 (dead)
        else:
            phases = [("direct", direct_pads), ("walk", walk_pads)]
'''
new = '''        have_corridor_keepers = len(ks) >= 2
        me_y = next(s for s in ships(data["frame"]) if s["chrome"] == 14)["c"][1]
        if wp[1] < 34 and wp[0] > 14:
            phases = [("direct", direct_pads), ("walk", walk_pads)]
            if not have_corridor_keepers:
                phases.append(("wrap", wrap_pads))
        elif wp[1] < 34 and wp[0] <= 14:
            # Long corridor jump from wrap column while ship north → GAME_OVER.
            # Only slide south to y=24; retry corridor after ship is up.
            if me_y < 34:
                phases = [("wrap", [(14, 24), (13, 24), (14, 25)])]
            else:
                phases = [("direct", direct_pads)]
        else:
            phases = [("direct", direct_pads), ("walk", walk_pads)]
'''
if old not in t:
    # show nearby
    i = t.find("have_corridor_keepers")
    print(repr(t[i:i+500]))
    raise SystemExit("phases block mismatch")
t = t.replace(old, new, 1)
p.write_text(t, encoding="utf-8")
print("ok")
