from pathlib import Path
p = Path(__file__).resolve().parent / "r11l_l3_2wp_probe.py"
t = p.read_text(encoding="utf-8")
old = '''    # Prefer easternmost + a second with cheb>=5 and x>=20 (avoid wrap lag).
    east = max(corridor, key=lambda w: (w[0], w[1]))
    rest = sorted(
        [w for w in corridor if w != east],
        key=lambda w: (
            0 if w[0] >= 20 else 1,
            0 if max(abs(w[0] - east[0]), abs(w[1] - east[1])) >= 5 else 1,
            -w[0],
            -w[1],
        ),
    )
    keepers = [east] + rest[:1]
    stragglers = sorted(
        [w for w in cur if w not in keepers],
        key=lambda w: (0 if w[0] > 16 else 1, -w[1], w[0]),
    )
    print(f"  collapse keepers={keepers} stragglers={stragglers}")
'''
new = '''    # Two eastern corridor keepers with cheb>=5; never keep wrap-column (x<=16).
    corridor_e = [w for w in corridor if w[0] > 16] or list(corridor)
    corridor_sorted = sorted(corridor_e, key=lambda w: (-w[0], -w[1]))
    keepers = []
    for w in corridor_sorted:
        if not keepers:
            keepers.append(w)
            continue
        if max(abs(w[0] - keepers[0][0]), abs(w[1] - keepers[0][1])) >= 5:
            keepers.append(w)
            break
    if len(keepers) < 2 and len(corridor_sorted) >= 2:
        keepers = corridor_sorted[:2]
    # Shallow / wrap first — do not thrash corridor extras before them.
    stragglers = sorted(
        [w for w in cur if w not in keepers],
        key=lambda w: (0 if w[1] < 34 else 1, 0 if w[0] <= 16 else 1, -w[1], w[0]),
    )
    print(f"  collapse keepers={keepers} stragglers={stragglers}")
'''
if old not in t:
    raise SystemExit("keepers block not found")
t = t.replace(old, new, 1)
# Cap collapse rounds in run_probe when burning
old2 = "    for ci in range(8):\n        d, ok = collapse_to_2(sess, d, freeze15)"
new2 = "    for ci in range(4):\n        d, ok = collapse_to_2(sess, d, freeze15)"
if old2 in t:
    t = t.replace(old2, new2, 1)
    print("capped collapse rounds to 4")
p.write_text(t, encoding="utf-8")
print("keepers patched")
