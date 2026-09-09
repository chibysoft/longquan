"""v49: eastern plant pair + looser translate gap + dx_list for gate."""
from pathlib import Path

p = Path(__file__).with_name("r11l_l3_2wp_probe.py")
t = p.read_text(encoding="utf-8")

t = t.replace(
    """        # Proven pair (v16): (24,36)+(18,36). Do NOT plant wrap-col once corridor exists.
        base_dests = [
            (24, 36),
            (18, 36),
            (30, 36),
            (20, 36),
            (26, 36),
            (32, 36),
        ]""",
    """        # Prefer eastern pair so ship forms nearer x>=28 (save translate bud).
        # Fallback to v16 (24,36)+(18,36) if east blocked.
        base_dests = [
            (24, 36),
            (30, 36),
            (32, 36),
            (18, 36),
            (20, 36),
            (26, 36),
        ]""",
    1,
)

t = t.replace(
    "lead_steps = [s for s in (dx, dx - 1, 4, 3, 6, 2) if s >= 2 and gap + s <= 12]",
    "lead_steps = [s for s in (dx, dx - 1, 5, 6, 4, 3, 7, 2) if s >= 2 and gap + s <= 18]",
    1,
)

# lag must clear ship; also allow cheb 5-10
t = t.replace(
    """            lag_cands = []
            for lax in range(6, 14):
                for lay in (0, 2, -2, 1, -1):
                    gd = (lag[0] + lax, min(38, max(34, lag[1] + lay)))
                    cheb_l = max(abs(gd[0] - ld[0]), abs(gd[1] - ld[1]))
                    if 5 <= cheb_l <= 8:
                        lag_cands.append(gd)""",
    """            lag_cands = []
            for lax in range(5, 16):
                for lay in (0, 2, -2, 1, -1):
                    gd = (lag[0] + lax, min(38, max(34, lag[1] + lay)))
                    cheb_l = max(abs(gd[0] - ld[0]), abs(gd[1] - ld[1]))
                    if 5 <= cheb_l <= 10:
                        lag_cands.append(gd)""",
    1,
)

t = t.replace(
    "def run_probe(dx_list=(3, 3, 4, 4, 5)):",
    "def run_probe(dx_list=(5, 5, 6, 6)):",
    1,
)

# Soften east-of-ship lag clear to me+1 (was +2) when bud tight
t = t.replace(
    "if wp[0] < me[0] < max(others, key=lambda p: p[0])[0] and dest[0] <= me[0] + 2:",
    "if wp[0] < me[0] < max(others, key=lambda p: p[0])[0] and dest[0] <= me[0] + 1:",
    1,
)

p.write_text(t, encoding="utf-8")
print("v49 patch ok")
