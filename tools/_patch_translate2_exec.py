"""One-shot patch: replace translate2 execute loop with lead-then-lag refresh."""
from pathlib import Path

p = Path(__file__).with_name("r11l_l3_2wp_probe.py")
t = p.read_text(encoding="utf-8")
start = t.find("    lead_dest, lag_dest = pair\n")
end = t.find("\n\ndef west_to_neck(", start)
if start < 0 or end < 0:
    raise SystemExit(f"markers not found start={start} end={end}")
new = '''    lead_dest, lag_dest = pair
    data, newc, st = move_wp(sess, data, lead, lead_dest, freeze15)
    print(
        f"  translate2-lead {lead}->{lead_dest} {st}->{newc} "
        f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
        f"n={len(count_free14(data['frame'], freeze15)) if 'frame' in data else '?'} "
        f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
    )
    if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
        return data, False
    if st != "moved":
        print("  translate2 lead noop — abort")
        return data, False
    cur2 = count_free14(data["frame"], freeze15)
    if len(cur2) != 2:
        print("  translate2 post-lead flock broke")
        return data, False
    lag_now = min(cur2, key=lambda w: (w[0], w[1]))
    data, newc, st = move_wp(sess, data, lag_now, lag_dest, freeze15)
    print(
        f"  translate2-lag {lag_now}->{lag_dest} {st}->{newc} "
        f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
        f"n={len(count_free14(data['frame'], freeze15)) if 'frame' in data else '?'} "
        f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
    )
    if st == "dead" or data.get("state") == "GAME_OVER" or "frame" not in data:
        return data, False
    if st != "moved":
        print("  translate2 lag noop — abort (lead already moved)")
        return data, False
    if len(count_free14(data["frame"], freeze15)) != 2:
        print("  translate2 post-lag flock broke")
        return data, False
    return data, True

'''
p.write_text(t[:start] + new + t[end:], encoding="utf-8")
print("patched", p)
