# ft09 迁移报告（阶段 4 / execution-plan §6）

> 2026-09-08 · 终点硬证据汇总（闭卷 · levels/WIN · 库路径）  
> **说明**：ft09 在阶段 3 之前已由路径 B（`maskflip`）全关 WIN；本报告按施工图口径补档。

---

## 验收对照（execution-plan §0 / §6）

| 要求 | 证据 |
|------|------|
| 真实 scorecard / levels | `state=WIN`，`levels_completed=6`（`win_levels=6`，无 L7） |
| 闭卷 | 不读引擎源码；转移由样例诱导；目标由帧解码 |
| 三样证据 | 见下「证据链」 |
| 步数合规 | 库规划 L5=21 clicks、L6=13 clicks（见 maskflip clear report） |

主报告：[`ft09-maskflip-clear-report.md`](ft09-maskflip-clear-report.md)  
背景：[`ft09-full-clear-report.md`](ft09-full-clear-report.md) · 结构归纳：[`structure-induction-ft09.md`](structure-induction-ft09.md)

---

## 证据链

1. **转移原语**：`flip_block` / `xor_plus` / `xor_north`（`longquan/interactive/maskflip/`）  
2. **目标层**：`decode_l4_like_targets` + `plan_clicks_gf2`  
3. **线上通关**：`python tools/ft09_maskflip_clear.py` → WIN  

taxonomy 落点：E 族 **toggle**（阶段 1.5 补入）。

---

## 与选择器（1a）的关系

帧级分流：`longquan.selector.select_family(ft09_frame) == "toggle"`  
→ 管道 `interactive.maskflip`（不是 `solve_auto` 几何路径）。

---

## 结论

**阶段 4 验收通过（已提前达成，本文件为归档）。**  
verdict=`maskflip_lib_full_clear_win`
