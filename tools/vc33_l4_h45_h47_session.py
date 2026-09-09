"""Single-session L4 remodel run: enter_scan+H46 then H45+H47.

tags=["vc33_recon"] only. One scorecard.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ls20_online_validate import _api_key  # noqa: E402
from tools.vc33_l3_probe import Sess  # noqa: E402
from tools.vc33_l4_enter_scan import OUT as OUT_SCAN  # noqa: E402
from tools.vc33_l4_enter_scan import run as run_scan  # noqa: E402
from tools.vc33_l4_remodel import OUT as OUT_REM  # noqa: E402
from tools.vc33_l4_remodel import run as run_remodel  # noqa: E402

OUT = ROOT / "tests/fixtures/vc33_l4_h45_h47_session.json"


def main():
    key = _api_key()
    sess = Sess(key)
    out = {"hypotheses": ["enter_scan", "H45", "H46", "H47"], "parts": {}}
    try:
        sess.open()
        out["game_id"] = sess.game_id
        print("===== ENTER SCAN + H46 =====")
        scan = {"hypotheses": ["enter_scan", "H46"]}
        _d, _g, cleared = run_scan(sess, scan)
        OUT_SCAN.write_text(
            json.dumps(scan, indent=2, ensure_ascii=False, default=float),
            encoding="utf-8",
        )
        print("saved", OUT_SCAN)
        out["parts"]["scan"] = {
            "H46_verdict": scan.get("H46_verdict"),
            "enter_hist": (scan.get("enter") or {}).get("hist"),
            "after_c7_hist": (scan.get("after_c7") or {}).get("hist"),
            "c7_n": len(scan.get("c7_clicks") or []),
            "c5_nonzero": sum(1 for r in (scan.get("c5_clicks") or []) if r.get("nd")),
            "odd_n": len(scan.get("odd_clicks") or []),
            "CLEARED": scan.get("CLEARED"),
        }
        if cleared:
            out["CLEARED"] = True
            return 0

        print("===== H45 + H47 =====")
        rem = {"hypotheses": ["H45", "H47"]}
        _d, _g, cleared = run_remodel(sess, rem)
        OUT_REM.write_text(
            json.dumps(rem, indent=2, ensure_ascii=False, default=float),
            encoding="utf-8",
        )
        print("saved", OUT_REM)
        out["parts"]["remodel"] = {
            "H45_verdict": rem.get("H45_verdict"),
            "H47_verdict": rem.get("H47_verdict"),
            "CLEARED": rem.get("CLEARED"),
        }
        if cleared:
            out["CLEARED"] = True
    finally:
        sess.close()
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("saved", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
