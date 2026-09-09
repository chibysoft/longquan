"""Restore v24-proven plant/collapse path; kill regressive experiments."""
from pathlib import Path

p = Path(__file__).resolve().parent / "r11l_l3_2wp_probe.py"
t = p.read_text(encoding="utf-8")

# --- plant: remove stop-at-1 and stop-after-first ---
t2 = t
# Remove early break on 1 corridor
old = '''        shallow_n = len([c for c in cur if c[1] < 34])
        # Only ONE corridor plant during west — two early corridor pads lock
        # ship at ~(20,26) and every south merge fails footprint through hazard.
        if len(cor) >= 1 and me["c"][1] >= 26:
            print(
                f"  plant stop at 1 corridor={cor} shallow={shallow_n} "
                f"ship={me['c']} moves={moves}"
            )
            break
        if len(cor) >= 2:
'''
new = '''        shallow_n = len([c for c in cur if c[1] < 34])
        if len(cor) >= 2:
'''
if old in t2:
    t2 = t2.replace(old, new, 1)
    print("removed stop-at-1")
else:
    print("WARN stop-at-1 block not found")

old = '''        if placed:
            # Hard stop after first corridor plant — second plant locks y~26 footprint.
            cor_now = [c for c in count_free14(data["frame"], freeze15) if c[1] >= 34]
            if len(cor_now) >= 1:
                print(f"  plant stop after first corridor={cor_now}")
                break
            continue
'''
new = '''        if placed:
            continue
'''
if old in t2:
    t2 = t2.replace(old, new, 1)
    print("removed stop-after-first")
else:
    print("WARN stop-after-first not found")

# Soft-ok needs 2 corridor
old = '''    # Soft-ok: >=1 corridor plant + bud, ship at/near neck (collapse/neck-slide pulls south).
    if (
        not ok
        and info["bud"] >= 30
        and info["ship"][1] >= 25
        and len(corridor) >= 1
    ):
'''
new = '''    # Soft-ok: 2 corridor plants (v24 path); ship hauled during collapse absorb.
    if (
        not ok
        and info["bud"] >= 30
        and info["ship"][1] >= 25
        and len(corridor) >= 2
    ):
'''
if old in t2:
    t2 = t2.replace(old, new, 1)
    print("soft-ok needs 2 corridor")
else:
    print("WARN soft-ok block not found")

# --- collapse phases: direct for non-wrap while ship north; wrap-col only y=24 ---
old = '''        have_corridor_keepers = len(ks) >= 2
        me_now = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        on_neck = me_now["c"][0] <= 19
        if wp[1] < 34 and wp[0] > 14:
            me_y0 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)["c"][1]
            if me_y0 < 34:
                # Ship still north — wrap/walk only; direct long jumps dead.
                phases = [("wrap", wrap_pads), ("walk", walk_pads)]
            else:
                phases = [("direct", direct_pads), ("walk", walk_pads)]
                if on_neck or not have_corridor_keepers:
                    phases.append(("wrap", wrap_pads))
        elif wp[1] < 34 and wp[0] <= 14:
            phases = [("walk", walk_pads), ("wrap", wrap_pads), ("direct", direct_pads)]
        else:
            phases = [("direct", direct_pads), ("walk", walk_pads)]
'''
new = '''        have_corridor_keepers = len(ks) >= 2
        me_y0 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)["c"][1]
        if wp[1] < 34 and wp[0] > 14:
            # v30: (24,19)->(21,36) works while ship y~26. NEVER wrap (eats keepers).
            phases = [("direct", direct_pads), ("walk", walk_pads)]
        elif wp[1] < 34 and wp[0] <= 14:
            # Wrap-column long jump while ship north → GO. Only slide to y=24.
            if me_y0 < 34:
                phases = [("wrap", [(14, 24), (13, 24), (14, 25)])]
            else:
                phases = [("direct", direct_pads)]
        else:
            phases = [("direct", direct_pads), ("walk", walk_pads)]
'''
if old in t2:
    t2 = t2.replace(old, new, 1)
    print("fixed collapse phases")
else:
    print("WARN phases block not found")
    i = t2.find("have_corridor_keepers")
    print(repr(t2[i:i+700]))

# Skip footprint when ship north on direct
old = '''                if phase != "wrap" and not ship_footprint_ok(g, *tci):
                    print(f"    collapse skip pad{pad} nxt{nxt} footprint {tci}")
                    continue
'''
# may already have me_y variant
if old in t2:
    t2 = t2.replace(
        old,
        '''                me_yf = next(s for s in ships(data["frame"]) if s["chrome"] == 14)["c"][1]
                if phase == "direct" and me_yf < 34 and nxt[1] < 36:
                    continue
                if phase != "wrap" and me_yf >= 34 and not ship_footprint_ok(g, *tci):
                    print(f"    collapse skip pad{pad} nxt{nxt} footprint {tci}")
                    continue
''',
        1,
    )
    print("fixed footprint")
elif "me_y >= 34 and not ship_footprint_ok" in t2 or "me_yf >= 34" in t2:
    print("footprint already gated")
else:
    # try with me_y already present
    old = '''                me_y = next(s for s in ships(data["frame"]) if s["chrome"] == 14)["c"][1]
                # Ship north: centroid prediction sits in hazard and false-rejects.
                if phase == "direct" and me_y < 34 and nxt[1] < 36:
                    continue
                if phase != "wrap" and me_y >= 34 and not ship_footprint_ok(g, *tci):
                    print(f"    collapse skip pad{pad} nxt{nxt} footprint {tci}")
                    continue
'''
    if old in t2:
        print("footprint already good")
    else:
        print("WARN footprint block")

# Disable neck_slide call if present (can burn / mis-place)
old = '''    # Pull ship onto west neck before collapse (avoid y~29–33 footprint lock).
    info = snap(d, freeze15, "pre-neck")
    if info["ship"][0] > 19 or info["ship"][1] < 32:
        d, _ = neck_slide14(sess, d, freeze15)
'''
if old in t2:
    # find how much to skip — read until after-neck
    start = t2.find(old)
    end = t2.find('info = snap(d, freeze15, "after-neck")', start)
    if end > start:
        # keep after-neck snap or replace block with nothing
        end_line = t2.find("\n", end)
        t2 = t2[:start] + t2[end_line + 1 :]
        print("removed neck_slide block")
    else:
        print("WARN after-neck not found")
else:
    print("WARN neck_slide block not found")

p.write_text(t2, encoding="utf-8")
print("done", p)
