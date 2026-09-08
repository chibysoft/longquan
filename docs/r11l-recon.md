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

## L3（部分坐实，未通关）

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
- 最佳未通关线：early-clear15 → 西廊两 hop → south 种 lead → **collapse y≤32 straggler** → lift → lead+lag；曾到船 **(29,34) d14≈45 bud≈2–3**。`r11l_l3_sync_probe` 本轮回归约 **(26,35) d14≈47 bud≈3**。
- 入场立刻 collapse→2wp 会烧预算且编队更差；颈口对 **y≤32** straggler 的 collapse **必要**（跳过会卡死东廊）。
- `west_south` 瘦身：**已停用**（易误 2wp + lead 独跳 GAME_OVER at y=33）。
- 忌：noop 连烧；y≤32 时东拉 → GAME_OVER；**lift 与 lead 同回合**易丢中段 wp；wave15 解封空转；`free_wps_for(15)` 偷 lead。

**2wp 最小探针**（`tools/r11l_l3_2wp_probe.py`，2026-09-09）：
- 成功门：船 x≥28 y≥34、free14==2、bud≥28、无 GAME_OVER。
- 已做到：hop1+plant 后 corridor 双点 + bud≈34；西绕浅点 `(19,24)→(14,24)→(14,32)`；曾压到 **n=2 bud≈23**（门限差 5）。
- 未过门：hazard 北浅点必须西绕再南；同列 merge `(14,32)→(14,34)` 易 noop；2wp 后乱 lift 会 GO。
- 纪律：gap>8 只拉 lag；整队同位移；y≥34 才东拉；noop 停。

**断点**：
1. 西+南+clear 后东廊常只剩 bud≈10–16，到 (29,34) 后 bud 耗尽，距目标仍 d14≈45 且 15 未动。
2. 4wp 东拉效率低；**2wp 长跨**：能成形但到东廊中段时 bud 常 <28。
3. 目标仍是 **东廊中段 2wp 且 bud≥28**（再谈通关与 15）。

下一刀：只收紧 2wp 探针（plant 避 x=14 叠柱；merge 用 cheb2–3 斜向靠；禁 2wp 后 noop-lift）。

## 选择器

`r11l.score_frame` 已实现；尚未挂入 `selector`。

## 下一步

L3 chrome14 收口；勿背罐头轨迹。
