from pathlib import Path
p = Path(__file__).with_name("r11l_l3_2wp_probe.py")
t = p.read_text(encoding="utf-8")
old = '''    d, ok = collapse_to_2(sess, d, freeze15)
    if d.get("state") == "GAME_OVER" or "frame" not in d:
        print("FAIL GO during collapse")
        return 1
    info = snap(d, freeze15, "collapsed")
    if not ok:
        print("FAIL collapse to 2wp")
        return 1
'''
new = '''    ok = False
    for ci in range(4):
        d, ok = collapse_to_2(sess, d, freeze15)
        if d.get("state") == "GAME_OVER" or "frame" not in d:
            print("FAIL GO during collapse")
            return 1
        freeze15 = lock_other_ship(d["frame"], 14)
        info = snap(d, freeze15, f"collapsed-{ci}")
        if ok:
            break
        print(f"  collapse round{ci} still n={info['n']}")
    if not ok:
        print("FAIL collapse to 2wp")
        return 1
'''
if old not in t:
    raise SystemExit('collapse call missing')
p.write_text(t.replace(old, new, 1), encoding='utf-8')
print('multi collapse ok')
