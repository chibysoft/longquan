from pathlib import Path

p = Path(__file__).resolve().parent / "r11l_l3_2wp_probe.py"
t = p.read_text(encoding="utf-8")

# 1) Fix collapse Phase A: prefer direct corridor merge over west-wrap when keeper is close.
old_phase = '''        # Shallow @y~24 is north of hazard band; go west/east then south.
        # Phase A: north of hazard and still east of wrap column → slide west.
        # Phase B: already at wrap column (x<=14) or past hazard → go south/SE.
        if wp[1] <= 26 and wp[0] > 14:
            pads = [(14, 24), (13, 24), (12, 24), (14, 25), (13, 25)]
        elif wp[1] <= 26 and wp[0] <= 14:'''

new_phase = '''        # Shallow north of hazard: if a corridor keeper is nearby, jump to
        # cheb 2–3 merge on y>=34. Only west-wrap when keepers are far east.
        near_k = (
            k[1] >= 34
            and abs(k[0] - wp[0]) <= 12
            and abs(k[1] - wp[1]) <= 24
        )
        if wp[1] <= 28 and near_k:
            pads = [
                (k[0], 34),
                (k[0] - 3, 34),
                (k[0] + 3, 34),
                (k[0] - 2, 34),
                (k[0] + 2, 34),
                (k[0] - 3, k[1]),
                (k[0] + 3, k[1]),
                (20, 34),
                (22, 34),
                (24, 34),
                (18, 34),
                k,
            ]
        elif wp[1] <= 26 and wp[0] > 14:
            pads = [(14, 24), (13, 24), (12, 24), (14, 25), (13, 25)]
        elif wp[1] <= 26 and wp[0] <= 14:'''

if old_phase not in t:
    raise SystemExit("phase block not found")
t = t.replace(old_phase, new_phase, 1)

# Fix wrapping detection — near_k path is NOT wrapping.
old_wrap = '''        dest = None
        wrapping = wp[1] <= 26 and wp[0] > 14
        on_wrap_col = wp[0] <= 14
        for pad in pads:
            if not (0 <= pad[0] < 64 and 0 <= pad[1] < 64):
                continue
            if wrapping:
                pass  # y=24 west-slide pads ok
            elif pad[1] < 34:'''

new_wrap = '''        dest = None
        wrapping = (not near_k) and wp[1] <= 26 and wp[0] > 14
        on_wrap_col = (not near_k) and wp[0] <= 14
        for pad in pads:
            if not (0 <= pad[0] < 64 and 0 <= pad[1] < 64):
                continue
            if wrapping:
                pass  # y=24 west-slide pads ok
            elif pad[1] < 34:'''

if old_wrap not in t:
    raise SystemExit("wrap block not found")
t = t.replace(old_wrap, new_wrap, 1)

# 2) Skip lift whenever >=2 corridor exist (even if ship y<32).
old_skip = '''    corridor = [w for w in info["free14"] if w[1] >= 34]
    # If >=2 corridor wps already, do NOT burn lift noops (costs ~6 bud).
    if len(corridor) >= 2 and info["ship"][1] >= 32:
        print(f"  skip-lift corridor={corridor} ship={info['ship']} bud={info['bud']}")
        ok = True
    else:'''

new_skip = '''    corridor = [w for w in info["free14"] if w[1] >= 34]
    # If >=2 corridor wps already, do NOT burn lift noops — collapse stragglers.
    if len(corridor) >= 2:
        print(f"  skip-lift corridor={corridor} ship={info['ship']} bud={info['bud']}")
        ok = True
    else:'''

if old_skip not in t:
    raise SystemExit("skip-lift block not found")
t = t.replace(old_skip, new_skip, 1)

# 3) Plant early-stop: require ship y>=27 AND at most 1 shallow, or y>=28.
old_enough = '''        if len(cor) >= 2:
            xs = sorted(c[0] for c in cor)
            if xs[-1] - xs[0] >= 5 and me["c"][1] >= 26:
                print(f"  plant enough corridor={cor} ship={me['c']} moves={moves}")
                break'''

new_enough = '''        shallow_n = len([c for c in cur if c[1] < 34])
        if len(cor) >= 2:
            xs = sorted(c[0] for c in cor)
            if xs[-1] - xs[0] >= 5 and (
                me["c"][1] >= 28 or (me["c"][1] >= 27 and shallow_n <= 1)
            ):
                print(
                    f"  plant enough corridor={cor} shallow={shallow_n} "
                    f"ship={me['c']} moves={moves}"
                )
                break'''

if old_enough not in t:
    raise SystemExit("plant enough block not found")
t = t.replace(old_enough, new_enough, 1)

p.write_text(t, encoding="utf-8")
print("patched collapse+skip+plant")
