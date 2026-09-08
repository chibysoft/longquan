from pathlib import Path

p = Path(__file__).with_name("r11l_l3_sync_probe.py")
t = p.read_text(encoding="utf-8")
t2 = t.replace("if travel < 4 or travel > 16:", "if travel < 4 or travel > 22:", 1)
if t2 == t:
    print("travel already patched or missing")
else:
    t = t2
    print("travel cap -> 22")

old2 = """        if me[\"c\"][1] >= 27:
            return leap14_east_once(sess, data, freeze15, lv0, stride=6)
        if ok:
            return data, True
"""
new2 = """        if me[\"c\"][1] >= 27:
            return leap14_east_once(sess, data, freeze15, lv0, stride=6)
        # Leads already in corridor: skip second diamond even if ship still y<27.
        flock = count_free14(data[\"frame\"], freeze15)
        corridor_leads = [w for w in flock if w[1] >= 33]
        if len(corridor_leads) >= 2 and me[\"c\"][1] >= 24:
            print(f\"  west_south handoff leads={corridor_leads} ship={me['c']}\")
            return leap14_east_once(sess, data, freeze15, lv0, stride=6)
        if ok:
            return data, True
"""
if old2 not in t:
    raise SystemExit("old2 missing")
t = t.replace(old2, new2, 1)
p.write_text(t, encoding="utf-8")
print("handoff patched")
