# 当前断点交接（Handoff）

> 2026-09-06 · 给 Cursor 接手的当前状态快照，不是设计文档。
> **口径（与 verify-games.md 第三版对齐）**：ls20 = move+match；copy 撤回未验证。

---

## 当前进度

**关键路径：阶段 1b —— L1+L2 seated 线上 PASS；停在 L3 感知。**

```
① 交互族坐实（ls20 = move+match） ← 我们现在在这里
   ├── move / 任务 A              ← ✅
   ├── match 通关（H19/H20/H21/H23）← ✅ L1+L2 seated clear PASS
   └── ls20 L3–L7 / 全关          ← ⏳ L3 感知待修
② 阶段1.5：反向验证
③ 阶段2：程序表示
④ 阶段3：结构归纳
⑤ 阶段4：ft09 迁移
```

mate（m0r0）**不并行**。

---

## 新坐实（L2，2026-09-06）

| 代号 | 事实 |
|------|------|
| **过关陋帧** | levels+1 响应帧仍是旧关布局；下一 ACTION 才切到新关（sync 用 ACTION1） |
| **H21 能量** | playfield 色11 小团是补给；耗尽约 21 步后软重置回出生点（6 层全11 闪帧） |
| **H23 武装仪式** | L2+：接触 marker 后必须再走 UP→DOWN→DOWN→UP（同列上下扫），否则不能进 stamp 色9 格 |
| **盖印阈值** | mover 与 stamp 重叠 **≥10**（整块 5×2），仅擦边不够 |
| **规划器** | `tools/ls20_seated_clear.py`：能量感知 BFS + 强制仪式；**禁止罐头表** |

复跑：`python tools/ls20_seated_clear.py --max-levels 7`  
报告：`docs/ls20-seated-clear-report.md`  
L3 首帧：`tests/fixtures/ls20_l3_frame_live.json`

---

## L3 阻塞（下一步）

- 色12 不止一块：真实可动块仍是 **5×2 / 10px**（`locate_mover` 已改优先匹配）
- marker 用小连通域（约 5 格、非扁条）；L3 候选 `(50,11)-(52,13)`
- stamp / walkable / 通关是否仍 H19–H23 未坐实；当前 `plan_two_phase` 在 armed 段 BFS 失败
- 勿把 recording 罐头动作写入 solver

---

## 已确认的事实（L1 基线，仍有效）

1. **步长 = 5px**；可动块色12；障碍初值 {4,9}；武装后障碍仅 {4}
2. **H19**：携带物与色0/1 重叠 = 武装；**H20**：武装后进入 stamp → levels+1（无需 ACTION5）
3. 真实 L1 帧：`tests/fixtures/ls20_l1_frame_live.json`

---

## 三点决策（仍有效）

match = 人定假设 + 线上证伪；先 ls20 后 mate；不写罐头。
