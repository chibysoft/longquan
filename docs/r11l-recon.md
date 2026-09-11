# r11l 探路（waypoint + match）

> 2026-09-08 · 闭卷 · game_id=`r11l-495a7899` · win_levels=6  
> API：`/api/games/r11l` · tags=`click` · baseline=`[22,33,51,26,52,49]`

## 坐实（L1）

| 元素 | 帧语义 |
|------|--------|
| 动作 | 仅 **ACTION6** 点选 |
| 路径点 | 5×5 十字：闲置色 **3**、选中色 **0**（排除左栏步数条） |
| 飞船 | 色 **6** 芯 + chrome；中心 = 路径点中心均值 |
| 目标 | 同 chrome 色空心菱形；L1 心约 `(39,21)` |
| 墙 | 色 **2** |
| 通关 | 飞船 AABB 盖住目标 |

**L1 几何通关**：拖选中 wp → 选另一 → 再拖近目标。  
`python tools/r11l_seated_clear.py --max-levels 1` → PASS。

## 坐实（L2）

夹具：`tests/fixtures/r11l_l2_enter.json`（L1 后再点一次空白）。

| 坐实 | 要点 |
|------|------|
| 2 船 | chrome **12** @≈(24,12)；chrome **15** @≈(49,41) |
| 归属 | wp 子集质心匹配船芯（15 船 2wp；12 船 3wp） |
| 目标 | 同 chrome 菱形：12→(40,51)；15→(57,18) |
| 通关 | **两船同时**盖住各自目标 |
| 移动约束 | 新质心 5×5 踩墙/险区 → noop 或 GAME_OVER |
| 叠点 | 两 wp 中心 Chebyshev&lt;5 → 点击变选中而非移动 |
| 步数 | 左栏色0 计数 ≈ 剩余 ACTION6；L2 约 63，每次搬 wp ≈3 次点击 |
| 感知陷阱 | wp 落在船身 5×5 内会被船体像素盖住 → 检测丢失；垫点须在环上（cheb≥5） |
| 近距优先 | 先紧凑停 chrome15（锁其 wp），再迁 chrome12 |

**L2 通关策略**（已线上 PASS）：

1. `park_compact` chrome15（wp 落在目标近邻，避免挡北走廊）
2. `formation_migrate` chrome12：船身净空 BFS → 每 hop 环垫 + 落后 wp 地板大步；`nonlocked` 重同步；禁回退；盯预算
3. 末段 `park_compact` 盖目标

`python tools/r11l_seated_clear.py --max-levels 2` → PASS。  
实现：`tools/r11l_l2_clear_probe.py` · `tools/r11l_l2_core.py`。

## L3（chrome15 已通；chrome14 中东门已通）

夹具：`tests/fixtures/r11l_l3_enter.json`（L2 通关后帧，勿乱点空白）。

| 坐实 | 要点 |
|------|------|
| 2 船 | chrome **14**（4 wp）@≈(27,15)；chrome **15**（2 wp）@≈(44,37) |
| 目标 | 14→(55,53)；15→(34,57) |
| 通关 | 两船同时盖住各自目标 |
| 险区 | 色10 大片；15 的净空路径先东再南，走廊极窄 |
| 步数 | L3 约 63；西廊两 hop 后稳定 bud≈32 |

**已通**：chrome15 用 `OFFS=((5,0),(5,6))` 同步；`clear_l3` 交错 leap14 / wave15（`tools/r11l_l3_sync_probe.py`）。  
**L2 回归**：2-wp 先 `park_compact`；3-wp 旧环垫；`formation_pads` 4-wp 强制足迹+禁 greedy 南冲。  
**L3 chrome14 进展**（2026-09-08 续 · Auto）：
- 西廊两 hop（max_moves=5）稳定到 **(18,28) bud≈32**；压到 4 会中途 wp-merge。
- **必先 `clear15_corridor`**：入场 (37,34) 封印；东撤到 (42,41)。勿 seal-jump（28→42）——线上会把 4wp 收成 1。
- **lead dx 上限 4–6**：dx≥8 同样丢西侧 wp；落地勿进封印 cheb≤5（会并进 15）。
- **浅北毒质心**：y∈[28,32] 钉船在 ~(20,32)；须 lift/north 到 y≥33 后东拉才合法。
- 入场立刻 collapse→2wp 会烧预算且编队更差；颈口对 **y≤32** straggler 的 collapse **必要**。
- 忌：noop 连烧；y≤32 时东拉 → GAME_OVER；**lift 与 lead 同回合**易丢中段 wp；wave15 解封空转。

**2wp 中东门 PASS** (`tools/r11l_l3_2wp_probe.py`，2026-09-09 · v67，复跑 bud=32)：
- 门：船 x≥28 y≥34、free14==2、bud≥28、非 GAME_OVER → **已过**。
- **成形**：reshape cap3 → plant `(26,36)+(20,36)` → collapse `(23,36)/(29,36)` → 2wp `(19,36)/(29,36)`，船 `(24,36)`，**bud≈37**。（旧 24/18 起步船仅 22，双移后卡 26。）
- **双移**：lead `+5→(34,36)` + lag same-row → 船 **(28,36)** n=2 **bud≈32**。
- **硬约束**：lead 单跳 +5 安全、≥+7 掉 flock；禁 lead-only/lead2 二次大跳；lag 不能越过船（同排/对角皆 noop 或夹死）；禁 plant `(28/30,36)`（collapse dead→GO）。
- **复跑**：`python tools/r11l_l3_2wp_probe.py`

**断点（2026-09-11 · Auto）**：西绕 y44 口袋已弃。**门后非 frog SE-ny** 已接入 `clear_l3`。
- **当前最佳（v68）**：**d15=0** ship15@(34,57)；**d14=26 / bud=4**（hold，不烧 S6048）。船14@(44,38) free=(60,38)+(60,44)。
- **关键**：`early-dock` = early15E 后立刻 fin15 + **(28,58)** → d15=0 bud≈17 再 SE；`fin15w→(28,58)`（非 28,56）。
- **S6048 / stack-east**：d14−1 耗 bud≈3 → bud=1 陷阱；d15=0 且 x60 走廊时跳过。
- **硬否**：post-S6044 南推多 noop；alt SE 均不如 baseline 走廊；单步 N6038 扫描未破 d14=25。

## 选择器

`r11l.score_frame` 已实现；尚未挂入 `selector`。

## 下一步

1. 在 bud≥8 的更早节点找南向出口，或 mid-east/SE 再省 ≥8 预算。  
2. N6038 dense scan（`_l3_n6038scan_probe`）继续找 d14<25。
