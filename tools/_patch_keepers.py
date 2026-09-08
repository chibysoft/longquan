from pathlib import Path
p = Path(__file__).with_name("r11l_l3_2wp_probe.py")
t = p.read_text(encoding="utf-8")
old = '''    keepers = sorted(cur, key=lambda w: (-w[0], -w[1]))[:2]
    stragglers = [w for w in cur if w not in keepers]
'''
new = '''    # Keepers must already be on corridor y>=34 — never keep a shallow wp.
    corridor = [w for w in cur if w[1] >= 34]
    if len(corridor) < 2:
        print(f"  collapse need >=2 corridor, got {corridor}")
        return data, False
    keepers = sorted(corridor, key=lambda w: (-w[0], -w[1]))[:2]
    stragglers = [w for w in cur if w not in keepers]
'''
if old not in t:
    raise SystemExit('keepers missing')
p.write_text(t.replace(old, new, 1), encoding='utf-8')
print('keepers ok')
