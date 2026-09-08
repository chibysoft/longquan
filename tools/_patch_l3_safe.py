from pathlib import Path

p = Path(__file__).with_name("r11l_l3_sync_probe.py")
t = p.read_text(encoding="utf-8")

# 1) Disable west_south — it caused accidental 2wp + GAME_OVER; baseline diamond is safer.
old_ws = """    # West wall after hop1: lean south instead of second diamond.
    if me["c"][0] <= 22 and 16 <= me["c"][1] < 28:
"""
new_ws = """    # West wall lean-south DISABLED (2026-09-09): accidental 2wp then
    # lead (34,34)->(38,34) GAME_OVER. Keep classic diamond hops.
    if False and me["c"][0] <= 22 and 16 <= me["c"][1] < 28:
"""
if old_ws not in t:
    raise SystemExit("west_south gate missing")
t = t.replace(old_ws, new_ws, 1)

# 2) Lead only when ship y>=34; 2wp never long-stride if lag gap large.
old_lead = """                if label == "-lead":
                    if me["c"][1] < 33:
                        continue
                    dx_list = [4, 5, 6]
                elif sealed:
                    dx_list = [4, 5, 6]
                else:
                    # 2wp can take longer strides; 3+ MUST stay short —
                    # live dx>=8 on a locomotive drops western wps (4→1).
                    # Short by default; only 2-wp flocks get long strides.
                    nfree = len(count_free14(data["frame"], freeze15))
                    if nfree <= 2 and me["c"][1] >= 33:
                        dx_list = [8, 10, 6, 5, 4]
                    else:
                        dx_list = [4, 5, 6]
"""
new_lead = """                if label == "-lead":
                    # y=33 still GAME_OVER'd on live 2wp lead hop — need y>=34.
                    if me["c"][1] < 34:
                        continue
                    nfree = len(count_free14(data["frame"], freeze15))
                    if nfree <= 2:
                        # Only short lead until lag catches (gap<=8).
                        lags = [c for c in others if c[0] < w[0]]
                        gap = (w[0] - max(c[0] for c in lags)) if lags else 0
                        if gap > 8:
                            continue
                        dx_list = [4, 5]
                    else:
                        dx_list = [4, 5, 6]
                elif sealed:
                    dx_list = [4, 5, 6]
                else:
                    # Never dx>=8 until seated collapse proves safe; short only.
                    dx_list = [4, 5, 6]
"""
if old_lead not in t:
    raise SystemExit("lead dx block missing")
t = t.replace(old_lead, new_lead, 1)

# 3) Always path_ok for lead / 2wp moves.
old_path = """                    # Long leaps need path_ok; short lead/lag corridor hops may skip.
                    need_path = dx >= 10 or t[0] >= 42
                    if need_path and not centroid_path_ok(cur_now, trial, g):
                        continue
"""
new_path = """                    # Lead and 2wp always need path_ok — short hops still GAME_OVER.
                    nfree = len(cur_now)
                    need_path = (
                        label == "-lead"
                        or nfree <= 2
                        or dx >= 8
                        or t[0] >= 42
                    )
                    if need_path and not centroid_path_ok(cur_now, trial, g):
                        continue
"""
if old_path not in t:
    raise SystemExit("path_ok block missing")
t = t.replace(old_path, new_path, 1)

# 4) Stacked 2wp with wide gap: haul lag only (skip lead).
old_else = """        else:
            # Twin western lags at cheb<=6 block each other's east hops (noop).
"""
# Find the stacked else that has Free same-x - actually the merge-lag was inserted
# before shallow. Add gap-guard before lead pull in the non-post_seal else.
old_pull_lead = """            if not _try_pull(lead[:1], "-lead"):
                return data, False
            # Always try one lag pull after lead (or instead) to unstick centroid.
"""
new_pull_lead = """            # 2wp with lead far ahead: haul lag first — lone lead hop GAME_OVER'd.
            nfree_s = len(count_free14(data["frame"], freeze15))
            lag_gap = 0
            if lead and lag:
                lag_gap = lead[0][0] - lag[0][0]
            if nfree_s <= 2 and lag_gap > 8:
                print(
                    f"  sync_east14 2wp-lag-first gap={lag_gap} "
                    f"ship={me['c']} bud={step_budget(data['frame'])}"
                )
                if not _try_pull(lag[:1], "-lag"):
                    return data, False
            elif not _try_pull(lead[:1], "-lead"):
                return data, False
            # Always try one lag pull after lead (or instead) to unstick centroid.
"""
if old_pull_lead not in t:
    raise SystemExit("lead pull missing")
t = t.replace(old_pull_lead, new_pull_lead, 1)

p.write_text(t, encoding="utf-8")
print("patched ok")
