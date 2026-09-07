# ls20 L4 H5e gate-diff + pickup2/c8

## phase `a` → **DIFF_DONE_NO_CLEAR**

- `{'tag': 'l4', 'snap': {'gate': (1, 1), 'gate_in_walk_u': False, 'gate_in_walk_a': True, 'stamp_c9': 6, 'has_plus': False, 'unlock_cands': [(6, 6)], 'marker': (26, 32, 27, 33), 'c9': 23, 'c12': 12, 'c14': 22, 'c0': 5, 'c8': 14, 'c11': 98, 'ui': 82, 'cursor': (10, 1), 'mover': (54, 5, 58, 6)}}`
- `{'tag': 'fuel', 'step': 1, 'action': 3, 'cursor': (9, 1), 'mover': (49, 5, 53, 6), 'levels': 3, 'ui': 80}`
- `{'tag': 'fuel', 'step': 2, 'action': 3, 'cursor': (8, 1), 'mover': (44, 5, 48, 6), 'levels': 3, 'ui': 78}`
- `{'tag': 'fuel', 'step': 3, 'action': 3, 'cursor': (7, 1), 'mover': (39, 5, 43, 6), 'levels': 3, 'ui': 76}`
- `{'tag': 'fuel', 'step': 4, 'action': 2, 'cursor': (7, 2), 'mover': (39, 10, 43, 11), 'levels': 3, 'ui': 74}`
- `{'tag': 'fuel', 'step': 5, 'action': 3, 'cursor': (6, 2), 'mover': (34, 10, 38, 11), 'levels': 3, 'ui': 72}`
- `{'tag': 'fuel', 'step': 6, 'action': 2, 'cursor': (6, 3), 'mover': (34, 15, 38, 16), 'levels': 3, 'ui': 70}`
- `{'tag': 'fuel', 'step': 7, 'action': 3, 'cursor': (5, 3), 'mover': (29, 15, 33, 16), 'levels': 3, 'ui': 68}`
- `{'tag': 'fuel', 'step': 8, 'action': 3, 'cursor': (4, 3), 'mover': (24, 15, 28, 16), 'levels': 3, 'ui': 66}`
- `{'tag': 'fuel', 'step': 9, 'action': 3, 'cursor': (3, 3), 'mover': (19, 15, 23, 16), 'levels': 3, 'ui': 84}`
- `{'tag': 'to21', 'step': 1, 'action': 4, 'cursor': (4, 3), 'mover': (24, 15, 28, 16), 'levels': 3, 'ui': 82}`
- `{'tag': 'to21', 'step': 2, 'action': 1, 'cursor': (4, 2), 'mover': (24, 10, 28, 11), 'levels': 3, 'ui': 80}`
- `{'tag': 'to21', 'step': 3, 'action': 1, 'cursor': (4, 1), 'mover': (24, 5, 28, 6), 'levels': 3, 'ui': 78}`
- `{'tag': 'to21', 'step': 4, 'action': 3, 'cursor': (3, 1), 'mover': (19, 5, 23, 6), 'levels': 3, 'ui': 76}`
- `{'tag': 'to21', 'step': 5, 'action': 3, 'cursor': (2, 1), 'mover': (14, 5, 18, 6), 'levels': 3, 'ui': 74}`
- `{'tag': 'diff', 'dir': 'UP', 'n': 2, 'transitions': {'11->3': 2}, 'cursor': (2, 1), 'gate_u': False, 'stamp_c9': 9, 'c9': 23, 'c14': 22}`
- `{'tag': 'diff', 'dir': 'DOWN', 'n': 2, 'transitions': {'11->3': 2}, 'cursor': (2, 1), 'gate_u': False, 'stamp_c9': 9, 'c9': 23, 'c14': 22}`
- `{'tag': 'diff', 'dir': 'LEFT', 'n': 80, 'transitions': {'5->0': 80}, 'cursor': (2, 1), 'gate_u': False, 'stamp_c9': 9, 'c9': 23, 'c14': 22}`
- `{'tag': 'diff', 'dir': 'RIGHT', 'n': 132, 'transitions': {'0->5': 80, '3->9': 15, '3->12': 10, '9->3': 12, '9->5': 3, '11->3': 2, '12->3': 8, '12->5': 2}, 'cursor': (3, 1), 'gate_u': False, 'stamp_c9': 6, 'c9': 23, 'c14': 22}`
- `{'tag': 'after_diff_plan', 'ok': True, 'info': {'t2': (1, 1), 'fuel_end': 19, 'path_len': 2, 'stamp': (8, 4, 14, 10), 'cursor0': (3, 1)}, 'snap': {'gate': (1, 1), 'gate_in_walk_u': False, 'gate_in_walk_a': True, 'stamp_c9': 6, 'has_plus': False, 'unlock_cands': [(6, 6)], 'marker': (26, 32, 27, 33)}}`
- `{'tag': 'after_diff_stamp', 'step': 1, 'action': 3, 'cursor': (2, 1), 'mover': (14, 5, 18, 6), 'levels': 3, 'ui': 66}`
- `{'tag': 'after_diff_stamp', 'step': 2, 'action': 3, 'cursor': (2, 1), 'mover': (14, 5, 18, 6), 'levels': 3, 'ui': 66}`

