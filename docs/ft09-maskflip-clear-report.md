# ft09 maskflip 库通关（结构归纳路径B）

> 脚本：`tools/ft09_maskflip_clear.py`
> 库：`longquan/interactive/maskflip/`

## 结论

**PASS** — 库规划通关：`levels`→`6`，`state=WIN`（win_levels=6）。

> verdict=`maskflip_lib_full_clear_win`

## 轨迹摘要

- L5 cleared: `True` clicks=`21`
- L6 cleared: `True` clicks=`13`

## 方法

1. 转移层：`flip_block` / `xor_plus` / `xor_north`（`induce_transition` 可从样例归纳）。
2. 目标层：`decode_l4_like_targets` + `plan_clicks_gf2`。
3. 通关判据仅 `levels_completed` / `state=WIN`。

