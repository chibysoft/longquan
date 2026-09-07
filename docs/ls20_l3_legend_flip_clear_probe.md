# ls20 L3 legend flip -> L1/L2 clear 流程（E8）报告

> 脚本：`tools/ls20_l3_legend_flip_clear_probe.py`
> 性质：设计期探路（最小动作 + 比对 levels），非运行时求解器

---

## 结论

**PLAN_FAIL_AFTER_DISSOLVE**

## 逐步

- `{'tag': 'l3_start', 'levels': 2, 'mover': (9, 40, 13, 41), 'layers': 1, 'c9': 23, 'c11': 96, 'c12': 36}`
- `{'tag': 'at_point', 'levels': 2, 'mover': (24, 45, 28, 46), 'layers': 1, 'c9': 23, 'c11': 28, 'c12': 36}`
- `{'tag': 'post_dissolve', 'levels': 2, 'mover': (29, 45, 33, 46), 'layers': 1, 'c9': 45, 'c11': 24, 'c12': 10}`
- `{'tag': 'plan_fail_after_dissolve', 'error': 'no path to marker contact; marker=(50, 11, 52, 13)', 'levels': 2}`

## 判读

- `CLEARED`：legend flip（环溶解）后，L1/L2 流程使 levels 2→3 →
  机制锁定：环溶解 = 前置「武装」步骤。
- `NOT_CLEARED`：legend flip 后 L1/L2 流程仍不过 → 排除「legend flip
  是缺失前置」假设，机制另找。
- `PLAN_FAIL_AFTER_DISSOLVE`：溶解后 planner 找不到 contact/stamp 路径
  （能量/可达性），本身即负结果。
- `CLEARED_BY_DISSOLVE` / `CLEARED_DURING_WALK`：溶解或途中即过关。