### diff summary

- **UP**: n=2 trans=`{'11->3': 2}` cursor (2, 1)→(2, 1)
- **DOWN**: n=2 trans=`{'11->3': 2}` cursor (2, 1)→(2, 1)
- **LEFT**: n=80 trans=`{'5->0': 80}` cursor (2, 1)→(2, 1)
- **RIGHT**: n=132 trans=`{'0->5': 80, '3->9': 15, '3->12': 10, '9->3': 12, '9->5': 3, '11->3': 2, '12->3': 8, '12->5': 2}` cursor (2, 1)→(3, 1)

## phase `b` → **B_NO_CLEAR**

- `{'tag': 'l4', 'snap': {'gate': (1, 1), 'gate_in_walk_u': False, 'gate_in_walk_a': True, 'stamp_c9': 6, 'has_plus': False, 'unlock_cands': [(6, 6)], 'marker': (26, 32, 27, 33), 'c9': 23, 'c12': 12, 'c14': 22, 'c0': 5, 'c8': 14, 'c11': 98, 'ui': 82, 'cursor': (10, 1), 'mover': (54, 5, 58, 6)}}`
- `{'tag': 'fuel', 'step': 1, 'action': 3, 'cursor': (9, 1), 'mover': (49, 5, 53, 6), 'levels': 3, 'ui': 80}`
- `{'tag': 'fuel', 'step': 2, 'action': 3, 'cursor': (8, 1), 'mover': (44, 5, 48, 6), 'levels': 3, 'ui': 78}`
- `{'tag': 'fuel', 'step': 3, 'action': 3, 'cursor': (7, 1), 'mover': (39, 5, 43, 6), 'levels': 3, 'ui': 76}`
- `{'tag': 'fuel', 'step': 4, 'action': 2, 'cursor': (7, 2), 'mover': (39, 10, 43, 11), 'levels': 3, 'ui': 74}`
- `{'tag': 'fuel', 'step': 5, 'action': 3, 'cursor': (6, 2), 'mover': (34, 10, 38, 11), 'levels': 3, 'ui': 72}`
- `{'tag': 'fuel', 'step': 6, 'action': 2, 'cursor': (6, 3), 'mover': (34, 15, 38, 16), 'levels': 3, 'ui': 70}`
- `{'tag': 'fuel', 'step': 7, 'action': 3, 'cursor': (5, 3), 'mover': (29, 15, 33, 16), 'levels': 3, 'ui': 68}`
- `{'tag': 'fuel', 'step': 8, 'action': 3, 'cursor': (4, 3), 'mover': (24, 15, 28, 16), 'levels': 3, 'ui': 66}`
- `{'tag': 'fuel', 'step': 9, 'action': 3, 'cursor': (3, 3), 'mover': (19, 15, 23, 16), 'levels': 3, 'ui': 84}`
- `{'tag': 'to84', 'step': 1, 'action': 4, 'cursor': (4, 3), 'mover': (24, 15, 28, 16), 'levels': 3, 'ui': 82}`
- `{'tag': 'to84', 'step': 2, 'action': 4, 'cursor': (5, 3), 'mover': (29, 15, 33, 16), 'levels': 3, 'ui': 80}`
- `{'tag': 'to84', 'step': 3, 'action': 4, 'cursor': (6, 3), 'mover': (34, 15, 38, 16), 'levels': 3, 'ui': 78}`
- `{'tag': 'to84', 'step': 4, 'action': 4, 'cursor': (7, 3), 'mover': (39, 15, 43, 16), 'levels': 3, 'ui': 76}`
- `{'tag': 'to84', 'step': 5, 'action': 2, 'cursor': (7, 4), 'mover': (39, 20, 43, 21), 'levels': 3, 'ui': 74}`
- `{'tag': 'to84', 'step': 6, 'action': 4, 'cursor': (8, 4), 'mover': (44, 20, 48, 21), 'levels': 3, 'ui': 72}`
- `{'tag': 'warp', 'step': 1, 'action': 2, 'cursor': (8, 9), 'mover': (44, 45, 48, 46), 'levels': 3, 'ui': 70}`
- `{'tag': 'land', 'before': (8, 4), 'after': (8, 9), 'snap': {'gate': (1, 1), 'gate_in_walk_u': False, 'gate_in_walk_a': True, 'stamp_c9': 6, 'has_plus': False, 'unlock_cands': [(6, 6)], 'marker': (26, 32, 27, 33), 'c9': 23, 'c12': 12, 'c14': 22, 'c0': 5, 'c8': 14, 'c11': 78, 'ui': 70, 'cursor': (8, 9), 'mover': (44, 45, 48, 46)}}`
- `{'tag': 'to_pu2', 'step': 1, 'action': 1, 'cursor': (8, 8), 'mover': (44, 40, 48, 41), 'levels': 3, 'ui': 68}`
- `{'tag': 'to_pu2', 'step': 2, 'action': 3, 'cursor': (6, 8), 'mover': (34, 40, 38, 41), 'levels': 3, 'ui': 66}`
- `{'tag': 'to_pu2', 'step': 3, 'action': 3, 'cursor': (6, 8), 'mover': (34, 40, 38, 41), 'levels': 3, 'ui': 64}`
- `{'tag': 'to_pu2', 'step': 4, 'action': 2, 'cursor': (6, 9), 'mover': (34, 45, 38, 46), 'levels': 3, 'ui': 62}`
- `{'tag': 'to_pu2', 'step': 5, 'action': 2, 'cursor': (6, 10), 'mover': (34, 50, 38, 51), 'levels': 3, 'ui': 84}`
- `{'tag': 'at_pu2', 'cursor': (6, 10), 'before_c11': 78, 'after_c11': 84, 'before_ui': 70, 'after_ui': 84, 'snap': {'gate': (1, 1), 'gate_in_walk_u': False, 'gate_in_walk_a': True, 'stamp_c9': 6, 'has_plus': False, 'unlock_cands': [(6, 6)], 'marker': (26, 32, 27, 33), 'c9': 23, 'c12': 12, 'c14': 22, 'c0': 5, 'c8': 14, 'c11': 84, 'ui': 84, 'cursor': (6, 10), 'mover': (34, 50, 38, 51)}}`
- `{'tag': 'c8_hits', 'hits': [(10, 12), (11, 12)]}`
- `{'tag': 'b_stamp_plan', 'ok': True, 'info': {'t2': (1, 1), 'fuel_end': 3, 'path_len': 18, 'stamp': (8, 4, 14, 10), 'cursor0': (6, 10)}, 'snap': {'gate': (1, 1), 'gate_in_walk_u': False, 'gate_in_walk_a': True, 'stamp_c9': 6, 'has_plus': False, 'unlock_cands': [(6, 6)], 'marker': (26, 32, 27, 33)}}`
- `{'tag': 'b_stamp_stamp', 'step': 1, 'action': 3, 'cursor': (5, 10), 'mover': (29, 50, 33, 51), 'levels': 3, 'ui': 82}`
- `{'tag': 'b_stamp_stamp', 'step': 2, 'action': 3, 'cursor': (4, 10), 'mover': (24, 50, 28, 51), 'levels': 3, 'ui': 80}`
- `{'tag': 'b_stamp_stamp', 'step': 3, 'action': 1, 'cursor': (4, 9), 'mover': (24, 45, 28, 46), 'levels': 3, 'ui': 78}`
- `{'tag': 'b_stamp_stamp', 'step': 4, 'action': 3, 'cursor': (3, 9), 'mover': (19, 45, 23, 46), 'levels': 3, 'ui': 76}`
- `{'tag': 'b_stamp_stamp', 'step': 5, 'action': 3, 'cursor': (2, 9), 'mover': (14, 45, 18, 46), 'levels': 3, 'ui': 74}`
- `{'tag': 'b_stamp_stamp', 'step': 6, 'action': 1, 'cursor': (2, 8), 'mover': (14, 40, 18, 41), 'levels': 3, 'ui': 72}`
- `{'tag': 'b_stamp_stamp', 'step': 7, 'action': 1, 'cursor': (2, 7), 'mover': (14, 35, 18, 36), 'levels': 3, 'ui': 70}`
- `{'tag': 'b_stamp_stamp', 'step': 8, 'action': 1, 'cursor': (2, 6), 'mover': (14, 30, 18, 31), 'levels': 3, 'ui': 68}`
- `{'tag': 'b_stamp_stamp', 'step': 9, 'action': 1, 'cursor': (2, 5), 'mover': (14, 25, 18, 26), 'levels': 3, 'ui': 66}`
- `{'tag': 'b_stamp_stamp', 'step': 10, 'action': 1, 'cursor': (2, 4), 'mover': (14, 20, 18, 21), 'levels': 3, 'ui': 64}`
- `{'tag': 'b_stamp_stamp', 'step': 11, 'action': 4, 'cursor': (3, 4), 'mover': (19, 20, 23, 21), 'levels': 3, 'ui': 62}`
- `{'tag': 'b_stamp_stamp', 'step': 12, 'action': 4, 'cursor': (4, 4), 'mover': (24, 20, 28, 21), 'levels': 3, 'ui': 60}`
- `{'tag': 'b_stamp_stamp', 'step': 13, 'action': 1, 'cursor': (4, 3), 'mover': (24, 15, 28, 16), 'levels': 3, 'ui': 58}`
- `{'tag': 'b_stamp_stamp', 'step': 14, 'action': 1, 'cursor': (4, 2), 'mover': (24, 10, 28, 11), 'levels': 3, 'ui': 56}`
- `{'tag': 'b_stamp_stamp', 'step': 15, 'action': 1, 'cursor': (4, 1), 'mover': (24, 5, 28, 6), 'levels': 3, 'ui': 54}`
- `{'tag': 'b_stamp_stamp', 'step': 16, 'action': 3, 'cursor': (3, 1), 'mover': (19, 5, 23, 6), 'levels': 3, 'ui': 52}`
- `{'tag': 'b_stamp_stamp', 'step': 17, 'action': 3, 'cursor': (2, 1), 'mover': (14, 5, 18, 6), 'levels': 3, 'ui': 50}`
- `{'tag': 'b_stamp_stamp', 'step': 18, 'action': 3, 'cursor': (2, 1), 'mover': (14, 5, 18, 6), 'levels': 3, 'ui': 50}`
