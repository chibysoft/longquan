from pathlib import Path

p = Path(__file__).resolve().parent / "r11l_l3_2wp_probe.py"
t = p.read_text(encoding="utf-8")

# Insert neck_slide helper before collapse_to_2 if missing
if "def neck_slide14(" not in t:
    anchor = "def collapse_to_2(sess, data, freeze15):"
    helper = r'''def neck_slide14(sess, data, freeze15):
    """Pull ship onto west neck (x<=19) by sliding an eastern corridor wp west.

    Needed when 2 corridor plants left ship at ~(20,26): any south merge then
    puts the centroid through the y~29–33 hazard band.
    """
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    if me["c"][0] <= 19 and me["c"][1] >= 28:
        return data, True
    if step_budget(data["frame"]) < 10:
        return data, False
    cur = count_free14(data["frame"], freeze15)
    cor = [w for w in cur if w[1] >= 34]
    if len(cor) < 1:
        return data, False
    g = _plane(data["frame"])
    # Slide easternmost corridor wp west, keeping y>=34 and sep from siblings.
    lead = max(cor, key=lambda w: w[0])
    others = [c for c in cur if c != lead]
    for dest in (
        (lead[0] - 6, lead[1]),
        (lead[0] - 8, lead[1]),
        (lead[0] - 6, 34),
        (lead[0] - 4, 36),
        (16, 36),
        (16, 34),
        (18, 36),
        (18, 34),
    ):
        if dest[0] < 14 or dest[1] < 34 or dest == lead:
            continue
        if not (0 <= dest[0] < 64 and 0 <= dest[1] < 64):
            continue
        if int(g[dest[1], dest[0]]) not in (5, 3, 0, 6):
            continue
        if near_any(dest, others + freeze15, cheb=5):
            continue
        trial = [dest if c == lead else c for c in cur]
        tc = centroid(trial)
        tci = (int(round(tc[0])), int(round(tc[1])))
        if not ship_footprint_ok(g, *tci):
            continue
        data, newc, st = move_wp(sess, data, lead, dest, freeze15)
        print(
            f"  neck-slide {lead}->{dest} {st}->{newc} "
            f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if st == "moved":
            me2 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            return data, me2["c"][0] <= 20
    print("  neck-slide no-move", cur, "ship", me["c"])
    return data, False


'''
    t = t.replace(anchor, helper + anchor, 1)

# Wire neck_slide into run_probe before collapse loop
old = '''    ok = False
    for ci in range(8):
        d, ok = collapse_to_2(sess, d, freeze15)'''
new = '''    # Pull ship onto west neck before collapse (avoid y~29–33 footprint lock).
    info = snap(d, freeze15, "pre-neck")
    if info["ship"][0] > 19 or info["ship"][1] < 32:
        d, _ = neck_slide14(sess, d, freeze15)
        if d.get("state") == "GAME_OVER" or "frame" not in d:
            print("FAIL GO during neck-slide")
            return 1
        freeze15 = lock_other_ship(d["frame"], 14)
        snap(d, freeze15, "after-neck")

    ok = False
    for ci in range(8):
        d, ok = collapse_to_2(sess, d, freeze15)'''
if old not in t:
    raise SystemExit("collapse loop anchor not found")
t = t.replace(old, new, 1)

# Also: for collapse walk/direct, if ship x<=19, allow wrap again for stragglers
# (have_corridor_keepers still disables wrap — enable wrap when ship on neck)
old2 = '''        have_corridor_keepers = len(ks) >= 2
        if wp[1] < 34 and wp[0] > 14:
            phases = [("walk", walk_pads), ("direct", direct_pads)]
            if not have_corridor_keepers:
                phases.append(("wrap", wrap_pads))'''
new2 = '''        me_now = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        on_neck = me_now["c"][0] <= 19
        have_corridor_keepers = len(ks) >= 2
        if wp[1] < 34 and wp[0] > 14:
            phases = [("walk", walk_pads), ("direct", direct_pads)]
            # Wrap only when ship already on neck (safe) or no corridor keepers.
            if on_neck or not have_corridor_keepers:
                phases.append(("wrap", wrap_pads))'''
if old2 not in t:
    print("WARN phase block not found — check manually")
else:
    t = t.replace(old2, new2, 1)

p.write_text(t, encoding="utf-8")
print("neck_slide wired")
