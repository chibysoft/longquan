from pathlib import Path

p = Path(__file__).with_name("r11l_l3_sync_probe.py")
t = p.read_text(encoding="utf-8")
old = """    # Near choke: up to 3 south nudges. Order matters:
    # 1) clear shallow (14,32)→(14,36)  2) seed lead (24,25)→(28,33)
    # Stop only when lead exists AND no y∈[28,32] shallow remains.
    if me["c"][1] < 32:
"""
new = """    # Near choke: up to 3 south nudges. Order matters:
    # 1) clear shallow (14,32)→(14,36)  2) seed lead (24,25)→(28,33)
    # Stop only when lead exists AND no y∈[28,32] shallow remains.
    # Skip when west_south already planted ≥2 corridor leads — nudge merges them.
    flock0 = count_free14(data["frame"], freeze15)
    corridor0 = [w for w in flock0 if w[1] >= 33]
    shallow0 = [w for w in flock0 if 28 <= w[1] <= 32]
    if me["c"][1] < 32 and not (len(corridor0) >= 2 and not shallow0):
"""
if old not in t:
    raise SystemExit("south-burst header missing")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("skip south-burst ok")
