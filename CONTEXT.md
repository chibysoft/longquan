# 龙泉项目上下文（Context）

> 2026-09-05 · 给 Cursor 的快速入门
> 阅读时间：5 分钟
> **口径**：ls20 = move+match；copy 未验证（见 verify-games.md 第三版）

---

## 一句话定位

龙泉是一个**闭卷会学 agent**：给一个没见过的 ARC-AGI-3 游戏，程序不读源码、不背答案，自己从观测中归纳规则并通关。

---

## 核心设计

- **规则原语（primitives）**：反射、移动、匹配、配对……数量有限，可穷举。
- **规则组合（composition）**：原语的排列组合，数量无限，无法穷举。
- **会学的本质**：在可穷尽的“原语层”上，用组合语法覆盖会爆炸的“组合层”。

已验证：reflect（AR25 L1–L3）。进行中：交互族 move（ls20）线上闭环；match 待任务 A 之后。copy 几何代码在库中但**无真实验证游戏**。

---

## 项目结构

```
longquan/
├── hypotheses/   # 几何原语（reflect 已验证；copy/recolor/translate 未验证）
├── interactive/  # 交互族（ls20 init、move、BFS）
├── tests/        # 含 fixtures/ls20_l1_frame_live.json
├── docs/         # 思想文档 + 施工图 + handoff
└── CONTEXT.md
```

---

## 当前阶段

**关键路径：阶段 1b —— 交互族在 ls20 上坐实（move+match）**

- ✅ ls20 init 适配器（walkable 锚定线上四方向 reach）
- ✅ move 状态机 + BFS（离线单测通过）
- ✅ 任务 A：线上闭环验证——PASS，0px
- ✅ 任务 B：match 通关（H19/H20）——L1 seated clear PASS
- ⏳ ls20 L2+ / 全关——下一步

mate（m0r0）不与 match 并行。细节见 `docs/current-handoff.md`。

---

## 三条红线（任何代码必须遵守）

1. 不读游戏引擎源码（运行时）
2. 不 import 罐头答案
3. 不以“像素看起来对了”当通过——以线上实测为准

---

## 下一步

执行 `docs/current-handoff.md` 任务 A。通过后再谈 match；失败则查 walkable / 坐标系映射。
