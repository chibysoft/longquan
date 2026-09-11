"""ls20 L4 intervention probe: counterfactual (control vs intervention).

方向 2 落地。时序因果必须靠**干预**而非纯观测坐实——录屏只有一条成功轨迹，
只能看到「压环 → 过关」的相关，看不到反事实。本探针把 L4 回放到 stamp gate
之前，然后**成对跑**：

  control       L4 开局 → 直接 armed stamp            → levels 变不变？
  intervention  L4 开局 → 执行候选解锁动作 X → armed stamp → levels 变不变？

只有 control 卡住（levels 不变）而 intervention 过关（levels +1），才能坐实
「X 是 gate 可进的必要前置」——这是因果，不是相关。

关键纠正（armed-is-default）：mover 全程 carrying（armed 是常态，不是目标）。
所以「进 gate」本身就是 armed mover 走向 stamp gate 格，不存在「先武装」。
真变量 = stamp gate 是否可进。判据只信 levels（红线 3：线上实测，不看像素像不像）。

USAGE
  python tools/ls20_l4_intervention_probe.py --interventions control,crush
  python tools/ls20_l4_intervention_probe.py            # 默认全跑
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from longquan.interactive import ls20
from tools.ls20_online_validate import DIR_TO_ACTION, OnlineSession, _api_key
from tools.ls20_l4_arming_probe import _climb_to_l4, _gate_walk, _plan_crush
from tools.ls20_seated_clear_full import (
    _unlock_candidates,
    _plan_to_pickup,
    _plan_to_contact,
    _plan_armed_stamp_only,
)

REPORT = ROOT / "docs" / "ls20_l4_intervention_probe.md"


def _act(sess, frame, meta, a, log, tag):
    resp = sess.action(DIR_TO_ACTION[a])
    frame, meta = resp["frame"], resp
    log.append({
        "tag": tag, "action": DIR_TO_ACTION[a],
        "cursor": ls20.init(frame).cursor,
        "mover": ls20.locate_mover(frame),
        "levels": int(meta.get("levels_completed") or 0),
    })
    return frame, meta


def _exec_path(sess, frame, meta, path, log, tag):
    lv = int(meta.get("levels_completed") or 0)
    for i, a in enumerate(path, 1):
        frame, meta = _act(sess, frame, meta, a, log, f"{tag}_step")
        if int(meta.get("levels_completed") or 0) > lv:
            return frame, meta, True
    return frame, meta, False


def _try_armed_stamp(sess, frame, meta, log, tag):
    """行为判据：执行 armed stamp 路径，levels 是否 +1。"""
    path, c, f, info = _plan_armed_stamp_only(frame)
    log.append({"tag": f"{tag}_plan", "ok": path is not None,
                "path_len": None if path is None else len(path),
                "info": info, "snap": _gate_walk(frame)})
    if path is None:
        log.append({"tag": "RESULT", "verdict": f"{tag}_PLAN_FAIL", "levels": meta.get("levels_completed")})
        return frame, meta, "PLAN_FAIL"
    frame, meta, leveled = _exec_path(sess, frame, meta, path, log, f"{tag}_stamp")
    verdict = f"{tag}_PASS" if leveled else f"{tag}_FAIL"
    log.append({"tag": "RESULT", "verdict": verdict,
                "levels": meta.get("levels_completed"),
                "snap": _gate_walk(frame)})
    return frame, meta, verdict


def _do_crush(sess, frame, meta, log):
    """干预动作：压环每个 unlock candidate（armed-only 非 gate 格）。"""
    cands = _unlock_candidates(frame)
    log.append({"tag": "crush_cands", "cands": cands, "snap": _gate_walk(frame)})
    if not cands:
        log.append({"tag": "crush", "verdict": "NO_CAND"})
        return frame, meta
    # 补给（bottom only，别吃 mid pickup，保 ui 给最后 stamp）
    p_pu, _ = _plan_to_pickup(frame, bottom_only=True)
    if p_pu:
        frame, meta, _ = _exec_path(sess, frame, meta, p_pu, log, "fuel")
    for cand in cands:
        p, _ = _plan_crush(frame, cand)
        if p is None:
            log.append({"tag": "crush", "cell": cand, "verdict": "UNREACHABLE"})
            continue
        log.append({"tag": "crush_plan", "cell": cand, "len": len(p),
                    "actions": [DIR_TO_ACTION[a] for a in p]})
        for i, a in enumerate(p, 1):
            frame, meta = _act(sess, frame, meta, a, log, "crush_step")
        reached = ls20.init(frame).cursor == cand
        log.append({"tag": "post_crush", "cell": cand, "reached": reached,
                    "cursor": ls20.init(frame).cursor,
                    "levels": meta.get("levels_completed"),
                    "snap": _gate_walk(frame),
                    "c9": int((ls20._plane(frame) == 9).sum()),
                    "c14": int((ls20._plane(frame) == 14).sum())})
    return frame, meta


def _do_contact(sess, frame, meta, log):
    """干预动作：marker 接触（L4 曾假设的「武装」接触，现作为候选解锁动作）。"""
    p, c, f, info = _plan_to_contact(frame)
    log.append({"tag": "contact_plan", "ok": p is not None, "info": info,
                "snap": _gate_walk(frame)})
    if p is None:
        log.append({"tag": "contact", "verdict": "NO_PATH"})
        return frame, meta
    frame, meta, _ = _exec_path(sess, frame, meta, p, log, "contact")
    log.append({"tag": "post_contact", "cursor": ls20.init(frame).cursor,
                "levels": meta.get("levels_completed"),
                "snap": _gate_walk(frame)})
    return frame, meta


def run_trial(intervention: str) -> dict:
    key = _api_key()
    if not key:
        raise RuntimeError("no ARC_API_KEY")
    sess = OnlineSession(key)
    log = []
    try:
        sess.open(tags=[f"ls20_l4_interv_{intervention}"])
        frame, meta = _climb_to_l4(sess)
        lv = int(meta.get("levels_completed") or 0)
        log.append({"tag": "l4_start", "levels": lv, "snap": _gate_walk(frame),
                    "mover": ls20.locate_mover(frame)})
        print(f"=== intervention={intervention} lv={lv} ===")

        if intervention == "control":
            # 不干预，直接 armed stamp
            _, _, verdict = _try_armed_stamp(sess, frame, meta, log, "control")
        elif intervention == "crush":
            frame, meta = _do_crush(sess, frame, meta, log)
            _, _, verdict = _try_armed_stamp(sess, frame, meta, log, "crush")
        elif intervention == "contact":
            frame, meta = _do_contact(sess, frame, meta, log)
            _, _, verdict = _try_armed_stamp(sess, frame, meta, log, "contact")
        else:
            raise ValueError(intervention)

        print(f"verdict={verdict}")
        return {"intervention": intervention, "verdict": verdict,
                "levels_start": lv,
                "levels_end": int(meta.get("levels_completed") or 0),
                "log": log}
    finally:
        sess.close()


def _write_report(results: list[dict]) -> None:
    lines = [
        "# ls20 L4 intervention probe (观测 → 干预)",
        "",
        "> 方向 2 落地：时序因果靠干预坐实，非纯观测。成对反事实对照。",
        "> 判据只信 levels（红线 3）。armed 是常态，真变量 = gate 是否可进。",
        "",
    ]
    for r in results:
        lines.append(f"## intervention `{r['intervention']}` → **{r['verdict']}**")
        lines.append("")
        lines.append(f"- levels {r['levels_start']} → {r['levels_end']}")
        for row in r["log"]:
            lines.append(f"- `{row}`")
        lines.append("")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {REPORT}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interventions", default="control,crush,contact",
                    help="comma list: control,crush,contact")
    args = ap.parse_args()
    interventions = [x.strip() for x in args.interventions.split(",") if x.strip()]
    results = [run_trial(i) for i in interventions]
    _write_report(results)

    # 因果判定：control 卡住 + 某个干预过关 → 该干预必要
    control = next((r for r in results if r["intervention"] == "control"), None)
    cleared = [r for r in results if r["verdict"].endswith("_PASS")]
    if control and control["verdict"].endswith("_FAIL"):
        if cleared:
            print(f"\n[因果坐实] control 卡住，而 {[c['intervention'] for c in cleared]} 过关")
            print("  => 这些干预动作是 L4 gate 可进的必要前置。")
            return 0
        print("\n[未坐实] control 卡住，且所有干预也都卡住 —— 候选解锁动作还没覆盖到真正的解锁。")
        return 1
    if control and control["verdict"].endswith("_PASS"):
        print("\n[假设推翻] control 直接过关 —— L4 gate 本来就可进，'解锁' 不是必要前置。")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
