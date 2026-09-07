# 当前断点交接（Handoff）

> 2026-09-07 · 给 Cursor 接手的当前状态快照，不是设计文档。
> **口径（与 verify-games.md 第三版对齐）**：ls20 = move+match；copy 撤回未验证。
> **并行线**：ft09 L1–L4 通关；L4 为三态循环 mask-flip（0→fixed，2→8）。

---

## 当前进度

**关键路径仍是 ls20 L3 武装；ft09 为验收线并行探路。**

```
① 交互族坐实（ls20 = move+match）
   ├── move / 任务 A              ← ✅
   ├── match 通关（H19/H20/H21/H23）← ✅ L1+L2 seated clear PASS
   └── ls20 L3–L7 / 全关          ← ⏳ L3 能走到 stamp 门前，武装未迁移
…
⑤ 阶段4：ft09 迁移               ← ⏳ L1–L4 ✅；L4 三态规则已锁
```

mate（m0r0）**不并行**。

---

## ft09（2026-09-07）

| 项 | 状态 |
|----|------|
| L1 | ✅ base9→8；0=翻；单 3×3 |
| L2 | ✅ base9→12；双层 3×3 并集 |
| L3 | ✅ base8→12；十字 4 图案；fixed==base 极性反转 |
| L4 | ✅ **三态** `9→8→12→9`；宏格 `0→fixed色`、`2→8`；三图案一致；21 点 levels 3→4 |
| 图例 | 右上 4×4 堆叠 9/8/12 = 循环次序 |
| 产物 | `ft09_l4_click_flip_probe.py` · `ft09_l4_frame_live.json` · `ft09_l4_click_flip_trajectory.json` · `docs/ft09-l4-click-flip-probe.md` |

**ft09 下一步**：L5 拉帧+闭环（检验三态规则是否再迁）。

---

## 新坐实（L2 + L3 感知/传送，2026-09-06）

| 代号 | 事实 |
|------|------|
| **过关陋帧** | levels+1 响应帧仍是旧关；下一 ACTION 才切新关（sync ACTION1） |
| **H21 能量** | playfield 色11 补给；约 21 步耗尽软重置 |
| **H23 武装仪式** | **L2 坐实**：接触后 UP→DOWN→DOWN 可进 stamp 色9。**L3 未迁移**：同序列到门前仍被色9挡住 |
| **盖印阈值** | mover 与 stamp 重叠 **≥10** |
| **L3 init** | `locate_mover` 认 5×2；marker 小连通域；勿用全色12 bbox |
| **L3 传送门** | `detect_warps`：顶带+西侧色1 轨 → 入口格任意动作先落到同行段右端再尝试该方向（如 `(1,1)+LEFT → (5,1)`） |
| **规划器** | `tools/ls20_seated_clear.py`：能量 BFS + 强制仪式 + warps；**禁止罐头表** |

复跑：`python tools/ls20_seated_clear.py --max-levels 7`  
L3 帧：`tests/fixtures/ls20_l3_frame_live.json`

---

## L3 阻塞（下一步）

**已排除：**

- init / cursor / marker / stamp 提取（门前 `(10,9)`，下一格 `(10,10)` walk_a=True / walk_u=False）
- move 坐标（L1/L2 偏差 0；L3 传送已建模）
- 能量耗尽（门前仍有 c11，是色9 挡住而非软重置先发生）
- 多种仪式变体（UDD / UDDU / 水平扫 / +ACTION5）均不能进 stamp

**未坐实：**

- L3 的武装条件（H23 几何「上/下扫过」在 L3 上未让引擎放开色9）
- 是否另有 marker / 双标记 / 必须先吃满补给 / 其它触发

**下一步：** 针对 L3 单独开可证伪假设轮（不要再盲调规划器）。

---

## 已确认的事实（L1 基线，仍有效）

1. **步长 = 5px**；可动块色12；障碍初值 {4,9}；武装后障碍仅 {4}
2. **H19/H20**：L1 接触即武装 → stamp
3. 真实 L1 帧：`tests/fixtures/ls20_l1_frame_live.json`

---

## 三点决策（仍有效）

闭卷；不读引擎源码作运行时输入；不 import 罐头答案表。
