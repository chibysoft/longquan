from pathlib import Path

p = Path(__file__).with_name("r11l_l3_sync_probe.py")
t = p.read_text(encoding="utf-8")
old = """        cheap = all(
            min(max(abs(s[0] - k[0]), abs(s[1] - k[1])) for k in keepers) <= 8
            for s in stragglers
        )
        if cheap:
"""
new = """        cheap = all(
            min(max(abs(s[0] - k[0]), abs(s[1] - k[1])) for k in keepers) <= 8
            for s in stragglers
        )
        # Baseline needed collapse of deep-north (14,25) even when "far".
        must = any(s[1] <= 32 for s in stragglers)
        if cheap or must:
"""
if old not in t:
    raise SystemExit("cheap check missing")
t = t.replace(old, new, 1)

# On merge-shallow noop: stop retrying (don't burn). Mark pulls so we don't loop.
old2 = """                                if st == "moved":
                                    pulls += 1
                                    moved_any = True
                                    g = _plane(data["frame"])
                                    me = next(
                                        s
                                        for s in ships(data["frame"])
                                        if s["chrome"] == 14
                                    )
                                    cur_now = count_free14(data["frame"], freeze15)
                                    band = [
                                        w
                                        for w in cur_now
                                        if 28 <= w[1] <= 38
                                    ] or cur_now
                                    lead = sorted(
                                        band,
                                        key=lambda w: (-w[0], abs(w[1] - 34)),
                                    )
                                    lag = sorted(
                                        band,
                                        key=lambda w: (w[0], abs(w[1] - 34)),
                                    )
                                    lead_x0 = lead[0][0] if lead else 0
                                    # Merged: continue to lead/lag this turn.
                                    shallow_band = [
                                        w for w in band if 28 <= w[1] <= 32
                                    ]
"""
new2 = """                                if st == "moved":
                                    pulls += 1
                                    moved_any = True
                                    g = _plane(data["frame"])
                                    me = next(
                                        s
                                        for s in ships(data["frame"])
                                        if s["chrome"] == 14
                                    )
                                    cur_now = count_free14(data["frame"], freeze15)
                                    band = [
                                        w
                                        for w in cur_now
                                        if 28 <= w[1] <= 38
                                    ] or cur_now
                                    lead = sorted(
                                        band,
                                        key=lambda w: (-w[0], abs(w[1] - 34)),
                                    )
                                    lag = sorted(
                                        band,
                                        key=lambda w: (w[0], abs(w[1] - 34)),
                                    )
                                    lead_x0 = lead[0][0] if lead else 0
                                    shallow_band = [
                                        w for w in band if 28 <= w[1] <= 32
                                    ]
                                else:
                                    # noop: do not retry merge-shallow this turn.
                                    pulls = max(pulls, 1)
"""
if old2 not in t:
    raise SystemExit("merge-shallow moved block missing")
t = t.replace(old2, new2, 1)

p.write_text(t, encoding="utf-8")
print("ok")
