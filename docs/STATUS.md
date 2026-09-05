# 龙泉 STATUS：当前状态与下一步

> 2026-09-05 · Longquan 龙泉 · 状态权威文档，跟踪龙泉进度与证据

---

## 当前状态摘要

- **思想底座闭环（六份）**：从原理到运行时，已完整闭环。
  1. `methodology.md` —— 为什么：规则原语量小可穷尽，组合量大易爆；三层定位 L0/L1/L2
  2. `primitives.md` —— 怎么做：原语接口（score/cover/backproject）+ 选择器工作流
  3. `primitives-taxonomy.md` —— 做哪些：17 原语全集（几何/拓扑/颜色/对称四族）
  4. `the-real-mountain.md` —— 真高山是结构归纳，最优解是相对的（DSL内最短可证明，真规则不可证明）
  5. `retry-loop.md` —— 怎么活下来：升级重试 + 步数预算（RHAE平方惩罚）+ 锚点分级
  6. `roadmap.md` —— 三站路线（单原语做扎实 → 原语库成形 → 结构归纳）

- **代码骨架已立**：perceive/search/motion/loop/memory + hypotheses（mirror），L1 能力等价灵境 M1（线上验证 levels=1）。

- **待追平**：L2/L3 三缺口（轴可动+负坐标、横轴真实帧识别、反射镜像干扰）。

---

## 路线进度（三站）

| 站 | 内容 | 状态 |
|----|------|------|
| 站 1 | 单原语做扎实（reflect 补全，追平 L1-L3） | 进行中：三缺口待修 |
| 站 2 | 原语库成形（选择器 + 第一批原语 reflect/translate/recolor/copy） | 未开始 |
| 站 3 | 结构归纳（程序合成：MDL + 约束求解，迁移 ft09） | 未开始 |

---

## 下一步：站 2 选择器 + 原语库第一批

按 roadmap 和 primitives.md 的落地清单：

1. `hypotheses/mirror.py` → 改名 `reflect.py`，接口对齐 score/cover/backproject 三函数
2. 补「原语库注册表」`hypotheses/registry.py`
3. loop.py 加「原语选择器」：遍历 registry，按 score 排序逐个试
4. reflect 原语补全「轴可动 + 负坐标」（反射原语的固有属性）

**依赖关系**：站 2 依赖站 1 完成（reflect 先做扎实，才有资格谈选择器）。

---

## 环境备忘

- FUSE 挂载写中文会损坏（null 字节）；代码用纯 ASCII，改文件用「删旧+Write重建」
- git 操作在自己 Windows 上做（本 VM git init/commit 会写坏 .git）
- 线上验证用 `three.arcprize.org`；RHAE 公式 `(人类基准/AI步数)²`，RESET 计步
