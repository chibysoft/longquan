# ft09 L3 点击闭环探针

> 脚本：`tools/ft09_l3_click_flip_probe.py`
> 真帧：`D:/Projects/longquan/tests/fixtures/ft09_l3_frame_live.json`
> 轨迹：`D:/Projects/longquan/tests/fixtures/ft09_l3_click_flip_trajectory.json`
> 判据：`levels_completed` `2` → `3`

## 结论

**PASS** — L3 发现 4 枚图案，极性感知并集 14 点，`levels` 2→3。 base=`8` flip_to=`12`；fixed==flip_to 时 0=翻；fixed==base 时 **2=翻（极性反转）**。

> verdict=`l3_mask_flip_pass`

## L3 新坐实（相对 L1/L2）

| 项 | L1 | L2 | L3 |
|----|----|----|----|
| base（未翻） | 9 | 9 | **8** |
| flip_to | 8 | 12 | **12** |
| 图案数 | 1（中谜题） | 2（上下） | **4**（十字） |
| 极性 | 恒 0=翻 | 恒 0=翻 | **fixed==base 时反转** |

## L3 帧摘要

- hist: `{4: 3028, 8: 852, 12: 87, 0: 72, 2: 56, 11: 1}`
- base/flip_to = `8` / `12`
- plan_n = `14`

- patch[0] origin=`[28, 12]` fixed=`12` polarity=`normal` macro=`{'0,0': '0', '0,1': '0', '0,2': '0', '1,0': '0', '1,1': 'fixed', '1,2': '2', '2,0': '2', '2,1': '0', '2,2': '2'}`
- patch[1] origin=`[20, 28]` fixed=`8` polarity=`inverted` macro=`{'0,0': '2', '0,1': '0', '0,2': '2', '1,0': '2', '1,1': 'fixed', '1,2': '0', '2,0': '0', '2,1': '0', '2,2': '2'}`
- patch[2] origin=`[36, 28]` fixed=`8` polarity=`inverted` macro=`{'0,0': '2', '0,1': '0', '0,2': '0', '1,0': '0', '1,1': 'fixed', '1,2': '2', '2,0': '2', '2,1': '0', '2,2': '2'}`
- patch[3] origin=`[28, 44]` fixed=`12` polarity=`normal` macro=`{'0,0': '2', '0,1': '0', '0,2': '2', '1,0': '0', '1,1': 'fixed', '1,2': '2', '2,0': '0', '2,1': '0', '2,2': '0'}`

## 轨迹

- step 1 @[23, 7] block=[20, 4] pol=normal lv=2 diff={'8->12': 36}
- step 2 @[31, 7] block=[28, 4] pol=normal lv=2 diff={'8->12': 36, '12->11': 1}
- step 3 @[39, 7] block=[36, 4] pol=normal lv=2 diff={'8->12': 36, '12->11': 1}
- step 4 @[23, 15] block=[20, 12] pol=normal lv=2 diff={'8->12': 36}
- step 5 @[15, 23] block=[12, 20] pol=inverted lv=2 diff={'8->12': 36, '12->11': 1}
- step 6 @[31, 23] block=[28, 20] pol=normal lv=2 diff={'8->12': 36, '12->11': 1}
- step 7 @[15, 31] block=[12, 28] pol=inverted lv=2 diff={'8->12': 36}
- step 8 @[47, 31] block=[44, 28] pol=inverted lv=2 diff={'8->12': 36, '12->11': 1}
- step 9 @[31, 39] block=[28, 36] pol=inverted lv=2 diff={'8->12': 36, '12->11': 1}
- step 10 @[47, 39] block=[44, 36] pol=inverted lv=2 diff={'8->12': 36}
- step 11 @[23, 47] block=[20, 44] pol=normal lv=2 diff={'8->12': 36, '12->11': 1}
- step 12 @[23, 55] block=[20, 52] pol=normal lv=2 diff={'8->12': 36, '12->11': 1}
- step 13 @[31, 55] block=[28, 52] pol=normal lv=2 diff={'8->12': 36}
- step 14 @[39, 55] block=[36, 52] pol=normal lv=3 diff={'8->12': 36}

## 产物

- `D:/Projects/longquan/tests/fixtures/ft09_l3_frame_live.json`
- `D:/Projects/longquan/tests/fixtures/ft09_l3_click_flip_trajectory.json`

