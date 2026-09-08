from pathlib import Path

p = Path(__file__).with_name("r11l_l3_sync_probe.py")
t = p.read_text(encoding="utf-8")

old = """    north_strag = [w for w in cur0 if w[1] < 28]
    corridor_ready = any(w[1] >= 33 for w in cur0)
    if step_budget(data["frame"]) < 12 or (corridor_ready and me["c"][1] >= 32):
        north_strag = []
"""
new = """    # Always lift deep-north (y<28) — skipping left (14,25) and stuck ship at y=32.
    north_strag = [w for w in cur0 if w[1] < 28]
    if step_budget(data["frame"]) < 10:
        north_strag = []
"""
if old not in t:
    raise SystemExit("north block missing")
t = t.replace(old, new, 1)

# When defer-east (ship y<33), still allow shallow compact / don't force_east spam.
# In leap14_east_once: if sync deferred and ship y<33, nudge south instead of force_east.
old_f = """    # Fallback: force_east — skip reshape thrash.
    if me["c"][1] >= 28:
        data, forced = force_east_step(sess, data, freeze15)
        if forced:
            me2 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            print(
                f"  east14 force-first ship={me2['c']} "
                f"bud={step_budget(data['frame'])}"
            )
            return data, True
"""
new_f = """    # Fallback: if still shallow (y<33), nudge south — do NOT force_east (poisons).
    if me["c"][1] >= 28:
        me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
        if me["c"][1] < 33:
            data, nudged = emergency_nudge14(sess, data, freeze15, lv0)
            if nudged:
                me2 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
                print(
                    f"  east14 shallow-nudge ship={me2['c']} "
                    f"bud={step_budget(data['frame'])}"
                )
                return data, True
            return data, False
        data, forced = force_east_step(sess, data, freeze15)
        if forced:
            me2 = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
            print(
                f"  east14 force-first ship={me2['c']} "
                f"bud={step_budget(data['frame'])}"
            )
            return data, True
"""
if old_f not in t:
    raise SystemExit("force_east fallback missing")
t = t.replace(old_f, new_f, 1)

p.write_text(t, encoding="utf-8")
print("ok")
