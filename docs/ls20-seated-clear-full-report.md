# ls20 seated 多关通关报告（含 L3 通用解锁规则）

> game_id=`ls20-9607627b`
> final levels=`3` / win_levels=`7` state=`NOT_FINISHED`

## 结论

**L1-L3 PASS** — levels=3，L3 通用解锁规则生效。

## 逐步

- `{'event': 'attempt', 'levels_before': 0, 'info': {'t1': (3, 6), 't2': (6, 2), 'ov': 10, 'marker': (20, 31, 22, 33), 'stamp': (33, 9, 39, 15), 'path1_len': 6, 'ritual_len': 0, 'path2_len': 7, 'cursor0': (6, 9), 'pickups': (), 'fuel0': 21, 'fuel_end': 8, 'path_len': 13, 'ritual': False, 'warps': {}}, 'actions': [3, 3, 3, 1, 1, 1, 4, 1, 4, 4, 1, 1, 1], 'levels_after': 1, 'steps_used': 13}`
- `{'event': 'level_sync', 'levels': 1, 'mover': (29, 35, 33, 36)}`
- `{'event': 'attempt', 'levels_before': 1, 'info': {'t1': (9, 9), 't2': (2, 8), 'ov': 10, 'marker': (50, 46, 52, 48), 'stamp': (13, 39, 19, 45), 'path1_len': 16, 'ritual_len': 3, 'path2_len': 25, 'cursor0': (5, 7), 'pickups': ((15, 16, 17, 18), (40, 51, 42, 53)), 'fuel0': 21, 'fuel_end': 16, 'path_len': 44, 'ritual': True, 'warps': {}}, 'actions': [4, 1, 1, 1, 1, 1, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 1, 2, 2, 3, 3, 4, 4, 1, 1, 1, 1, 1, 1, 1, 3, 1, 3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2], 'levels_after': 2, 'steps_used': 44}`
- `{'event': 'level_sync', 'levels': 2, 'mover': (9, 40, 13, 41)}`
- `{'event': 'unlock', 'levels': 2, 'cell': (5, 9), 'mover': (29, 45, 33, 46), 'c9': 45, 'c12': 10}`
- `{'event': 'attempt', 'levels_before': 2, 'info': {'t1': (9, 2), 't2': (10, 10), 'ov': 10, 'marker': (50, 11, 52, 13), 'stamp': (53, 49, 59, 55), 'path1_len': 17, 'ritual_len': 3, 'path2_len': 4, 'cursor0': (5, 9), 'pickups': ((20, 31, 22, 33),), 'fuel0': 12, 'fuel_end': 2, 'path_len': 24, 'ritual': True, 'warps': {'((1, 1), (1, 0))': (6, 1), '((1, 1), (-1, 0))': (6, 1), '((1, 1), (0, 1))': (6, 1), '((1, 1), (0, -1))': (6, 1), '((10, 1), (0, 1))': (10, 9)}}, 'actions': [1, 1, 1, 3, 3, 4, 4, 4, 4, 4, 4, 4, 1, 1, 1, 3, 1, 1, 2, 2, 4, 1, 1, 2], 'levels_after': 3, 'steps_used': 24}`
- `{'event': 'level_sync', 'levels': 3, 'mover': (54, 5, 58, 6)}`
- `{'event': 'unlock', 'levels': 3, 'cell': (6, 6), 'mover': (54, 30, 58, 31), 'c9': 23, 'c12': 12}`
- `{'event': 'plan_fail', 'levels': 3, 'error': 'H23 ritual blocked (0, -1) at (4, 6)'}`

## 方法

- `plan_two_phase`：接触 → L2+ 强制 H23（UP/DOWN/DOWN）→ H20 盖印（ov≥10）
- **通用解锁规则**：armed-only 非 gate 且 y<54 的格 = 解锁对象；
  进入它（armed 步行）后重跑两阶段流程。L1/L2 无此类格（底部色板被排除），
  L3 唯一命中 (5,9) 环 → 压环翻面 → gate 开。
- 过关判据仅 `levels_completed` 增加（红线 3）。

