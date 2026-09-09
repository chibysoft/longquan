from pathlib import Path
p = Path(__file__).resolve().parent / "r11l_l3_2wp_probe.py"
t = p.read_text(encoding="utf-8")
old = '''        if len(cor) >= 2:
            xs = sorted(c[0] for c in cor)
            wrap_shallow = [c for c in cur if c[0] <= 14 and c[1] < 28]
            # Never stop while wrap-col straggler remains (v16 tugged it to (16,22)).
            if wrap_shallow:
                pass
            elif xs[-1] - xs[0] >= 5 and me["c"][1] >= 26:
                print(f"  plant enough corridor={cor} ship={me['c']} moves={moves}")
                break
        cands_wp = sorted(
            [w for w in cur if w[1] < 34 and w[0] > 14],
            key=lambda w: (-w[1], abs(w[0] - 22)),
        )
        # Prefer wrap-col tug only after two corridor plants exist.
        if len(cor) >= 2:
            wrap_wp = sorted(
                [w for w in cur if w[0] <= 14 and w[1] < 28],
                key=lambda w: (-w[1], w[0]),
            )
            if wrap_wp:
                cands_wp = wrap_wp + cands_wp
'''
new = '''        if len(cor) >= 2:
            xs = sorted(c[0] for c in cor if c[0] > 16) or sorted(c[0] for c in cor)
            if len(xs) >= 2 and xs[-1] - xs[0] >= 5:
                # STOP — wrap south-tugs create (9,34) / dead→GO (v49/v52).
                print(f"  plant enough corridor={cor} ship={me['c']} moves={moves}")
                break
        cands_wp = sorted(
            [w for w in cur if w[1] < 34 and w[0] > 14],
            key=lambda w: (-w[1], abs(w[0] - 22)),
        )
'''
if old not in t:
    raise SystemExit('block not found')
p.write_text(t.replace(old, new, 1), encoding='utf-8')
print('ok')
