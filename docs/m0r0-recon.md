# m0r0 探路（move+mate）

> 2026-09-08 · 闭卷 · game_id=`m0r0-492f87ba` · win_levels=6  
> API：`/api/games/m0r0`

---

## 已坐实

### 运动学（全关共用骨架）

| 事实 | 证据 |
|------|------|
| 双色10块；色5地板 | `locate_pieces` |
| 墙：L1=11/12；L2+=6/15 | 帧 uniq |
| 色8=危险格：可踩，但**踩着再动会软重置** | 线上 y38 带任意 A1–4 → 传回近出生点 |
| ACTION1–4：镜像意图、**独立**落地（一方堵另一方仍可动） | `[1,1]` 仅左上移；模型对齐 |
| `piece_w = step`；过关后可变（L1:5，L2:4） | `infer_params` |

### Mate（过关）

| 关 | 触发 | 路径例 |
|----|------|--------|
| **L3** | 挪开 2×2 色9 障碍后水平贴合+A4 | seated_clear；n10 32→16 |
| **L4** | 挪开 **3×3** 色9（step=5）后水平贴合+A4 | seated_clear；选中态色11与墙同色，靠紧凑块识别 |
| **L5** | 黄金态破守恒→右按 c12 垫→左穿门→顶缝贴合+**A3** | `clear_l5`；live A3/A4 对调 |
| **L6** | 垫 HOLD+桥→底带 h-merge→**A1 离垫**→**A3** | `clear_l6`；Y 同向；垫上压不过 |

过关后残留单块；下一 ACTION 刷出下一关双块。

### L3/L4 标记机制

| 事实 | 证据 |
|------|------|
| A6 点色9 → 选中；棋子→色1 幽灵 | 线上 |
| A1–4 驾驭标记（step=piece_w）；A6 点幽灵落子 | 线上 |
| 色9 挡棋子配置空间；挪到解锁落点后 `find_mate_path` 恢复 | 消融+线上 |
| L4 墙亦为色11：用边长 2–5 的紧凑色11 块识别选中标记 | `selected_marker_bbox` |

### 代码

- `longquan/interactive/m0r0.py` — 独立运动学 / 避险 BFS / `find_mate_path` / 标记驾驭
- `tools/m0r0_seated_clear.py` — 坐实清关（标记挪开 + 闭环 mate）
- 测：`tests/test_m0r0.py`
- 夹具：`m0r0_l1_frame_live.json`、`m0r0_l2_spawn.json`、`m0r0_l3_enter_a*.json`、`m0r0_l4_enter.json`

```bash
python -m pytest tests/test_m0r0.py -v
python tools/m0r0_seated_clear.py --max-levels 6
```

---

## L5（已通关）

详设：`docs/m0r0-l5-hypotheses.md`。`clear_l5` 写入 `tools/m0r0_seated_clear.py`。

| 坐实 | 要点 |
|------|------|
| 布局 | 6\|7 分缝；色15 右桥；色12/14 左门；无色9 |
| 运动 | **live A3=内收、A4=外扩**（相对 L1–4 模型对调） |
| 压力板 | HOLD：色15 开右桥；c12/c14 垫开左门 |
| 通关 | 黄金 `(10,42)+(58,26)` → A1 穿门 → 顶 `(26,6)|(30,6)` 贴合 → **A3** 压缩 |

夹具：`tests/fixtures/m0r0_l5_enter.json`。

---

## L6（已通关）

详设：`docs/m0r0-l6-hypotheses.md`。`clear_l6` 写入 `tools/m0r0_seated_clear.py`。

| 坐实 | 要点 |
|------|------|
| 布局 | 色8 险区；色9 一块；c12/c14 垫开 BR12/BR14 |
| 运动 | **Y 同向**；X 镜像同 L1–4（A3 外扩 / A4 内收） |
| 通关 | 底带水平合并 `(18,42,25,45)` → **A1 离垫** → **A3** 压缩（垫上压不动） |

夹具：`tests/fixtures/m0r0_l6_enter.json`。`seated_clear --max-levels 6` → WIN。

---

## 选择器

`select_family(m0r0_frame)=="mate"`
