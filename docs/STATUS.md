# 龙泉 STATUS：当前状态与下一步

> 2026-09-05 · Longquan 龙泉 · 状态权威文档，跟踪龙泉进度与证据

---

## 当前状态摘要

- **思想底座闭环（八份）**：从原理到运行时到施工，已完整闭环。
  1. `methodology.md` —— 为什么：规则原语量小可穷尽，组合量大易爆；三层定位
  2. `primitives.md` —— 怎么做：原语接口（score/cover/backproject）+ 选择器
  3. `primitives-taxonomy.md` —— 做哪些：17 原语全集
  4. `the-real-mountain.md` —— 真高山是结构归纳，最优解是相对的
  5. `retry-loop.md` —— 怎么活下来：升级重试 + 步数预算 + 锚点分级
  6. `step-budget.md` —— 经济基础：RHAE 平方惩罚，首试1.5×/累计2.5×
  7. `roadmap.md` —— 三站路线
  8. `execution-plan.md` —— 以终为始施工图，五阶段带验收

- **阶段 0 达成**：reflect 原语在 AR25 L1-L3 端到端线上通关（levels=3）。
  - 修复三缺口：可动轴识别（中心洞色0）、遍历所有轴候选+cost排序、横轴识别
  - L2 找到 cost=11 的解，比灵境 M1 的 32 步省 21 步

---

## 路线进度（五阶段，见 execution-plan.md）

| 阶段 | 内容 | 状态 |
|------|------|------|
| 0 | reflect 补全，追平 M1 | ✅ 达成：L1-L3 levels=3 |
| 1 | 4 原语 + 选择器 | 进行中 |
| 2 | 程序表示（原语序列） | 未开始 |
| 3 | 结构归纳（MDL + 约束求解） | 未开始 |
| 4 | ft09 迁移 + 报告 | 未开始 |

---

## 下一步：阶段 1 原语库成形

按 primitives.md 的落地清单：

1. `hypotheses/mirror.py` → 改名 `hypotheses/reflect.py`，接口对齐 score/cover/backproject
2. 补 `hypotheses/translate.py`、`recolor.py`、`copy.py`（第一批其余 3 个）
3. 写 `hypotheses/registry.py`：原语注册表
4. loop 加「原语选择器」：按 score 排序，逐个试，回放淘汰

**验证游戏的选择**（tags 不透露机制，需探路后定）：translate/recolor/copy 各从剩余 22 款里探路一个，用探路结论确定对应验证游戏。reflect 已在 AR25 验证。

---

## 环境备忘

- FUSE 挂载写中文会损坏（null 字节）；代码用纯 ASCII，改文件用「删旧+Write重建」
- git 操作在自己 Windows 上做（本 VM git init/commit 会写坏 .git）
- 线上验证用 `three.arcprize.org`；RHAE 公式 `(人类基准/AI步数)²`，RESET 计步
