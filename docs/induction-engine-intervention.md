# 状态机归纳引擎 · 方向 2 落地：观测 → 干预

> 接 `induction-engine-real-evidence.md` 的「下一步·第 2 条」。
> 日期 2026-09-11。诚实口径：本文区分「已坐实的相关」与「探针要坐实的因果」。

---

## 为什么纯观测不够

`induction-engine-real-evidence.md` 的三次证伪，根因是**观测模型建在流沙上**：
图例（左下角色12↔9）被我当成门锁，实为调色板 UI。随后方向 2 的时序分析又
挖出一条**推翻整个框架的硬事实**：

> **armed 是常态，不是目标。** mover 脚下 color9 全程 15–18 像素（carrying
> 渲染），lingjingsolo WIN 录屏 309 帧里 **0 帧 carrying==0**。mover 从出生到
> WIN 一直 carrying。

这意味着过去整条「找武装步骤 / 找解锁对象」的主线是错的——ls20 里「武装」
不作为变量存在。**真变量 = stamp gate 是否可进**（L1/L2 直接可进，L3+ 需先
压环）。

但问题来了：录屏只有**一条成功轨迹**（压环 → 过关），这只能证明**相关**，
看不到反事实——「不压环会怎样」没有发生。要坐实「压环是 gate 可进的必要
前置」，必须**主动干预**：回放到 gate 前，故意不压环，看 levels 是否真卡住。

这就是本文（方向 2 落地）的核心：**因果靠干预坐实，不靠观测推断**。

---

## 干预探针：成对反事实对照

`tools/ls20_l4_intervention_probe.py`。对每个候选解锁动作 X，跑**一对** trial：

| trial | 动作序列 | 判据 |
|-------|----------|------|
| **control** | L4 开局 → 直接 armed stamp | levels 变不变？ |
| **intervention** | L4 开局 → 执行 X → armed stamp | levels 变不变？ |

只有 `control` 卡住（levels 不变）而 `intervention` 过关（levels +1），才算
坐实「X 是必要前置」。若 `control` 直接过关，则「解锁」假设被推翻——gate
本来就可进。

三个候选干预动作（对应之前 hypotheses 里最可能的解锁机制）：

- `control` — 不干预（基线）
- `crush` — 压环（`_plan_crush`：unarmed 到相邻格 + 一步 armed 进 armed-only 环）
- `contact` — marker 接触（`_plan_to_contact`：曾假设的「武装接触」）

**判据只信 levels**（红线 3：线上实测，不看「像素像不像」）。中间快照
`_gate_walk`（gate 格、unlock_cands、stamp_c9）只作辅助定位，不作通过判据。

---

## L4 已知机制（相关，非因果）

`ls20_seated_clear_full.py` 的 L4 过关已坐实**相关**：

1. 压环（`unlock` = ring crush，`(6,6)` 环，经 `(7,5)` eject 建模后可达）
2. `plan_two_phase`（contact + H23）**失败**——被挡
3. fallback → `need_udd47`（L4 特有 UDD 仪式：UP 到 marker + DOWN 回 `(4,7)`）
4. → armed stamp 过关

关键注释：`L4: unlock (=ring crush) IS arming`。但这仍是一条**成功轨迹**，
「压环是否必要」没做反事实。干预探针补的就是这一刀。

---

## 尚未坐实（探针要回答的）

1. **压环是否必要**：control（不压环直接 stamp）是否卡住？
2. **UDD 仪式是否冗余**：crush（只压环不仪式）是否已够过关？若够，UDD 仪式
   不是解锁，只是让 mover 回到正确落点。
3. **contact 是否解锁**：contact（碰 marker 不压环）能否让 gate 可进？

---

## 下一步

1. 本机跑 `python tools/ls20_l4_intervention_probe.py`（需 `ARC_API_KEY` 环境
   变量 + 线上 `three.arcprize.org`）。VM 里无法跑线上。
2. 依对照结果：坐实哪一刀、推翻哪一刀，回写 `STATUS.md` 与 hypotheses。
3. 坐实后的规则（例：「压环 → gate 可进」）才是**真规则**，可喂给归纳引擎
   作为一条**可证伪的原语**，而非表面颜色特征。

---

## 工程债备忘（第 4 次）

VM `python -c "import ..."` 报 `move.py:73 SyntaxError: '[' was never closed`，
但 D:\ 直连 Read 确认该行完整 `__all__ = ["score", "actions", "step", "done"]`。
又是 FUSE 截断（第 4 次同款）。**收口判定仍以 Windows D:\ 直连为准，VM 报错
仅供参考。**
