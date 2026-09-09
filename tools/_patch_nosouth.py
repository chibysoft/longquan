from pathlib import Path
p = Path(__file__).resolve().parent / "r11l_l3_2wp_probe.py"
t = p.read_text(encoding="utf-8")
old = 'phases = [("south", south_pads), ("direct", direct_pads), ("walk", walk_pads)]'
new = 'phases = [("direct", direct_pads), ("walk", walk_pads)]  # no south 28-32 (dead)'
if old not in t:
    raise SystemExit(f"not found: {old!r}")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("ok")
