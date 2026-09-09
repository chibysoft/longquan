from pathlib import Path

p = Path("tools/r11l_l3_2wp_probe.py")
text = p.read_text(encoding="utf-8")
t0 = text.find("def translate2(")
t1 = text.find("def west_to_neck(")
assert t0 > 0 and t1 > 0

new = '''def translate2(sess, data, freeze15, dx: int = 5, dy: int = 0):
    """v67: lead+5, same-row lag (lands ~21, ship~26). No ylift (always noop)."""
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
    print(f"  translate2 v67 lead={lead} lag={lag} ship={me['c']}")

    ld = (lead[0] + 5, lead[1])
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
    gd = (lag_now[0] + 10, lag_now[1])
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

# Replace near-gate block in run_probe
a = text.find("    for round_i, dx in enumerate(dx_list):")
b = text.find('    print("=== RESULT ===")')
assert a > 0 and b > 0

loop = '''    for round_i, dx in enumerate(dx_list):
        if step_budget(d["frame"]) < 8:
            break
        if success_gate(info):
            break
        if info["ship"][1] < 34 or any(w[1] < 34 for w in info["free14"]):
            print(f"  translate refuse shallow ship={info['ship']} free={info['free14']}")
            break
        # Near gate: crawl lag +1/+2 toward ship, then micro-lead +3/+4.
        if info["ship"][0] >= 25 and info["ship"][0] < 28 and info["n"] == 2 and info["bud"] >= 30:
            print(f"--- finish round{round_i} ship={info['ship']} bud={info['bud']} ---")
            # 1) crawl lag toward ship (never past, never noop-chain)
            for step in (2, 1):
                if info["ship"][0] >= 28 or info["bud"] < 30:
                    break
                lead = max(info["free14"], key=lambda w: (w[0], w[1]))
                lag = min(info["free14"], key=lambda w: (w[0], w[1]))
                sx = info["ship"][0]
                dest = (min(lag[0] + step, sx - 1), lag[1])
                if dest[0] <= lag[0]:
                    continue
                cheb = abs(dest[0] - lead[0])
                if cheb < 5:
                    continue
                d, newc, st = move_wp(sess, d, lag, dest, freeze15)
                print(
                    f"  crawl-lag {lag}->{dest} {st}->{newc} "
                    f"ship={next(s for s in ships(d['frame']) if s['chrome']==14)['c'] if 'frame' in d else '?'} "
                    f"n={len(count_free14(d['frame'], freeze15)) if 'frame' in d else '?'} "
                    f"bud={step_budget(d['frame']) if 'frame' in d else '?'}"
                )
                if st == "dead" or d.get("state") == "GAME_OVER" or "frame" not in d:
                    return 1
                freeze15 = lock_other_ship(d["frame"], 14)
                info = snap(d, freeze15, f"after-crawl{round_i}")
                if st != "moved":
                    print("  crawl-lag noop — skip to micro")
                    break
                if info["n"] != 2:
                    print("  crawl-lag flock broke")
                    break
            if success_gate(info):
                break
            if info["n"] != 2:
                break
            # 2) micro-lead to pull ship ( +3 keeps n=2; try +4 for more pull )
            if info["ship"][0] < 28 and info["bud"] >= 30:
                lead = max(info["free14"], key=lambda w: (w[0], w[1]))
                lag = min(info["free14"], key=lambda w: (w[0], w[1]))
                for adx in (4, 3, 2):
                    ld = (lead[0] + adx, lead[1])
                    if ld[0] - lag[0] > 15:
                        continue
                    d, newc, st = move_wp(sess, d, lead, ld, freeze15)
                    print(
                        f"  micro-lead {lead}->{ld} {st}->{newc} "
                        f"ship={next(s for s in ships(d['frame']) if s['chrome']==14)['c'] if 'frame' in d else '?'} "
                        f"n={len(count_free14(d['frame'], freeze15)) if 'frame' in d else '?'} "
                        f"bud={step_budget(d['frame']) if 'frame' in d else '?'}"
                    )
                    if st == "dead" or d.get("state") == "GAME_OVER" or "frame" not in d:
                        return 1
                    if st != "moved":
                        continue
                    freeze15 = lock_other_ship(d["frame"], 14)
                    info = snap(d, freeze15, f"after-micro{round_i}")
                    if info["n"] != 2:
                        print("  micro-lead flock broke")
                        break
                    break
            if success_gate(info):
                break
            print("  finish stop (no +5 translate)")
            break
        if info["ship"][0] >= 25:
            print(f"  skip translate at ship={info['ship']} (seal risk)")
            break
        if info["bud"] < 34 and dx > 5:
            dx = 5
        print(f"--- translate round{round_i} dx={dx} ---")
        d, ok = translate2(sess, d, freeze15, dx=dx, dy=0)
        if d.get("state") == "GAME_OVER" or "frame" not in d:
            print(f"FAIL GO on translate dx={dx}")
            return 1
        freeze15 = lock_other_ship(d["frame"], 14)
        info = snap(d, freeze15, f"after-dx{dx}")
        if success_gate(info):
            break
        if info["n"] != 2:
            print(f"translate flock lost n={info['n']} — stop")
            break
        if not ok and info["ship"][0] < 24:
            print(f"translate dx={dx} soft-fail — stop translate (save bud)")
            break
        if not ok:
            print(f"translate dx={dx} soft-fail mid-east — try next")
            continue

'''

# Use text BEFORE translate2 replace for the loop markers - need current file
text = text[:t0] + new + text[t1:]
a = text.find("    for round_i, dx in enumerate(dx_list):")
b = text.find('    print("=== RESULT ===")')
assert a > 0 and b > 0, (a, b)
text = text[:a] + loop + text[b:]
p.write_text(text, encoding="utf-8")
print("patched v67")
