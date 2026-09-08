# vc33 L1 可证伪假设

> 2026-09-09 · 闭卷 · 夹具：`tests/fixtures/vc33_l1_frame_live.json`  
> game_id=`vc33-5430563c` · win_levels=7 · RESET `available_actions=[6]`  
> 纪律：只认帧 / `available_actions` / 线上响应；不读引擎。

## 开局帧表面（观察）

| 元素 | 像素事实 |
|------|----------|
| 顶栏 | y=0 色 **7**；ACTION6 后 `(63,0)` 常→**4**（UI） |
| 色9 垫 | 上 `(60–63,24–27)`；下 `(60–63,32–35)` |
| 精灵 | 色 **4** 体 + 右侧色 **11** 强调带 |
| 梁缝 | 色5 梁中色 **11** @ `(38–39,28–31)` |

## 假设与裁决

| ID | 假设 | 裁决 | 依据 |
|----|------|------|------|
| H1 点选 | ACTION6 点特定对象才改棋盘 | **SUPPORTED** | 色9 有效；空白/精灵 noop |
| H2 定向位移 | 有效点击→固定轴受迫位移 | **SUPPORTED** | 上 +4x / 下 −4x |
| H3 四向移动 | A1–4 逐步平移 | **REFUTED** | 仅 `[6]` |
| H4 平移原语 | 点击指定目标格 | **REFUTED** | 空白不放置 |
| **H5 对齐通关** | 强调带与梁缝 **同 x 区间** ⇒ 过关 | **SUPPORTED** | 3×下垫后 accent `(38–39)`==gap；`levels` 0→1 |

脚本：`tools/vc33_recon_probe.py` · `tools/vc33_l1_clear_hunt.py` · `tools/vc33_l1_align_check.py`

## L2 增量裁决

| ID | 假设 | 裁决 | 依据 |
|----|------|------|------|
| H5 对齐通关 | accent 与同色梁缝 x 区间重合 ⇒ 过关 | **SUPPORTED** | accent14 `(28–29)`==gap14；`levels` 1→2 |
| H6 纯平移足够 | 只点 ±x 垫即可过关 | **REFUTED** | 连点 +x 卡在 accent≈20 |
| H7 环境垫开路 | Δsprite=0 但改 3↔0 的垫能解除右移阻塞 | **SUPPORTED** | y24 与 y44 交替后可到 x=28；y16 易堵死 |

脚本：`tools/vc33_l2_unblock_hunt.py` · `tools/vc33_l2_clear_confirm.py`

## L3 增量裁决

| ID | 假设 | 裁决 | 依据 |
|----|------|------|------|
| H8 竖直对齐 | 三 accent 的 y 与同色 gap y 重合 ⇒ 过关 | **SUPPORTED** | 全对齐时 `levels` 2→3 |
| H9 仅水平垫 | L3 仍是 ±x 冲量 | **REFUTED** | 垫为 ±y（步长 2） |
| H10 开路垫 | 环境垫解除竖直阻塞 | **SUPPORTED** | env24 后 pad12 可再上移；错序易 GAME_OVER |

脚本：`tools/vc33_l3_pad_map.py` · `tools/vc33_l3_clear_v5.py`
