"""Check carrying_near_mover after real (4,6) contact."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from longquan.interactive.match import carrying_bbox_from_cursor
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_seated_clear import _ov
from tools.ls20_seated_clear_full import _plan_to_contact
from tools.ls20_l4_dd_ritual_probe import boot_l4
from tools.ls20_l4_stamp9_probe import stamp9


def snap(frame, tag):
    st = ls20.init(frame)
    offset = ls20.grid_offset(frame)
    markers = [g for g in st.goals if g.id == "ls20-marker"]
    marker = markers[0].shape if markers else None
    carry = st.carrying
    cb = carrying_bbox_from_cursor(st.cursor, offset)
    mov = ls20.locate_mover(frame)
    print(tag, "cur", st.cursor, "carry", carry, "marker", marker,
          "ov", None if marker is None else _ov(cb, marker),
          "s9", stamp9(frame)[0], "ui", ls20.ui_energy(frame),
          "goals", [g.id for g in st.goals])


def main():
    sess = OnlineSession(_api_key())
    try:
        sess.open(tags=["ls20_l4_carry_check"])
        frame, meta = boot_l4(sess)
        snap(frame, "post_unlock")
        for i in range(20):
            pc, cc, _, ic = _plan_to_contact(frame)
            snap(frame, f"pre{i}")
            if pc is None:
                print("fail", ic)
                break
            if len(pc) == 0:
                print("plan says already", ic)
                break
            resp = sess.action(DIR_TO_ACTION[pc[0]])
            frame, meta = resp["frame"], resp
            snap(frame, f"post{i}")
            st = ls20.init(frame)
            if st.carrying:
                print("HAS CARRYING")
                break
            markers = [g for g in st.goals if g.id == "ls20-marker"]
            if markers and st.cursor == (4, 6):
                offset = ls20.grid_offset(frame)
                ov = _ov(carrying_bbox_from_cursor(st.cursor, offset), markers[0].shape)
                print("at46 ov", ov)
                if ov > 0:
                    print("OVERLAP CONTACT")
                    break
    finally:
        sess.close()


if __name__ == "__main__":
    main()
