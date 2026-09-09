from pathlib import Path
p = Path(__file__).resolve().parent / "r11l_l3_2wp_probe.py"
t = p.read_text(encoding="utf-8")
repls = [
(
"""        if wp[1] < 34 and wp[0] > 14:
            phases = [("direct", direct_pads)]  # never walk mid-band (dead/GO)
""",
"""        if wp[1] < 34 and wp[0] > 14:
            # Proven live pads only (k+/-3 from east keeper often dead/noop).
            phases = [("direct", [(21, 36), (27, 36), (24, 36), (18, 36), (30, 36)])]
""",
),
(
"""        base_dests = [
            (24, 36),
            (30, 36),
            (32, 36),
            (18, 36),
            (20, 36),
            (26, 36),
        ]
""",
"""        base_dests = [
            (24, 36),
            (18, 36),
            (20, 36),
            (26, 36),
            (30, 36),
        ]
""",
),
(
"""                if st == "dead":
                    # Dead through hazard often cascades to GO — abort collapse.
                    print(f"    collapse dead pad — abort")
                    return data, False
""",
"""                if st == "dead":
                    print(f"    collapse dead pad — stop this wp")
                    break
""",
),
]
for a, b in repls:
    if a not in t:
        print("MISSING", repr(a[:60]))
    else:
        t = t.replace(a, b, 1)
        print("ok", repr(a[:40]))
p.write_text(t, encoding="utf-8")
