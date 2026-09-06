# ls20 seated 多关通关报告

> game_id=`ls20-9607627b`
> final levels=`2` / win_levels=`7` state=`NOT_FINISHED`

## 结论

**PARTIAL** — 至少 L1 过；停在 levels=2。

## 逐步

- `{'event': 'attempt', 'levels_before': 0, 'info': {'t1': (3, 6), 't2': (6, 2), 'ov': 10, 'marker': (20, 31, 22, 33), 'stamp': (33, 9, 39, 15), 'path1_len': 6, 'ritual_len': 0, 'path2_len': 7, 'cursor0': (6, 9), 'pickups': (), 'fuel0': 21, 'fuel_end': 8, 'path_len': 13, 'ritual': False, 'warps': {}}, 'actions': [3, 3, 3, 1, 1, 1, 4, 1, 4, 4, 1, 1, 1], 'levels_after': 1, 'steps_used': 13}`
- `{'event': 'level_sync', 'levels': 1, 'mover': (29, 35, 33, 36), 'sync_action': 1}`
- `{'event': 'attempt', 'levels_before': 1, 'info': {'t1': (9, 9), 't2': (2, 8), 'ov': 10, 'marker': (50, 46, 52, 48), 'stamp': (13, 39, 19, 45), 'path1_len': 16, 'ritual_len': 3, 'path2_len': 25, 'cursor0': (5, 7), 'pickups': ((15, 16, 17, 18), (40, 51, 42, 53)), 'fuel0': 21, 'fuel_end': 16, 'path_len': 44, 'ritual': True, 'warps': {}}, 'actions': [4, 1, 1, 1, 1, 1, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 1, 2, 2, 3, 3, 4, 4, 1, 1, 1, 1, 1, 1, 1, 3, 1, 3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2], 'levels_after': 2, 'steps_used': 44}`
- `{'event': 'level_sync', 'levels': 2, 'mover': (9, 40, 13, 41), 'sync_action': 1}`
- `{'event': 'attempt', 'levels_before': 2, 'info': {'t1': (9, 2), 't2': (10, 10), 'ov': 10, 'marker': (50, 11, 52, 13), 'stamp': (53, 49, 59, 55), 'path1_len': 21, 'ritual_len': 3, 'path2_len': 8, 'cursor0': (1, 8), 'pickups': ((35, 16, 37, 18), (20, 31, 22, 33)), 'fuel0': 21, 'fuel_end': 0, 'path_len': 32, 'ritual': True, 'warps': {'((1, 1), (1, 0))': (6, 1), '((1, 1), (-1, 0))': (6, 1), '((1, 1), (0, 1))': (6, 1), '((1, 1), (0, -1))': (6, 1)}}, 'actions': [1, 1, 1, 1, 1, 1, 1, 3, 2, 2, 4, 2, 2, 4, 4, 4, 4, 1, 1, 3, 1, 1, 2, 2, 4, 2, 2, 2, 2, 2, 2, 2], 'levels_after': 2, 'error': 'path exhausted without level-up'}`

## 方法

- `ls20.init`：`locate_mover` 认 5×2 色12（L3+ 去装饰）
- L3+：`detect_warps` 顶带传送门（色1 侧轨 → 同行段落点）
- 接触 → L2+ 强制 H23（UP/DOWN/DOWN）→ H20 盖印（ov≥10）
- H21 能量感知 BFS；过关后 sync ACTION1 再规划

