from pathlib import Path
p = Path(__file__).with_name("r11l_l3_2wp_probe.py")
t = p.read_text(encoding="utf-8")
old = '''        pads = [
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
new = '''        # Phase A: if still north of hazard, first slide west on y=24.
        if wp[1] <= 26:
            pads = [(14, 24), (13, 24), (12, 24), (14, 25), (13, 25)]
        else:
            pads = [
                (14, 28),
                (14, 32),
                (14, 36),
                (15, 34),
                (20, 34),
                k,
                (28, 34),
            ]
'''
old2 = '''            if nxt[1] < 32:
                print(f"    collapse skip pad{pad} nxt{nxt} too north")
                continue
'''
new2 = '''            # West-wrap phase may stay at y=24; south phase needs y>=32.
            if wp[1] <= 26:
                if nxt[1] > 26 or nxt[0] >= wp[0]:
                    # must move west (or stay west) along wrap
                    if nxt[0] >= wp[0] and nxt != (14, 24):
                        print(f"    collapse skip pad{pad} nxt{nxt} not west wrap")
                        continue
            elif nxt[1] < 32:
                print(f"    collapse skip pad{pad} nxt{nxt} too north")
                continue
'''
# Allow up to 3 collapse moves for wrap+south+merge
old3 = '''    for wp in stragglers:
'''
# Better: loop collapse until 2wp or 3 moves
old4 = '''    print(f"  collapse keepers={keepers} stragglers={stragglers}")
    for wp in stragglers:
'''
new4 = '''    print(f"  collapse keepers={keepers} stragglers={stragglers}")
    for _round in range(4):
      cur = count_free14(data["frame"], freeze15)
      if len(cur) <= 2:
        break
      corridor = [w for w in cur if w[1] >= 34]
      keepers = sorted(corridor, key=lambda w: (-w[0], -w[1]))[:2] if len(corridor) >= 2 else keepers
      stragglers = [w for w in cur if w not in keepers]
      if not stragglers:
        break
      wp = stragglers[0]
'''
# This gets messy with indentation. Simpler approach: call collapse twice from run_probe.

if old not in t:
    raise SystemExit('pads missing')
t = t.replace(old, new, 1)
if old2 not in t:
    raise SystemExit('north check missing')
t = t.replace(old2, new2, 1)
p.write_text(t, encoding='utf-8')
print('wrap phase ok')
