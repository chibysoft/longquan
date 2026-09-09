from pathlib import Path

p = Path(__file__).with_name("r11l_l3_2wp_probe.py")
t = p.read_text(encoding="utf-8")
start = t.find("def translate2(sess, data, freeze15, dx: int, dy: int = 0):")
end = t.find("\ndef west_to_neck(", start)
assert start > 0 and end > 0, (start, end)

new = r'''def translate2(sess, data, freeze15, dx: int, dy: int = 0):
    """v60: ONE lead +5 then lag. No second lead (drops flock)."""
    me = next(s for s in ships(data["frame"]) if s["chrome"] == 14)
    cur = count_free14(data["frame"], freeze15)
    if len(cur) != 2:
        print(f"  translate2 need exactly 2, got {cur}")
        return data, False
    if me["c"][1] < 34 or any(w[1] < 34 for w in cur):
        print(f"  translate2 refuse shallow ship={me['c']} cur={cur}")
        return data, False

    lead = max(cur, key=lambda w: (w[0], w[1]))
    lag = min(cur, key=lambda w: (w[0], w[1]))
    print(f"  translate2 v60 lead={lead} lag={lag} ship={me['c']}")

    ld = (lead[0] + 5, lead[1])
    gd = (lag[0] + 10, lag[1])
    data, newc, st = move_wp(sess, data, lead, ld, freeze15)
    print(
        f"  translate2-lead {lead}->{ld} {st}->{newc} "
        f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
        f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
    )
    if st != "moved" or data.get("state") == "GAME_OVER" or "frame" not in data:
        return data, False
    cur2 = count_free14(data["frame"], freeze15)
    if len(cur2) != 2:
        print(f"  translate2 post-lead flock broke {cur2}")
        return data, False
    lag_now = min(cur2, key=lambda w: (w[0], w[1]))
    data, newc, st = move_wp(sess, data, lag_now, gd, freeze15)
    print(
        f"  translate2-lag {lag_now}->{gd} {st}->{newc} "
        f"ship={next(s for s in ships(data['frame']) if s['chrome']==14)['c'] if 'frame' in data else '?'} "
        f"n={len(count_free14(data['frame'], freeze15)) if 'frame' in data else '?'} "
        f"bud={step_budget(data['frame']) if 'frame' in data else '?'}"
    )
    if st != "moved" or data.get("state") == "GAME_OVER" or "frame" not in data:
        return data, False
    if len(count_free14(data["frame"], freeze15)) != 2:
        print("  translate2 post-lag flock broke")
        return data, False
    return data, True


'''
p.write_text(t[:start] + new + t[end:], encoding="utf-8")
t2 = p.read_text(encoding="utf-8")
assert "translate2 v60" in t2
assert "lead2" not in t2
# Ensure run loop calls lag_haul
assert "lag_haul_east" in t2
print("ok v60")
