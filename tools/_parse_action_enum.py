"""Parse tee log from vc33_l4_action_enum into partial JSON."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "tools/_l4_action_enum_run.txt"
OUT = ROOT / "tests/fixtures/vc33_l4_action_enum.partial.json"

PAT = re.compile(
    r"\| ([\w/]+)\s+\| (KEEP|CLEAR)\s+\| d=\(([+-]?\d+),([+-]?\d+)\) "
    r"cy ([\d.]+)->([\d.]+) \| mid=(\w+) \| h12 (\d+)->(\d+) \| lv=(\d+) \| ch=\{([^}]*)\}"
)


def main():
    # Tee-Object on Windows writes UTF-16 LE
    raw = LOG.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        text = raw.decode("utf-16")
    else:
        text = raw.decode("utf-8", errors="replace")
    rows = []
    for m in PAT.finditer(text):
        label, keep, dx, dy, cy0, cy1, mid, h0, h1, lv, ch = m.groups()
        chd = {}
        if ch.strip():
            for part in ch.split(","):
                part = part.strip()
                if not part:
                    continue
                k, v = part.split(":")
                chd[k.strip().strip("'")] = int(v.strip())
        rows.append(
            {
                "label": label,
                "ok": True,
                "h12_keep": keep == "KEEP",
                "dx": float(dx),
                "dy": float(dy),
                "cy0": float(cy0),
                "cy1": float(cy1),
                "h12_before": int(h0),
                "h12_after": int(h1),
                "mid_ch": mid == "CHG",
                "lv1": int(lv),
                "ch": chd,
            }
        )
    print("parsed", len(rows))
    for r in rows:
        print(r["label"], "KEEP" if r["h12_keep"] else "CLEAR", f"d=({r['dx']:+.0f},{r['dy']:+.0f})")
    OUT.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
