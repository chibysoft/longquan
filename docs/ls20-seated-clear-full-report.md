# ls20 seated 多关通关报告（含 L3 通用解锁规则）

> game_id=`ls20-9607627b`
> final levels=`7` / win_levels=`7` state=`WIN`

## 结论

**PASS** — 全关 seated 通关（levels=7）。

## 逐步

- `{'event': 'attempt', 'levels_before': 0, 'info': {'ritual': False, 'pickups': (), 'unlocked_stamp': False, 't2': (6, 2), 'path_len': 13, 'closed_loop': False, 'mode': None}, 'actions': [3, 3, 3, 1, 1, 1, 4, 1, 4, 4, 1, 1, 1], 'levels_after': 1, 'steps_used': 13}`
- `{'event': 'level_sync', 'levels': 1, 'mover': (29, 35, 33, 36)}`
- `{'event': 'attempt', 'levels_before': 1, 'info': {'ritual': True, 'pickups': ((15, 16, 17, 18), (40, 51, 42, 53)), 'unlocked_stamp': False, 't2': (2, 8), 'path_len': 44, 'closed_loop': False, 'mode': None}, 'actions': [4, 1, 1, 1, 1, 1, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 1, 2, 2, 3, 3, 4, 4, 1, 1, 1, 1, 1, 1, 1, 3, 1, 3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2], 'levels_after': 2, 'steps_used': 44}`
- `{'event': 'level_sync', 'levels': 2, 'mover': (9, 40, 13, 41)}`
- `{'event': 'unlock', 'levels': 2, 'cell': (5, 9), 'mover': (29, 45, 33, 46), 'c9': 45, 'c12': 10}`
- `{'event': 'attempt', 'levels_before': 2, 'info': {'ritual': True, 'pickups': ((20, 31, 22, 33),), 'unlocked_stamp': False, 't2': (10, 10), 'path_len': 24, 'closed_loop': False, 'mode': None}, 'actions': [1, 1, 1, 3, 3, 4, 4, 4, 4, 4, 4, 4, 1, 1, 1, 3, 1, 1, 2, 2, 4, 1, 1, 2], 'levels_after': 3, 'steps_used': 24}`
- `{'event': 'level_sync', 'levels': 3, 'mover': (54, 5, 58, 6)}`
- `{'event': 'unlock', 'levels': 3, 'cell': (6, 6), 'mover': (34, 30, 38, 31), 'c9': 21, 'c12': 10}`
- `{'event': 'ring_phase', 'levels': 3, 'osc': 2, 'c9': 41}`
- `{'event': 'ring_phase_mid', 'levels': 3, 'cursor': (3, 3), 'ui': 84, 'c9': 43}`
- `{'event': 'attempt', 'levels_before': 3, 'info': {'ritual': True, 'pickups': (), 'unlocked_stamp': True, 't2': (1, 1), 'path_len': None, 'closed_loop': True, 'mode': 'udd47+stamp'}, 'actions': [2, 3, 2, 3, 2, 2, 4, 1, 2, 2, 4, 1, 1, 1, 1, 4, 4, 1, 1, 1, 3, 3, 3], 'levels_after': 4, 'steps_used': 23}`
- `{'event': 'level_sync', 'levels': 4, 'mover': (49, 35, 53, 36)}`
- `{'event': 'attempt', 'levels_before': 4, 'info': {'ritual': False, 'pickups': ((45, 6, 47, 8), (10, 11, 12, 13), (15, 46, 17, 48)), 'unlocked_stamp': True, 't2': (1, 1), 'path_len': None, 'closed_loop': True, 'mode': 'l5_rec_stamp'}, 'actions': [4, 1, 1, 3, 1, 3, 3, 2, 4, 3, 4, 3, 4, 4, 1, 2, 3, 3, 3, 1, 3, 3, 3, 4, 4, 2, 2, 2, 2, 2, 4, 4, 2, 4, 4, 4, 1, 4, 4, 2, 2, 2, 1], 'levels_after': 5, 'steps_used': 44}`
- `{'event': 'level_sync', 'levels': 5, 'mover': (24, 45, 28, 46)}`
- `{'event': 'attempt', 'levels_before': 5, 'info': {'ritual': False, 'pickups': ((10, 6, 12, 8), (40, 6, 42, 8), (10, 46, 12, 48)), 'unlocked_stamp': True, 't2': (1, 1), 'path_len': None, 'closed_loop': True, 'mode': 'l6_rec_stamp'}, 'actions': [3, 1, 3, 3, 1, 1, 1, 4, 4, 4, 4, 4, 4, 1, 4, 1, 4, 1, 1, 2, 2, 2, 1, 1, 3, 1, 2, 3, 3, 4, 3, 3, 3, 3, 3, 2, 2, 2, 2, 4, 4, 1, 3, 4, 3, 3, 1, 1, 1, 1, 1, 1, 1, 2, 4, 4, 4, 4, 4, 4, 2, 4, 4, 1, 1, 2, 2, 2, 2, 2, 2], 'levels_after': 6, 'steps_used': 72}`
- `{'event': 'level_sync', 'levels': 6, 'mover': (19, 10, 23, 11)}`
- `{'event': 'attempt', 'levels_before': 6, 'info': {'ritual': False, 'pickups': ((10, 6, 12, 8), (40, 8, 40, 8), (30, 21, 32, 23)), 'unlocked_stamp': True, 't2': (1, 1), 'path_len': None, 'closed_loop': True, 'mode': 'l7_rec_win'}, 'actions': [1, 2, 2, 3, 3, 2, 2, 2, 2, 2, 1, 2, 4, 2, 1, 4, 1, 2, 1, 2, 1, 2, 1, 2, 3, 3, 1, 1, 1, 4, 4, 4, 4, 1, 4, 4, 2, 4, 4, 1, 1, 4, 2, 2, 3, 3, 3, 1, 2, 2, 2, 2], 'levels_after': 7, 'steps_used': 53}`
- `{'event': 'done', 'levels': 7, 'state': 'WIN'}`

## 方法

- `plan_two_phase`：接触 → L2+ 强制 H23（UP/DOWN/DOWN）→ H20 盖印（ov≥10）
- **通用解锁规则**：armed-only 非 gate 且 y<54 的格 = 解锁对象；
  进入它（armed 步行）后重跑两阶段流程。L1/L2 无此类格（底部色板被排除），
  L3 唯一命中 (5,9) 环 → 压环翻面 → gate 开。
- 过关判据仅 `levels_completed` 增加（红线 3）。

