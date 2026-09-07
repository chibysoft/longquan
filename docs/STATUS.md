# 龙泉 STATUS：当前状态与下一步

> 2026-09-05 · Longquan 龙泉 · 状态权威文档，跟踪龙泉进度与证据
> **口径（与 verify-games.md 第三版对齐）**：ls20 = move+match；copy 撤回未验证。

---

## 当前状态摘要

- **思想底座闭环（八份）**：从原理到运行时到施工，已完整闭环。
  1. `methodology.md` —— 为什么：规则原语量小可穷尽，组合量大易爆；三层定位
  2. `primitives.md` —— 怎么做：原语接口（score/cover/backproject）+ 选择器
  3. `primitives-taxonomy.md` —— 做哪些：23 原语五族全集（含 E 族交互）
  4. `the-real-mountain.md` —— 真高山是结构归纳，最优解是相对的
  5. `retry-loop.md` —— 怎么活下来：升级重试 + 步数预算 + 锚点分级
  6. `step-budget.md` —— 经济基础：RHAE 平方惩罚，首试1.5×/累计2.5×
  7. `roadmap.md` —— 三站路线
  8. `execution-plan.md` —— 以终为始施工图，五阶段带验收

- **阶段 0 达成**：reflect 原语在 AR25 L1-L3 端到端线上通关（levels=3）。
  - 修复三缺口：可动轴识别（中心洞色0）、遍历所有轴候选+cost排序、横轴识别
  - L2 找到 cost=11 的解，比灵境 M1 的 32 步省 21 步

- **原语全集探路结论（2026-09-05，见 verify-games.md 第三版）**：ARC-AGI-3 是交互式引擎，不是网格变换题。原语全集扩为五族 23 个（新增 E 族）。**唯一坐实的几何原语：reflect→ar25。** copy/recolor/translate 三次假设均被推翻（无主导验证游戏）。**ls20 = move+match**（不是 copy）。当前关键路径 = 交互族坐实。

---

## 路线进度（五阶段，见 execution-plan.md）

| 阶段 | 内容 | 状态 |
|------|------|------|
| 0 | reflect 补全，追平 M1 | ✅ 达成：L1-L3 levels=3 |
| 1a | 选择器（solve_auto） | 部分：代码已有；AR25 自动选对验收未收口 |
| 1b | 交互族坐实（move+match @ ls20） | move✅；L1+L2 seated✅；L3 感知/传送✅；**卡在 L3 武装迁移** |
| 1.5 | 原语库反向验证 | 未开始 |
| 2 | 程序表示（原语序列） | 未开始 |
| 3 | 结构归纳（MDL + 约束求解） | 未开始 |
| 4 | ft09 迁移 + 报告 | ✅ **全关 WIN**；路径B `maskflip` 库通关（见 `docs/structure-induction-ft09.md`） |

---

## 下一步：阶段 1b 交互族坐实（唯一优先）

顺序钉死（见 `docs/current-handoff.md`）：

1. **任务 A**：ls20 move 线上闭环——✅ PASS
2. **任务 B**：match — **H19/H20 坐实**；L1 seated PASS
3. **任务 C**：L2+ — **L2 seated PASS**（H21 能量 + H23 仪式）；`tools/ls20_seated_clear.py`
4. **下一步**：L3 武装可证伪假设轮（H23 未跨关）；勿再盲调规划器；禁止罐头序列
5. 工程加速可选：`D:\Projects\Prime Agent`（DeepSeek）只做探针/跑分，不写答案表进 solver
6. mate（m0r0）**不并行**

几何族 copy 代码可留库，标注「未验证」；不以 ls20 当 copy 的验证游戏。

---

## 环境备忘

- FUSE 挂载写中文会损坏（null 字节）；代码用纯 ASCII，改文件用「删旧+Write重建」
- git 操作在自己 Windows 上做（本 VM git init/commit 会写坏 .git）
- 线上验证用 `three.arcprize.org`；RHAE 公式 `(人类基准/AI步数)²`，RESET 计步
