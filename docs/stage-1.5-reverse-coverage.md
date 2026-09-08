# 阶段 1.5：原语库反向覆盖盘点

> 2026-09-08 · execution-plan §3.5  
> **目标**：已解游戏的真规则 → 对照 taxonomy 23 原语；覆盖则进阶段 2，缺口则先补原语。  
> **红线**：不硬凑标签；无主导验证游戏的原语保持「未验证」。

---

## 1. 已解游戏清单（线上 WIN）

| 游戏 | 通关证据 | 真规则（一句话） | 主导原语（候选） | taxonomy 覆盖？ |
|------|----------|------------------|------------------|-----------------|
| **ar25** | reflect L1–L3 levels=3 | 沿轴反射补全 | **reflect** | ✅ A 族 |
| **ls20** | seated clear L1–L7 WIN | 移动 + 接触/盖印匹配 | **move + match** | ✅ E 族 |
| **ft09** | maskflip 全关 WIN | 点击翻转宏格 / GF(2) 目标 | **toggle**（maskflip） | ✅ E 族 |
| **m0r0** | seated clear L1–L6 WIN | 双块镜像/同向移动 + 贴合压缩 | **move + mate** | ✅ E 族 |

非 WIN、仅探路标注（不计入 1.5 验收，但作边界参考）：

| 游戏 | 探路主导 | taxonomy |
|------|----------|----------|
| r11l | waypoint + match | E 已列，未坐实 |
| tr87 | sequence + match | E 已列，未坐实 |
| vc33 | gravity | E 已列，未坐实 |

---

## 2. 逐游戏规则结构

### 2.1 ar25 → reflect

- **状态**：对象格 + 轴候选  
- **动作**：选择轴 → 反射写回  
- **过关**：输出网格与目标一致（levels++）  
- **原语**：`hypotheses/reflect.py`（score/cover/backproject）  
- **缺口**：无

### 2.2 ls20 → move + match

- **状态**：cursor、walkable、warps（hop/eject/portal）、fuel、armed、stamp/marker  
- **动作**：四向一步（含 warp 后处理）  
- **过关**：stamp 接触满足匹配 → `levels_completed++` / WIN  
- **原语映射**：
  - **move**：步进 + 能量 + 传送（实现于 `interactive/ls20.py`，非 `hypotheses/` cover 接口）
  - **match**：marker contact / stamp ov / unlock crush（同左）
- **工程 vs 规则**：L5–L7 用 recording 航点是 **closed-loop 工程 shortcut**，不新增原语；规则层仍是 move+match。  
- **接口缺口（记入 1.5，不阻塞覆盖判定）**：E 族尚未统一到 `score/cover/backproject`；ls20 用 interactive 状态机。阶段 2 组合前需决定：E 族用转移接口还是沿用 cover。

### 2.3 ft09 → maskflip（缺口）

- **状态**：宏格颜色场；点击 → 局部翻转 / XOR 邻域  
- **动作**：点选 `(x,y)`  
- **过关**：宏格匹配目标色（GF(2) 规划）→ levels++ / WIN  
- **实现**：`longquan/interactive/maskflip/`（`flip_block` / `xor_plus` / `xor_north` + induce + goal）  
- **taxonomy**：E 族现有 move/mate/match/sequence/gravity/waypoint —— **无一主导「点击翻转棋盘态」**  
  - 不是 move（无步进光标）  
  - 不是 match  alone（匹配是目标层；转移层是 flip/XOR）  
  - 接近「对称/模式」但动作是交互点击，应落在 **E 族新原语**

**拟补原语（名称待定，先记缺口）**：

| 候选名 | 含义 | 参数 | 验证游戏 |
|--------|------|------|----------|
| **toggle** / **maskflip** | 点击触发局部掩码翻转或线性（GF(2)）邻域效应 | 核形状 / XOR 邻域 | ft09 |

不把 ft09 硬贴成 match 或 recolor（违背「不硬凑」）。

---

## 3. 覆盖结论

| 检查项 | 结果 |
|--------|------|
| ar25 被 reflect 覆盖 | ✅ |
| ls20 被 move+match 覆盖 | ✅ |
| ft09 被现有原语覆盖 | ✅ 经补 **toggle** 后覆盖（实现=`maskflip`） |
| copy/recolor/translate 是否因 ls20/ft09「复活」 | ❌ 仍无主导验证游戏 |

**验收状态**：**通过（2026-09-08）**——ft09 缺口已以 E 族 **toggle** 补入 taxonomy，验证指针 → `interactive/maskflip/`（已 WIN）。ar25/ls20 覆盖不变。

遗留（不阻塞阶段 2 开工，记入 STATUS）：
- E 族尚未统一 `score/cover/backproject`
- fixtures / verify-games「ls20=copy」残留表述（fixtures README 已更正；execution-plan 等处仍有旧口径）

---

## 4. 收口动作（已做）

1. ✅ taxonomy E 族增加 **toggle**，验证游戏 = ft09 → `interactive/maskflip/`
2. ✅ m0r0 mate 坐实（库外，L1–L6 WIN）→ `interactive/m0r0.py` + `tools/m0r0_seated_clear.py`
3. 可选遗留见上「遗留」；下一库外关 = **r11l**
4. → 阶段 2 程序表示

---

## 5. 非目标（本阶段不做）

- ~~不并行坐实 m0r0/mate~~（已完成后移出）
- 不把 L5–L7 recording 航点「升格」为 waypoint 原语（除非另开可证伪假设）  
- 不重开 copy→ls20 假说
