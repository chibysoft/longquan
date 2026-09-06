# 帧样本固化（fixtures）

> 推进核输出 · 2026-09-05 · ls20 真实帧样本 + 规则逆向结论
> 来源：官方线上回放 recording（**设计期参考，不是运行时输入**，运行时只能吃帧）

---

## 重要更正（2026-09-05 第三版）

本 fixture 最初是为「copy 原语」固化的，但推进核随后深挖 ls20 源码，**推翻了「ls20 = copy 主导」的判断**——ls20 的真实规则是 **move + match（移动光标 + 形状/颜色/旋转匹配 + 盖印）**，不是「复制 N 份」。参见 `docs/verify-games.md`。

因此：

- **帧样本本身仍有价值**（ls20 是交互族 move/match 的验证候选），保留。
- **「色 11 = 目标格」是错的**：色 11 是**步数进度条 UI**（剩余步数指示），不是目标。真正的目标槽是色 5 的 `rjlbuycveu`（tag `rjlbuycveu`）。
- copy 原语已**撤回「未验证」**（与 recolor/translate 并列）。下面的「copy 接口规格」仅作几何语义参考，不再是「可派活」的任务。

---

## 文件

- `ls20_l1_frame.json` —— ls20（游戏 id `ls20-9607627b`）L1 起始帧，64×64 原始像素帧。
  - 结构：`{"meta": {...}, "l1_reset": [[...64 行...]]}`，`l1_reset` 是 64×64 的 int 数组。
  - **更正（2026-09-05）**：ls20 **不是**「3×3 像素 cell / 21×21 棋盘」。那是从 AR25 错误继承的假设。ls20 是**像素级房间导航游戏**——起始形状 7×7、光标 3×3、目标槽 5×5、中岛障碍 10×15、地板 40×25，都不是 3 的倍数。完整分析见 `docs/ls20-frame-semantics.md`。
  - **不能**用 `perceive.py` 吃（它是 AR25 特化，色语义完全不同）。ls20 的 init 需新写。

---

## ls20 规则（move + match 主导，推进核源码逆向结论）

ls20 是「移动 + 匹配」游戏，**主导原语是 move + match**（交互族），不是 copy：

1. 玩家携带一个「**起始形状**」（由 `data` 的 StartShape/StartColor/StartRotation 指定，sprite 模板可旋转、可换色）。
2. 场景里有 1 个（或少数几个）「**目标槽**」（tag `rjlbuycveu`，色 5 的 5×5 块），每个目标要求「某个形状 + 某个颜色 + 某个旋转」（由 GoalShape/GoalColor/GoalRotation 指定）。
3. 玩家移动光标（ACTION1-4 = 上下左右）到目标槽：**若当前携带的形状/颜色/旋转匹配目标要求，就「盖印」到目标槽**（目标槽被消除，视为完成）。
4. 所有目标槽完成 → 过关（levels_completed 递增）。
5. 有步数上限（StepCounter=42），底部有色 11 步数进度条 UI 显示剩余步数，超时判负。

**关键区分**：ls20 的「盖印」是「移动 + 匹配 + 单次放置」，不是「复制 N 份」。这决定了它的主导原语是 move/match（E 族），不是 copy（B 族拓扑）。

---

## 颜色语义（L1 帧，推进核标定，第三版已更正色 11）

| 颜色 | 含义 | L1 帧中数量 |
|------|------|------------|
| 3 | 地板背景 + 步数进度条「剩余段」 | 112 |
| 4 | 墙壁/边框背景 | 278 |
| 5 | **起始形状 + 玩家光标 + 目标槽底衬(rjlbuycveu) + 调色板** | 32 |
| 9 | GoalColor（目标色标记） | 5 |
| 11 | **步数进度条「已用段」UI（非目标）** | 82（42段×2px） |
| 8 | 生命值指示（剩余次数） | 12 |
| 12 | UI 标记 | 10 |

**注意**：色 5 混杂了多样东西（起始形状、玩家光标、目标槽底衬、调色板），**拆形状是推进核的认知活**，不是原语实现的体力活。

---

## 交互族 move/match 的接口语义（已设计，认知活）

ls20 的主导是 move + match，这属于 E 族交互原语。它们的接口**已设计为「状态机五件套」**（`init/actions/step/done` + 复用 `score`），见 `docs/primitive-interface-interactive.md`——因为交互族的规则是「状态×动作→新状态」的转移（移动、匹配消除、盖印），不能套 reflect/copy 的「一次性几何覆盖」契约。

WorldState 字段的精确化、action 类型、sequence/gravity/waypoint 是否要新状态字段，仍是推进核的认知活，**不在公司团队的体力活范围**。实现时不要自己拍板这些。

---

## （已撤回）copy 原语接口规格 —— 仅作几何语义参考

> 以下 copy 的 cover/backproject 几何语义是**正确且通用**的（「复制 N 份」的几何覆盖本身没错），但它不再有「ls20」这个验证游戏。留作参考，不构成可派活任务。

### cover(rel_cells, pos, param) -> set

```python
# 源形状 rel_cells 放在 pos，param = 完整副本偏移列表。
# 返回「源自身 + 所有副本」覆盖的棋盘格并集（与 reflect 的「源+镜像」同一契约）。
bx, by = pos
covered = {(bx + cx, by + cy) for cx, cy in rel_cells}
for dx, dy in param:
    covered |= {(bx + dx + cx, by + dy + cy) for cx, cy in rel_cells}
return covered
```

### backproject(rel_cells, targets, param, w, h) -> list

```python
# 给定目标格集合 + 偏移列表，反推源 bbox 原点候选（源或任一副本能落到目标）。
# 过滤出界，排序返回。
```

---

## 红线提醒

见 `docs/dev-task-spec.md` §1 三条红线：

- **不得读引擎源码作运行时输入**：这个帧是「设计期参考」，运行时代码只能吃帧。
- **几何覆盖 ≠ 通关**：通关以「回放 levels 递增」为准。
- **不硬凑验证游戏**：ls20 被更正为 move+match 后，不要再拿它当 copy 的验证游戏。
