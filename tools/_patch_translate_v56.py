from pathlib import Path
p = Path(__file__).resolve().parent / "r11l_l3_2wp_probe.py"
t = p.read_text(encoding="utf-8")
# In translate2 iter_pairs / lead loop: gap<=14, skip repeat noop dests, prefer dx=5
old = """        lead_steps = [s for s in (dx, dx - 1, 4, 3, 2) if s >= 2 and gap + s <= 12]
        for adx in lead_steps:
            # Prefer same-row y=36; only then y+/-2.
            for ady in (0, 2, -2):
                ld = (lead[0] + adx, min(38, max(34, lead[1] + ady)))
                if not _translate_dest_ok(g, cur, lead, ld, [lag], freeze15, me_c):
                    continue
"""
new = """        # v40: lead (27,36)->(32,36) worked (gap 10->15). Cap 14 was too tight for +5.
        lead_steps = [s for s in (5, dx, 4, 3, 6, 2) if s >= 2 and gap + s <= 15]
        for adx in lead_steps:
            for ady in (0,):  # same-row only — (29,38)/(29,34) noop/dead
                ld = (lead[0] + adx, lead[1])
                if ld in getattr(iter_pairs, '_tried', set()):
                    continue
                if not _translate_dest_ok(g, cur, lead, ld, [lag], freeze15, me_c):
                    continue
"""
if old not in t:
    raise SystemExit('iter lead_steps not found')
t = t.replace(old, new, 1)

old2 = """    for ld, gd in iter_pairs():
        data, newc, st = move_wp(sess, data, lead, ld, freeze15)
        print(
            f"  translate2-lead {lead}->{ld} {st}->{newc} "
            f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if st != "moved":
            continue  # try next pair
"""
new2 = """    tried_lead = set()
    for ld, gd in iter_pairs():
        if ld in tried_lead:
            continue
        tried_lead.add(ld)
        data, newc, st = move_wp(sess, data, lead, ld, freeze15)
        print(
            f"  translate2-lead {lead}->{ld} {st}->{newc} "
            f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
            f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
        )
        if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
            return data, False
        if st != "moved":
            continue  # try next distinct lead dest
"""
if old2 not in t:
    raise SystemExit('lead loop not found')
t = t.replace(old2, new2, 1)
p.write_text(t, encoding="utf-8")
print("patched")
