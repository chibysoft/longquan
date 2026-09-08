from pathlib import Path

p = Path(__file__).with_name("r11l_l3_sync_probe.py")
t = p.read_text(encoding="utf-8")
old = """        flock = count_free14(data["frame"], freeze15)
        corridor_leads = [w for w in flock if w[1] >= 33]
        if len(corridor_leads) >= 2 and me["c"][1] >= 24:
            print(f\"  west_south handoff leads={corridor_leads} ship={me['c']}\")
            return leap14_east_once(sess, data, freeze15, lv0, stride=6)
"""
new = """        flock = count_free14(data["frame"], freeze15)
        corridor_leads = [w for w in flock if w[1] >= 33]
        # Need ship y>=28 — handing off at y=25 burns a dead east turn + nudge.
        if len(corridor_leads) >= 2 and me["c"][1] >= 28:
            print(f\"  west_south handoff leads={corridor_leads} ship={me['c']}\")
            return leap14_east_once(sess, data, freeze15, lv0, stride=6)
"""
if old not in t:
    raise SystemExit("handoff missing")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("handoff y>=28")
