from pathlib import Path
p = Path(__file__).with_name("r11l_l3_2wp_probe.py")
t = p.read_text(encoding="utf-8")

# Skip expensive lift when corridor already seeded.
old = '''    d, ok = ensure_y34(sess, d, freeze15)
    if d.get("state") == "GAME_OVER" or "frame" not in d:
        print("FAIL GO during lift")
        return 1
    info = snap(d, freeze15, "lifted")
    if not ok:
        # Soft continue: collapse may eat the last shallow.
        print("WARN lift incomplete — try collapse anyway")
'''
new = '''    info = snap(d, freeze15, "pre-lift")
    corridor = [w for w in info["free14"] if w[1] >= 34]
    # If >=2 corridor wps already, do NOT burn lift noops (costs ~6 bud).
    if len(corridor) >= 2 and info["ship"][1] >= 32:
        print(f"  skip-lift corridor={corridor} ship={info['ship']} bud={info['bud']}")
        ok = True
    else:
        d, ok = ensure_y34(sess, d, freeze15)
        if d.get("state") == "GAME_OVER" or "frame" not in d:
            print("FAIL GO during lift")
            return 1
        info = snap(d, freeze15, "lifted")
        if not ok:
            print("WARN lift incomplete — try collapse anyway")
'''
if old not in t:
    raise SystemExit('lift block missing')
t = t.replace(old, new, 1)

# When gap<=8 same-delta fails near sibling, try lag-only +4/+6 again.
old2 = '''        if not ok:
            print(f"translate dx={dx} stopped")
            break
'''
new2 = '''        if not ok:
            print(f"translate dx={dx} soft-fail — continue next round")
            continue
'''
if old2 not in t:
    print('soft-fail block missing')
else:
    t = t.replace(old2, new2, 1)

p.write_text(t, encoding='utf-8')
print('skip-lift ok')
