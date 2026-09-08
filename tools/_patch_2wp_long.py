from pathlib import Path

p = Path(__file__).with_name("r11l_l3_sync_probe.py")
t = p.read_text(encoding="utf-8")
old = """                    # Always short-stride on live until an explicit successful
                    # collapse14_to_2wp; dx>=8 drops remaining western wps.
                    dx_list = [4, 5, 6]
"""
new = """                    # Short by default; only 2-wp flocks get long strides.
                    nfree = len(count_free14(data["frame"], freeze15))
                    if nfree <= 2 and me["c"][1] >= 33:
                        dx_list = [8, 10, 6, 5, 4]
                    else:
                        dx_list = [4, 5, 6]
"""
if old not in t:
    raise SystemExit("dx default missing")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("2wp long ok")
