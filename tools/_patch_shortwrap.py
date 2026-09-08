from pathlib import Path
p = Path(__file__).with_name("r11l_l3_2wp_probe.py")
t = p.read_text(encoding="utf-8")
# Prefer short west wrap hops before long south.
old = '''        pads = [
            k,
            (14, 36),
            (20, 34),
            (28, 34),
            (24, 34),
            (k[0] - 3, 34),
            (k[0] + 3, 34),
        ]
'''
new = '''        pads = [
            (14, 28),
            (14, 30),
            (13, 28),
            (14, 32),
            (14, 36),
            (15, 34),
            (20, 34),
            k,
            (28, 34),
            (24, 34),
        ]
'''
old2 = '''            nxt = floor_bfs(g, wp, pad, max_step=14)
'''
new2 = '''            nxt = floor_bfs(g, wp, pad, max_step=6)
'''
# On noop, try next pad instead of aborting whole collapse.
old3 = '''        if st != "moved":
            print("  collapse abort", st)
            return data, False
'''
new3 = '''        if st != "moved":
            print(f"  collapse noop/skip {st} — try next")
            continue
'''
for a,b,n in [(old,new,'pads'),(old2,new2,'step'),(old3,new3,'noop')]:
    if a not in t:
        print('missing', n)
    else:
        t = t.replace(a,b,1)
        print('ok', n)
p.write_text(t, encoding='utf-8')
