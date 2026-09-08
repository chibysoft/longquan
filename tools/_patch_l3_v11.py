from pathlib import Path

p = Path(__file__).with_name("r11l_l3_sync_probe.py")
t = p.read_text(encoding="utf-8")

# Disable merge-lag block (noop burns ~3 every turn).
old = """            # Twin western lags at cheb<=6 block each other's east hops (noop).
            # Merge the west-most into its sibling to leave lead+1 lag (2wp mode).
            west_lags = [w for w in lag if w[0] < lead_x0 - 4]
            if len(west_lags) >= 2 and pulls < 1 and step_budget(data["frame"]) >= 10:
"""
# Replace the whole if body by forcing False
if old not in t:
    raise SystemExit("merge-lag header missing")
t = t.replace(
    old,
    """            # Twin-lag merge DISABLED — live noops burned budget with 0 progress.
            west_lags = [w for w in lag if w[0] < lead_x0 - 4]
            if False and len(west_lags) >= 2 and pulls < 1 and step_budget(data["frame"]) >= 10:
""",
    1,
)

# Skip north polish when corridor already has y>=33 leads (south-burst done).
old_n = """    north_strag = [w for w in cur0 if w[1] < 28]
    if step_budget(data["frame"]) < 12:
        north_strag = []
"""
new_n = """    north_strag = [w for w in cur0 if w[1] < 28]
    corridor_ready = any(w[1] >= 33 for w in cur0)
    if step_budget(data["frame"]) < 12 or (corridor_ready and me["c"][1] >= 32):
        north_strag = []
"""
if old_n not in t:
    raise SystemExit("north_strag missing")
t = t.replace(old_n, new_n, 1)

# Allow collapse again at bud>=18 when stragglers cheap (baseline used 18).
old_c = """        and step_budget(data["frame"]) >= 22
"""
# Only the collapse gate in leap14_east_once - be careful there may be multiple
count = t.count(old_c)
print("collapse bud>=22 count", count)
if "and step_budget(data[\"frame\"]) >= 22" in t:
    # replace only in collapse context - find unique block
    old_block = """    if (
        me["c"][1] >= 31
        and len(flock) >= 4
        and step_budget(data["frame"]) >= 22
    ):
"""
    new_block = """    if (
        me["c"][1] >= 31
        and len(flock) >= 4
        and step_budget(data["frame"]) >= 18
    ):
"""
    if old_block not in t:
        raise SystemExit("collapse gate missing")
    t = t.replace(old_block, new_block, 1)
    print("collapse bud -> 18")

p.write_text(t, encoding="utf-8")
print("ok")
