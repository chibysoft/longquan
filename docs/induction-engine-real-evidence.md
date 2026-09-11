# 状态机归纳引擎 · 首次实战（接真实数据）

> 引擎反向验证（tests/test_induction.py）用的是**手写证据**。本文记录把引擎
> 接上**真实录屏**（lingjingsolo WIN recording）后，第一次真正跑起来的结论。
> 日期 2026-09-11。

## 做了什么

1. `longquan/induction/ls20_extract.py` —— 桥：把 ls20 渲染帧提取成结构化
   `State`（特征 + 目标），复用探针里已经跑通的提取逻辑（`_gate_walk` /
   `_has_plus_marker`），让「探针」和「引擎」共享同一套特征定义。
2. `tools/ls20_induct_l4.py` —— 回放录屏 → 逐帧 `extract_state` → 建
   `Transition` → 喂 `Inducer`，攻击真正的 L4。
3. `evidence.Transition` 加了 `target` 字段：同一个引擎既能攻「完成」目标
   （`gate_u`），也能攻「解锁」目标（`legend_unlocked`），不再写死目标。
4. `evidence.FEATURES` 增补三个真实 plane 级信号：`legend_locked`（图例锁）、
   `total_c9`（相位质量）、`stamp_c9`（盖章槽内色9「锁」字形）。

## 结果（诚实口径）

### 发现一：目标 `gate_u` 是退化的

引擎在 308 条真实 Transition 上穷举 12 万条规则**全否证**。原因：ls20 的
「gate」格设计上就是 armed-only（必须 armed 才能盖印），所以 `gate_u` 每关
只在 `levels_completed` 递增**那一帧** False→True——它等价于「这关做完了」，
不是关卡中段的「解锁」子事件；翻点前帧与几十个中段普通帧特征同构。

### 发现二：图例翻转（legend flip）才是真解锁信号

沿 E7 的线索（「24px color12→color9」），我直接在录屏上验证了**左下角 UI 图例**
（y≥54 chrome 区）的行为，每关都干净地发生两次翻转：

| 关 | locked（图例=色12） | unlocked（图例=色9） |
|---|---|---|
| L2 | idx 58 | idx 74（压环） |
| L3 | idx 111 | idx 113 |
| L4 | idx 140 | idx 148 |
| L5 | idx 213 | idx 217 |
| L6 | idx 256 | idx 266 |

图例锁 = 色12，解锁 = 色9，这是一个**单帧可观测、每关一致**的状态变量。
`legend_unlocked`（图例翻成色9）的 False→True 就发生在压环那一帧——正是
route 1 证明缺失的那个真变量。

### 发现三：但引擎对 `legend_unlocked` 也找不到规则

把 `legend_unlocked` 作目标，引擎仍穷举 12 万条全否证。这不是引擎坏，而是
**解锁的触发是「位置性」的**：压环 = armed mover 进入 armed-only 格 (5,9)。
这个「mover 当前在哪个格、是否贴着解锁对象」是当前特征表**没有**的观测量。
`legend_locked` 本身只是「结果状态」，不是「触发条件」。

## 结论：诊断从「缺一个特征」精确到「缺位置/邻接特征」

| 信号 | 性质 | 可归纳性 |
|---|---|---|
| `gate_u` | 完成代理，每关完成时翻一次 | 退化 |
| `legend_locked` / `legend_unlocked` | **真解锁状态**，压环帧翻转 | 可作为目标，但触发条件缺失 |
| cursor / 邻接 armed-only 格 | **触发条件**（mover 在 (5,9) 压环） | **缺失，route 2 下一步** |

引擎「找不到规则」的两次输出都是**正确且诚实**的：第一次证明目标退化，第二次
证明触发条件是位置性的、落在当前特征空间之外。

## 下一步

- **route 2（继续）**：加「cursor 位置」+「cursor 是否/能否一步进入 armed-only
  格」作为特征。压环规则 =「mover 进入 armed-only 解锁对象格」——有了邻接特征，
  引擎应能重导出 `armed_only_nonempty AND 邻接解锁对象 → legend 翻转`。
- route 3（工程债）：FUSE 中文挂载抖动已第 4 次咬人（VM 里 `ls20.py` 被截断成
  101 行 vs D:\ 直连 545 行）。本次结论全部在 VM 内联提取复算，收口以 Windows
  D:\ 直连为准。
