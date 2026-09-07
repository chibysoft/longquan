# ls20 L3 interact 探针（E1）报告

> 脚本：`tools/ls20_l3_interact_probe.py`
> 性质：设计期探路（最小动作 + 比对 levels），非运行时求解器

---

## 结论

**BLOCKED**

| 项 | 值 |
|----|----|
| contact | `(9, 2)` |
| stamp gate | `(10, 10)` |
| marker | `(50, 11, 52, 13)` |
| stamp | `(53, 49, 59, 55)` |
| fuel0 | 21 |

## 逐步

- `{'step': 0, 'action': 'RESET', 'levels': 2, 'mover': (9, 40, 13, 41), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 96, 'layers': 1}`
- `{'step': 1, 'action': 1, 'levels': 2, 'mover': (9, 35, 13, 36), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 92, 'layers': 1}`
- `{'step': 2, 'action': 1, 'levels': 2, 'mover': (9, 30, 13, 31), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 88, 'layers': 1}`
- `{'step': 3, 'action': 1, 'levels': 2, 'mover': (9, 25, 13, 26), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 84, 'layers': 1}`
- `{'step': 4, 'action': 1, 'levels': 2, 'mover': (9, 20, 13, 21), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 80, 'layers': 1}`
- `{'step': 5, 'action': 1, 'levels': 2, 'mover': (9, 15, 13, 16), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 76, 'layers': 1}`
- `{'step': 6, 'action': 1, 'levels': 2, 'mover': (9, 10, 13, 11), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 72, 'layers': 1}`
- `{'step': 7, 'action': 1, 'levels': 2, 'mover': (9, 5, 13, 6), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 68, 'layers': 17}`
- `{'step': 8, 'action': 3, 'levels': 2, 'mover': (29, 5, 33, 6), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 64, 'layers': 1}`
- `{'step': 9, 'action': 2, 'levels': 2, 'mover': (29, 10, 33, 11), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 60, 'layers': 1}`
- `{'step': 10, 'action': 2, 'levels': 2, 'mover': (29, 15, 33, 16), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 56, 'layers': 1}`
- `{'step': 11, 'action': 4, 'levels': 2, 'mover': (34, 15, 38, 16), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 92, 'layers': 1}`
- `{'step': 12, 'action': 2, 'levels': 2, 'mover': (34, 20, 38, 21), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 88, 'layers': 1}`
- `{'step': 13, 'action': 2, 'levels': 2, 'mover': (34, 25, 38, 26), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 84, 'layers': 1}`
- `{'step': 14, 'action': 4, 'levels': 2, 'mover': (39, 25, 43, 26), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 80, 'layers': 1}`
- `{'step': 15, 'action': 4, 'levels': 2, 'mover': (44, 25, 48, 26), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 76, 'layers': 1}`
- `{'step': 16, 'action': 4, 'levels': 2, 'mover': (49, 25, 53, 26), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 72, 'layers': 1}`
- `{'step': 17, 'action': 4, 'levels': 2, 'mover': (54, 25, 58, 26), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 68, 'layers': 1}`
- `{'step': 18, 'action': 1, 'levels': 2, 'mover': (54, 20, 58, 21), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 64, 'layers': 1}`
- `{'step': 19, 'action': 1, 'levels': 2, 'mover': (54, 15, 58, 16), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 60, 'layers': 1}`
- `{'step': 20, 'action': 3, 'levels': 2, 'mover': (49, 15, 53, 16), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 56, 'layers': 1}`
- `{'step': 21, 'action': 1, 'levels': 2, 'mover': (49, 10, 53, 11), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 52, 'layers': 1}`
- `{'step': 'INTERACT', 'action': 5, 'levels': 2, 'mover': (49, 10, 53, 11), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 52, 'layers': 1}`
- `{'step': 'post1', 'action': 4, 'levels': 2, 'mover': (54, 10, 58, 11), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 48, 'layers': 1}`
- `{'step': 'post2', 'action': 2, 'levels': 2, 'mover': (54, 15, 58, 16), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 44, 'layers': 1}`
- `{'step': 'post3', 'action': 2, 'levels': 2, 'mover': (54, 20, 58, 21), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 40, 'layers': 1}`
- `{'step': 'post4', 'action': 2, 'levels': 2, 'mover': (54, 25, 58, 26), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 36, 'layers': 1}`
- `{'step': 'post5', 'action': 2, 'levels': 2, 'mover': (54, 30, 58, 31), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 32, 'layers': 1}`
- `{'step': 'post6', 'action': 2, 'levels': 2, 'mover': (54, 35, 58, 36), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 28, 'layers': 1}`
- `{'step': 'post7', 'action': 2, 'levels': 2, 'mover': (54, 40, 58, 41), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 24, 'layers': 1}`
- `{'step': 'post8', 'action': 2, 'levels': 2, 'mover': (54, 45, 58, 46), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 20, 'layers': 1}`
- `{'step': 'post9', 'action': 2, 'levels': 2, 'mover': (54, 45, 58, 46), 'second': (30, 48, 31, 48), 'c9': 23, 'c14': 2, 'c11': 20, 'layers': 6}`

## 判读

**BLOCKED — 候选1（interact = 武装机制）证伪，证据决定性。**

三条硬证据：

1. **interact 是纯 no-op**：`frame_changed_keys=[]`。接触格 `(9,2)` 发 ACTION5 后，
   mover / 第二块 / c9=23 / c14=2 / c11=52 / layers **全不变**。interact 在 L3
   连一个像素都不动，更不可能武装。

2. **色9门仍关**：post-interact 走 armed 路径到 `(10,9)`(像素 `(54,45)`)，第 9 脚
   DOWN 试图进 `(10,10)`(像素 `(54,50)`)，mover 卡在 `(54,45)` 不动 —— 色9 依然挡门，
   武装没发生。

3. **撞门 flash**：post9 的 DOWN 被挡时帧 `layers=6`（其余步 layers=1）。这是引擎对
   「撞上色9门」的特殊多层渲染，与软重置（layers 变多且 c11 归零）不同（此处 c11=20
   未归零）。它标记了 `(10,10)` 确实是一道「门」，只是没被 interact 打开。

**排除后剩余候选（见 `docs/ls20_l3_arming_deadlock.md` §5）：**

- ~~候选1：interact 武装~~ ❌ 本轮证伪。
- 候选2：第二块是武装标记，触发非 overlap（相邻 / 色12-色12 接触 / 罩住）。
- 候选3：color14 是武装材料（L3 独有，但几何不可接触）。

**下一步**：候选2 需要解「能量布局」——第二块门 `(5,9)` 距接触点 12 步、接触后燃料
~11 不可达（见 `ls20_l3_energy_topography.md`）。要测候选2，得先找到「满能量抵达下半区」
的路径，或重审补给真实能量值 / 未建模补给。

