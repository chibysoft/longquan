from pathlib import Path

p = Path(__file__).with_name("r11l_l3_sync_probe.py")
t = p.read_text(encoding="utf-8")
old = """                elif sealed:
                    dx_list = [4, 5, 6, 8]
                else:
                    # 2wp can take longer strides; 3+ stay short.
                    nfree = len(count_free14(data["frame"], freeze15))
                    if nfree <= 2:
                        dx_list = [8, 10, 12, 6, 5, 4]
                    else:
                        dx_list = [6, 8, 4, 5, 10]
"""
new = """                elif sealed:
                    dx_list = [4, 5, 6]
                else:
                    # 2wp can take longer strides; 3+ MUST stay short —
                    # live dx>=8 on a locomotive drops western wps (4→1).
                    nfree = len(count_free14(data["frame"], freeze15))
                    if nfree <= 2:
                        dx_list = [8, 10, 12, 6, 5, 4]
                    else:
                        dx_list = [4, 5, 6]
"""
if old not in t:
    raise SystemExit("dx block missing")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("dx capped")
