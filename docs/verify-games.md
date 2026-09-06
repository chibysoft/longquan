# 验证游戏探路结论（translate / recolor / copy）

> 2026-09-05 · Longquan 龙泉 · 推进核探路输出（含线上实测 + 引擎源码逆向）
> 目的：给 dev-task-spec.md 的「前置输入」填上「游戏→原语」映射
> 方法：读官方引擎源码（设计期「考前复习」）标规则机制；线上实测坐实；**不读源码作运行时输入**

---

## 0. 结论一张表（第三版，copy 也被源码逆向修正）

| 原语 | 验证游戏 | 置信度 | 判定依据 | 状态 |
|------|---------|--------|---------|------|
| reflect 反射 | **ar25** | ✅ 已验证 | 对象关于镜像轴反射 | L1-L3 已通关，收口 |
| copy 复制 | ❌ 暂无 | — | 原候选 ls20 实为「移动+匹配」 | **撤回，未验证** |
| recolor 变色 | ❌ 暂无 | — | 原候选 m0r0 实为「移动配对」 | 撤回，未验证 |
| translate 平移 | ❌ 暂无 | — | 原候选 vc33 实为「重力/点选」 | 撤回，未验证 |

**唯一坐实的是 reflect → ar25。** 经典网格变换四族里的 translate/recolor/copy 三者在 25 款里都没有「主导原语」的游戏。

---

## 1. 重大发现：ARC-AGI-3 是「交互式引擎」，不是「网格变换题」

这是这次探路最关键的结论，比「哪个游戏对应哪个原语」更重要。

经典 ARC（Chollet 原始 benchmark）是「输入网格 → 输出网格」的**变换题**：translate/recolor/copy/reflect 都是网格变换原语。但 ARC-AGI-3 的「游戏」是**实时交互引擎**，逐个源码逆向后发现，多数游戏的主导机制落在「网格变换」之外：

| 游戏 | 主导机制（源码逆向） | 属于「网格变换」？ |
|------|---------------------|:---:|
| ar25 | 镜像反射 | ✅ reflect |
| ls20 | 移动光标 + 形状/颜色/旋转匹配 + 盖印 | ❌ move/match |
| r11l | 路径点拖动 + 目标匹配 | ❌ 交互/匹配 |
| m0r0 | 移动块使同色配对消失 | ❌ 移动/配对 |
| cd82 | 移动篮子收集/填充 | ❌ 移动/收集 |
| tr87 | 形状序列匹配 + 颜色重映射动画 | ❌ 序列/匹配 |
| g50t | 移动角色 + 躲避障碍 | ❌ 动作/躲避 |
| vc33 | 点选 sprite 触发重力移动 | ❌ 重力/物理 |

**含义**：经典网格变换原语（reflect/translate/recolor/copy）里，**只有 reflect 在 25 款里能找到「主导原语」的真实游戏**；translate、recolor、copy 都没有对应的纯验证游戏——因为 ARC-AGI-3 的真实规则分布，重心已经整体偏离经典 ARC 网格变换。

---

## 2. 三个候选为何被推翻（线上实测 + 源码证据）

三次**同源误判**：都栽在「看到表面线索就下结论」，没深挖 `step()` 的真实规则。

### recolor → m0r0（原假设错）

- 表面线索：每关 `data["psqw"]=[color1,color2]`、render 里双色填充、step 里大量 `color_remap`。
- 线上实测：m0r0 帧色 {5,10,11,12}，发 ACTION6 点画面中心无任何帧变化（diff=0）。
- 源码真相：`step` 里 `color_remap(None, 1/9/11/10)` 只是**选中/碰撞的视觉反馈**，不是规则。真规则是**移动块使同色块重合配对消失**（`fvqnbtefro` 里 `len==2` 则 INTANGIBLE 消除），ACTION1-4 是方向移动。
- 结论：m0r0 是「移动 + 配对」游戏，不是 recolor。

### translate → vc33（原假设错）

- 表面线索：每关 `data["Gravity"]=[dx,dy]`。
- 源码真相：`step` 里 ACTION6 是**点选 sprite**，触发重力/下落/位移动画，不是「对象整体平移 (dx,dy)」。Gravity 是环境物理参数，不是规则原语。
- 结论：vc33 是「重力/点选」游戏，不是 translate。

