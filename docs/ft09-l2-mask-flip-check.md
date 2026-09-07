# ft09 L2 mask-flip 泛化检查

> 脚本：`tools/ft09_l2_frame_grab.py`
> levels_completed = `1`（L1 已过，真 L2 帧）
> available_actions = `[6]`
> ACTION1 sync pixel-diff from stale post-clear = `3556`

## 结论

**FAIL（L1 mask-flip 不能直接锁死）** — 过关后需 ACTION1 sync 才拿到真 L2。L2 仍是 ACTION6 + 含 0/2 的压缩图案，但：（1）布局从双 3×3 变为约 `(20,14)` 起的 **5×3** 块阵；（2）图案中心“固定格”从 color**8** 换成 color**12**；（3）开局无 color8 已翻转块。同族机制，**非** L1 坐标/字母表的 drop-in。

> verdict=`layout_encoding_migrated`

## 操作发现

- L1 通关当帧仍是**已解 L1**（中部 9→8 残留，0/2 图案未换）。
- 必须再发一次 **ACTION1**（即使 available_actions 仍只列 `[6]`）才切入真 L2。
- 与 ls20「过关陋帧 + sync ACTION1」同型。

## L2 帧摘要

- hist: `{4: 3460, 9: 484, 12: 86, 0: 36, 2: 28, 11: 2}`
- n0/n2/n8/n9/n12 = 36/28/0/484/86
- UI bar: `{'n12': 62, 'n11': 2, 'row_hist': {12: 62, 11: 2}}`
- 5×3 block majority @ (20,14): `[[9, 9, 9], [9, 0, 9], [9, 9, 9], [9, 0, 9], [9, 9, 9]]`
- instr patches: 2

- instr[0] origin=`[28, 22]` hist=`{0: 20, 2: 12, 12: 4}` macro=`{'0,0': '0', '0,1': '2', '0,2': '2', '1,0': '0', '1,1': '12', '1,2': '0', '2,0': '0', '2,1': '2', '2,2': '0'}`
- instr[1] origin=`[28, 38]` hist=`{0: 16, 2: 16, 12: 4}` macro=`{'0,0': '0', '0,1': '2', '0,2': '0', '1,0': '2', '1,1': '12', '1,2': '2', '2,0': '0', '2,1': '0', '2,2': '2'}`

## 与 L1 对照

| 项 | L1 | L2（真帧） |
|----|----|------------|
| 动作 | ACTION6 | ACTION6 |
| 背景主色 | 5 | 4 |
| 布局 | 左示例 3×3 + 中谜题 3×3 @ (36,36) | 5×3 块阵 @ ~(20,14)，两枚 0/2 图案在中列 |
| 图案字母 | 0 / 2 / **8** | 0 / 2 / **12** |
| 开局 color8 | 有（已翻示例） | **0** |
| 底栏 UI | color12 | color12（含少量 11） |

## 对 mask-flip 的裁决

- **不能**把 L1 的「读 (44,44) 的 0/2/8 → 点中部 3×3 → 9变8」直接固化为全 ft09 solver。
- **L2 闭环已 PASS**（见 `docs/ft09-l2-click-flip-probe.md`）：0=翻 / 2=留仍成立；落地色 **9→12**；双层 3×3 图案并集、共享格只点一次 → levels 1→2。
- 工作假说升级为：同族 mask-flip，**网格原点 / 翻后色 / 固定色 / 谜题层数** 从帧内重解析。

## 产物

- fixture: `D:/Projects/longquan/tests/fixtures/ft09_l2_frame_live.json`
- L2 闭环：`tools/ft09_l2_click_flip_probe.py` · `tests/fixtures/ft09_l2_click_flip_trajectory.json`

