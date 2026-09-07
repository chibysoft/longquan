# ft09 L4 点击闭环探针

> 脚本：`tools/ft09_l4_click_flip_probe.py`
> 真帧：`D:/Projects/longquan/tests/fixtures/ft09_l4_frame_live.json`
> 轨迹：`D:/Projects/longquan/tests/fixtures/ft09_l4_click_flip_trajectory.json`
> 判据：`levels_completed` `3` → `4`

## 结论

**PASS** — L4 三态 mask-flip：`0→fixed色`，`2→8`，点击沿 `9→8→12→9` 循环到位；`levels` 3→4；总点击 21。

> verdict=`l4_ternary_mask_flip_pass`

## L4 坐实规则

1. **右上图例** `9 / 8 / 12`（各 4×4）= 点击循环次序。
2. **宏格语义**：`0 → 该图案 fixed 色`；`2 → 8`。
3. **多图案**：三枚 3×3（fixed 12 / 9 / 12）目标在共享格上一致；按格点击 0–2 次到位。
4. 二进制「只点一次 9→8」**不够**；此前失败原因在此。

## 帧摘要

- hist: `{4: 3228, 9: 668, 8: 16, 12: 87, 2: 64, 0: 32, 11: 1}`
- patches: 3
- need: `{'12,14': 1, '20,14': 2, '28,14': 1, '12,22': 1, '28,22': 1, '12,30': 1, '20,30': 2, '28,30': 1, '44,14': 1, '44,22': 1, '36,30': 1, '20,38': 1, '36,38': 1, '20,46': 2, '28,46': 2, '36,46': 2}`

## 轨迹

- step 1 block=[12, 14] 9→8 (tgt 8) lv=3
- step 2 block=[20, 14] 9→8 (tgt 12) lv=3
- step 3 block=[20, 14] 8→12 (tgt 12) lv=3
- step 4 block=[28, 14] 9→8 (tgt 8) lv=3
- step 5 block=[44, 14] 9→8 (tgt 8) lv=3
- step 6 block=[12, 22] 9→8 (tgt 8) lv=3
- step 7 block=[28, 22] 9→8 (tgt 8) lv=3
- step 8 block=[44, 22] 9→8 (tgt 8) lv=3
- step 9 block=[12, 30] 9→8 (tgt 8) lv=3
- step 10 block=[20, 30] 9→8 (tgt 12) lv=3
- step 11 block=[20, 30] 8→12 (tgt 12) lv=3
- step 12 block=[28, 30] 9→8 (tgt 8) lv=3
- step 13 block=[36, 30] 9→8 (tgt 8) lv=3
- step 14 block=[20, 38] 9→8 (tgt 8) lv=3
- step 15 block=[36, 38] 9→8 (tgt 8) lv=3
- step 16 block=[20, 46] 9→8 (tgt 12) lv=3
- step 17 block=[20, 46] 8→12 (tgt 12) lv=3
- step 18 block=[28, 46] 9→8 (tgt 12) lv=3
- step 19 block=[28, 46] 8→12 (tgt 12) lv=3
- step 20 block=[36, 46] 9→8 (tgt 12) lv=3
- step 21 block=[36, 46] 8→12 (tgt 12) lv=4

## 产物

- `D:/Projects/longquan/tests/fixtures/ft09_l4_frame_live.json`
- `D:/Projects/longquan/tests/fixtures/ft09_l4_click_flip_trajectory.json`

