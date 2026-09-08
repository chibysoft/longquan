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
| 步数 | L3 约 63；停 15 约耗 25，留给 14 偏紧 |

**已通**：chrome15 用固定东侧偏移 `OFFS=((5,0),(5,6))` 同步平移整条细路径 → 稳定停在目标（`tools/r11l_l3_sync_probe.py`）。  
**断点**：chrome14 四 wp；默认净空先西绕，编队/sync 易丢 wp 或 `centroid_path_ok` 卡死；预算不足。

下一刀：给 14 做「目标距离加权」净空 / 或 4-wp 可行偏移全路径 sync；控制停 15 后预算 ≥45。

## 选择器

`r11l.score_frame` 已实现；尚未挂入 `selector`。

## 下一步

L3 chrome14 收口；勿背罐头轨迹。
