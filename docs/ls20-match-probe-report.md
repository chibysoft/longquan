# ls20 match 探路报告（round 5 · H16–H20）

> 2026-09-05 · game_id=`ls20-9607627b`

| 假设 | 裁决 | 要点 |
|------|------|------|
| H16 | **REFUTED** | 直达 shape-gate 再 UP：引擎挡住，levels=0 |
| H17 | **REFUTED** | 仅放开色9、不经 0/1：终点仍停在 (34,15)，levels=0 |
| H18 | INCONCLUSIVE | 无 H16/H17 通关帧可鉴名 |
| **H19** | **SUPPORTED** | 先到色0/1 近邻（携带重叠标记）再进起始形状带 → levels+1 |
| **H20** | **SUPPORTED** | 武装后从 gate UP 进入原色9 禁区，n9↓、levels+1 |

## 通关条件（levels+1）— 已坐实

两段式（仅 ACTION1–4，**不**依赖 ACTION5，**不**背罐头序列）：

1. **武装**：走到携带物与色0/1 标记重叠的 walkable 格（`match.react` → `armed=True`）
2. **盖印**：`walkable` 按 armed 重建（障碍仅色4）→ BFS 到与色5 起始形状块重叠最大的格 → 进入后 `ls20-stamp.done`

线上验证：`python tools/ls20_l1_seated_clear.py` → **PASS levels≥1**（13 步规划）。

## 纪律

- 未把 Lingjing `_LEVEL_ACTIONS` 写入 solver；recording 仅作设计期帧观测
- `match.done` 现依 H19/H20 几何坐实
