# ft09 L5 点击闭环探针

> 脚本：`tools/ft09_l5_click_flip_probe.py`
> 真帧：`D:/Projects/longquan/tests/fixtures/ft09_l5_frame_live.json`
> 轨迹：`D:/Projects/longquan/tests/fixtures/ft09_l5_click_flip_trajectory.json`
> 判据：`levels_completed` `4` → `4`

## 结论

**FAIL** — L5 二元极性未通关（levels 仍 4）。 patches=8 legend=`[]` hist=`{4: 2632, 14: 1072, 3: 84, 15: 24, 0: 92, 2: 80, 6: 48, 12: 64}`。

> verdict=`l5_binary_polarity_fail`

## L5 坐实 / 候选规则

1. 右上图例 `14 / 15`（x≈56）= 点击二元切换。
2. 指令宏格字母表 `{0,2,3,14,15}`；**3 = 跳过**（背景/越界/邻接字形）。
3. 极性：`fixed==15` → 正常 0=翻；`fixed==14` → 反转 2=翻。
4. 多图案并集，只点 solid-14 一次。

## 帧摘要

- hist: `{4: 2632, 14: 1072, 3: 84, 15: 24, 0: 92, 2: 80, 6: 48, 12: 64}`
- legend: `[]`
- patches: 8
- plan: `[{'ax': 30, 'ay': 4, 'polarity': 'normal'}, {'ax': 14, 'ay': 20, 'polarity': 'normal'}, {'ax': 30, 'ay': 20, 'polarity': 'normal'}, {'ax': 46, 'ay': 20, 'polarity': 'normal'}, {'ax': 14, 'ay': 36, 'polarity': 'normal'}, {'ax': 30, 'ay': 36, 'polarity': 'inverted'}, {'ax': 46, 'ay': 36, 'polarity': 'inverted'}, {'ax': 14, 'ay': 52, 'polarity': 'inverted'}, {'ax': 30, 'ay': 52, 'polarity': 'inverted'}, {'ax': 22, 'ay': 12, 'polarity': 'inverted'}, {'ax': 22, 'ay': 28, 'polarity': 'inverted'}, {'ax': 38, 'ay': 44, 'polarity': 'inverted'}]`

- patch[0] origin=`[14, 4]` fixed=`14` macro=`{'0,0': 3, '0,1': 3, '0,2': 3, '1,0': 3, '1,1': 14, '1,2': 0, '2,0': 3, '2,1': 0, '2,2': 2}`
- patch[1] origin=`[38, 12]` fixed=`15` macro=`{'0,0': 0, '0,1': 3, '0,2': 3, '1,0': 2, '1,1': 15, '1,2': 3, '2,0': 0, '2,1': 2, '2,2': 0}`
- patch[2] origin=`[6, 28]` fixed=`15` macro=`{'0,0': 3, '0,1': 2, '0,2': 0, '1,0': 3, '1,1': 15, '1,2': 2, '2,0': 3, '2,1': 2, '2,2': 0}`
- patch[3] origin=`[38, 28]` fixed=`14` macro=`{'0,0': 2, '0,1': 0, '0,2': 2, '1,0': 0, '1,1': 14, '1,2': 0, '2,0': 2, '2,1': 0, '2,2': 2}`
- patch[4] origin=`[54, 28]` fixed=`14` macro=`{'0,0': 2, '0,1': 0, '0,2': 3, '1,0': 0, '1,1': 14, '1,2': 3, '2,0': 2, '2,1': 0, '2,2': 3}`
- patch[5] origin=`[22, 36]` fixed=`14` macro=`{'0,0': 0, '0,1': 2, '0,2': 0, '1,0': 2, '1,1': 14, '1,2': 2, '2,0': 0, '2,1': 3, '2,2': 0}`
- patch[6] origin=`[22, 44]` fixed=`14` macro=`{'0,0': 2, '0,1': 3, '0,2': 2, '1,0': 0, '1,1': 14, '1,2': 0, '2,0': 2, '2,1': 0, '2,2': 2}`
- patch[7] origin=`[46, 52]` fixed=`14` macro=`{'0,0': 2, '0,1': 0, '0,2': 3, '1,0': 0, '1,1': 14, '1,2': 3, '2,0': 3, '2,1': 3, '2,2': 3}`

## 轨迹

- step 1 block=[30, 4] 14→15 (normal) lv=4
- step 2 block=[14, 20] 14→15 (normal) lv=4
- step 3 block=[30, 20] 14→15 (normal) lv=4
- step 4 block=[46, 20] 14→15 (normal) lv=4
- step 5 block=[14, 36] 14→15 (normal) lv=4
- step 6 block=[30, 36] 14→15 (inverted) lv=4
- step 7 block=[46, 36] 14→15 (inverted) lv=4
- step 8 block=[14, 52] 14→15 (inverted) lv=4
- step 9 block=[30, 52] 14→15 (inverted) lv=4
- step 10 block=[22, 12] 14→15 (inverted) lv=4
- step 11 block=[22, 28] 14→15 (inverted) lv=4
- step 12 block=[38, 44] 14→15 (inverted) lv=4

## 产物

- `D:/Projects/longquan/tests/fixtures/ft09_l5_frame_live.json`
- `D:/Projects/longquan/tests/fixtures/ft09_l5_click_flip_trajectory.json`

