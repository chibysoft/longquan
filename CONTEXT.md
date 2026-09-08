# 龙泉项目上下文（Context）

> 2026-09-08 · 给 Cursor 的快速入门
> **口径**：ls20 = move+match；ft09 = toggle；m0r0 = move+mate；copy 未验证

---

## 一句话定位

龙泉是一个**闭卷会学 agent**：给一个没见过的 ARC-AGI-3 游戏，程序不读源码、不背答案，自己从观测中归纳规则并通关。

---

## 核心设计

- **规则原语（primitives）**：反射、移动、匹配、配对……数量有限，可穷举。
- **规则组合（composition）**：原语的排列组合，数量无限，无法穷举。
- **会学的本质**：在可穷尽的“原语层”上，用组合语法覆盖会爆炸的“组合层”。

已验证：reflect（AR25）、move+match（ls20）、toggle（ft09）、move+mate（m0r0）。copy 几何代码在库中但**无真实验证游戏**。

---

## 项目结构

```
longquan/
├── hypotheses/   # 几何原语（reflect 已验证；copy/recolor/translate 未验证）
├── interactive/  # 交互族（ls20 / maskflip / m0r0）
├── tests/        # fixtures + 单测
├── docs/         # 思想文档 + 施工图 + handoff
└── CONTEXT.md
```

---

## 当前阶段

主线五阶段已收口。库外交互族：ls20 / ft09 / m0r0 均 WIN。

**下一步：r11l L3+** —— L1–L2 seated PASS；见 `docs/current-handoff.md`。

---

## 三条红线（任何代码必须遵守）

1. 不读游戏引擎源码（运行时）
2. 不 import 罐头答案
3. 不以“像素看起来对了”当通过——以线上实测为准
