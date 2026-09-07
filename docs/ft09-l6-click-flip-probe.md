# ft09 L6 点击闭环探针

> 脚本：`tools/ft09_l6_click_flip_probe.py`
> 真帧：`D:/Projects/longquan/tests/fixtures/ft09_l6_frame_live.json`
> 轨迹：`D:/Projects/longquan/tests/fixtures/ft09_l6_click_flip_trajectory.json`
> 判据：`levels_completed` `5` → `6`

## 结论

**PASS** — L6：pip 砖 `11↔14` + 北邻耦合 XOR；目标 `0→fixed`/`2→other`；GF(2) 求解；`levels` 5→6；点击 13。  
**且** `win_levels=6` → 本关通关即 **ft09 全关 WIN**（无 L7）。

> verdict=`l6_north_couple_gf2_pass`（全关见 `docs/ft09-full-clear-report.md`）

## L6 坐实规则

1. 图例 `11 / 14`：pip 砖（主体 11/14 + 顶中色6 标记）二元切换；色6 保留。
2. **北邻耦合**：点击翻转自身；若正北 `ay-GAP` 也是 pip 砖，则一并翻转。
3. 宏格 `{0,2,3,14}`；**3=跳过**；本关 fixed 均为 14。
4. 目标（L4 二元化）：**`0→fixed`，`2→other(11)`**。
5. 多图案一致；在北邻耦合下 **GF(2)** 求解点击集。
6. 只认 `levels_completed`。

## 帧摘要

- hist: `{4: 3064, 11: 720, 14: 32, 6: 88, 3: 32, 2: 40, 0: 56, 12: 64}`
- legend: `[{'x0': 60, 'y0': 0, 'color': 11}, {'x0': 60, 'y0': 4, 'color': 14}]`
- tiles: 22
- plan: `[[4, 6], [4, 14], [20, 14], [36, 14], [12, 22], [20, 22], [12, 30], [28, 30], [36, 30], [44, 30], [20, 38], [44, 38], [52, 38]]`

- patch[0] origin=`[12, 6]` fixed=`14` macro=`{'0,0': 3, '0,1': 3, '0,2': 3, '1,0': 2, '1,1': 14, '1,2': 3, '2,0': 0, '2,1': 0, '2,2': 2}`
- patch[1] origin=`[36, 22]` fixed=`14` macro=`{'0,0': 2, '0,1': 0, '0,2': 2, '1,0': 0, '1,1': 14, '1,2': 0, '2,0': 0, '2,1': 0, '2,2': 2}`
- patch[2] origin=`[20, 30]` fixed=`14` macro=`{'0,0': 2, '0,1': 0, '0,2': 0, '1,0': 0, '1,1': 14, '1,2': 0, '2,0': 2, '2,1': 0, '2,2': 2}`
- patch[3] origin=`[44, 46]` fixed=`14` macro=`{'0,0': 2, '0,1': 0, '0,2': 0, '1,0': 3, '1,1': 14, '1,2': 2, '2,0': 3, '2,1': 3, '2,2': 3}`

## 轨迹

- step 1 block=[4, 6] 11→14 lv=5
- step 2 block=[4, 14] 11→14 lv=5
- step 3 block=[20, 14] 11→14 lv=5
- step 4 block=[36, 14] 11→14 lv=5
- step 5 block=[12, 22] 11→14 lv=5
- step 6 block=[20, 22] 11→14 lv=5
- step 7 block=[12, 30] 11→14 lv=5
- step 8 block=[28, 30] 11→14 lv=5
- step 9 block=[36, 30] 11→14 lv=5
- step 10 block=[44, 30] 11→14 lv=5
- step 11 block=[20, 38] 11→14 lv=5
- step 12 block=[44, 38] 11→14 lv=5
- step 13 block=[52, 38] 11→14 lv=6

## 产物

- `D:/Projects/longquan/tests/fixtures/ft09_l6_frame_live.json`
- `D:/Projects/longquan/tests/fixtures/ft09_l6_click_flip_trajectory.json`

