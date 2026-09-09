"""Merge partial enum rows + OUT (e.g. click_gap) into final fixture."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTIAL = ROOT / "tests/fixtures/vc33_l4_action_enum.partial.json"
OUT = ROOT / "tests/fixtures/vc33_l4_action_enum.json"


def summarize(rows):
    keep_up = [r for r in rows if r.get("h12_keep") and (r.get("dy") or 0) < -0.1]
    keep_any = [r for r in rows if r.get("h12_keep") and abs(r.get("dy") or 0) > 0.1]
    keep_hop = [
        r
        for r in rows
        if r.get("h12_keep") and abs(r.get("dx") or 0) > 0.1 and abs(r.get("dy") or 0) < 0.1
    ]
    clear_up = [
        r for r in rows if r.get("ok") and not r.get("h12_keep") and (r.get("dy") or 0) < -0.1
    ]
    mid = [r for r in rows if r.get("mid_ch")]
    summary = {
        "keep_and_up": [r["label"] for r in keep_up],
        "keep_and_any_dy": [r["label"] for r in keep_any],
        "keep_and_hop_flat": [r["label"] for r in keep_hop],
        "clear_and_up": [r["label"] for r in clear_up],
        "mid_response": [r["label"] for r in mid],
        "n_rows": len(rows),
    }
    if summary["keep_and_up"]:
        reading = "FOUND_LOCK — exists action that keeps c12 AND raises cy"
    elif summary["clear_and_up"] and not summary["keep_and_up"]:
        reading = (
            "DUAL12_NOT_PRECONDITION_VIA_CLIMB — all upward moves clear c12; "
            "dual-12 climb path blocked"
        )
    else:
        reading = "NO_UP_WHILE_C12 — no upward move observed while c12 lit in tested states"
    return summary, reading


def main():
    subprocess.check_call([sys.executable, str(ROOT / "tools/_parse_action_enum.py")])
    partial = json.loads(PARTIAL.read_text(encoding="utf-8"))
    cur = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"rows": []}
    by = {r["label"]: r for r in partial}
    for r in cur.get("rows", []):
        by[r["label"]] = r
    labels = [r["label"] for r in partial]
    for r in cur.get("rows", []):
        if r["label"] not in labels:
            labels.append(r["label"])
    rows = [by[l] for l in labels if l in by]
    summary, reading = summarize(rows)
    OUT.write_text(
        json.dumps({"rows": rows, "summary": summary, "reading": reading}, indent=2, default=str),
        encoding="utf-8",
    )
    print("n", len(rows))
    print("summary", json.dumps(summary, indent=2))
    print("READING", reading)
    for r in rows:
        k = "KEEP" if r["h12_keep"] else "CLEAR"
        mid = "Y" if r.get("mid_ch") else "N"
        print(
            f"| {r['label']:24s} | {k:5s} | d=({r['dx']:+.0f},{r['dy']:+.0f}) "
            f"| mid={mid} | h12 {r['h12_before']}->{r['h12_after']} |"
        )


if __name__ == "__main__":
    main()
