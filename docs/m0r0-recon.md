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
| **L1** | 水平贴合（合并为 10×5）+ **ACTION4** | `find_mate_path` 15 步；`levels=1`，n10 50→25 |
| **L1 另解** | 竖直叠放 + A1/A2 | 亦通 |
| **L2** | 避色8；水平贴合 + **ACTION4** | ~25 步；`levels=2`，n10 32→16 |
| **L2 注意** | 同关竖直叠放 + A1/A2 **未**升关 | 压缩只平移/拆开 |

过关后残留单块；下一 ACTION 刷出下一关双块。

### 代码

- `longquan/interactive/m0r0.py` — 独立运动学 / 避险 BFS / `find_mate_path`（偏水平+A4）
- `tools/m0r0_seated_clear.py` — 坐实清关
- 测：`tests/test_m0r0.py`（含 mate path）
- 夹具：`m0r0_l1_frame_live.json`、`m0r0_l2_spawn.json`、`m0r0_l3_enter_a*.json`

```bash
python -m pytest tests/test_m0r0.py -v
python tools/m0r0_seated_clear.py --max-levels 2
```

---

## 断点：L3

- 进入：L2 残留后 A1–4 均可刷出双 4×4（色9 标记 12px 出现）。
- 离线 BFS ≈2140 态：**无**正交贴合态（网格奇偶 + 中缝墙使 gap 最小为 4）。
- gap=4 时 A4 为空操作；色9 不可被块覆盖；随机 80 步无 `levels++`。
- baseline_actions L3≈203 → 可能是新机制，不是 L1/L2 的 flush+compress。

### L3 下一步假设

1. 非贴合 mate（隔一格 / 对角 / 对齐色9）  
2. A5/A6 在新锚点（色9 或中缝）  
3. 色9/其它色为可交互目标，需先「解锁」再贴合  

---

## 选择器

`select_family(m0r0_frame)=="mate"`
