# ls20 L3 压环后完整流程（E10b）报告

> 脚本：`tools/ls20_l3_crush_then_clear_probe.py`
> 性质：设计期探路（先吃补给 → 压环 → 完整 L1/L2 流程 → 比对 levels）

---

## 结论

**CLEARED**

## 逐步

- `{'tag': 'l3_start', 'levels': 2, 'mover': (9, 40, 13, 41), 'layers': 1, 'c9': 23, 'c12': 36, 'c11': 96, 'ui': 80}`
- `{'tag': 'pickup', 'step': 1, 'action': 1, 'mover': (9, 35, 13, 36), 'levels': 2, 'ui': 76}`
- `{'tag': 'pickup', 'step': 2, 'action': 1, 'mover': (9, 30, 13, 31), 'levels': 2, 'ui': 72}`
- `{'tag': 'pickup', 'step': 3, 'action': 1, 'mover': (9, 25, 13, 26), 'levels': 2, 'ui': 68}`
- `{'tag': 'pickup', 'step': 4, 'action': 1, 'mover': (9, 20, 13, 21), 'levels': 2, 'ui': 64}`
- `{'tag': 'pickup', 'step': 5, 'action': 1, 'mover': (9, 15, 13, 16), 'levels': 2, 'ui': 60}`
- `{'tag': 'pickup', 'step': 6, 'action': 1, 'mover': (9, 10, 13, 11), 'levels': 2, 'ui': 56}`
- `{'tag': 'pickup', 'step': 7, 'action': 1, 'mover': (9, 5, 13, 6), 'levels': 2, 'ui': 52}`
- `{'tag': 'pickup', 'step': 8, 'action': 3, 'mover': (29, 5, 33, 6), 'levels': 2, 'ui': 48}`
- `{'tag': 'pickup', 'step': 9, 'action': 2, 'mover': (29, 10, 33, 11), 'levels': 2, 'ui': 44}`
- `{'tag': 'pickup', 'step': 10, 'action': 2, 'mover': (29, 15, 33, 16), 'levels': 2, 'ui': 40}`
- `{'tag': 'pickup', 'step': 11, 'action': 4, 'mover': (34, 15, 38, 16), 'levels': 2, 'ui': 84}`
- `{'tag': 'post_pickup', 'levels': 2, 'mover': (34, 15, 38, 16), 'layers': 1, 'c9': 23, 'c12': 36, 'c11': 92, 'ui': 84}`
- `{'tag': 'to_ring', 'step': 1, 'action': 3, 'mover': (29, 15, 33, 16), 'levels': 2, 'ui': 80}`
- `{'tag': 'to_ring', 'step': 2, 'action': 2, 'mover': (29, 20, 33, 21), 'levels': 2, 'ui': 76}`
- `{'tag': 'to_ring', 'step': 3, 'action': 2, 'mover': (29, 25, 33, 26), 'levels': 2, 'ui': 72}`
- `{'tag': 'to_ring', 'step': 4, 'action': 2, 'mover': (29, 30, 33, 31), 'levels': 2, 'ui': 68}`
- `{'tag': 'to_ring', 'step': 5, 'action': 2, 'mover': (29, 35, 33, 36), 'levels': 2, 'ui': 64}`
- `{'tag': 'to_ring', 'step': 6, 'action': 2, 'mover': (29, 40, 33, 41), 'levels': 2, 'ui': 60}`
- `{'tag': 'to_ring', 'step': 7, 'action': 3, 'mover': (24, 40, 28, 41), 'levels': 2, 'ui': 56}`
- `{'tag': 'to_ring', 'step': 8, 'action': 2, 'mover': (24, 45, 28, 46), 'levels': 2, 'ui': 52}`
- `{'tag': 'post_crush', 'levels': 2, 'mover': (29, 45, 33, 46), 'layers': 1, 'c9': 45, 'c12': 10, 'c11': 56, 'ui': 48}`
- `{'tag': 'plan', 'info': {'t1': (9, 2), 't2': (10, 10), 'ov': 10, 'marker': (50, 11, 52, 13), 'stamp': (53, 49, 59, 55), 'path1_len': 17, 'ritual_len': 3, 'path2_len': 4, 'cursor0': (5, 9), 'pickups': ((20, 31, 22, 33),), 'fuel0': 10, 'fuel_end': 2, 'path_len': 24, 'ritual': True, 'warps': {'((1, 1), (1, 0))': (6, 1), '((1, 1), (-1, 0))': (6, 1), '((1, 1), (0, 1))': (6, 1), '((1, 1), (0, -1))': (6, 1), '((10, 1), (0, 1))': (10, 9)}}, 'actions': [1, 1, 1, 3, 3, 4, 4, 4, 4, 4, 4, 4, 1, 1, 1, 3, 1, 1, 2, 2, 4, 1, 1, 2]}`
- `{'tag': 'clear', 'step': 1, 'action': 1, 'mover': (29, 40, 33, 41), 'levels': 2, 'ui': 44}`
- `{'tag': 'clear', 'step': 2, 'action': 1, 'mover': (29, 35, 33, 36), 'levels': 2, 'ui': 40}`
- `{'tag': 'clear', 'step': 3, 'action': 1, 'mover': (29, 30, 33, 31), 'levels': 2, 'ui': 36}`
- `{'tag': 'clear', 'step': 4, 'action': 3, 'mover': (24, 30, 28, 31), 'levels': 2, 'ui': 32}`
- `{'tag': 'clear', 'step': 5, 'action': 3, 'mover': (19, 30, 23, 31), 'levels': 2, 'ui': 84}`
- `{'tag': 'clear', 'step': 6, 'action': 4, 'mover': (24, 30, 28, 31), 'levels': 2, 'ui': 80}`
- `{'tag': 'clear', 'step': 7, 'action': 4, 'mover': (29, 30, 33, 31), 'levels': 2, 'ui': 76}`
- `{'tag': 'clear', 'step': 8, 'action': 4, 'mover': (34, 30, 38, 31), 'levels': 2, 'ui': 72}`
- `{'tag': 'clear', 'step': 9, 'action': 4, 'mover': (39, 30, 43, 31), 'levels': 2, 'ui': 68}`
- `{'tag': 'clear', 'step': 10, 'action': 4, 'mover': (44, 30, 48, 31), 'levels': 2, 'ui': 64}`
- `{'tag': 'clear', 'step': 11, 'action': 4, 'mover': (49, 30, 53, 31), 'levels': 2, 'ui': 60}`
- `{'tag': 'clear', 'step': 12, 'action': 4, 'mover': (54, 30, 58, 31), 'levels': 2, 'ui': 56}`
- `{'tag': 'clear', 'step': 13, 'action': 1, 'mover': (54, 25, 58, 26), 'levels': 2, 'ui': 52}`
- `{'tag': 'clear', 'step': 14, 'action': 1, 'mover': (54, 20, 58, 21), 'levels': 2, 'ui': 48}`
- `{'tag': 'clear', 'step': 15, 'action': 1, 'mover': (54, 15, 58, 16), 'levels': 2, 'ui': 44}`
- `{'tag': 'clear', 'step': 16, 'action': 3, 'mover': (49, 15, 53, 16), 'levels': 2, 'ui': 40}`
- `{'tag': 'clear', 'step': 17, 'action': 1, 'mover': (49, 10, 53, 11), 'levels': 2, 'ui': 36}`
- `{'tag': 'clear', 'step': 18, 'action': 1, 'mover': (49, 5, 53, 6), 'levels': 2, 'ui': 32}`
- `{'tag': 'clear', 'step': 19, 'action': 2, 'mover': (49, 10, 53, 11), 'levels': 2, 'ui': 28}`
- `{'tag': 'clear', 'step': 20, 'action': 2, 'mover': (49, 15, 53, 16), 'levels': 2, 'ui': 24}`
- `{'tag': 'clear', 'step': 21, 'action': 4, 'mover': (54, 15, 58, 16), 'levels': 2, 'ui': 20}`
- `{'tag': 'clear', 'step': 22, 'action': 1, 'mover': (54, 10, 58, 11), 'levels': 2, 'ui': 16}`
- `{'tag': 'clear', 'step': 23, 'action': 1, 'mover': (54, 5, 58, 6), 'levels': 2, 'ui': 12}`
- `{'tag': 'clear', 'step': 24, 'action': 2, 'mover': (54, 50, 58, 51), 'levels': 3, 'ui': 8}`

## 判读

- `CLEARED`：legend flip（环溶解）+ 完整流程使 levels 2→3 → 机制锁定：
  环溶解 = 前置「武装」步骤。
- `NOT_CLEARED`：压环 + 完整流程仍不过 → 排除「legend flip 是缺失前置」
  假设，机制转向字形族（rot180 仪式）或其它。
- `PLAN_FAIL_AFTER_CRUSH`：压环后 planner 仍找不到完整路径（能量/可达性），
  本身即负结果。
- `CLEARED_BY_CRUSH`：压环本身即过关。