### copy → ls20（原假设错，第三版新增）

- 表面线索：ls20 源码里大量 `clone().set_position()`（如 `ihdgageizm` 色4块铺了 100+ 个），我据此判「copy 主导」。
- 源码真相：那些 `clone().set_position()` 是**静态场景铺设**（墙/地板/边框），不是「复制规则」。真正的运行时规则在 `step()`：
  - ACTION1-4 = 方向移动光标；
  - `pbznecvnfr()`（过关判定）= 光标到达目标槽 `rjlbuycveu`（色5的5×5块，tag `rjlbuycveu`）且当前携带的形状/颜色/旋转匹配 `data` 里的 GoalShape/GoalColor/GoalRotation → 消除目标槽。
  - 这是 **move + match**，不是「复制 N 份」。
- 额外证据：L1 的色 11 不是目标，是**步数进度条 UI**（`step` 里 `frame[61:63, 13+i] = 11 if 剩余 else 3`）。我之前把「13 个色 11 格」误当「13 个目标槽」，实为进度条 42 段里已用的 13 段。目标槽 L1 只有 1 个。
- 结论：ls20 是「移动 + 匹配」游戏，不是 copy。

**三个误判的同源教训**：`color_remap`、`Gravity`、`clone().set_position()` 都是「渲染/场景」层面的表面线索，不是「规则」。判断规则必须读 `step()`/`on_action()` 的运行时逻辑。这也是为什么探路要「线上实测 + 源码逆向」双管齐下——单看帧或单看数据键都会误判。

---

## 3. 这对后续意味着什么

**核心结论**：经典网格变换四族里，**只有 reflect 有真实主导游戏（ar25）**；translate/recolor/copy 三者在 25 款里都没有主导游戏。ARC-AGI-3 的真实规则重心是**交互族**（move/mate/match/sequence/gravity/waypoint）。

因此方向明确：

1. **第一批收缩为 reflect（唯一真坐实）**。copy 撤回「未验证」，与 recolor/translate 并列——遵守红线 2 与「不硬凑验证游戏、宁留未验证不造假」的纪律。
2. **原语全集加交互族**（E 族 move/mate/match/sequence/gravity/waypoint），这才是 25 款的真实规则分布。
3. **下一个目标 = 交互族坐实**：move/mate/match 的 cover/backproject（或更合适的转移接口）语义设计 + 用 m0r0/r11l/tr87/ls20 等已标主导原语的游戏做验证。

---

## 4. 已坐实、可继续的：reflect → ar25

本次探路唯一确定的净收益：

- **reflect 主导**：ar25 是「对象关于镜像轴反射」，reflect 是主导原语。
- **红线合规**：用 reflect 原语从帧出发解 ar25，不碰罐头。
- **状态**：L1-L3 已通关，收口，作范本。

其余原语（translate/recolor/copy）的验证游戏，待交互族坐实后，从真实规则分布重新评估——不硬凑。

---

## 5. 已落地 / 待办

- [x] 方向 B（扩充交互族）已拍板。
- [x] primitives-taxonomy.md 加 E 族，全集 23 原语。
- [x] dev-task-spec.md 第一批收缩为 reflect+copy，撤掉 recolor/translate。
- [x] ls20 真实帧样本固化进 tests/fixtures/（`ls20_l1_frame.json` + README）。
- [x] **copy 的 ls20 坐实被源码逆向推翻**（2026-09-05 第三版）：ls20 = move+match，copy 撤回未验证。
- [ ] 纠正 fixtures README 的 ls20 规则描述（copy 主导 → move+match 主导）。
- [ ] 纠正 dev-task-spec.md（copy 任务撤回，第一批只剩 reflect）。
- [ ] 交互族（move/mate/match）接口语义设计 + 坐实（下一个认知活）。

---

## 6. 一句话

**ARC-AGI-3 是交互式引擎，不是网格变换题——25 款里多数游戏的主导机制（移动配对、序列匹配、重力、路径点、移动匹配）落在经典 ARC 网格变换原语之外。** 经典四族里只有 reflect(ar25) 有真实验证游戏；translate/recolor/copy 三次探路全被源码逆向推翻（表面线索 color_remap/Gravity/clone 都是误导，深挖 step() 才见真规则）。方向 = 收缩到 reflect，扩充交互族并坐实 move/mate/match。
