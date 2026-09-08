from pathlib import Path

p = Path(__file__).with_name("r11l_l3_sync_probe.py")
t = p.read_text(encoding="utf-8")

# Cap east_block approach strides too.
old_eb = """            if east_block:
                lead_x = max(o[0] for o in east_block)
                gap = lead_x - w[0]
                dx_list = [
                    d
                    for d in (gap - 6, gap - 8, gap - 5, 8, 6, 5, 4)
                    if 4 <= d <= 12
                ]
                if not dx_list:
                    dx_list = [6, 5, 4]
"""
new_eb = """            if east_block:
                lead_x = max(o[0] for o in east_block)
                gap = lead_x - w[0]
                # Never close with dx>=8 — merges western flock on live.
                dx_list = [
                    d
                    for d in (gap - 6, gap - 5, 6, 5, 4)
                    if 4 <= d <= 6
                ]
                if not dx_list:
                    dx_list = [6, 5, 4]
"""
if old_eb not in t:
    raise SystemExit("east_block missing")
t = t.replace(old_eb, new_eb, 1)

old_nf = """                    nfree = len(count_free14(data["frame"], freeze15))
                    if nfree <= 2:
                        dx_list = [8, 10, 12, 6, 5, 4]
                    else:
                        dx_list = [4, 5, 6]
"""
new_nf = """                    # Always short-stride on live until an explicit successful
                    # collapse14_to_2wp; dx>=8 drops remaining western wps.
                    dx_list = [4, 5, 6]
"""
if old_nf not in t:
    raise SystemExit("nfree block missing")
t = t.replace(old_nf, new_nf, 1)

# Soften seed: prefer dx<=6 from current wp, avoid (28,33) if near siblings.
old_seed = """            for dest in (
                (30, 34),
                (28, 33),
                (32, 34),
                (28, 36),
                (30, 36),
                (wp[0] + 6, 34),
                (wp[0] + 8, 34),
            ):
"""
new_seed = """            for dest in (
                (wp[0] + 4, 34),
                (wp[0] + 5, 34),
                (wp[0] + 6, 34),
                (30, 34),
                (32, 34),
                (28, 36),
                (30, 36),
            ):
"""
if old_seed not in t:
    raise SystemExit("seed missing")
t = t.replace(old_seed, new_seed, 1)

p.write_text(t, encoding="utf-8")
print("east strides capped")
