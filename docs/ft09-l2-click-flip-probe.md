# ft09 L2 点击闭环探针

> 脚本：`tools/ft09_l2_click_flip_probe.py`
> 轨迹：`D:/Projects/longquan/tests/fixtures/ft09_l2_click_flip_trajectory.json`
> 判据：`levels_completed` `1` → `2`

## 结论

**PASS** — 按帧内 0/2/12 图案推导点击（双层 3×3 取并集、共享格只点一次），`levels_completed` 1→2。L2：**0=翻、2=留**；翻转色为 **9→12**（L1 为 9→8）；固定格 color12。

> verdict=`l2_mask_flip_pass`

## 假设

- H1：`(20,14)` 起 5×3 块阵内，上下各一枚 3×3（中心为 0/2/12 图案）
- H2：0=flip、2=keep、12=fixed；翻转落地色为 **9→12**（非 L1 的 9→8）
- H3：两图案目标在共享行一致 → 对绝对块坐标取 **并集** 各点一次
- H4：通关只看 levels 递增

## 推导出的点击

- **upper** instr@[28, 22] macro=`{'0,0': 'flip', '0,1': 'keep', '0,2': 'keep', '1,0': 'flip', '1,1': 'fixed', '1,2': 'flip', '2,0': 'flip', '2,1': 'keep', '2,2': 'flip'}` flips=`[(0, 0), (1, 0), (1, 2), (2, 0), (2, 2)]`
- **lower** instr@[28, 38] macro=`{'0,0': 'flip', '0,1': 'keep', '0,2': 'flip', '1,0': 'keep', '1,1': 'fixed', '1,2': 'keep', '2,0': 'flip', '2,1': 'flip', '2,2': 'keep'}` flips=`[(0, 0), (0, 2), (2, 0), (2, 1)]`

## 轨迹摘要

- step 1 upper block[0, 0] @ [23, 17] lv=1 diff={'9->12': 36, '12->11': 2}
- step 2 upper block[1, 0] @ [23, 25] lv=1 diff={'9->12': 36, '12->11': 2}
- step 3 upper block[1, 2] @ [39, 25] lv=1 diff={'9->12': 36, '12->11': 2}
- step 4 upper block[2, 0] @ [23, 33] lv=1 diff={'9->12': 36, '12->11': 2}
- step 5 upper block[2, 2] @ [39, 33] lv=1 diff={'9->12': 36, '12->11': 2}
- step 6 lower block[2, 0] @ [23, 49] lv=1 diff={'9->12': 36, '12->11': 2}
- step 7 lower block[2, 1] @ [31, 49] lv=2 diff={'9->12': 36}

## 产物

- `D:/Projects/longquan/tests/fixtures/ft09_l2_click_flip_trajectory.json`

