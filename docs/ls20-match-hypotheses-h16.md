# ls20 match 假设 H16–H18（第五轮 · 新假设族）

> 2026-09-05 · **不再围着 ACTION5/6 打转**  
> 设计期依据：官方 recording 帧序列（非罐头动作入库；action_input 未记录真实 id，只读帧）  
> 脚本：`python tools/ls20_match_probe.py --round 5`

---

## 设计期观测（recording 帧，非运行时输入）

L1 `0→1` 时色12 从 `(34,15)` 步进到 `(34,10)`（进入顶区起始形状），同时 playfield `n9` 45→39、`n5` 略降；**色0/1 仍在**；全程无证据表明需要 ACTION5。

这与当前 `ls20` walkable（障碍含色9）冲突：`(6,2)` 因 footprint 含起始形状色9 被判不可走，但线上帧显示光标进入了该像素带。

---

## H16 — 从 `(6,3)` 再向上一步可进入「色9 禁区」并 levels+1

**陈述**：在已坐实坐标系下走到色5 主块近邻 walkable 格后，再发 ACTION1（上）。若色12 的像素 y 继续减小（进入原 walkable 禁区）且 `levels_completed` +1，则「色9 障碍」模型过严，且过关=走入起始形状带。

**支持**：该步后 levels≥1 且 bbox12.y 小于出发时。  
**推翻**：光标不动（撞墙）或动了但 levels 仍 0。

---

## H17 — 障碍仅色4：放开色9 后规划进入起始形状重叠格可通关

**陈述**：临时用 `obstacles={4}` 重建 walkable，BFS 到「色12 预测 bbox 与起始形状色5 块重叠面积最大」的逻辑格，仅 ACTION1–4 执行。期望 levels+1。

**支持**：levels+1。  
**推翻**：路径执行完 levels 仍 0（或无法走进重叠格）。

---

## H18 — 过关签名：进入起始形状后色9 净减少且 levels+1（可写 done）

**陈述**：若 H16/H17 支持，则 match 过关的可观测签名为：`levels+1` 且（相对进入前）起始形状区域内色9 像素减少。用于写 `done`/`step` 的坐实标准，而不是背动作序列。

**支持**：H16 或 H17 的通关帧满足该签名。  
**推翻**：通关帧不出现色9 减少（则签名要改，仍可有 levels+1）。

---

## 纪律

- **不**把 Lingjing `_LEVEL_ACTIONS` 罐头序列写进 `match` / solver。  
- recording / 罐头只用于提出可证伪几何假设。  
- 仅当 levels+1 被线上坐实，才改 `done`。

---

## 第五轮续：H19/H20 坐实

| 假设 | 裁决 |
|------|------|
| H16 / H17 | REFUTED（缺 0/1 武装则无法进入形状带） |
| **H19 / H20** | **SUPPORTED** |

`match.done` / `react` / `build_walkable(armed=)` 已落地；`tools/ls20_l1_seated_clear.py` 线上 PASS。
