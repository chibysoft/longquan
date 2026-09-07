# ft09 全关闭环（L1–L6 WIN）

> 2026-09-07  
> 判据：`levels_completed == win_levels == 6` 且 `state == WIN`  
> 脚本链：`tools/ft09_l{1..6}_*_probe.py`；爬升入口 `climb_to_level`（L5 模块）+ `clear_l6`

## 结论

**PASS / 全关** — ft09 共 6 关（API `win_levels=6`）。L6 最后一击后 `levels_completed=6`、`state=WIN`；此后 ACTION 返回 `GAME_NOT_STARTED_ERROR`，需 RESET 重开。无 L7。

> verdict=`ft09_full_clear_win_levels_6`

## 分关坐实摘要

| 关 | levels | 机制要点 | 点击量（本关） |
|----|--------|----------|----------------|
| L1 | 0→1 | base9→8；0=翻 | 4 |
| L2 | 1→2 | base9→12；双图案并集 | 7 |
| L3 | 2→3 | base8→12；fixed==base 极性反转 | 14 |
| L4 | 3→4 | 三态 9→8→12；0→fixed、2→8 | 21 |
| L5 | 4→5 | 14↔15；色6 checker 十字 XOR；GF(2) | 21 |
| L6 | 5→6 | pip 砖 11↔14；北邻耦合 XOR；GF(2) | 13 |

共性：宏格 0/2（及后期 3=跳过）编码目标；过关响应是陋帧，下一 ACTION 才切关；**只认 `levels_completed`**（进度条可刷）。

## 全关证据

- 游戏元数据：`win_levels=6`；`baseline_actions=[43,12,23,28,65,37]`（六关）
- L6 终步响应：`levels_completed=6`，`state=WIN`，`available_actions=[6]`
- 终步后再发 ACTION6/ACTION1 → `GAME_NOT_STARTED_ERROR`

## 复跑

```bash
python tools/ft09_l6_click_flip_probe.py   # 爬升 L1–L5 后清 L6 → WIN
```

## 产物

- `docs/ft09-l1`…`l6-click-flip-probe.md`
- `tests/fixtures/ft09_l*_frame_live.json` / `*_trajectory.json`
- 本报告
