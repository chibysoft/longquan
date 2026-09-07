# 结构归纳（ft09 / 路径B）

> 2026-09-07 · 从人工探路切换到「转移原语 + 样例诱导 + 目标 GF(2)」  
> 红线：不读源码、不背罐头点击表、通关只认 `levels_completed` / `state=WIN`

## 两层模型（必须拆开）

```
样例 (before, click, after)
        │
        ▼
  induce_transition  ──►  TransitionProgram.predict(frame, xy)
                              （flip_block / xor_plus / xor_north / branch_appearance）

关卡真帧
        │
        ▼
  decode_l4_like_targets  ──►  want[block]=color
        │
        ▼
  plan_clicks_gf2(effect_fn)  ──►  点击序列 ──► levels+1
```

| 层 | 回答的问题 | 不是 |
|----|------------|------|
| **转移** | 点一下棋盘怎么变？ | 通关要点哪里 |
| **目标** | 宏格 0/2/3 要什么终态？点哪些算子？ | 点击的像素副作用细节 |

**禁止**把 L5 写成 `if macro==0: flip elif macro==2: xor`——宏格编码目标色，不算子选择。

## 已实现模块

| 路径 | 作用 |
|------|------|
| [`longquan/interactive/maskflip/`](../longquan/interactive/maskflip/) | `flip_block` / `xor_plus` / `xor_north` + `induce` + `goal` |
| [`tools/ft09_extract_click_samples.py`](../tools/ft09_extract_click_samples.py) | 从 fixture 合成样例并诱导转移程序 |
| [`tools/ft09_maskflip_clear.py`](../tools/ft09_maskflip_clear.py) | 库规划线上通关（L5+L6→WIN） |
| [`tests/test_maskflip.py`](../tests/test_maskflip.py) | 离线单测 + 诱导 holdout + GF(2) 对齐探针 |

## 转移原语

| 原语 | `step` |
|------|--------|
| `flip_block` | 一块内色对互换（装饰色保留） |
| `xor_plus` | 十字邻域 XOR；字形臂跳过 |
| `xor_north` | 自身 +（若正北同类）北邻 |

接口：`score` / `step(grid, xy, param)` / `backproject(before, after)`。

## 诱导结果（离线）

`python tools/ft09_extract_click_samples.py` →

- L5：`branch_appearance`（complexity=2），holdout OK  
- L6：`xor_north`（complexity=1），holdout OK  

见 `tests/fixtures/ft09_induced_transition.json`。

## 目标层

- `decode_l4_like_targets`：`0→fixed`，`2→other`，`3=skip`  
- `plan_clicks_gf2` + `effect_l5_solid_and_checker` / `effect_xor_north`  
- 与探针 `plan_l5_gf2` / `plan_l6_gf2` 点击集一致（单测钉死）

## 线上验收

```bash
python -m pytest tests/test_maskflip.py -q
python tools/ft09_extract_click_samples.py
python tools/ft09_maskflip_clear.py    # → state=WIN, levels=6
```

报告：[`docs/ft09-maskflip-clear-report.md`](ft09-maskflip-clear-report.md)  
全关背景：[`docs/ft09-full-clear-report.md`](ft09-full-clear-report.md)（**无 L7**，`win_levels=6`）

## 与路径A关系

L1–L6 探针脚本是路径A遗产，提供 fixture / 监督信号。路径B 用同一事实进库，**通关规划走 `maskflip` 库**，不再为新关写坐标表。

## 下一步（可选）

- 把 L4 `toggle_cycle` 补进转移原语，诱导三态  
- 选择器：`score` 在 maskflip vs move/match 间分流  
- 回到 ls20 L3 武装（主关键路径）
